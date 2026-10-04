---
name: watch-video
description: "Gets the transcript of a video, and optionally its key visual moments, from YouTube, Loom, Vimeo, Riverside, Zoom recordings, X, Instagram, TikTok, or a video file on your computer. Use when you want the words, a summary, or the key moments of a video, at the depth you pick: transcript (default, free), visual (adds frames), or multimodal (sends the video to Google Gemini). Use when you say \"watch this video\", \"transcribe this video\", \"get the transcript of this\", \"transcribe this Loom\", \"summarize this recording\", \"key moments from this video\", or \"what happens in this video\"."
---

# Watch video

Get a video's transcript, and on request its key visual moments, into a folder of plain files.

The commands live in tested scripts in `scripts/`. Your job is to run them in order, read their JSON output, and route on it.

Every script prints one JSON object. `"status": "ok"` means continue. `"status": "error"` carries `error`, and often `fix` and `kind`. Run scripts with `python3 <this skill's folder>/scripts/<name>.py`.

## Step 1: Check the environment

Run `scripts/preflight.py`. It reports the OS, tools, Whisper backend, network reach, API keys, and output folder, plus `can` and `cannot` lists in plain words.

- **No shell at all** (you cannot run commands here): say that this skill needs a place that can run scripts, such as Claude Code or Cowork. Ask for a transcript file instead, and stop.
- **Something missing**: on macOS, preflight names a `brew` or `uv` command. On Linux, it offers `--install`, which puts yt-dlp, ffmpeg, and faster-whisper into a private folder (`~/.cache/watch-video/venv`). Ask before installing anything, then run `preflight.py --install`.
- Run preflight once per session, not once per video.

## Step 2: Read the request

Input: a URL, an 11-character YouTube ID, or a path to a video or audio file. A playlist is refused with its video count. Ask for one video.

| The person says | Mode |
|---|---|
| Nothing about depth, or "transcript" | `transcript` |
| "visual", "key moments", "what's on screen", "screenshots" | `visual` |
| "multimodal", "use Gemini", "analyze the delivery" | `multimodal` |

Options to pass along when the person asks: `--from 10:00 --to 20:00` (only that section), `--lang es`, `--cookies-from-browser chrome` (private videos, own computer only), `--force` (redo finished steps).

## Step 3: Get metadata

Run `scripts/fetch.py meta <input> [--from ..] [--to ..] [--cookies-from-browser ..]`. It creates the workdir and prints its path. A second run on the same video returns the cached workdir with no download.

If `is_social` is true (X, Instagram, TikTok) and the `read-social` skill is installed, run it on the same URL for the author, post text, and engagement. Save its JSON as `post.json` in the workdir. If `read-social` is not installed, skip this. yt-dlp still gets the video.

## Step 4: Get the transcript

Run `scripts/transcribe.py <workdir>` with any `--lang`. It tries, in order: a transcript file you already have (pass `--transcript FILE`, or a `.vtt`/`.srt`/`.json`/`.txt` beside a local video), platform captions, local Whisper, and hosted transcription (only with `--allow-upload`).

- **`"status": "partial"`** (exit code 3): long videos transcribe in 10-minute chunks. Run the same command again, without `--force`, until the status is `ok`. Tell the person how far along it is.
- **`warning` is set**: no backend passed the coverage and words-per-minute check. Keep the transcript and pass the warning on.
- **`kind: no_whisper` or `model_download`**: if `OPENAI_API_KEY` or `GROQ_API_KEY` is set, offer hosted transcription and follow the privacy gate below. Otherwise ask for a transcript file.
- **`kind: network`, `bot_check`, or `geo`**: do not retry or look for workarounds. Say which step failed and offer the two options that work: upload the file here, or download it on your own computer and hand it back.
- Long CPU-only run: when preflight shows no GPU and no Apple Silicon and the video runs over 30 minutes, say it may run slower than the video plays, and offer hosted transcription if a key is set.

**Transcript mode stops here.** Go to Step 7.

## Step 5: Visual mode

1. Run `scripts/estimate.py <workdir> --mode visual [--style ..] [--contact-sheets]`. Style: `screen` for demos and Loom, `slides` for talks with slides, `talking` for podcasts and talking heads, `auto` when unsure. Use `--contact-sheets` for slow-changing video: it tiles 9 frames per image.
2. If `needs_confirm` is true, show the frame count and estimated tokens and ask before going on. Never show a price.
3. Run `scripts/frames.py <workdir>` with the same style and sheet options. It downloads the video at up to 720p if needed, drops near-identical frames, and deletes the downloaded video afterwards. Pass `--keep` to keep it.
4. Read each image listed in `read`. Use `frames.json` to pair each frame with its timestamp and the words spoken around it.
5. Write `moments.md`, then `summary.md`, using the templates in `references/templates.md`.

## Step 6: Multimodal mode

1. No `GEMINI_API_KEY`: say so and offer visual mode. Do not fall back to dense frame reading.
2. Run `scripts/estimate.py <workdir> --mode multimodal` and follow the privacy gate.
3. Run `scripts/fetch.py media <workdir> --video`.
4. Write `gemini-prompt.md` in the workdir from the multimodal prompt in `references/templates.md`, adjusted to what the person asked for.
5. Run `scripts/gemini.py <workdir> --prompt-file <workdir>/gemini-prompt.md`. It deletes the uploaded copy from Google when done.
6. Write `summary.md` from `gemini.md` and the transcript, with the extra multimodal section from the template.

## Privacy gate

Before any upload to Gemini or a hosted transcription service, say what will be sent and where ("the 42-minute audio track, to OpenAI"), and ask. For anything that looks like a private call (Zoom, Riverside, a local file), suggest "no" as the default and offer the local route.

## Step 7: Report

In chat:

1. One line: `<source> · <title> · <duration> · <mode> · <word count> words`.
2. The workdir path.
3. Visual or multimodal: the top 3 moments with timestamps, plus any action items or decisions from `summary.md`.
4. Any warning from the scripts, in plain words.
5. Transcript mode only: one closing line offering to pull out the key ideas with `distill-video`, if it is installed. Skip this line when `distill-video` called this skill.

## Files in the workdir

| File | What it holds |
|---|---|
| `metadata.json` | Title, uploader, duration, chapters, caption tracks, file paths |
| `transcript.json` | The canonical transcript: segments with start, end, text, and speaker when known |
| `transcript.md` | Readable paragraphs, each starting with its timestamp |
| `transcript.txt` | Plain text, no timestamps |
| `frames/`, `frames.json`, `sheets/` | Visual mode frames and their manifest |
| `moments.md`, `summary.md` | Visual and multimodal write-ups |
| `post.json` | Social post data from `read-social`, when used |

The workdir lives in `WATCH_VIDEO_DIR` if set, else `output_dir` in the config file (`~/.config/watch-video/config.json`; see `config.example.json`), else `./videos/` in the current folder.

## More detail

- `references/sources.md`: what each site supports and its quirks.
- `references/troubleshooting.md`: errors and what to tell the person.
- `references/templates.md`: `moments.md`, `summary.md`, and the Gemini prompt.
- Tests: `python3 -m unittest discover -s tests` from this skill's folder.
