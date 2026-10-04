#!/usr/bin/env python3
"""Get a transcript for a workdir, trying backends in order.

    python3 transcribe.py <workdir> [--backend auto|file|captions|whisper|hosted]
                          [--transcript FILE] [--lang en] [--allow-upload]
                          [--max-seconds 240] [--force]

Order for --backend auto:
  1. a transcript you already have (--transcript, or a file beside a local video)
  2. platform captions (human before auto-generated)
  3. local Whisper (MLX-Whisper on Apple Silicon, faster-whisper elsewhere)
  4. hosted transcription, only with --allow-upload

Each result must pass a sanity check (coverage and words per minute) or the
next backend runs. Local Whisper works in chunks and stops after
--max-seconds; status "partial" means run the same command again to resume.

Writes transcript.json (canonical, timed segments), transcript.md and
transcript.txt into the workdir.
"""

import argparse
import datetime
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from argparse import Namespace
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

PARTIAL_EXIT = 3
MIN_WPM, MAX_WPM = 60, 250
COVERAGE = 0.90
TS = r"(?:(\d+):)?(\d{1,2}):(\d{2})(?:[.,](\d{1,3}))?"


# ---------- parsing ----------

def ts_to_seconds(text):
    m = re.match(TS, text.strip())
    if not m:
        return None
    h, mnt, s, frac = m.groups()
    total = int(h or 0) * 3600 + int(mnt) * 60 + int(s)
    if frac:
        total += int(frac.ljust(3, "0")) / 1000.0
    return float(total)


SPEAKER_LINE = re.compile(r"^([A-Z][\w.'-]*(?: [A-Z][\w.'-]*){0,3}|Speaker \d+):\s+(.+)$")


def clean_cue_text(raw, speakers):
    """Strip tags, keep a <v Name> voice tag or a 'Name: ' prefix as the speaker."""
    speaker = None
    m = re.search(r"<v(?:\.[^ >]*)?\s+([^>]+)>", raw)
    if m:
        speaker = m.group(1).strip()
    text = re.sub(r"<[^>]+>", "", raw)
    text = html.unescape(text)
    lines = [re.sub(r"\s+", " ", l).strip() for l in text.split("\n")]
    lines = [l for l in lines if l]
    if speakers and not speaker and lines:
        sm = SPEAKER_LINE.match(lines[0])
        if sm:
            speaker = sm.group(1)
            lines[0] = sm.group(2)
    return lines, speaker


def parse_cues(text, speakers=False):
    """VTT and SRT both become [{start, end, lines, speaker}]."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("﻿")
    cues = []
    for block in re.split(r"\n{2,}", text):  # a line holding only a space does not end a cue
        rows = block.strip("\n").split("\n")
        idx = next((i for i, r in enumerate(rows) if "-->" in r), None)
        if idx is None:
            continue
        left, right = rows[idx].split("-->", 1)
        start = ts_to_seconds(left)
        end = ts_to_seconds(right.strip().split(" ")[0])
        if start is None or end is None:
            continue
        lines, speaker = clean_cue_text("\n".join(rows[idx + 1:]), speakers)
        cues.append({"start": start, "end": end, "lines": lines, "speaker": speaker})
    return cues


def overlap_len(prev, cur):
    """Largest k where the last k lines of prev equal the first k lines of cur."""
    for k in range(min(len(prev), len(cur)), 0, -1):
        if prev[-k:] == cur[:k]:
            return k
    return 0


def dedupe_rolling(cues):
    """YouTube auto-captions repeat the previous line at the top of each cue.

    Only text that overlaps the cue right before it is dropped, so a line that
    is spoken twice at different times survives.
    """
    segments = []
    prev = []
    for cue in cues:
        lines = cue["lines"]
        k = overlap_len(prev, lines)
        new = list(lines[k:])
        if new and prev and k == 0 and new[0] != prev[-1] and new[0].startswith(prev[-1]):
            new[0] = new[0][len(prev[-1]):].strip()
        prev = lines
        new = [l for l in new if l]
        if new:
            segments.append({"start": cue["start"], "end": cue["end"], "text": " ".join(new),
                             "speaker": cue.get("speaker")})
    return segments


def cues_to_segments(cues):
    return [{"start": c["start"], "end": c["end"], "text": " ".join(c["lines"]), "speaker": c.get("speaker")}
            for c in cues if c["lines"]]


def parse_json_transcript(data):
    if isinstance(data, dict) and "events" in data:  # YouTube json3
        segs = []
        for ev in data["events"]:
            text = "".join(s.get("utf8", "") for s in ev.get("segs") or []).strip()
            if text:
                start = ev.get("tStartMs", 0) / 1000.0
                segs.append({"start": start, "end": start + ev.get("dDurationMs", 0) / 1000.0, "text": text})
        return segs
    items = data.get("segments") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("JSON transcript has no segments list")
    segs = []
    for it in items:
        if not isinstance(it, dict):
            continue
        text = (it.get("text") or it.get("transcript") or "").strip()
        start = it.get("start", it.get("start_time", it.get("startTime")))
        end = it.get("end", it.get("end_time", it.get("endTime", start)))
        if isinstance(start, str):
            start = ts_to_seconds(start)
        if isinstance(end, str):
            end = ts_to_seconds(end)
        if text and start is not None:
            segs.append({"start": float(start), "end": float(end if end is not None else start), "text": text,
                         "speaker": it.get("speaker") or it.get("speaker_name")})
    return segs


TXT_LINE = re.compile(r"^\[?" + TS + r"\]?\s*(?:-\s*)?(.*)$")


def parse_txt(text, speakers=True):
    """Timed lines like '[00:01:02] text' become segments; plain text is one untimed segment."""
    lines = [l.strip() for l in text.replace("\r\n", "\n").split("\n") if l.strip()]
    timed = []
    for line in lines:
        m = TXT_LINE.match(line)
        if m and m.group(2) is not None:
            start = ts_to_seconds(line.lstrip("[").split("]")[0].split(" ")[0])
            body = m.group(5).strip()
            speaker = None
            if speakers:
                sm = SPEAKER_LINE.match(body)
                if sm:
                    speaker, body = sm.group(1), sm.group(2)
            if start is not None and body:
                timed.append({"start": start, "end": start, "text": body, "speaker": speaker})
    if timed and len(timed) >= len(lines) * 0.5:
        for a, b in zip(timed, timed[1:]):
            a["end"] = b["start"]
        return timed, True
    return [{"start": 0.0, "end": 0.0, "text": " ".join(lines), "speaker": None}], False


def parse_transcript_file(path, rolling=False, speakers=True):
    """Return (segments, timed)."""
    path = Path(path)
    raw = path.read_text(encoding="utf-8", errors="replace")
    ext = path.suffix.lower()
    if ext in (".vtt", ".srt"):
        cues = parse_cues(raw, speakers=speakers)
        return (dedupe_rolling(cues) if rolling else cues_to_segments(cues)), True
    if ext in (".json", ".json3"):
        return parse_json_transcript(json.loads(raw)), True
    if ext == ".txt":
        return parse_txt(raw, speakers)
    raise ValueError("unsupported transcript type: %s" % ext)


# ---------- sanity check ----------

def word_count(segments):
    return sum(len(s["text"].split()) for s in segments)


def sanity(segments, span, timed=True, offset=0.0):
    """Coverage within 10% of the span and 60 to 250 words per minute."""
    words = word_count(segments)
    stats = {"words": words, "span_seconds": span}
    reasons = []
    if not segments or words == 0:
        return False, ["no text"], stats
    if timed and span:
        last_end = max(s["end"] for s in segments) - offset
        stats["coverage"] = round(min(1.0, last_end / span), 3)
        if last_end < span * COVERAGE:
            reasons.append("transcript ends at %s of %s" % (common.fmt_ts(last_end), common.fmt_ts(span)))
    if span and span >= 60:
        wpm = words / (span / 60.0)
        stats["wpm"] = round(wpm)
        if wpm < MIN_WPM:
            reasons.append("%d words per minute is too low (under %d)" % (wpm, MIN_WPM))
        elif wpm > MAX_WPM:
            reasons.append("%d words per minute is too high (over %d)" % (wpm, MAX_WPM))
    return not reasons, reasons, stats


# ---------- rendering ----------

def paragraphs(segments, gap=2.0, soft=60.0, hard=120.0):
    paras, cur = [], []
    for seg in segments:
        if cur:
            start = cur[0]["start"]
            last = cur[-1]
            new_para = (
                seg["start"] - last["end"] > gap
                or (seg.get("speaker") and seg.get("speaker") != last.get("speaker"))
                or (seg["start"] - start > soft and re.search(r"[.!?]\W*$", last["text"]))
                or seg["start"] - start > hard
            )
            if new_para:
                paras.append(cur)
                cur = []
        cur.append(seg)
    if cur:
        paras.append(cur)
    return paras


def render(meta, segments, timed):
    md = ["# %s" % meta.get("title", "Transcript"), ""]
    txt = []
    for para in paragraphs(segments):
        text = " ".join(s["text"] for s in para)
        speaker = para[0].get("speaker")
        label = "**%s:** " % speaker if speaker else ""
        stamp = "**[%s]** " % common.fmt_ts(para[0]["start"]) if timed else ""
        md += [stamp + label + text, ""]
        txt += [("%s: " % speaker if speaker else "") + text, ""]
    return "\n".join(md), "\n".join(txt)


def write_outputs(meta, segments, backend, timed, check, language=None, warning=None):
    wd = Path(meta["workdir"])
    for s in segments:
        s["start"] = round(float(s["start"]), 2)
        s["end"] = round(float(s["end"]), 2)
        if not s.get("speaker"):
            s.pop("speaker", None)
    record = {
        "title": meta.get("title"),
        "source_url": meta.get("webpage_url") or meta.get("files", {}).get("source"),
        "backend": backend,
        "language": language,
        "timed": timed,
        "clip": meta.get("clip"),
        "duration": meta.get("duration"),
        "sanity": check,
        "warning": warning,
        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "segments": segments,
    }
    common.write_json(wd / "transcript.json", record)
    md, txt = render(meta, segments, timed)
    (wd / "transcript.md").write_text(md)
    (wd / "transcript.txt").write_text(txt)
    meta.setdefault("files", {})["transcript"] = str(wd / "transcript.json")
    common.save_metadata(wd, meta)
    return record


# ---------- clip window ----------

def span_of(meta):
    clip = meta.get("clip")
    if clip:
        end = clip.get("end") if clip.get("end") is not None else meta.get("duration")
        return (end or 0) - (clip.get("start") or 0)
    return meta.get("duration")


def clip_segments(meta, segments):
    clip = meta.get("clip")
    if not clip:
        return segments
    start = clip.get("start") or 0
    end = clip.get("end") if clip.get("end") is not None else float("inf")
    return [s for s in segments if s["end"] > start and s["start"] < end]


# ---------- backends: existing file and captions ----------

def try_file(meta, path):
    segs, timed = parse_transcript_file(path, rolling=False, speakers=True)
    return clip_segments(meta, segs), timed, None


def try_captions(meta, lang, force):
    import fetch  # local module
    res = fetch.cmd_captions(Namespace(workdir=meta["workdir"], lang=lang, force=force))
    if res.get("status") != "ok":
        raise common.Failure({"status": "error", "error": res.get("reason", "no captions")})
    segs, timed = parse_transcript_file(res["path"], rolling=(res["kind"] == "auto"), speakers=False)
    return clip_segments(meta, segs), timed, res["lang"].replace("-orig", "")


# ---------- backends: whisper ----------

def whisper_engine():
    """Pick the local Whisper engine: ('mlx-lib', py) | ('mlx-cli', path) | ('faster', py) | None."""
    if common.is_apple_silicon():
        py = common.python_with_module("mlx_whisper")
        if py:
            return "mlx-lib", py
        cli = shutil.which("mlx_whisper") or common.find_tool("mlx_whisper")
        if cli:
            return "mlx-cli", cli
    py = common.python_with_module("faster_whisper")
    if py:
        return "faster", py
    return None


def has_cuda():
    if shutil.which("nvidia-smi"):
        try:
            return subprocess.run(["nvidia-smi", "-L"], capture_output=True, timeout=15).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False
    return False


def pick_model(engine, cfg, override):
    if override:
        return override
    if engine.startswith("mlx"):
        return cfg["whisper_model_mlx"]
    return cfg["whisper_model_gpu"] if has_cuda() else cfg["whisper_model_cpu"]


def audio_source(meta):
    files = meta.get("files", {})
    for key in ("audio", "video", "source"):
        if files.get(key) and Path(files[key]).exists():
            return files[key], bool(files.get(key + "_clipped"))
    return None, False


def prepare_audio(meta, ff, force):
    """One 16 kHz mono WAV of the clip (or whole video), cached in whisper/."""
    wd = Path(meta["workdir"]) / "whisper"
    wd.mkdir(exist_ok=True)
    wav = wd / "audio.wav"
    if wav.exists():
        return wav
    src, already_clipped = audio_source(meta)
    if not src:
        import fetch
        res = fetch.cmd_media(Namespace(workdir=meta["workdir"], audio=True, video=False, force=False))
        meta.update(common.load_metadata(meta["workdir"]))
        src, already_clipped = res["path"], bool(meta.get("clip"))
    cmd = [ff, "-hide_banner", "-loglevel", "error", "-y"]
    clip = meta.get("clip")
    if clip and not already_clipped:
        cmd += ["-ss", str(clip.get("start") or 0)]
        if clip.get("end") is not None:
            cmd += ["-to", str(clip["end"])]
    cmd += ["-i", src, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        common.fail("ffmpeg could not extract audio.", detail=r.stderr[-300:])
    return wav


def run_engine(engine, target, model, chunk, lang):
    """Transcribe one chunk; returns {'language', 'segments'} with chunk-relative times."""
    if engine == "mlx-cli":
        with tempfile.TemporaryDirectory() as tmp:
            cmd = [target, str(chunk), "--model", model, "--output-format", "json",
                   "--output-dir", tmp, "--verbose", "False"]
            if lang:
                cmd += ["--language", lang]
            r = subprocess.run(cmd, capture_output=True, text=True)
            out = Path(tmp) / (chunk.stem + ".json")
            if r.returncode != 0 or not out.exists():
                common.fail("mlx_whisper failed.", detail=(r.stderr or r.stdout)[-400:])
            data = json.loads(out.read_text())
        return {"language": data.get("language"),
                "segments": [{"start": s["start"], "end": s["end"], "text": s["text"].strip()} for s in data.get("segments", [])]}
    cmd = [target, os.path.abspath(__file__), "_engine", engine, model, str(chunk), lang or ""]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        detail = (r.stderr or r.stdout)[-600:]
        if re.search(r"huggingface|HTTPSConnection|ConnectionError|LocalEntryNotFound|snapshot_download", detail, re.I):
            common.fail("The Whisper model could not be downloaded from this environment.",
                        fix="Use an existing transcript, or allow hosted transcription (--backend hosted --allow-upload) if an API key is set.",
                        kind="model_download", detail=detail)
        common.fail("Local Whisper failed.", detail=detail)
    return json.loads(r.stdout)


def engine_entry(engine, model, chunk, lang):
    """Runs inside the interpreter that has the Whisper library installed."""
    lang = lang or None
    if engine == "mlx-lib":
        import mlx_whisper
        res = mlx_whisper.transcribe(chunk, path_or_hf_repo=model, language=lang, verbose=None)
        segs = [{"start": s["start"], "end": s["end"], "text": s["text"].strip()} for s in res.get("segments", [])]
        print(json.dumps({"language": res.get("language"), "segments": segs}))
        return
    from faster_whisper import WhisperModel
    try:
        wm = WhisperModel(model, device="auto", compute_type="default")
    except Exception:
        wm = WhisperModel(model, device="cpu", compute_type="int8")
    segments, info = wm.transcribe(chunk, language=lang, vad_filter=True)
    segs = [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segments]
    print(json.dumps({"language": info.language, "segments": segs}))


def chunked(meta, ff, chunk_seconds, force, transcribe_chunk, label, budget):
    """Shared loop for local and hosted Whisper. Resumes from finished chunks."""
    wav = prepare_audio(meta, ff, force)
    total = common.media_duration(wav) or span_of(meta) or 0
    n = max(1, int(math.ceil(total / float(chunk_seconds))))
    cdir = Path(meta["workdir"]) / "whisper" / label
    cdir.mkdir(parents=True, exist_ok=True)
    state = common.read_json(cdir / "state.json", {}) or {}
    if state.get("chunk_seconds") not in (None, chunk_seconds):
        shutil.rmtree(cdir)
        cdir.mkdir(parents=True)
        state = {}
    state["chunk_seconds"] = chunk_seconds
    started = time.time()
    for i in range(n):
        out = cdir / ("chunk-%03d.json" % i)
        if out.exists():
            continue
        if i > 0 and time.time() - started > budget:
            common.write_json(cdir / "state.json", state)
            done = len(list(cdir.glob("chunk-*.json")))
            return None, {"done": done, "total": n}
        piece = cdir / ("chunk-%03d.wav" % i)
        subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y", "-ss", str(i * chunk_seconds),
                        "-t", str(chunk_seconds), "-i", str(wav), "-c", "copy", str(piece)], check=True)
        res = transcribe_chunk(piece, state.get("language"))
        if not state.get("language") and res.get("language"):
            state["language"] = res["language"]
        common.write_json(out, {"index": i, "offset": i * chunk_seconds, **res})
        piece.unlink()
        common.write_json(cdir / "state.json", state)
    offset = (meta.get("clip") or {}).get("start") or 0
    segments = []
    for i in range(n):
        data = common.read_json(cdir / ("chunk-%03d.json" % i))
        for s in data["segments"]:
            if s["text"].strip():
                segments.append({"start": s["start"] + data["offset"] + offset,
                                 "end": s["end"] + data["offset"] + offset, "text": s["text"].strip()})
    return (segments, state.get("language")), {"done": n, "total": n}


def try_whisper(meta, cfg, args):
    found = whisper_engine()
    if not found:
        common.fail("No local Whisper is installed.", fix=common.install_hint("whisper"), kind="no_whisper")
    engine, target = found
    model = pick_model(engine, cfg, args.model)
    ff = common.require_ffmpeg()

    def one(piece, lang):
        return run_engine(engine, target, model, piece, args.lang or lang)

    return chunked(meta, ff, int(cfg["chunk_seconds"]), args.force, one, "local", args.max_seconds), "whisper:%s:%s" % (engine, model)


# ---------- backends: hosted ----------

HOSTED = {
    "openai": ("OPENAI_API_KEY", "https://api.openai.com/v1/audio/transcriptions", "whisper-1"),
    "groq": ("GROQ_API_KEY", "https://api.groq.com/openai/v1/audio/transcriptions", "whisper-large-v3-turbo"),
}


def multipart(fields, file_field, file_path):
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields:
        parts.append(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (boundary, name, value)).encode())
    parts.append(('--%s\r\nContent-Disposition: form-data; name="%s"; filename="%s"\r\nContent-Type: audio/wav\r\n\r\n'
                  % (boundary, file_field, Path(file_path).name)).encode())
    parts.append(Path(file_path).read_bytes())
    parts.append(("\r\n--%s--\r\n" % boundary).encode())
    return b"".join(parts), "multipart/form-data; boundary=%s" % boundary


def hosted_provider(cfg):
    preferred = cfg.get("hosted_provider", "openai")
    order = [preferred] + [p for p in HOSTED if p != preferred]
    for name in order:
        if name in HOSTED and os.environ.get(HOSTED[name][0]):
            return name
    return None


def try_hosted(meta, cfg, args):
    if not args.allow_upload:
        common.fail("Hosted transcription uploads the audio to a third party and needs --allow-upload.", kind="needs_consent")
    name = hosted_provider(cfg)
    if not name:
        common.fail("No hosted transcription key is set.", fix="Set OPENAI_API_KEY or GROQ_API_KEY.", kind="no_key")
    env, url, model = HOSTED[name]
    ff = common.require_ffmpeg()

    def one(piece, lang):
        fields = [("model", model), ("response_format", "verbose_json"), ("timestamp_granularities[]", "segment")]
        if args.lang or lang:
            fields.append(("language", args.lang or lang))
        body, ctype = multipart(fields, "file", piece)
        req = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Authorization": "Bearer " + os.environ[env], "Content-Type": ctype})
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            common.fail("%s transcription failed (HTTP %s)." % (name, e.code), detail=e.read()[:300].decode("utf-8", "replace"))
        except urllib.error.URLError as e:
            common.fail("Could not reach %s from this environment." % name, detail=str(e.reason), kind="network")
        lang_out = data.get("language")
        if lang_out and len(lang_out) > 3:
            lang_out = None  # OpenAI returns names like "english"; keep the first chunk's detection simple
        return {"language": lang_out,
                "segments": [{"start": s["start"], "end": s["end"], "text": s["text"].strip()} for s in data.get("segments", [])]}

    return chunked(meta, ff, int(cfg["chunk_seconds"]), args.force, one, "hosted-" + name, args.max_seconds), "hosted:%s:%s" % (name, model)


# ---------- ladder ----------

def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "_engine":
        engine_entry(*sys.argv[2:6])
        return
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workdir")
    ap.add_argument("--backend", default="auto", choices=["auto", "file", "captions", "whisper", "hosted"])
    ap.add_argument("--transcript", help="a .vtt, .srt, .json or .txt transcript to use")
    ap.add_argument("--lang", help="language code, e.g. en, es, de")
    ap.add_argument("--model", help="override the Whisper model")
    ap.add_argument("--allow-upload", action="store_true", help="allow hosted transcription")
    ap.add_argument("--max-seconds", type=int, default=240, help="stop Whisper after this long; rerun to resume")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    meta = common.load_metadata(args.workdir)
    cfg = common.load_config()
    lang = args.lang or cfg.get("language")
    args.lang = lang
    wd = Path(meta["workdir"])

    if args.force:
        for name in ("transcript.json", "transcript.md", "transcript.txt"):
            (wd / name).unlink(missing_ok=True)
        shutil.rmtree(wd / "whisper", ignore_errors=True)
    existing = common.read_json(wd / "transcript.json")
    if existing and not args.force and args.backend == "auto" and not args.transcript and \
            (not lang or (existing.get("language") or "").startswith(lang)):
        common.emit(summary(meta, existing, cached=True))
        return

    span = span_of(meta)
    order = {"auto": ["file", "captions", "whisper", "hosted"]}.get(args.backend, [args.backend])
    if args.backend == "auto" and not args.allow_upload:
        order.remove("hosted")
    attempts, candidates = [], []

    files = [args.transcript] if args.transcript else meta.get("sidecar_transcripts", [])
    for step in order:
        try:
            if step == "file":
                if not files:
                    continue
                for f in files:
                    try:
                        segs, timed, got_lang = try_file(meta, f)
                    except (OSError, ValueError) as e:
                        attempts.append({"backend": "file", "file": f, "ok": False, "reason": str(e)})
                        continue
                    if consider(meta, "file:" + Path(f).name, segs, timed, got_lang, span, attempts, candidates):
                        return
                continue
            if step == "captions":
                if meta.get("is_local"):
                    continue
                segs, timed, got_lang = try_captions(meta, lang, args.force)
                if consider(meta, "captions", segs, timed, got_lang, span, attempts, candidates):
                    return
                continue
            runner = try_whisper if step == "whisper" else try_hosted
            (result, progress), backend = runner(meta, cfg, args)
            if result is None:
                common.emit({"status": "partial", "backend": backend, "chunks_done": progress["done"],
                             "chunks_total": progress["total"], "workdir": str(wd),
                             "next": "Run the same command again, without --force, to continue."})
                sys.exit(PARTIAL_EXIT)
            segs, got_lang = result
            if consider(meta, backend, segs, True, got_lang, span, attempts, candidates):
                return
        except common.Failure as f:
            attempts.append({"backend": step, "ok": False, "reason": f.payload.get("error"),
                             "fix": f.payload.get("fix"), "kind": f.payload.get("kind")})

    if candidates:
        best = max(candidates, key=lambda c: (c["backend"].startswith(("whisper", "hosted")), c["check"].get("coverage") or 0))
        record = write_outputs(meta, best["segments"], best["backend"], best["timed"], best["check"], best["language"],
                               warning="No backend passed the sanity check: " + "; ".join(best["reasons"]))
        common.emit(summary(meta, record, attempts=attempts))
        return
    fixes = [a["fix"] for a in attempts if a.get("fix")]
    common.fail("No transcript could be produced.", fix=fixes[0] if fixes else None, attempts=attempts)


def consider(meta, backend, segs, timed, got_lang, span, attempts, candidates):
    ok, reasons, stats = sanity(segs, span, timed, (meta.get("clip") or {}).get("start") or 0.0)
    check = {"passed": ok, "reasons": reasons, **stats}
    attempts.append({"backend": backend, "ok": ok, "reasons": reasons})
    if ok or (not timed and segs and word_count(segs) > 0):
        record = write_outputs(meta, segs, backend, timed, check, got_lang,
                               warning=None if timed else "Transcript has no timestamps, so coverage could not be checked.")
        common.emit(summary(meta, record, attempts=attempts))
        return True
    if segs:
        candidates.append({"backend": backend, "segments": segs, "timed": timed, "check": check,
                           "language": got_lang, "reasons": reasons})
    return False


def summary(meta, record, cached=False, attempts=None):
    wd = Path(meta["workdir"])
    out = {
        "status": "ok",
        "cached": cached,
        "backend": record["backend"],
        "language": record.get("language"),
        "words": word_count(record["segments"]),
        "segments": len(record["segments"]),
        "timed": record.get("timed", True),
        "sanity": record.get("sanity"),
        "warning": record.get("warning"),
        "workdir": str(wd),
        "files": {k: str(wd / ("transcript." + k)) for k in ("json", "md", "txt")},
    }
    if attempts:
        out["attempts"] = attempts
    return out


if __name__ == "__main__":
    common.run_main(main)
