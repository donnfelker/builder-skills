# Changelog

Versions follow the rules in [AGENTS.md](AGENTS.md#versioning). The current version lives in `.claude-plugin/plugin.json`.

## 1.1.3

- `watch-video` says where video links work: Claude desktop and Claude Code. Cloud sessions are often blocked by video sites. When that happens, it tells you to switch and explains why in plain words.
- `watch-video` explains the network setting for code in Claude, with a warning about the risk of opening network access, and offers attaching the file as the option that needs no change.
- `watch-video` installs its tools without asking inside Claude's temporary sandboxes. On your own computer it still asks first.

## 1.1.2

- `watch-video` saves to `~/Documents/videos/` by default again, so all videos stay together and saved work is reused from any folder. In Cowork it saves to Claude's outputs folder, so you can see the files without saying where.
- `read-social` saves to `~/Documents/social-fetches/` by default again, or Claude's outputs folder in Cowork.
- `watch-video` preflight: when the network blocks video sites or the Whisper model download, it names the Claude setting to change instead of suggesting `--install`.

## 1.1.1

- Moved the "Try saying" phrases out of the README skills table into a new `EXAMPLES.md`, with one worked example per skill.
- The README skills table is now generated from each skill's frontmatter by a Sync Skills workflow after each push to `main`.
- Added an OpenAI Codex plugin (`.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json`) and Codex install, update, and remove steps.
- README: names the agents it works with, adds "What are skills?", a diagram of how the skills work together, usage examples, install tips for agent-run installs and `/plugin` outside the terminal, and `--list`.
- Added `CONTRIBUTING.md`.

## 1.1.0

- Added `watch-video`: transcripts from video links and files, with optional visual and multimodal modes. Runs on macOS (Homebrew, MLX-Whisper) and Linux (pip, faster-whisper), with tested scripts, caching, clip ranges, and a privacy gate before any upload.
- Added `read-social`: reads social posts by URL into one JSON shape. Free strategies first, including defuddle, with paid APIs only behind keys.
- Added GitHub workflows: repo rule checks (`scripts/check-repo.py`), the Agent Skills validator, skill tests on Linux and macOS, and a release on each version bump.
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
