---
name: "revise-plan"
description: "Stress-tests a plan and returns the smallest revision that makes it more likely to succeed. Use when you have a plan for a project, launch, trip, move, or any multi-step goal and want it checked before you act on it, even if you only ask for a second opinion. Use when you say \"revise my plan\", \"review this plan\", \"stress-test this plan\", \"poke holes in my plan\", \"what is my plan missing\", \"is this plan solid\", or \"will this plan work\"."
---

# Revise plan

Stress-test the supplied plan and return the smallest revision that materially improves its likelihood of success.

This skill is built to run repeatedly. Each revised plan becomes the next run's input. So preserve useful decisions, avoid unnecessary churn, and stop when no material improvements are justified. A review that rewrites a working plan every time never lets the plan settle.

## Input

- **Plan.** The plan to review. It may be pasted, attached, in a file, or earlier in the conversation. If more than one version exists, use the most recent revised plan unless the user points to another. If you cannot find a plan, ask for it and stop.
- **Optional updates.** New information, answers to earlier questions, or changes in direction. There may be none.

If the user says the plan is final, skip the review and return only the clean execution copy described under [Revised Plan](#revised-plan).

## Establish context

Read the entire plan before reviewing it. Extract its intended outcome, success criteria, constraints, dependencies, and explicit fixed decisions. Use relevant conversation context when available.

- Treat the plan as sufficient to begin. Do not require a separate context form.
- Do not ask the user to repeat information already supplied.
- Use explicitly stated information directly. Label consequential inferences `[ASSUMPTION]`.
- Carry existing `[ASSUMPTION]` labels forward until an update confirms or refutes them. An assumption that has survived earlier reviews is still an assumption.
- Do not treat existing implementation choices or inferred preferences as fixed decisions.
- Missing constraints mean "unknown," not "unlimited."
- If the goal or success criteria are implicit but reasonably clear, proceed with that interpretation. Make it visible in the revised plan where useful.
- Follow explicit user updates when they supersede earlier information. Flag unresolved conflicts only when they materially affect execution.

## Review standard

Judge the plan against its intended outcome and constraints, not against a generic ideal. Match the depth of review to the scale and stakes of the work.

A material issue changes what someone should do, in what order, with what resources, or under what conditions. Exclude cosmetic preferences, speculative edge cases, and additions whose benefits do not justify their costs.

If the plan already contains a Decision History and no updates are supplied, it has been reviewed before with no new information. Revise it only for Critical or High issues.

Review these dimensions without forcing an issue into every category:

1. **Goal fit.** If every step succeeds, is the intended outcome achieved? What necessary work is missing? What work does not contribute?
2. **Assumptions.** What must be true? Which uncertain assumption would cause the greatest disruption if false?
3. **Sequencing.** What is out of order, blocked, or dependent on unfinished work?
4. **Feasibility.** Is the plan practical within its stated constraints? Explain the basis for challenging estimates.
5. **Failure modes.** What consequential failures are plausible? How would they be detected early, and what response is practical?
6. **Efficiency.** What can be cut, merged, simplified, or safely run in parallel, accounting for shared resources and coordination costs?

## Use judgment before asking

Default to completing the review and revision in the current response.

Distinguish between:

- **Design choices you can reasonably recommend.** Choose a sensible default and revise the plan.
- **User-specific facts you cannot know.** Ask only if the answer is necessary to avoid a materially wrong revision.

An unspecified detail is not automatically a blocker. Prefer a useful, reversible decision over a clarification question. Present new design choices as recommendations, not as facts about the user's requirements.

For a small project, such as a weekend trip, a party, or a garage cleanout, do not request budgets, deadlines, owners, or organizational context unless their absence creates a concrete execution problem.

For example, when reviewing a plan for a family reunion, you can decide open details such as the order of activities or who brings what when the plan leaves them open and they affect execution. If the plan starts with a venue already booked, do not add venue-search steps unless required.

Ask a question only when all three conditions apply:

1. The answer is not already available or reasonably inferable.
2. Different plausible answers would materially change the plan.
3. Proceeding on an assumption would create significant risk, waste, or rework.

If a reasonable, reversible assumption allows progress, label it and proceed.

If a missing answer blocks only part of the plan, revise the unaffected portions and identify the specific blocked decision. Do not block the entire review unnecessarily.

Ask at most three questions, ranked by impact. Explain which decision depends on each answer. Carry forward genuine unanswered blockers without creating duplicates.

Zero questions is the preferred outcome when the plan provides enough direction.

## Revision rules

- Keep what works, including its wording. Change a step only when you can name the material problem it fixes.
- Prefer the smallest effective fix. Account for the effort, complexity, and risk introduced by the fix itself.
- Do not expand the project beyond its intended purpose.
- Do not invent facts, commitments, available resources, or precise estimates. Label uncertain estimates `[ESTIMATE]`.
- Where useful, put a cheap test of a high-impact assumption early. State what result would change execution. Do not add tests that would not influence a decision.
- Respect explicit fixed decisions. If they make the goal infeasible, surface the conflict instead of silently changing them.
- Preserve phase names, structure, and step IDs unless a material issue requires changing them. Do not renumber unchanged steps.
- Add owners, estimates, dependencies, or done criteria only where they materially improve execution. Do not force every plan into a larger template.
- Every addition to the plan (step, assumption, risk, or history entry) must trace to a listed issue or a user update. Avoid length added solely for explanation or completeness.
- Consult any Decision History included in the plan. Entries marked user-decided are fixed decisions. Entries marked review-recommended are defaults chosen by an earlier review: correct them whenever you can name a specific defect. Reopen a user-decided entry only when new evidence or changed constraints warrant it. Explain why.
- Distinguish a fix incorporated into the plan from a result validated in practice. Repeated review does not establish real-world feasibility.

## Output format

Return these sections, in this order, with these headings.

### Verdict

Choose one and briefly explain:

- **Revised.** Material improvements made. No critical decisions remain blocked.
- **Blocked.** Missing information or conflicting requirements prevent a viable complete plan, even if unaffected portions were improved.
- **Converged.** No supported changes would materially improve execution.

Convergence means no further revision is justified by the available information. It does not mean the plan has been validated in practice. If progress now depends on an answer or external evidence, identify it. Do not recommend another identical review without new information.

### Material Issues

Rank issues by severity:

- **Critical.** Prevents the goal or violates a hard constraint.
- **High.** Substantially threatens success or causes costly rework.
- **Medium.** Meaningfully changes execution.

For each issue, provide:

- Issue ID and severity
- Problem
- Evidence from the plan, or explicitly labeled inference
- Consequence if ignored
- Smallest effective fix

List only issues that warrant changing the plan or require a blocked decision to be resolved. If none, write "None."

### Revised Plan

Return the complete plan in a single fenced block, ready to execute or paste into the next run. Never use "unchanged" or "see above" as a substitute for plan content. The next run sees only what is inside the block.

Preserve the input's structure. Where a listed issue calls for it, incorporate consequential assumptions, material remaining risks, and blocked decisions at the point they affect execution. For risks that warrant monitoring, include an observable warning sign and the action it triggers.

Keep enough context inside the plan for the next review to understand its purpose and consequential decisions without needing this review's other sections.

When a revision makes a material decision, preserve or append a compact Decision History within the plan. Record only material decisions, their rationale, and conditions for revisiting them. Mark each entry user-decided or review-recommended. Merge duplicates and superseded entries without losing relevant reasoning. Distinguish decisions adopted in the plan from outcomes validated by evidence. Omit the Decision History when no material decision has been made.

**Clean execution copy.** When the verdict is Converged, or the user states the plan is final, return the plan with the Decision History removed and `[ASSUMPTION]` labels removed from assumptions that an update confirmed. Keep unresolved assumptions and open risks that affect execution. Make no other changes.

If the plan came from a file, ask once before overwriting it with the revised plan. If the user already agreed in this conversation, save without asking again.

### Changelog

List each material change and the issue ID or user update it resolves. Explain any reversal of an earlier decision. If nothing changed, write "None."

### Questions (only if needed)

Include this section only when questions meet the criteria under [Use judgment before asking](#use-judgment-before-asking). For each, identify the affected decision and what can proceed while awaiting an answer.

Make sure any question that blocks execution is also captured at the relevant point in the revised plan, so it survives the next run.
