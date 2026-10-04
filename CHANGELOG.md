# Changelog

Versions follow the rules in [AGENTS.md](AGENTS.md#versioning). The current version lives in `.claude-plugin/plugin.json`.

## 1.1.0

- Added `watch-video`: transcripts from video links and files, with optional visual and multimodal modes. Runs on macOS (Homebrew, MLX-Whisper) and Linux (pip, faster-whisper), with tested scripts, caching, clip ranges, and a privacy gate before any upload.
- Added `read-social`: reads social posts by URL into one JSON shape. Free strategies first, including defuddle, with paid APIs only behind keys.
- `distill-video` now accepts a video link or file and gets the transcript through `watch-video` when it is installed. Notes cite timestamps when the transcript has them.

## 1.0.1

- Updated the plugin description in `marketplace.json` to match the new tagline.

## 1.0.0

- Renamed the pack from `maverick-skills` to `builder-skills`. New tagline: "Skills for people who build things."
- If you installed the old name, remove it and install `builder-skills` using the steps in the README.

## 0.4.0

- Added `distill-video`.

## 0.3.1

- `revise-plan` now keeps the plan in a working file (`<name>-revisions.md`) between runs, asks before replacing the original plan file, and saves a pasted plan as `<slugified-name>-plan.md`.

## 0.3.0

- Added `revise-plan`.

## 0.2.0

- Added `new-skills-repo`.
- Removed the `example-skill` placeholder.

## 0.1.0

- Initial release.
- Added `example-skill` as a placeholder.
