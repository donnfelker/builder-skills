# Builder Skills

**Skills for people who build things.**

A free pack of skills for AI agents. It is for people who build things, like a business, a project, a habit, or a plan, and want help with the decisions, writing, learning, and planning along the way. You do not need to learn a new tool to use it.

Works with Claude (the desktop app, Cowork, and Claude Code), OpenAI Codex, Cursor, and any agent that supports the [Agent Skills spec](https://agentskills.io).

Built by [Donn Felker](https://donnfelker.com) ([X](https://x.com/donnfelker) · [Instagram](https://instagram.com/donnfelker) · [LinkedIn](https://linkedin.com/in/donnfelker) · [YouTube](https://youtube.com/@donn-felker) · [Website](https://donnfelker.com) · [Newsletter](https://donnfelker.substack.com)).

**Contributions welcome.** Have an idea for a skill or a fix? See [CONTRIBUTING.md](CONTRIBUTING.md). Run into a problem or have a question? [Open an issue](https://github.com/donnfelker/builder-skills/issues).

## What are skills?

A skill is a short instruction file that teaches an AI agent how to do one kind of task well, such as making a decision or turning a video into notes. Once installed, the agent notices when your request matches a skill and follows its steps. You keep talking to it the way you already do.

## Skills

<!-- SKILLS:START -->
| Skill | Description |
|-------|-------------|
| [distill-video](skills/distill-video/) | Turns a video, podcast, interview, lecture, talk, or tutorial into a short set of notes on what mattered: the main... |
| [new-skills-repo](skills/new-skills-repo/) | Builds a new public GitHub repo that shares a pack of agent skills, with install steps and a README. Use when you say... |
| [read-social](skills/read-social/) | Reads a social media post from its link and returns the same structured result for every site: author, date, text,... |
| [revise-plan](skills/revise-plan/) | Stress-tests a plan and returns the smallest revision that makes it more likely to succeed. Use when you have a plan... |
| [watch-video](skills/watch-video/) | Gets the transcript of a video, and optionally its key visual moments, from YouTube, Loom, Vimeo, Riverside, Zoom... |
<!-- SKILLS:END -->

See [EXAMPLES.md](EXAMPLES.md) for what to say to each skill and what you get back.

## How the skills work together

Every skill works on its own. Some get more done when another one is installed too:

```
"Distill this video <link>"
        |
        v
  distill-video ---- needs a transcript ----> watch-video
  (notes on what                              (transcript, frames,
   mattered)                                    key moments)
                                                     |
                                    X, Instagram, or TikTok video
                                                     |
                                                     v
                                                read-social
                                          (post author, text,
                                           engagement)

  revise-plan        stress-tests any plan
  new-skills-repo    turns your own skills into a shareable repo
```

If a helper skill is missing, the first skill says what it needs and asks you for it instead.

## Install

Pick one method. If you are not sure, use the first one.

### Claude desktop app or Cowork (no terminal needed)

1. Open the Claude desktop app or go to [claude.ai](https://claude.ai).
2. Open **Customize**, then **Plugins**.
3. Click **Add**, then **Add marketplace**.
4. Paste this and confirm:

```
donnfelker/builder-skills
```

5. Find **builder-skills** in the list and click **Add**.

The skills now work in chat, Cowork, and Claude Code on your account.

### Claude Code

```
/plugin marketplace add donnfelker/builder-skills
/plugin install builder-skills@builder-skills
```

`/plugin` only works in an interactive Claude Code session in the terminal. In Claude Code on the web, GitHub Actions, or other non-interactive sessions you will see "/plugin isn't available in this environment". Use these commands in a terminal instead:

```
claude plugin marketplace add donnfelker/builder-skills
claude plugin install builder-skills@builder-skills
```

### OpenAI Codex

```
codex plugin marketplace add donnfelker/builder-skills
codex plugin add builder-skills@builder-skills
```

Or, after adding the marketplace, type `/plugins` inside a Codex session and choose **builder-skills**.

### Any agent: all skills

Needs [Node.js](https://nodejs.org).

```
npx skills add donnfelker/builder-skills
```

### Any agent: one skill

```
npx skills add donnfelker/builder-skills --skill new-skills-repo
```

To see every skill before you pick, add `--list`:

```
npx skills add donnfelker/builder-skills --list
```

> [!TIP]
> If you ask an agent to run `npx skills add` for you, the installer may put the skills in `.agents/skills/`, a folder Claude Code does not read. Name the agent to fix it:
>
> ```
> npx skills add donnfelker/builder-skills -a claude-code
> ```

### Manual: clone and copy

```
git clone https://github.com/donnfelker/builder-skills.git
cp -r builder-skills/skills/* ~/.claude/skills/
```

This copies the skills into Claude Code's personal skills folder. Other agents use a different folder. Check your agent's docs.

## How to use a skill

You do not need to type a command. Describe what you want, and Claude picks the matching skill:

```
"Distill this video: https://www.youtube.com/watch?v=..."
-> uses distill-video

"Transcribe this Loom: https://www.loom.com/share/..."
-> uses watch-video

"Read this tweet: https://x.com/example/status/..."
-> uses read-social

"Poke holes in my plan for launching next month"
-> uses revise-plan
```

**Example.** You type:

> I want to share my skills with other people. Make me a skills repo.

Claude loads `new-skills-repo`, asks for the repo name, your GitHub username, and what the skills are for, then builds the repo folder and makes the first commit.

To call a skill by name:

- Claude desktop and Cowork: type `/` and pick the skill from the list.
- Claude Code: type `/builder-skills:new-skills-repo`.

## Updating

| Method | How |
|--------|-----|
| Claude desktop / Cowork | **Customize > Plugins**, open the marketplace, click **Check for updates**. |
| Claude Code | `claude plugin update builder-skills@builder-skills` |
| OpenAI Codex | `codex plugin marketplace upgrade` |
| `npx skills` | `npx skills update` |
| Manual | `git pull`, then copy the skills again. |

## Uninstalling

| Method | How |
|--------|-----|
| Claude desktop / Cowork | **Customize > Plugins**, open **builder-skills**, open its menu, click **Remove**. |
| Claude Code | `claude plugin uninstall builder-skills@builder-skills` |
| OpenAI Codex | `codex plugin remove builder-skills@builder-skills` |
| `npx skills` | `npx skills remove` |
| Manual | Delete the copied folders from your skills directory. |

## Contributing

Found a mistake or have a skill to add? Open an issue or a pull request. See [CONTRIBUTING.md](CONTRIBUTING.md) for how.

## License

[MIT](LICENSE). Free to use, copy, and change.

## Hat tip

Some skills were influenced by [makerskills](https://github.com/coreyhaines31/makerskills) by Corey Haines (MIT License, Copyright (c) 2026 Corey Haines) and have been altered for this repository.

## About the author

Built by Donn Felker.

- X: [@donnfelker](https://x.com/donnfelker)
- Instagram: [@donnfelker](https://instagram.com/donnfelker)
- LinkedIn: [/in/donnfelker](https://linkedin.com/in/donnfelker)
- YouTube: [youtube.com/@donn-felker](https://youtube.com/@donn-felker)
- Web: [donnfelker.com](https://donnfelker.com)
- Substack: [donnfelker.substack.com](https://donnfelker.substack.com)
