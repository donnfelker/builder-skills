---
name: example-skill
description: Turns a vague goal into three concrete next steps you can do this week. Use when someone says "help me get started," "I don't know where to begin," "break this down for me," "what should I do first," or "I'm overwhelmed by this project." This is a placeholder skill. Replace it with a real one.
---

# Example Skill

Help the person turn one vague goal into three next steps they can finish this week.

## Steps

1. Ask what the goal is, in the person's own words. If they already said it, skip this.
2. Ask two questions, one at a time:
   - What does "done" look like?
   - What is the deadline, if there is one?
3. Write three next steps. Each step must:
   - Start with a verb.
   - Take under two hours.
   - Be something the person can do without waiting on anyone else.
4. Name the one step to do first and say why in one sentence.

## Output

Use this format:

**Goal:** (one sentence)

**Next steps:**
1. ...
2. ...
3. ...

**Start with:** step number and a one-sentence reason.

## Rules

- Keep it short. No more than 150 words in the final answer.
- If the goal is too big for three steps, say so and pick the first slice of it.
- If `decide` is installed and the person is stuck choosing between options, use it. Otherwise, ask which option they lean toward and why.
