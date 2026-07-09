---
name: final-polish
description: Append a concise, human-style note to your final answer after
  completing a task — the approach, what changed, and why. Use whenever you
  finish a coding task, config change, refactor, bug fix, or any non-trivial
  analysis that produced changes or decisions.
---

# Final Polish

After you finish a task, add a short note at the end of your answer explaining
what you did and why — like a teammate leaving a quick comment, not a report.

## When to add it

You finished a task involving **changes or decisions**: code edits, config
changes, refactors, bug fixes, multi-step analysis with a conclusion.

## When to skip it

- Pure Q&A — no files changed, no decision made
- Trivial change (typo, one-line tweak)
- User asked for brevity, code-only, or "just do it"
- Nothing meaningful to explain

## What to cover

Keep it tight. Drop any section with nothing to say.

- **Approach** — the route you took and why this one (1–2 sentences)
- **Changes** — concrete: files, functions, behaviors touched. Many changes →
  bullet list; group by area if it helps the reader.
- **Reason** — the root cause or tradeoff behind the change
- **Notes** *(optional)* — risk, follow-up, known limitation

## How to write it

Write like a person, not like an AI summary.

- Short sentences. State facts.
- Say what changed and why, directly. No padding.
- Drop empty adjectives — comprehensive, robust, seamless, deep, powerful.
- No filler openers — First, Moreover, In conclusion, It's worth noting.
- No rule-of-three lists unless each item earns its place.
- No em-dash chains. Don't symbolize what a simple change "represents".
- Keep code, terms, and proper nouns in their original form.

## Length

Length follows the work, not a fixed number.

- Small change → one or two lines.
- Big refactor → name every file and function you touched.
- The cap is on padding, not on lines. Every line must carry information.
- Don't collapse real changes to look terse. Don't pad to look thorough.

## Example

> Approach: reuse open DB connections via a pool instead of one per request.
> Changes: `db.ts` adds `Pool`; `handler.ts` switches to `pool.query`.
> Reason: connection handshake was the bottleneck under load. Pooling removes it.
> Notes: pool size fixed at 10 for now — revisit if we see waits.
