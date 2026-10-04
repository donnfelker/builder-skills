---
name: distill-video
description: "Turns a video, podcast, interview, lecture, talk, or tutorial into a short set of notes on what mattered: the main message, key ideas, lessons, systems, and concrete things to try. Use when you have a transcript (pasted, in a file, or saved by watch-video) or a video link or file, and want the value pulled out of it, even if you only say \"summarize this\". Use when you say \"distill this video\" followed by a link, \"summarize this YouTube video\", \"summarize this transcript\", \"key takeaways from this podcast\", \"turn this transcript into notes\", \"what's worth remembering from this\", or \"break down this lecture\"."
---

# Distill video

Turn a transcript of spoken content into a short body of knowledge: what mattered, what to learn, what to apply, and where to go next.

This is not a shorter transcript. A recap that walks through the video in order makes the reader do the real work of deciding what mattered. Your job is to do that work for them.

## Step 1: Get the transcript

Work out what the input is, then get a transcript from it.

- **Transcript text or file.** Pasted, attached, or a `.txt`, `.md`, `.vtt`, or `.srt` file. Read it directly. Do not ask the user to paste something that is already in a file.
- **Folder.** Look for `transcript.md` first (it has timestamps), then `transcript.txt`, then the closest match.
- **Video link or video file.** If `watch-video` is installed, run it in transcript mode on the link or file, and tell it `distill-video` is the caller. Then read `transcript.md` from the workdir it reports. A second request for the same video returns the saved transcript at once, so do not search for old transcripts yourself. Never ask for visual or multimodal mode from here.
- **Video, but `watch-video` is not installed.** Ask for a transcript, and say that the `watch-video` skill can fetch one from a link. For YouTube without it: open the video, expand the description, click "Show transcript," then select and copy the text.
- **Nothing to read.** Ask for the transcript and stop.

Never write a distillation from a title, a description, or what you already know about the speaker or video. Why: it reads as a summary of the video but is a guess, and the user cannot tell the difference.

## Step 2: Read all of it and size it up

Read the entire transcript before writing anything. Then answer these for yourself (do not print them):

- What is this mainly about, and what question or problem does it address?
- What is the speaker's main message?
- What kind of content is it: teaching, tutorial, interview, persuasion, personal story, technical, philosophical?
- Who is it for?
- One main topic, or several?
- Is the transcript clean enough to analyze with confidence?

Let the answers shape the output. A tutorial needs steps. A philosophy talk needs arguments, not forced action items.

### Transcript problems

Auto-generated transcripts are messy. Expect missing punctuation, no speaker labels, misheard words, `[music]` tags, and timestamps.

- **Timestamps.** When the transcript has them (`transcript.md` from `watch-video` starts each paragraph with one, like `**[00:12:34]**`), add the start time in brackets after each key idea and each quote, such as `[00:12:34]`, so the reader can jump to that spot. Use the time of the paragraph the idea came from. One timestamp per idea is enough. When the transcript has no timestamps, leave them out.
- Fix an obvious mishearing silently only when the meaning is certain. Otherwise keep the original word and flag it.
- If the transcript looks cut off, or parts are garbled, say what you could and could not analyze. Do not present a partial read as the whole piece.

### Long transcripts

Transcripts up to about 2 hours (roughly 25,000 words) fit in one read. For long ones, work in this order:

1. Find the major topic clusters.
2. Pull the strongest ideas from each cluster.
3. Spot ideas that come back in different parts.
4. Merge them into one.
5. Decide which ideas matter across the whole piece.
6. Build the distillation from those.

Do not summarize each section and stack the results. Why: that produces long, repetitive output that follows the video's order instead of its importance.

## Step 3: Decide what is worth keeping

**Keep what is useful, not what is long.** Favor insight, usefulness, original thinking, and ideas that explain something. Cut greetings, intros, sponsor reads, housekeeping, filler, repeated points, jokes that teach nothing, and tangents. Keep a story or example only when it makes an important idea clearer or easier to remember.

**Weigh by importance, not airtime.** A 30-second remark can matter more than a 15-minute segment. Why: speakers spend time on what is fun to talk about, which is not always what is worth knowing.

**Merge repeats.** If the speaker makes the same point five ways, it becomes one idea. Note that it was repeated if the repetition itself signals emphasis.

**Keep the conditions.** Retain qualifications, exceptions, and "this only works if" details that change the meaning. Why: advice stripped of its conditions becomes wrong advice.

**Do not oversimplify technical content.** Keep key terms and nuance. A simpler version that is incorrect is worse than a harder one that is right.

## Step 4: Separate what was said from what you inferred

The reader must always know whose idea they are reading. Use three levels:

1. **Said.** The speaker states it. Write it as "The speaker recommends..." or "[Name] argues..."
2. **Implied.** A reasonable conclusion from what was said. Write it as "An implied principle is..." or "This suggests..."
3. **Derived.** A structure you built from the speaker's ideas, such as a checklist or framework. Label it "Derived framework" and say it is your construction.

Never present a framework you built as one the speaker named or created. Why: one invented attribution makes the whole distillation untrustworthy.

Quotation marks mean "these are the speaker's exact words." Use them only for text that appears in the transcript word for word, apart from fixed mishearings. Do not put quotation marks around:

- a paraphrase, even a close one ("thank God for unanswered prayers" when the speaker said "thank God for the prayers that weren't answered")
- a name you gave an idea ("the boxes and phases process"). Use bold or plain text for your own labels.
- a title or name you know from outside the transcript

If you are not sure the words are exact, find them in the transcript or remove the quotation marks.

In interviews and podcasts, keep the host's questions separate from the guest's ideas. If there are no speaker labels and you cannot tell who said something, say so instead of guessing.

## Step 5: Write the distillation

Use the structure below as a default, not a form to fill. Leave out any section that would only hold filler. A history lecture may have no system. A five-minute video may have two ideas. Never invent content to fill a heading.

**One point, one home.** Each idea appears in exactly one section. Lessons, Put This Into Practice, and Worth Remembering must each add something Key Ideas did not say, or the item is cut. Why: repetition across sections is the most common way these notes get long without getting better.

**Length follows density, not duration.** A 2-hour interview with three real ideas gets a short distillation. Use these as limits, not suggestions:

- Short or thin content (under about 15 minutes, or little real substance): 400 words or fewer.
- Everything else: 1,200 words or fewer. Most land between 500 and 1,000.

Count the words before you save. If you are over, cut until you are under. Do not keep the extra and explain why. Why: going over always feels justified while writing, and that feeling is how distillations turn back into summaries. Being over the limit means something lower-value stayed in. Find it and remove it. Good things to cut first: Keep in Mind items that are minor, mishearing notes that do not change the meaning, a second example of the same point, and any section that partly repeats another. The first response is the highest-value layer. The detail you cut is still available through follow-up questions.

### Template

```markdown
# [Video title or short descriptive name]

**Source:** [speaker or channel, if known] · [length, if known] · [type of content]

## The Video in 60 Seconds

[1 to 3 short paragraphs. What it is about, what the speaker is trying to say,
the main conclusion, and why it matters. Someone who reads only this section
should understand the essence.]

## Key Ideas

### [Short descriptive heading]
[The idea, explained clearly, with its important conditions.]

[3 to 8 ideas. Match the real number. Order by importance.]

## Lessons

- [What the reader should take away, one level above the speaker's words.
  Example. Key idea: the speaker says to build an audience before the product
  is done. Lesson: audience building is part of product development, not a
  launch task.]

## Systems & Frameworks

**Explicit** (described by the speaker)
- [Name or description]: [steps, rule, or model]

**Derived** (built from the speaker's ideas, not named by them)
- [Name]: [steps, rule, or model]

## Put This Into Practice

- [A specific action someone could try this week, tied to an idea above.]

## Worth Remembering

- [A distinction, analogy, example, or counterintuitive point worth keeping.
  Not a quote collection.]

## Keep in Mind

- [Assumptions, unsupported claims, opinion stated as fact, advice that depends
  on context, or a missing counterargument. Only when relevant.]

## Where We Could Go Next

- [3 to 5 follow-ups specific to this content. 2 or 3 is fine for short content.]
```

### Section rules

- **The Video in 60 Seconds.** Covers the whole piece, not only the opening. Do not call it an "Executive Summary."
- **Key Ideas.** Each gets a short heading and a clear explanation. Rewrite rambling speech into clear sentences.
- **Lessons.** Answers "What should I learn from this?" If a lesson only restates a key idea, cut it.
- **Systems & Frameworks.** Look for processes, routines, checklists, decision rules, rules of thumb, mental models, formulas, and diagnostic questions. Use the Explicit and Derived labels whenever both kinds appear. Drop the section if there are none. Do not invent a framework to fill it.
- **Put This Into Practice.** Each action should trace back to a specific idea from the transcript and be concrete enough to try. "Think about how this applies to your life" is not an action. "Before your next post, write the hook first and cut anything that does not support it" is.
- **Worth Remembering.** Only items that are memorable or useful on their own.
- **Keep in Mind.** Help the reader interpret the content. Do not argue with the speaker for the sake of it.
- **Where We Could Go Next.** Specific to this transcript. Examples: turn a framework into a checklist, build a 30-day experiment, compare the approach with another method, expand one idea, pull only the tactical advice, test the strongest and weakest arguments, adapt the system to the user's goal. Never "Would you like to know anything else?"

### Adjust for the type of content

| Type | Focus on |
|------|----------|
| Educational | Concepts, explanations, lessons |
| Business | Strategies, systems, decision rules, where it applies |
| Self-improvement | Principles, behavior changes, exercises, the assumptions behind them |
| Interview or podcast | Themes across a wandering conversation; the guest's ideas, not the host's prompts |
| Tutorial | Prerequisites, steps in order, warnings, details needed to do it |
| Technical | Correct terms and nuance |
| Philosophical | Arguments, assumptions, mental models, open questions; few or no action items |
| Personal story | The point of the story and what it shows; keep it short if there is little to extract |

## Step 6: Save and show

Save the distillation as `distillation.md` and also show it in the chat.

1. **Where.** If the transcript came from `watch-video` or from a file, save in the same folder as the transcript (for `watch-video`, its workdir). If it was pasted, save in the current working folder.
2. **Do not overwrite.** If `distillation.md` already exists there, do not replace it silently. Ask the user. If you cannot ask, save to a new folder named after the video (for example, `distill-<short-slug>/distillation.md`) and say where it went.
3. **No file access.** If you cannot write files here, show the distillation in the chat and say it was not saved.
4. After the distillation, tell the user where the file is in one line.

## Follow-up questions

The user may ask things like "explain point 3 more deeply," "what did the speaker actually say about hiring," "turn this into a checklist," "give me only the action items," "make a 30-day plan from this," or "challenge the main argument."

- Answer from the transcript, not from your distillation. If the transcript is in a file, read it again. Why: the distillation already dropped detail, and a follow-up often asks for exactly what was dropped.
- Keep the same labels: said, implied, or derived.
- If the transcript does not cover the question, say so.
- Answers stay in the chat unless the user asks to add them to the file.

## Final check before you answer

Read your draft once against this list and fix anything that fails:

- **Recap instead of knowledge.** Does it follow the video's order instead of what matters? Reorder by importance.
- **Invented attribution.** Is every "the speaker says" in the transcript? Is every framework you built labeled Derived?
- **Quotes.** Search the transcript for each phrase you put in quotation marks. If the exact words are not there, even if one word differs, fix the quote or remove the quotation marks.
- **Repeats.** Does any point appear in more than one section? Keep it in one.
- **Filler.** Is any section there only because the template has it? Remove it.
- **Vague actions.** Could someone actually do each action? Is each tied to an idea from the transcript?
- **Lost conditions.** Did a "only if" or "except when" get dropped?
- **Too long.** Is it over the word limit for this content? Cut until it is under. Would a reader get the same value from fewer words? Cut more.
- **Honesty.** Did you flag garbled, cut-off, or unclear parts instead of guessing?
