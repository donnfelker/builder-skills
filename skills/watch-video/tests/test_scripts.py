"""Offline tests for the watch-video scripts. Run: python3 -m unittest discover -s tests"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import common  # noqa: E402
import fetch  # noqa: E402
import frames  # noqa: E402
import transcribe as t  # noqa: E402

# YouTube auto-captions: each cue repeats the previous line, and a line
# holding a single space follows some timing lines (added back below).
ROLLING_VTT = """WEBVTT
Kind: captions
Language: en

00:00:00.320 --> 00:00:02.000 align:start position:0%

[Music]

00:00:02.000 --> 00:00:04.000 align:start position:0%

never<00:00:02.500><c> gonna</c><00:00:03.000><c> give</c>

00:00:04.000 --> 00:00:04.010 align:start position:0%
never gonna give


00:00:04.010 --> 00:00:06.000 align:start position:0%
never gonna give
you<00:00:04.500><c> up</c>

00:00:06.000 --> 00:00:06.010 align:start position:0%
you up


00:00:06.010 --> 00:00:08.000 align:start position:0%
you up
never<c> gonna</c><c> give</c>

00:00:08.000 --> 00:00:08.010 align:start position:0%
never gonna give


00:00:08.010 --> 00:00:10.000 align:start position:0%
never gonna give
you up
""".replace("position:0%\n\n", "position:0%\n \n")  # restore the space-only line YouTube writes

ZOOM_VTT = """WEBVTT

1
00:00:00.000 --> 00:00:05.000
Donn Felker: Welcome to the call.

2
00:00:05.000 --> 00:00:09.500
<v Jane Doe>Thanks for having me.</v>
"""

SRT = """1
00:00:01,000 --> 00:00:03,500
Hello &amp; welcome

2
00:00:03,500 --> 00:00:06,000
second line
"""


def write(tmp, name, text):
    p = Path(tmp) / name
    p.write_text(text)
    return p


class CaptionTests(unittest.TestCase):
    def test_rolling_dedupe_keeps_lines_spoken_twice(self):
        with tempfile.TemporaryDirectory() as tmp:
            segs, timed = t.parse_transcript_file(write(tmp, "a.vtt", ROLLING_VTT), rolling=True, speakers=False)
        text = " ".join(s["text"] for s in segs)
        self.assertTrue(timed)
        self.assertEqual(text, "[Music] never gonna give you up never gonna give you up")
        self.assertEqual(segs[0]["start"], 0.32)

    def test_without_rolling_cleanup_text_repeats(self):
        with tempfile.TemporaryDirectory() as tmp:
            segs, _ = t.parse_transcript_file(write(tmp, "a.vtt", ROLLING_VTT), rolling=False, speakers=False)
        self.assertGreater(t.word_count(segs), 11)

    def test_speaker_labels_from_prefix_and_voice_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            segs, _ = t.parse_transcript_file(write(tmp, "z.vtt", ZOOM_VTT))
        self.assertEqual([s["speaker"] for s in segs], ["Donn Felker", "Jane Doe"])
        self.assertEqual(segs[0]["text"], "Welcome to the call.")
        self.assertEqual(segs[1]["text"], "Thanks for having me.")

    def test_srt_with_entities(self):
        with tempfile.TemporaryDirectory() as tmp:
            segs, _ = t.parse_transcript_file(write(tmp, "a.srt", SRT))
        self.assertEqual(segs[0]["text"], "Hello & welcome")
        self.assertEqual((segs[0]["start"], segs[1]["end"]), (1.0, 6.0))

    def test_json_segments_and_timed_txt(self):
        with tempfile.TemporaryDirectory() as tmp:
            j = write(tmp, "a.json", json.dumps({"segments": [{"start": 0, "end": 2, "text": " hi "}]}))
            segs, _ = t.parse_transcript_file(j)
            self.assertEqual(segs[0]["text"], "hi")
            x = write(tmp, "b.txt", "[00:00:01] Ann Lee: first\n[00:00:05] second\n")
            segs, timed = t.parse_transcript_file(x)
        self.assertTrue(timed)
        self.assertEqual(segs[0]["speaker"], "Ann Lee")
        self.assertEqual(segs[0]["end"], 5.0)

    def test_plain_txt_is_untimed(self):
        with tempfile.TemporaryDirectory() as tmp:
            segs, timed = t.parse_transcript_file(write(tmp, "c.txt", "just words\nmore words\n"))
        self.assertFalse(timed)
        self.assertEqual(segs[0]["text"], "just words more words")


class SanityTests(unittest.TestCase):
    def seg(self, start, end, words):
        return {"start": start, "end": end, "text": " ".join(["w"] * words)}

    def test_passes_good_transcript(self):
        ok, reasons, stats = t.sanity([self.seg(0, 590, 1500)], 600)
        self.assertTrue(ok, reasons)
        self.assertEqual(stats["wpm"], 150)

    def test_fails_short_coverage(self):
        ok, reasons, _ = t.sanity([self.seg(0, 300, 1500)], 600)
        self.assertFalse(ok)
        self.assertIn("ends at", reasons[0])

    def test_fails_word_rate(self):
        self.assertFalse(t.sanity([self.seg(0, 600, 100)], 600)[0])
        self.assertFalse(t.sanity([self.seg(0, 600, 3000)], 600)[0])

    def test_clip_offset(self):
        ok, reasons, stats = t.sanity([self.seg(600, 1190, 1500)], 600, offset=600)
        self.assertTrue(ok, reasons)

    def test_short_video_skips_word_rate(self):
        self.assertTrue(t.sanity([self.seg(0, 30, 5)], 30)[0])


class RenderTests(unittest.TestCase):
    def test_paragraph_breaks_on_gap_and_speaker(self):
        segs = [{"start": 0, "end": 2, "text": "a."}, {"start": 2, "end": 3, "text": "b."},
                {"start": 10, "end": 11, "text": "c.", "speaker": "X"}]
        self.assertEqual([len(p) for p in t.paragraphs(segs)], [2, 1])

    def test_markdown_has_timestamps_text_has_none(self):
        md, txt = t.render({"title": "T"}, [{"start": 65, "end": 70, "text": "hello"}], True)
        self.assertIn("**[00:01:05]** hello", md)
        self.assertNotIn("00:01:05", txt)


class FetchTests(unittest.TestCase):
    def test_pick_track_prefers_human_then_orig(self):
        meta = {"language": "en", "captions_available": {"human": ["de", "en-US"], "auto": ["en", "en-orig"]}}
        self.assertEqual(fetch.pick_track(meta, None), ("en-US", "human"))
        meta["captions_available"]["human"] = []
        self.assertEqual(fetch.pick_track(meta, None), ("en-orig", "auto"))
        self.assertEqual(fetch.pick_track(meta, "fr"), (None, None))

    def test_bot_check_message_points_to_desktop_and_explains_why(self):
        fix = fetch.MESSAGES["bot_check"][1]
        self.assertIn("Claude desktop or Claude Code", fix)
        self.assertIn("data center", fix)

    def test_classify(self):
        self.assertEqual(fetch.classify("ERROR: Sign in to confirm you’re not a bot"), "bot_check")
        self.assertEqual(fetch.classify("ERROR: Private video"), "private")
        self.assertEqual(fetch.classify("urlopen error [Errno -3] Temporary failure in name resolution"), "network")
        self.assertEqual(fetch.classify("ERROR: something new broke"), "extractor")

    def test_youtube_id_and_source(self):
        self.assertEqual(fetch.youtube_id("https://youtu.be/abcdefghijk?t=3"), "abcdefghijk")
        self.assertEqual(fetch.youtube_id("https://www.youtube.com/shorts/abcdefghijk"), "abcdefghijk")
        self.assertEqual(fetch.detect_source("https://www.loom.com/share/x"), "loom")
        self.assertEqual(fetch.normalize_input("abcdefghijk"), "https://www.youtube.com/watch?v=abcdefghijk")

    def test_metadata_survives_pipes_and_emoji(self):
        meta = fetch.meta_from_ytdlp({"id": "x", "title": "Q&A | launch \U0001F389\nday", "upload_date": "20260102"}, "u")
        with tempfile.TemporaryDirectory() as tmp:
            common.write_json(Path(tmp) / "metadata.json", meta)
            back = common.read_json(Path(tmp) / "metadata.json")
        self.assertEqual(back["title"], "Q&A | launch \U0001F389\nday")
        self.assertEqual(back["upload_date"], "2026-01-02")

    def test_sidecars_need_matching_name_when_folder_has_several_videos(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("a.mp4", "b.mp4", "a.vtt", "b transcript.vtt"):
                write(tmp, name, "")
            self.assertEqual([Path(p).name for p in fetch.find_sidecars(Path(tmp) / "a.mp4")], ["a.vtt"])
            os.remove(Path(tmp) / "b.mp4")
            os.remove(Path(tmp) / "a.vtt")
            self.assertEqual([Path(p).name for p in fetch.find_sidecars(Path(tmp) / "a.mp4")], ["b transcript.vtt"])


class FrameTests(unittest.TestCase):
    def test_interval_stretches_to_cap(self):
        self.assertEqual(frames.plan_interval("screen", None, 600, 120), 5)
        self.assertEqual(frames.plan_interval("screen", None, 3600, 120), 30)

    def test_manifest_windows_match_speech(self):
        fr = [{"t": 0.0}, {"t": 10.0}, {"t": 20.0}]
        with tempfile.TemporaryDirectory() as tmp:
            common.write_json(Path(tmp) / "transcript.json", {"segments": [
                {"start": 0, "end": 4, "text": "one"}, {"start": 9, "end": 12, "text": "two"},
                {"start": 21, "end": 24, "text": "three"}]})
            out = frames.attach_transcript(fr, tmp, 30)
        self.assertEqual([f["transcript"] for f in out], ["one", "two", "three"])
        self.assertEqual(out[1]["window"], [5.0, 15.0])

    def test_cap_keeps_even_spread(self):
        with tempfile.TemporaryDirectory() as tmp:
            fr = []
            for i in range(10):
                write(tmp, "f%d.jpg" % i, "")
                fr.append({"file": "f%d.jpg" % i, "t": i})
            kept = frames.apply_cap(fr, 5, Path(tmp))
            self.assertEqual([f["t"] for f in kept], [0, 2, 4, 6, 8])
            self.assertEqual(len(list(Path(tmp).glob("*.jpg"))), 5)


class OutputDirTests(unittest.TestCase):
    def setUp(self):
        self.saved = (common.SANDBOX_OUTPUTS, os.environ.pop("WATCH_VIDEO_DIR", None))

    def tearDown(self):
        common.SANDBOX_OUTPUTS = self.saved[0]
        os.environ.pop("WATCH_VIDEO_DIR", None)
        if self.saved[1] is not None:
            os.environ["WATCH_VIDEO_DIR"] = self.saved[1]

    def test_order_env_then_config_then_sandbox_then_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            common.SANDBOX_OUTPUTS = Path(tmp) / "missing"
            self.assertEqual(common.output_base({"output_dir": None}), common.default_home().resolve())
            self.assertIn(common.default_home().parent.name, ("Documents", Path.home().name))
            common.SANDBOX_OUTPUTS = Path(tmp)
            self.assertEqual(common.output_base({"output_dir": None}), (Path(tmp) / "videos").resolve())
            self.assertEqual(common.output_base({"output_dir": tmp + "/cfg"}), Path(tmp + "/cfg").resolve())
            os.environ["WATCH_VIDEO_DIR"] = tmp + "/env"
            self.assertEqual(common.output_base({"output_dir": tmp + "/cfg"}), Path(tmp + "/env").resolve())


class PreflightTests(unittest.TestCase):
    def report(self, youtube, hf, ytdlp=None, whisper=None):
        return {"tools": {"yt-dlp": {"path": ytdlp}, "ffmpeg": {"path": "/usr/bin/ffmpeg"}},
                "network": {"youtube": youtube, "huggingface": hf},
                "whisper": {"backends": whisper or {}},
                "keys": {"GEMINI_API_KEY": False, "OPENAI_API_KEY": False, "GROQ_API_KEY": False},
                "output_dir": {"writable": True, "path": "/x"}, "youtube_js_runtime": True}

    def test_blocked_network_names_the_setting_not_install(self):
        import preflight
        r = self.report(youtube=False, hf=False)
        preflight.summarize(r)
        text = " ".join(r["cannot"])
        self.assertIn("Settings > Capabilities", text)
        self.assertIn("risk", text)
        self.assertNotIn("--install", text)

    def test_open_network_with_tools_is_ok(self):
        import preflight
        r = self.report(youtube=True, hf=True, ytdlp="/v/yt-dlp", whisper={"faster_whisper": {}})
        preflight.summarize(r)
        self.assertEqual(r["status"], "ok")


class TimeTests(unittest.TestCase):
    def test_parse_and_format(self):
        self.assertEqual(common.parse_time("1:02:03"), 3723)
        self.assertEqual(common.parse_time("10:00"), 600)
        self.assertEqual(common.fmt_ts(3723), "01:02:03")
        self.assertEqual(common.slugify("Q&A | Launch 🎉 Day!"), "qa-launch-day")


if __name__ == "__main__":
    unittest.main()
