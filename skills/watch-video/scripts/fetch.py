#!/usr/bin/env python3
"""Get a video's metadata, captions, and media into a workdir.

    python3 fetch.py meta <url-or-file> [--from 10:00] [--to 20:00] [--cookies-from-browser chrome] [--force]
    python3 fetch.py captions <workdir> [--lang en]
    python3 fetch.py media <workdir> --audio | --video

`meta` creates the workdir (keyed by video ID, so a second run reuses it) and
writes metadata.json. Later steps read file paths from metadata.json, never
from a guessed name like video.mp4.
"""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv", ".m4v", ".avi", ".mp3", ".m4a", ".wav", ".aac", ".ogg", ".flac"}

SOURCES = [
    ("youtube", ("youtube.com", "youtu.be", "youtube-nocookie.com")),
    ("loom", ("loom.com",)),
    ("vimeo", ("vimeo.com",)),
    ("riverside", ("riverside.fm", "riverside.com")),
    ("zoom", ("zoom.us",)),
    ("x", ("x.com", "twitter.com")),
    ("instagram", ("instagram.com",)),
    ("tiktok", ("tiktok.com",)),
]

SOCIAL = {"x", "instagram", "tiktok"}

# yt-dlp errors that mean "stop and tell the user", never "upgrade and retry".
ERROR_CLASSES = [
    ("bot_check", r"confirm you.re not a bot|Sign in to confirm you"),
    ("private", r"Private video|members-only|Join this channel|Sign in to confirm your age|login required|requires authentication|This video is only available"),
    ("unavailable", r"Video unavailable|has been removed|does not exist|HTTP Error 404|account associated with this video has been terminated"),
    ("geo", r"not available in your country|geo.?restrict"),
    ("network", r"Temporary failure in name resolution|Name or service not known|nodename nor servname|Connection refused|Network is unreachable|timed out|Tunnel connection failed|ProxyError|Unable to connect|Connection reset|getaddrinfo failed|CERTIFICATE_VERIFY_FAILED"),
    ("unsupported", r"Unsupported URL"),
]

MESSAGES = {
    "bot_check": ("The site asked for a sign-in to prove this is not a bot. This usually means the network is a datacenter or shared IP.",
                  "On your own computer, retry with --cookies-from-browser chrome (or safari, firefox). In a cloud sandbox, upload the video file instead, or run the download on your own computer and hand the file back."),
    "private": ("The video is private, members-only, or needs a login.",
                "On your own computer, retry with --cookies-from-browser chrome (or safari, firefox) while logged in. Sandboxes have no browser profile, so upload the file instead."),
    "unavailable": ("The video is unavailable or was removed.", None),
    "geo": ("The video is blocked in this region.", "Upload the file, or download it from a computer in a region where it plays."),
    "network": ("This environment cannot reach the video site.",
                "Upload the video file here, or run the download on your own computer and hand the file back."),
    "unsupported": ("yt-dlp does not support this URL.", "Download the video another way and pass the file path."),
}


def classify(stderr):
    for name, pattern in ERROR_CLASSES:
        if re.search(pattern, stderr, re.IGNORECASE):
            return name
    return "extractor"


def ytdlp_path():
    path = common.find_tool("yt-dlp")
    if not path:
        common.fail("yt-dlp is not installed.", fix=common.install_hint("yt-dlp"))
    return path


def upgrade_ytdlp(path):
    """One upgrade attempt, using whatever installed it."""
    real = os.path.realpath(path)
    if "Cellar" in real or real.startswith("/opt/homebrew") or real.startswith("/usr/local/Homebrew"):
        cmd = ["brew", "upgrade", "yt-dlp"]
    elif str(common.venv_dir()) in real:
        cmd = [str(common.venv_python()), "-m", "pip", "install", "--upgrade", "--quiet", "yt-dlp"]
    elif "/uv/tools/" in real and shutil.which("uv"):
        cmd = ["uv", "tool", "upgrade", "yt-dlp"]
    else:
        cmd = [path, "-U"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def run_ytdlp(args, cookies=None, timeout=900):
    """Run yt-dlp. On an extractor error, upgrade once and retry."""
    path = ytdlp_path()
    extra = ["--cookies-from-browser", cookies] if cookies else []
    upgraded = False
    while True:
        try:
            r = subprocess.run([path] + extra + args, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            common.fail("yt-dlp did not finish in %d seconds." % timeout,
                        fix="Run the same command again. Finished steps are cached.")
        if r.returncode == 0:
            return r.stdout
        kind = classify(r.stderr)
        if kind == "extractor" and not upgraded:
            upgraded = True
            common.warn("yt-dlp failed; upgrading it once and retrying")
            if upgrade_ytdlp(path):
                continue
        msg, fix = MESSAGES.get(kind, ("yt-dlp failed.", "Check the URL. If it plays in a browser, try again later."))
        common.fail(msg, fix=fix, kind=kind, detail=r.stderr.strip().splitlines()[-1][:300] if r.stderr.strip() else "")


def detect_source(url):
    host = (urlparse(url).hostname or "").lower()
    for name, domains in SOURCES:
        if any(host == d or host.endswith("." + d) for d in domains):
            return name
    return "web"


def normalize_input(raw):
    raw = raw.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", raw) and not Path(raw).exists():
        return "https://www.youtube.com/watch?v=" + raw
    return raw


def youtube_id(url):
    p = urlparse(url)
    if p.hostname and p.hostname.endswith("youtu.be"):
        return p.path.strip("/").split("/")[0] or None
    if "/shorts/" in p.path or "/live/" in p.path or "/embed/" in p.path:
        return p.path.rstrip("/").split("/")[-1]
    return (parse_qs(p.query).get("v") or [None])[0]


def clip_suffix(clip):
    if not clip:
        return ""
    def part(v):
        return str(int(v)) if v is not None else "end"
    return "-clip%s-%s" % (part(clip.get("start") or 0), part(clip.get("end")))


def first_paragraph(text, limit=600):
    text = (text or "").strip()
    return text.split("\n\n")[0][:limit]


def track_langs(tracks):
    return sorted(k for k in (tracks or {}) if k != "live_chat")


def meta_from_ytdlp(info, url):
    chapters = [{"start": c.get("start_time"), "end": c.get("end_time"), "title": c.get("title")}
                for c in (info.get("chapters") or [])]
    upload = info.get("upload_date")
    if upload and len(upload) == 8:
        upload = "%s-%s-%s" % (upload[:4], upload[4:6], upload[6:])
    return {
        "id": info.get("id"),
        "title": info.get("title") or info.get("fulltitle") or "untitled",
        "uploader": info.get("uploader") or info.get("channel") or info.get("uploader_id"),
        "duration": info.get("duration"),
        "upload_date": upload,
        "description": first_paragraph(info.get("description")),
        "chapters": chapters or None,
        "language": info.get("language"),
        "webpage_url": info.get("webpage_url") or url,
        "extractor": info.get("extractor_key") or info.get("extractor"),
        "captions_available": {
            "human": track_langs(info.get("subtitles")),
            "auto": track_langs(info.get("automatic_captions")),
        },
    }


def find_sidecars(path):
    """Transcript files next to a local video (Zoom and Riverside export these)."""
    found = []
    folder = path.parent
    videos = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in VIDEO_EXTS]
    only_video = len(videos) <= 1
    for f in sorted(folder.iterdir()):
        if f == path or not f.is_file():
            continue
        if f.suffix.lower() not in (".vtt", ".srt", ".json", ".txt"):
            continue
        same_stem = f.name.lower().startswith(path.stem.lower())
        transcriptish = re.search(r"transcript|caption|subtitle|\.vtt$|\.srt$", f.name, re.IGNORECASE)
        if same_stem or (transcriptish and only_video):
            found.append(str(f))
    return found


def cmd_meta(args):
    cfg = common.load_config()
    base = common.output_base(cfg)
    raw = normalize_input(args.input)
    clip = None
    try:
        start, end = common.parse_time(args.start), common.parse_time(args.end)
    except ValueError as e:
        common.fail(str(e))
    if start is not None or end is not None:
        clip = {"start": start or 0.0, "end": end}

    local = Path(raw).expanduser()
    if local.exists():
        if local.is_dir():
            common.fail("%s is a folder. Pass a video file." % local)
        local = local.resolve()
        st = local.stat()
        vid = common.short_hash("%s:%s:%s" % (local, st.st_size, int(st.st_mtime)))
        key = "local-%s-%s%s" % (common.slugify(local.stem, 30), vid, clip_suffix(clip))
        workdir = base / key
        meta = common.read_json(workdir / "metadata.json")
        if meta and not args.force:
            meta["cached"] = True
            return meta
        duration = common.media_duration(local)
        if duration is None:
            common.fail("Could not read the duration of %s." % local,
                        fix="Check that it is a video or audio file, and that ffmpeg is installed: " + common.install_hint("ffmpeg"))
        meta = {
            "id": vid, "title": local.stem, "uploader": None, "duration": duration,
            "upload_date": None, "description": None, "chapters": None, "language": None,
            "webpage_url": None, "extractor": "local",
            "captions_available": {"human": [], "auto": []},
            "sidecar_transcripts": find_sidecars(local),
        }
        source, is_local = "local", True
        files = {"source": str(local), "video": str(local), "video_downloaded": False}
    else:
        if not re.match(r"https?://", raw):
            common.fail("%s is not a file that exists here or a URL." % args.input)
        source = detect_source(raw)
        is_local = False
        yid = youtube_id(raw) if source == "youtube" else None
        index = common.read_json(base / ".index.json", {})
        index_key = raw + clip_suffix(clip)
        known = index.get(index_key) or (yid and "youtube-%s%s" % (yid, clip_suffix(clip)))
        if known and not args.force:
            meta = common.read_json(base / known / "metadata.json")
            if meta:
                meta["cached"] = True
                return meta
        out = run_ytdlp(["-J", "--no-playlist", "--no-warnings", raw], cookies=args.cookies_from_browser, timeout=300)
        try:
            info = json.loads(out)
        except ValueError:
            common.fail("yt-dlp returned output that is not JSON.", detail=out[:300])
        if info.get("_type") == "playlist":
            count = info.get("playlist_count") or len(info.get("entries") or [])
            common.fail("This is a playlist with %s videos. watch-video handles one video per run." % count,
                        fix="Pass the URL of one video from the playlist.", kind="playlist", count=count)
        meta = meta_from_ytdlp(info, raw)
        key = "%s-%s%s" % (source, re.sub(r"[^A-Za-z0-9_-]", "", str(meta["id"]))[:40] or common.short_hash(raw), clip_suffix(clip))
        workdir = base / key
        old = common.read_json(workdir / "metadata.json")
        files = (old or {}).get("files", {}) if not args.force else {}
        index[index_key] = key
        base.mkdir(parents=True, exist_ok=True)
        common.write_json(base / ".index.json", index)

    workdir.mkdir(parents=True, exist_ok=True)
    if clip and meta.get("duration") and (clip.get("end") is None or clip["end"] > meta["duration"]):
        clip["end"] = meta["duration"]
    meta.update({
        "input": args.input,
        "source": source,
        "is_local": is_local,
        "is_social": source in SOCIAL,
        "clip": clip,
        "workdir": str(workdir),
        "slug": common.slugify(meta["title"]),
        "files": files,
        "cookies_from_browser": args.cookies_from_browser,
        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
    })
    common.save_metadata(workdir, meta)
    meta["cached"] = False
    return meta


def pick_track(meta, lang):
    """Human captions before auto, in the requested or the video's own language."""
    avail = meta.get("captions_available") or {}
    want = (lang or meta.get("language") or "en").lower()
    base = want.split("-")[0]

    def match(langs, prefer_orig=False):
        langs = list(langs)
        ordered = []
        if prefer_orig:
            ordered += [l for l in langs if l.lower() == base + "-orig"]
        ordered += [l for l in langs if l.lower() == want]
        ordered += [l for l in langs if l.lower() == base]
        ordered += [l for l in langs if l.lower().startswith(base + "-") and not l.lower().endswith("-orig")]
        return ordered[0] if ordered else None

    human = match(avail.get("human", []))
    if human:
        return human, "human"
    auto = match(avail.get("auto", []), prefer_orig=True)
    if auto:
        return auto, "auto"
    return None, None


def cmd_captions(args):
    meta = common.load_metadata(args.workdir)
    wd = Path(meta["workdir"])
    if meta["is_local"]:
        return {"status": "none", "reason": "local file; sidecar transcripts are read by transcribe.py",
                "sidecar_transcripts": meta.get("sidecar_transcripts", [])}
    cached = meta["files"].get("captions")
    if cached and Path(cached["path"]).exists() and not args.force and (not args.lang or cached["lang"].startswith(args.lang)):
        return {"status": "ok", "cached": True, **cached}
    track, kind = pick_track(meta, args.lang)
    if not track:
        meta["files"]["captions"] = None
        common.save_metadata(wd, meta)
        return {"status": "none", "reason": "no captions in the requested language", "available": meta.get("captions_available")}
    for old in wd.glob("captions.*"):
        old.unlink()
    flag = "--write-subs" if kind == "human" else "--write-auto-subs"
    run_ytdlp([flag, "--skip-download", "--no-playlist", "--no-warnings", "--sub-langs", track,
               "--sub-format", "vtt/srt/best", "-o", str(wd / "captions.%(ext)s"), meta["webpage_url"]],
              cookies=meta.get("cookies_from_browser"), timeout=300)
    got = sorted(p for p in wd.glob("captions.*") if p.suffix.lower() in (".vtt", ".srt", ".json3", ".ttml", ".srv3"))
    if not got:
        meta["files"]["captions"] = None
        common.save_metadata(wd, meta)
        return {"status": "none", "reason": "yt-dlp listed captions but downloaded none"}
    record = {"path": str(got[0]), "kind": kind, "lang": track}
    meta["files"]["captions"] = record
    common.save_metadata(wd, meta)
    return {"status": "ok", "cached": False, **record}


def cmd_media(args):
    meta = common.load_metadata(args.workdir)
    wd = Path(meta["workdir"])
    kind = "audio" if args.audio else "video"
    if meta["is_local"]:
        return {"status": "ok", "path": meta["files"]["source"], "downloaded": False}
    existing = meta["files"].get(kind)
    if existing and Path(existing).exists() and not args.force:
        return {"status": "ok", "path": existing, "downloaded": False, "cached": True}
    if kind == "audio" and meta["files"].get("video") and Path(meta["files"]["video"]).exists():
        return {"status": "ok", "path": meta["files"]["video"], "downloaded": False, "cached": True,
                "note": "video already downloaded; using it for audio"}
    if kind == "audio":
        fmt = "ba/b"
        merge = []
    else:
        fmt = "bv*[height<=720]+ba/b[height<=720]/b"
        merge = ["--merge-output-format", "mp4"]
    section = []
    clip = meta.get("clip")
    if clip:
        end = clip.get("end")
        section = ["--download-sections", "*%s-%s" % (clip.get("start") or 0, end if end is not None else "inf")]
    if not common.find_ffmpeg() and (kind == "video" or clip):
        common.fail("ffmpeg is needed to download %s." % ("a clip" if clip else "video"), fix=common.install_hint("ffmpeg"))
    ff = common.find_ffmpeg()
    ff_args = ["--ffmpeg-location", ff] if ff and not shutil.which("ffmpeg") else []
    out = run_ytdlp(["-f", fmt] + merge + section + ff_args +
                    ["--no-playlist", "--no-warnings", "--no-progress", "--print", "after_move:filepath",
                     "-o", str(wd / (kind + ".%(ext)s")), meta["webpage_url"]],
                    cookies=meta.get("cookies_from_browser"), timeout=1800)
    lines = [l for l in out.strip().splitlines() if l.strip()]
    path = lines[-1] if lines else None
    if not path or not Path(path).exists():
        matches = sorted(wd.glob(kind + ".*"))
        path = str(matches[0]) if matches else None
    if not path:
        common.fail("The download finished but no %s file was found in %s." % (kind, wd))
    meta["files"][kind] = path
    meta["files"][kind + "_clipped"] = bool(clip)
    if kind == "video":
        meta["files"]["video_downloaded"] = True
    common.save_metadata(wd, meta)
    return {"status": "ok", "path": path, "downloaded": True}


def captions_summary(meta):
    avail = meta.get("captions_available") or {}
    auto = avail.get("auto", [])
    return {"human": avail.get("human", []), "auto_count": len(auto),
            "auto_original": [l for l in auto if l.endswith("-orig")]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("meta")
    m.add_argument("input")
    m.add_argument("--from", dest="start")
    m.add_argument("--to", dest="end")
    m.add_argument("--cookies-from-browser")
    m.add_argument("--force", action="store_true")
    c = sub.add_parser("captions")
    c.add_argument("workdir")
    c.add_argument("--lang")
    c.add_argument("--force", action="store_true")
    d = sub.add_parser("media")
    d.add_argument("workdir")
    g = d.add_mutually_exclusive_group(required=True)
    g.add_argument("--audio", action="store_true")
    g.add_argument("--video", action="store_true")
    d.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if args.cmd == "meta":
        meta = cmd_meta(args)
        common.emit({"status": "ok", "cached": meta.pop("cached", False), "workdir": meta["workdir"],
                     "title": meta["title"], "source": meta["source"], "duration": meta["duration"],
                     "language": meta.get("language"), "is_social": meta["is_social"],
                     "captions_available": captions_summary(meta),
                     "sidecar_transcripts": meta.get("sidecar_transcripts", []),
                     "clip": meta.get("clip")})
    elif args.cmd == "captions":
        common.emit(cmd_captions(args))
    else:
        common.emit(cmd_media(args))


if __name__ == "__main__":
    common.run_main(main)
