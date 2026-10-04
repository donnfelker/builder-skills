# Examples

One worked example per skill: what you say, and what the skill does.

The outputs are short, hand-written illustrations, not exact captures. Real runs give longer, more detailed answers.

---

## `distill-video`

**Try saying:** "Distill this video"

**You:** *"Distill this video: https://www.youtube.com/watch?v=..."*

**distill-video:** Gets the transcript (through `watch-video` if it is installed, otherwise it asks you to paste one), reads all of it, and returns short notes:

```
# How to Price a Side Project
Source: Example Channel · 48 min · teaching

## The Video in 60 Seconds
...
## Key Ideas
### Charge before you build [00:04:12]
...
## Put This Into Practice
- Write one sentence that names who pays and what they pay for.
```

The notes cover the main message, key ideas, lessons, and things to try. They mark what the speaker said apart from what the skill inferred.

---

## `new-skills-repo`

**Try saying:** "Make a skills repo"

**You:** *"I want to share my skills with other people. Make me a skills repo."*

**new-skills-repo:** Asks in one round for the repo name, your GitHub username, what the skills are for, and which skills to include. It restates your answers, shows the file tree and README outline, and waits for a yes. Then it builds the repo with a README, install steps, plugin manifests, `AGENTS.md`, and a license, and checks that every link and install command is correct.

---

## `read-social`

**Try saying:** "Read this tweet"

**You:** *"Read this tweet: https://x.com/example/status/1234567890"*

**read-social:** Tries free ways to read the post first, and asks before using a paid service. It returns one line plus the same JSON shape for every site:

```
@example · x · 2026-10-03 · "The post text..."
```

```json
{
  "platform": "x",
  "author": { "handle": "@example", "name": "Example Person" },
  "posted_at": "2026-10-03T16:53:00Z",
  "text": "The post text.",
  "engagement": { "likes": 51, "reposts": 13, "replies": 9, "views": null }
}
```

If part of the data is missing, it says what is missing and what would get it.

---

## `revise-plan`

**Try saying:** "Poke holes in my plan"

**You:** *"Poke holes in my plan for moving across the country in March."* (with the plan pasted or in a file)

**revise-plan:** Saves the plan to a working file, such as `cross-country-move-plan-revisions.md`, and reviews it for gaps, order, and risks. It replies with:

- **Verdict:** Revised, Blocked, or Converged.
- **Material issues:** ranked by severity, each with the smallest fix. Example: "High: the movers are booked before the lease is signed. Sign the lease first."
- **Revised plan:** written to the working file, ready for the next run.

Run it again after you make changes. It stops changing the plan once nothing material is left to fix.

---

## `watch-video`

**Try saying:** "Watch this video"

**You:** *"Watch this Loom: https://www.loom.com/share/..."*

**watch-video:** Checks what tools your computer has, gets the transcript from the site's captions or from Whisper running on your computer, and saves it to a folder:

```
loom · Weekly Update · 12:40 · transcript · 1,842 words
videos/loom-weekly-update-2026-10-04/
```

Ask for "key moments" to add screenshots of what is on screen. Ask for "multimodal" to send the video to Google Gemini. It asks before uploading anything.
