#!/usr/bin/env python3
"""Extract frames for visual mode, with real timestamps.

    python3 frames.py <workdir> [--style auto|screen|talking|slides] [--interval SECONDS]
                      [--cap 120] [--contact-sheets] [--keep] [--force]

Writes frames/frame-HH-MM-SS.jpg (1024px wide JPEG), frames.json (each frame's
timestamp and the transcript spoken around it) and, with --contact-sheets,
sheets/sheet-NNN.jpg (9 frames per image, timestamps burned in).

Near-identical frames are dropped. A downloaded video is deleted afterwards
unless --keep is passed; a local file you own is never deleted.
"""

import argparse
import math
import os
import re
import shutil
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

CADENCE = {"screen": 5, "slides": 10, "default": 15, "talking": 30}
SOURCE_STYLE = {"loom": "screen"}
SHEET = 9


def resolve_style(style, meta):
    if style and style != "auto":
        return style
    return SOURCE_STYLE.get(meta.get("source"), "default")


def plan_interval(style, interval, span, cap):
    base = interval or CADENCE[style]
    if span and span / base > cap:
        base = span / float(cap)
    return round(base, 2)


def video_path(meta):
    files = meta.get("files", {})
    for key in ("video", "source"):
        if files.get(key) and Path(files[key]).exists():
            if key == "source" or meta.get("is_local"):
                return files[key], False
            return files[key], bool(files.get("video_clipped"))
    import fetch
    res = fetch.cmd_media(Namespace(workdir=meta["workdir"], audio=False, video=True, force=False))
    meta.update(common.load_metadata(meta["workdir"]))
    return res["path"], bool(meta.get("clip"))


def has_filter(ff, name):
    r = subprocess.run([ff, "-hide_banner", "-filters"], capture_output=True, text=True)
    return re.search(r"\s%s\s" % name, r.stdout) is not None


def run_ffmpeg(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 and "fps_mode" in r.stderr and "Unrecognized option" in r.stderr:
        cmd = [("-vsync" if c == "-fps_mode" else c) for c in cmd]
        r = subprocess.run(cmd, capture_output=True, text=True)
    return r


def extract(ff, src, out_dir, interval, style, seek, offset):
    expr = "isnan(prev_selected_t)+gte(t-prev_selected_t\\,%s)" % interval
    if style == "slides":
        expr += "+gt(scene\\,0.3)"
    vf = "select='%s',mpdecimate=hi=64*12:lo=64*5:frac=0.33,scale=1024:-2,showinfo" % expr
    cmd = [ff, "-hide_banner", "-nostats", "-y"]
    if seek:
        cmd += ["-ss", str(seek[0])]
        if seek[1] is not None:
            cmd += ["-to", str(seek[1])]
    cmd += ["-i", str(src), "-an", "-vf", vf, "-fps_mode", "vfr", "-q:v", "4", str(out_dir / "tmp-%05d.jpg")]
    r = run_ffmpeg(cmd)
    if r.returncode != 0:
        common.fail("ffmpeg could not extract frames.", detail=r.stderr[-400:])
    times = [float(m) for m in re.findall(r"\[Parsed_showinfo[^\]]*\].*?pts_time:\s*([0-9.]+)", r.stderr)]
    tmp = sorted(out_dir.glob("tmp-*.jpg"))
    if len(times) != len(tmp):
        common.warn("frame count %d does not match timestamps %d; spacing evenly" % (len(tmp), len(times)))
        times = [i * interval for i in range(len(tmp))]
    frames = []
    seen = set()
    for path, t in zip(tmp, times):
        t = t + offset
        name = "frame-%s.jpg" % common.fmt_ts(t).replace(":", "-")
        n = 2
        while name in seen:
            name = "frame-%s-%d.jpg" % (common.fmt_ts(t).replace(":", "-"), n)
            n += 1
        seen.add(name)
        path.rename(out_dir / name)
        frames.append({"file": "frames/" + name, "t": round(t, 2), "ts": common.fmt_ts(t)})
    return frames


def apply_cap(frames, cap, root):
    if len(frames) <= cap:
        return frames
    step = len(frames) / float(cap)
    keep = {int(i * step) for i in range(cap)}
    kept = []
    for i, f in enumerate(frames):
        if i in keep:
            kept.append(f)
        else:
            (root / f["file"]).unlink()
    return kept


def attach_transcript(frames, workdir, span_end):
    data = common.read_json(Path(workdir) / "transcript.json")
    segs = (data or {}).get("segments") or []
    for i, f in enumerate(frames):
        lo = (frames[i - 1]["t"] + f["t"]) / 2 if i > 0 else f["t"] - 5
        hi = (f["t"] + frames[i + 1]["t"]) / 2 if i + 1 < len(frames) else (span_end or f["t"] + 30)
        f["window"] = [round(max(0, lo), 2), round(hi, 2)]
        f["transcript"] = " ".join(s["text"] for s in segs if s["end"] > lo and s["start"] < hi) if segs else None
    return frames


def contact_sheets(ff, frames, root):
    sheet_dir = root / "sheets"
    if sheet_dir.exists():
        shutil.rmtree(sheet_dir)
    sheet_dir.mkdir()
    label = has_filter(ff, "drawtext")
    sheets = []
    for n in range(0, len(frames), SHEET):
        group = frames[n:n + SHEET]
        out = sheet_dir / ("sheet-%03d.jpg" % (n // SHEET + 1))
        ok = False
        for with_label in ([True, False] if label else [False]):
            cmd = [ff, "-hide_banner", "-loglevel", "error", "-y"]
            for f in group:
                cmd += ["-i", str(root / f["file"])]
            chains = []
            for i, f in enumerate(group):
                chain = "[%d:v]scale=512:288:force_original_aspect_ratio=decrease,pad=512:288:(ow-iw)/2:(oh-ih)/2" % i
                if with_label:
                    chain += ",drawtext=text='%s':x=8:y=8:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.6" % f["ts"].replace(":", "\\:")
                chains.append(chain + "[v%d]" % i)
            if len(group) == 1:
                graph = ";".join(chains)
                mapping = "[v0]"
            else:
                layout = "|".join("%d_%d" % ((i % 3) * 512, (i // 3) * 288) for i in range(len(group)))
                graph = ";".join(chains) + ";" + "".join("[v%d]" % i for i in range(len(group))) + \
                    "xstack=inputs=%d:layout=%s:fill=black[out]" % (len(group), layout)
                mapping = "[out]"
            cmd += ["-filter_complex", graph, "-map", mapping, "-frames:v", "1", "-q:v", "4", str(out)]
            if subprocess.run(cmd, capture_output=True, text=True).returncode == 0:
                ok = True
                break
        if not ok:
            common.warn("could not build %s; read the single frames instead" % out.name)
            continue
        sheets.append({"file": "sheets/" + out.name, "frames": [f["ts"] for f in group], "labels": with_label})
        for f in group:
            f["sheet"] = "sheets/" + out.name
    return sheets


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workdir")
    ap.add_argument("--style", default="auto", choices=["auto", "screen", "talking", "slides", "default"])
    ap.add_argument("--interval", type=float)
    ap.add_argument("--cap", type=int)
    ap.add_argument("--contact-sheets", action="store_true")
    ap.add_argument("--keep", action="store_true", help="keep the downloaded video")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    cfg = common.load_config()
    meta = common.load_metadata(args.workdir)
    root = Path(meta["workdir"])
    manifest_path = root / "frames.json"
    cached = common.read_json(manifest_path)
    if cached and not args.force and (not args.contact_sheets or cached.get("sheets")):
        cached["cached"] = True
        common.emit({"status": "ok", **{k: v for k, v in cached.items() if k != "frames"}, "manifest": str(manifest_path)})
        return

    ff = common.require_ffmpeg()
    cap = args.cap or int(cfg["max_frames"])
    style = resolve_style(args.style, meta)
    clip = meta.get("clip") or {}
    start = clip.get("start") or 0.0
    end = clip.get("end") if clip.get("end") is not None else meta.get("duration")
    span = (end - start) if end else None
    interval = plan_interval(style, args.interval, span, cap)

    src, clipped = video_path(meta)
    seek = None
    if clip and not clipped:
        seek = (start, clip.get("end"))
    out_dir = root / "frames"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir()

    frames = extract(ff, src, out_dir, interval, style, seek, start if clip else 0.0)
    frames = apply_cap(frames, cap, root)
    frames = attach_transcript(frames, root, end)
    sheets = contact_sheets(ff, frames, root) if args.contact_sheets else []

    deleted = False
    files = meta.get("files", {})
    if not args.keep and files.get("video_downloaded") and files.get("video") and Path(files["video"]).exists():
        Path(files["video"]).unlink()
        files["video"] = None
        files["video_deleted"] = True
        deleted = True
    meta["files"] = files
    common.save_metadata(root, meta)

    expected = int(math.ceil(span / interval)) if span else None
    manifest = {
        "style": style,
        "interval_seconds": interval,
        "cap": cap,
        "expected_before_dedupe": expected,
        "count": len(frames),
        "sheets": sheets,
        "video_deleted": deleted,
        "frames": frames,
    }
    common.write_json(manifest_path, manifest)
    common.emit({"status": "ok", "cached": False, **{k: v for k, v in manifest.items() if k != "frames"},
                 "manifest": str(manifest_path), "frames_dir": str(out_dir),
                 "read": [s["file"] for s in sheets] if sheets else [f["file"] for f in frames]})


if __name__ == "__main__":
    common.run_main(main)
