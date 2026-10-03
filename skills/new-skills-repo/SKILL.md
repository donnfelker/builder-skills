---
name: "new-skills-repo"
description: "Builds a new public GitHub repo that shares a pack of agent skills, with install steps and a README. Use when you say \"new skills repo\", \"make a skills repo\", \"share my skills\", \"skill pack\", \"skill marketplace\", or \"publish my skills\"."
---

# New skills repo

Build a new GitHub-ready repository that distributes a pack of agent skills. The result installs three ways from one repo: as a single plugin (Claude Code and Cowork), through `npx skills add` (all skills or one skill, across many agents), and by manual clone and copy.

Nothing about the repo is assumed. Every name, link, and personal detail comes from the user. Never invent an author, handle, URL, or repo name, and never carry details over from a previous run.

## Step 1: Collect the inputs

Read the user's request first and take every detail they already gave. Ask only for what is missing. Ask everything in one round (use the question tool if one is available, otherwise a short numbered list in plain text). Do not start building until the required items are answered.

Required:

1. **Repo name.** Kebab-case. This is also the plugin name. If not provided, ask. Do not suggest a name unless asked.
2. **GitHub owner.** The user or org the repo will live under. Needed for every install command.
3. **What the pack is for.** One or two sentences: who it is for and what the skills help them do. This drives the README intro and the tone.
4. **Initial skills.** Names plus one line each. Also ask whether any exist already and where (a local path or repo) so they can be copied in. If the user has none ready, create one placeholder skill named `example-skill` and say clearly that it is a placeholder.

Optional, with defaults:

5. **Tagline.** Default: none. Offer to draft two or three options after the purpose is known.
6. **Author details for the README.** Ask what name to show and which links to include (website, social handles, newsletter, anything else). Default: no author section. Include only the links the user gives.
7. **License.** Default: MIT. Ask if they want something else. Ask what name goes on the copyright line (default: the author name, or the GitHub owner if no author name was given).
8. **Audience technical level.** Default: mixed, so the README leads with the non-technical install path.
9. **Writing rules.** Default: the rules in the Writing rules section below. Ask if they have house style rules to apply instead.
10. **Target directory.** Default: a new folder named after the repo in the current working directory.

Before building, restate the collected values in a short block and get a yes.

## Step 2: Check current conventions

Do not write manifests or install commands from memory. They change.

- Read the current Claude Code documentation for the plugin manifest and marketplace manifest schema.
- Read the README of the `skills` CLI (github.com/vercel-labs/skills) to confirm the discovery layout and the `--skill` and `--list` flags.
- Look at one well-regarded public skills repo for structure and README style. Ask the user for a reference repo they like. If they have none, pick a well-regarded public skills repo. Mirror structure and scannability. Do not copy content or wording.

If any of these cannot be reached, say so, build from the best available knowledge, and list what was not verified in the final report.

## Step 3: Propose, then build

Show the proposed file tree and the README outline. Wait for approval. Then build:

```
{repo-name}/
  skills/
    {skill-name}/SKILL.md
  .claude-plugin/        plugin manifest + marketplace manifest
  AGENTS.md
  CLAUDE.md
  README.md
  LICENSE
  .gitignore
```

### skills/

Flat. One folder per skill, kebab-case, each with a `SKILL.md` that has YAML frontmatter (`name`, `description`). The description says what the skill does and when to trigger it, including phrases a person would say.

Every skill must work when installed alone. If one skill benefits from another, reference it softly ("if `x` is installed, use it, otherwise do Y"). No hard dependencies between skills.

When copying in existing skills, keep their content intact. Remove or flag anything personal to the original owner (names, paths, private URLs, account details) and list what was changed.

### .claude-plugin/

Plugin manifest and marketplace manifest so the whole pack installs as one plugin named after the repo. One plugin for the whole pack, not one per skill. Use the schema confirmed in Step 2.

### AGENTS.md

The single source of truth for any agent working in the repo. Cover:

- What the repo is and who it is for
- Directory layout
- Rules for adding a skill: folder naming, frontmatter requirements, description style, the standalone rule
- How to keep the README skills table and the manifests in sync when a skill is added, renamed, or removed
- Versioning approach
- Writing rules for skill and README content
- A pre-commit checklist

### CLAUDE.md

First line is `@AGENTS.md` so the agents file is imported automatically. Below it, add only notes specific to Claude Code, if any exist. Do not duplicate AGENTS.md content.

### README.md

A first-time visitor should understand it in 30 seconds. Answer "what is this" and "how do I install it" before anything else. Tables and short sections, no long paragraphs. In this order:

1. Name, tagline (if given), and a two-sentence description of who it is for
2. Skills table: skill name linked to its folder, what it does, an example phrase that triggers it
3. Installation, one copy-paste block per method:
   - Claude desktop / Cowork plugin install, written step by step for non-technical readers
   - Claude Code plugin install
   - `npx skills add {owner}/{repo}` for all skills
   - `npx skills add {owner}/{repo} --skill {name}` for one skill
   - Manual clone and copy
4. How to use a skill, with one worked example
5. Updating and uninstalling
6. Contributing, linking to AGENTS.md for the rules
7. License
8. About the author, only if the user gave author details, with only the links they gave

Order the install methods by the audience's technical level from Step 1.

### LICENSE and .gitignore

LICENSE uses the chosen license (MIT by default) with the current year and the copyright name from Step 1. The .gitignore covers OS and editor files.

## Writing rules (defaults)

Apply to every generated file unless the user gave their own rules:

- Plain, direct language and short sentences
- Specific claims only, no marketing filler or hype words
- No em dashes
- Call the same thing by the same word throughout

## Step 4: Verify and report

Check each of these and report the result:

- Every SKILL.md has valid frontmatter with `name` and `description`, and `name` matches its folder
- Every skill appears in the README table, and every table row points to a real folder
- Manifests are valid JSON and reference real paths
- Every install command uses the correct `{owner}/{repo}`
- CLAUDE.md starts with `@AGENTS.md`
- No placeholder text, invented names, or invented links remain (search for braces, "example", "TODO", and "your-")

Initialize git and make one initial commit. Do not push and do not create the remote repo unless the user asks.

Finish with a short report: what was built, what was verified, anything not verified, any placeholder skills that need replacing, and the next steps to publish.