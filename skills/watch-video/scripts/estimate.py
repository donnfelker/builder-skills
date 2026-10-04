#!/usr/bin/env python3
"""Estimate frames and tokens before a visual or multimodal run.

    python3 estimate.py <workdir> --mode visual|multimodal [--style auto] [--interval N]
                        [--cap 120] [--contact-sheets]

Prints frame count, images to read, estimated tokens, and whether the skill
must ask before going on. No prices: they change too often to hardcode.
"""

import argparse
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
import frames as frames_mod  # noqa: E402

FRAME_TOKENS = 1024 * 576 // 750       # one 1024px-wide 16:9 JPEG read by Claude
SHEET_TOKENS = 1536 * 864 // 750       # one 3x3 contact sheet of 512px tiles
GEMINI_TOKENS_PER_SECOND = 300         # video plus audio at default resolution, rounded up
WORDS_PER_MINUTE = 150
TOKENS_PER_WORD = 1.3


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workdir")
    ap.add_argument("--mode", required=True, choices=["visual", "multimodal"])
    ap.add_argument("--style", default="auto")
    ap.add_argument("--interval", type=float)
    ap.add_argument("--cap", type=int)
    ap.add_argument("--contact-sheets", action="store_true")
    args = ap.parse_args()

    cfg = common.load_config()
    meta = common.load_metadata(args.workdir)
    clip = meta.get("clip") or {}
    start = clip.get("start") or 0.0
    end = clip.get("end") if clip.get("end") is not None else meta.get("duration")
    span = (end - start) if end else 0
    minutes = span / 60.0

    transcript = common.read_json(Path(meta["workdir"]) / "transcript.json")
    if transcript:
        words = sum(len(s["text"].split()) for s in transcript["segments"])
    else:
        words = int(minutes * WORDS_PER_MINUTE)
    transcript_tokens = int(words * TOKENS_PER_WORD)

    out = {"status": "ok", "mode": args.mode, "duration_seconds": span, "minutes": round(minutes, 1),
           "transcript_tokens": transcript_tokens}

    if args.mode == "visual":
        cap = args.cap or int(cfg["max_frames"])
        style = frames_mod.resolve_style(args.style, meta)
        interval = frames_mod.plan_interval(style, args.interval, span, cap)
        count = min(cap, int(math.ceil(span / interval))) if span else 0
        images = int(math.ceil(count / 9.0)) if args.contact_sheets else count
        image_tokens = images * (SHEET_TOKENS if args.contact_sheets else FRAME_TOKENS)
        threshold = int(cfg["confirm_frames_over"])
        out.update({
            "style": style, "interval_seconds": interval, "frames_max": count,
            "images_to_read": images, "image_tokens": image_tokens,
            "total_tokens": image_tokens + transcript_tokens,
            "uploads": None,
            "needs_confirm": count > threshold,
            "confirm_reason": "more than %d frames" % threshold if count > threshold else None,
            "note": "Near-identical frames are dropped, so the real count is often lower.",
        })
    else:
        gemini_tokens = int(span * GEMINI_TOKENS_PER_SECOND)
        out.update({
            "gemini_input_tokens": gemini_tokens,
            "uploads": "the video file to Google Gemini",
            "needs_confirm": True,
            "confirm_reason": "uploads the video to a third party",
        })
    common.emit(out)


if __name__ == "__main__":
    common.run_main(main)
