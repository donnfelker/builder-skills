# Contributing

Thanks for helping. Builder Skills is for people who build things, many of whom have never used a terminal. Every change should keep the skills easy to use for them.

## Report a problem or ask a question

[Open an issue](https://github.com/donnfelker/builder-skills/issues). Include:

- which skill you used, and where (Claude desktop, Cowork, Claude Code, Codex, or another agent)
- what you asked for
- what happened, and what you expected

## Suggest a skill

Open an issue first and describe the task the skill would help with. This pack is for non-technical work and life: decisions, writing, learning, and planning. Coding and other technical skills belong elsewhere.

## Improve or add a skill

1. Fork the repo and create a branch.
2. Make your change. The rules for skills (folder names, frontmatter, descriptions, writing style) are in [AGENTS.md](AGENTS.md). Read it before you start.
3. If you add, rename, or remove a skill, update `EXAMPLES.md` and `CHANGELOG.md`, and bump the version in `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` as described in AGENTS.md.
4. Rebuild the README skills table: `node .github/scripts/sync-skills.js`.
5. Run the checks: `python3 scripts/check-repo.py`. If the skill has a `tests/` folder, run `python3 -m unittest discover -s tests` from the skill's folder.
6. Open a pull request. Say what changed and how you tested it.

The same checks run on every pull request, so a failing check tells you what to fix.

## Writing style

Plain words, short sentences, no em dashes, and no hype words. The full list is in AGENTS.md.

## License

By contributing, you agree that your work is released under the [MIT License](LICENSE).
