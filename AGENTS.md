# AGENTS.md

Rules for any agent working in this repository. This file is the single source of truth.

## What this repo is

`builder-skills` is a free pack of agent skills for non-technical work and life: decisions, writing, learning, and planning. Tagline: "Skills for people who build things."

- GitHub: https://github.com/donnfelker/builder-skills
- Author: Donn Felker
- License: MIT
- Technical and coding skills do not belong here. They live in a different repo.

The audience is people who may have never used a terminal. Write every skill and every doc in plain language.

## Layout

```
builder-skills/
├── .claude-plugin/
│   ├── plugin.json         # plugin manifest (name, version, skills path)
│   └── marketplace.json    # marketplace manifest (lists the plugin)
├── .github/workflows/      # CI: repo rules, skill validation, skill tests, releases
├── scripts/
│   └── check-repo.py       # checks the rules in this file
├── skills/
│   └── <skill-name>/
│       ├── SKILL.md        # one folder per skill
│       └── tests/          # optional; CI runs them on Linux and macOS
├── AGENTS.md
├── CLAUDE.md               # imports AGENTS.md
├── CHANGELOG.md
├── LICENSE
└── README.md
```

The `skills/` directory is flat. Do not nest skills in category folders. The `npx skills` CLI, Claude Code, and Cowork all find skills at `skills/<name>/SKILL.md`.

## Rules for adding a skill

### Folder name
- Lowercase letters, digits, and hyphens only. 1 to 64 characters.
- The folder name must match the `name` in the frontmatter exactly.
- Use a short, plain name a person would recognize, like `decide` or `weekly-plan`.

### Frontmatter
Every `SKILL.md` starts with YAML frontmatter:

```yaml
---
name: skill-name
description: What the skill does. When to use it, with the phrases a person would say.
---
```

- `name` and `description` are required.
- `description` is 1 to 1024 characters.
- Wrap the description in quotes if it contains a colon.

### Description style
- First sentence: what the skill does.
- Second sentence: when to use it, starting with "Use when".
- Include 4 to 8 phrases a person would say, in quotes. Example: "help me decide," "I can't choose," "pros and cons."
- Write for a non-technical person. No jargon.

### Standalone rule
- Every skill must work when installed alone.
- No hard dependencies between skills.
- If one skill helps another, refer to it softly: "If `x` is installed, use it. Otherwise, do Y." Always spell out Y.

### Body
- Short sentences. Numbered steps for procedures.
- State the output format.
- Keep the body under 500 lines. Move long reference material to a `references/` folder inside the skill folder.

### Writing rules
- No em dashes or en dashes.
- No hype words: seamless, robust, powerful, cutting-edge, innovative, and similar.
- Specific claims only. Cut anything that does not change what the reader does.

## Keeping files in sync

When you add, rename, or remove a skill:

1. **README skills table.** Add, update, or remove the row. Columns: skill (linked to its folder), what it does, example trigger phrase. Keep rows in alphabetical order.
2. **README install examples.** The `--skill <name>` example must use a real skill name.
3. **`.claude-plugin/plugin.json`.** The `skills` path is `./skills`. It picks up new folders on its own. Do not list skills one by one. Bump `version`.
4. **`.claude-plugin/marketplace.json`.** Update the plugin `description` only if the scope of the pack changed. Do not add a version here. `plugin.json` is the single place for it.
5. **`CHANGELOG.md`.** Add an entry under the new version.

Do not rename the plugin or marketplace name (`builder-skills`). Users type it in install commands.

## Versioning

One version number, stored in `.claude-plugin/plugin.json`. Format `x.y.z`.

- **x:** repo-wide changes. Restructures, renames, breaking changes.
- **y:** a new skill is added.
- **z:** an existing skill is edited, or docs change.

Add a matching heading to `CHANGELOG.md` for every bump.

## Pre-commit checklist

Run `python3 scripts/check-repo.py` before committing. It checks most of the list below. CI runs it on every pull request with `--base origin/main`, which also requires a version bump when skills change. CI also runs the Agent Skills validator on changed skills and each skill's `tests/` folder.

Run each check before committing.

- [ ] Every `skills/*/SKILL.md` has frontmatter with `name` and `description`.
- [ ] Each `name` matches its folder name.
- [ ] Each description is 1024 characters or fewer and says when to trigger.
- [ ] No skill requires another skill to work.
- [ ] Every skill appears in the README table with a working folder link.
- [ ] `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` are valid JSON.
- [ ] `claude plugin validate .` passes, if the `claude` CLI is available.
- [ ] Every install command in the README uses `donnfelker/builder-skills`.
- [ ] Version bumped in `plugin.json` and noted in `CHANGELOG.md`.
- [ ] No em dashes, en dashes, or hype words in changed files.
- [ ] No secrets, personal paths, or private notes in any file.
