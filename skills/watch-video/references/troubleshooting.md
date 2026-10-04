# Troubleshooting

Scripts report errors as JSON with `error`, `fix`, and sometimes `kind`. Pass `error` and `fix` on in plain words.

| `kind` or symptom | Cause | What to tell the person |
|---|---|---|
| `network` | The network setting for code in Claude blocks the site. | Attach the video file (no setting change needed). Or change Settings > Capabilities and start a new session, after reading the risk warning in the message. Do not retry. |
| `bot_check` | The site wants a sign-in to prove the request is not a bot. Cloud sessions run on Anthropic's servers, and sites block data centers. | Run it in Claude desktop or Claude Code, which use the person's own internet connection. Already there: retry with `--cookies-from-browser chrome` (or `safari`, `firefox`). Or attach the file. |
| `private` | Private, members-only, or age-gated. | Same as `bot_check`. Sandboxes have no browser profile. |
| `geo` | Blocked in this region. | Upload the file. |
| `unavailable` | Removed or never existed. | Stop. |
| `unsupported` | yt-dlp does not know the site. | Download the video another way and pass the file. |
| `playlist` | The URL is a playlist. | Pick one video. |
| `extractor` (after one automatic upgrade) | yt-dlp is out of date for this site, or the site changed. | Try again later, or download the file another way. |
| `no_whisper` | No local Whisper. | macOS: `uv tool install mlx-whisper` or `pip install mlx-whisper`. Linux: `python3 scripts/preflight.py --install`. |
| `model_download` | Whisper could not download its model. Common in sandboxes. | Offer hosted transcription if a key is set, after the privacy gate. Otherwise ask for a transcript file. |
| `needs_consent` | Hosted transcription was tried without `--allow-upload`. | Ask first. |
| `no_key` | No API key for the hosted service or Gemini. | Use local Whisper, or visual mode instead of multimodal. |
| ffmpeg missing | | macOS: `brew install ffmpeg`. Linux: `python3 scripts/preflight.py --install`. |
| yt-dlp missing | | macOS: `brew install yt-dlp`. Linux: `python3 scripts/preflight.py --install`. |
| Python too old for yt-dlp | yt-dlp needs Python 3.10 or newer; macOS ships 3.9. | macOS: use the Homebrew yt-dlp. Linux: install a newer Python. |
| `warning` on a transcript | No backend passed the check (it ends early, or the words per minute look wrong). Music videos and long silences cause this. | Keep the transcript and say what the warning means. |
| Transcription stops with `partial` | Long video, chunked work. | Run the same command again without `--force`. |
| Vision pass unclear | Frames too small or too many. | Use fewer frames (`--cap 40`), or contact sheets off. |

