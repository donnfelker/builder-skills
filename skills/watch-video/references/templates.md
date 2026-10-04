# Templates

## moments.md (visual mode)

One entry per frame that shows something new. Skip frames that add nothing, such as a talking head that did not change. Quote the transcript only with words that appear in `frames.json`.

```markdown
# Key moments: <title>

## 00:00:15 (frames/frame-00-00-15.jpg)
**On screen:** Login form, email field focused.
**Said:** "So you just open it up and..."
**Note:** Start of the UI demo.

## 00:00:45 (frames/frame-00-00-45.jpg)
**On screen:** Dashboard with four cards.
**Said:** "And here's where you see all your projects."
**Note:** First time the dashboard appears.
```

When reading many frames, work in batches of about 10. For each frame: describe what is on screen in 1 or 2 sentences, note text visible on screen, note what changed from the previous frame, and flag anything that looks like a decision, an action, or a notable event.

## summary.md (visual and multimodal)

```markdown
# Summary: <title>

**Source:** <URL or file>
**Duration:** <hh:mm:ss>
**Watched:** <date>
**Mode:** <visual | multimodal>

## In short
<2 to 4 sentences>

## Key moments
- 00:00:15: <one line>
- 00:00:45: <one line>

## Action items
- <item> [timestamp]

## Decisions
- <decision> [timestamp]

## Quotes worth keeping
- "<exact words from the transcript>" [timestamp]

## Open questions
- <question raised but not answered>
```

Leave out any section with nothing real in it.

Multimodal mode adds:

```markdown
## Multimodal observations
- **Delivery:** <body language, energy, pacing>
- **Visual style:** <design, branding, on-screen text>
- **Audio:** <music, silence, sound quality>
```

Pick the observations that fit what the person asked for: a talk review needs delivery, an ad review needs visual style and pacing, a client call needs tone and reactions.

## Gemini prompt (multimodal)

Write this to `gemini-prompt.md`, then add one line on what the person wants to learn from the video.

```markdown
Watch this video and answer in Markdown.

1. Summarize it in 2 to 4 sentences.
2. List the key moments with timestamps (HH:MM:SS) and one line each: what is shown and what is said.
3. List action items and decisions with timestamps, if any.
4. Describe delivery (body language, energy, pacing), visual style, and audio.
5. Quote up to 5 lines worth keeping, word for word, with timestamps.

Only describe what is in the video. If something is unclear, say so.
```
