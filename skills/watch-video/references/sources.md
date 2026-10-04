# Sources

| Source | Download | Captions | Notes |
|---|---|---|---|
| YouTube | yt-dlp | Human captions and auto-captions | Auto-captions repeat lines; `transcribe.py` cleans them. Some videos trigger a "not a bot" sign-in check, even from home networks. yt-dlp reads YouTube more reliably with Node or Deno installed. |
| Loom | yt-dlp | Sometimes, through yt-dlp | Mostly screen shares. Visual mode uses `screen` style (a frame every 5 seconds) by default. |
| Vimeo | yt-dlp | Sometimes | Private or unlisted videos may need `--cookies-from-browser`. |
| Riverside | Exported file, or a direct download URL | Riverside exports transcripts | Put the exported `.srt`, `.vtt`, or `.txt` beside the video, or pass it with `--transcript`. Speaker labels are kept. |
| Zoom | The downloaded recording | Zoom exports a `.vtt` transcript when cloud transcripts are on | Put the `.vtt` beside the `.mp4`. Lines like `Name: text` become speaker labels. |
| X, Instagram, TikTok | yt-dlp | No | `read-social` (if installed) supplies the author, text, and engagement. Instagram and TikTok often block anonymous downloads. |
| Local file | Not needed | A transcript file beside it, if any | `.mp4`, `.mov`, `.webm`, `.mkv`, and audio files. Your own file is never deleted. |

## Transcript files beside a local video

A file counts as that video's transcript when its name starts with the video's name (`call.mp4` and `call.vtt`). When the folder holds only one video, any `.vtt`, `.srt`, or a file with "transcript" or "caption" in its name also counts.

## Frame styles

| Style | One frame every | Use for |
|---|---|---|
| `screen` | 5 seconds | Demos, Loom, screen shares |
| `slides` | 10 seconds, plus each slide change | Talks with slides |
| `default` | 15 seconds | Unsure |
| `talking` | 30 seconds | Podcasts, talking heads |

The interval stretches on long videos so the count stays under the cap (120 by default). Near-identical frames are dropped, so a static screen share yields only the frames where something changed.
