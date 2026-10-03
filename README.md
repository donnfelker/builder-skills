# Maverick Skills

**Skills for people who do life and work their own way.**

A free pack of skills for Claude and other AI agents. It is for people who want help with decisions, writing, learning, and planning, and who do not want to learn a new tool to get it.

## Skills

| Skill | What it does | Try saying |
|-------|--------------|------------|
| [new-skills-repo](skills/new-skills-repo/) | Builds a new public GitHub repo that shares a pack of skills, with install steps and a README. | "Make a skills repo" |

## Install

Pick one method. If you are not sure, use the first one.

### Claude desktop app or Cowork (no terminal needed)

1. Open the Claude desktop app or go to [claude.ai](https://claude.ai).
2. Open **Customize**, then **Plugins**.
3. Click **Add**, then **Add marketplace**.
4. Paste this and confirm:

```
donnfelker/maverick-skills
```

5. Find **maverick-skills** in the list and click **Add**.

The skills now work in chat, Cowork, and Claude Code on your account.

### Claude Code

```
/plugin marketplace add donnfelker/maverick-skills
/plugin install maverick-skills@maverick-skills
```

### Any agent: all skills

Needs [Node.js](https://nodejs.org).

```
npx skills add donnfelker/maverick-skills
```

### Any agent: one skill

```
npx skills add donnfelker/maverick-skills --skill new-skills-repo
```

### Manual: clone and copy

```
git clone https://github.com/donnfelker/maverick-skills.git
cp -r maverick-skills/skills/* ~/.claude/skills/
```

This copies the skills into Claude Code's personal skills folder. Other agents use a different folder. Check your agent's docs.

## How to use a skill

You do not need to type a command. Describe what you want, and Claude picks the matching skill.

**Example.** You type:

> I want to share my skills with other people. Make me a skills repo.

Claude loads `new-skills-repo`, asks for the repo name, your GitHub username, and what the skills are for, then builds the repo folder and makes the first commit.

To call a skill by name:

- Claude desktop and Cowork: type `/` and pick the skill from the list.
- Claude Code: type `/maverick-skills:new-skills-repo`.

## Updating

| Method | How |
|--------|-----|
| Claude desktop / Cowork | **Customize > Plugins**, open the marketplace, click **Check for updates**. |
| Claude Code | `claude plugin update maverick-skills@maverick-skills` |
| `npx skills` | `npx skills update` |
| Manual | `git pull`, then copy the skills again. |

## Uninstalling

| Method | How |
|--------|-----|
| Claude desktop / Cowork | **Customize > Plugins**, open **maverick-skills**, open its menu, click **Remove**. |
| Claude Code | `claude plugin uninstall maverick-skills@maverick-skills` |
| `npx skills` | `npx skills remove` |
| Manual | Delete the copied folders from your skills directory. |

## Contributing

Found a mistake or have a skill to add? Open an issue or a pull request. The rules for adding a skill are in [AGENTS.md](AGENTS.md).

## License

[MIT](LICENSE). Free to use, copy, and change.

## About the author

Built by Donn Felker.

- X: [@donnfelker](https://x.com/donnfelker)
- Instagram: [@donnfelker](https://instagram.com/donnfelker)
- LinkedIn: [/in/donnfelker](https://linkedin.com/in/donnfelker)
- YouTube: [youtube.com/@donn-felker](https://youtube.com/@donn-felker)
- Web: [donnfelker.com](https://donnfelker.com)
- Substack: [donnfelker.substack.com](https://donnfelker.substack.com)
