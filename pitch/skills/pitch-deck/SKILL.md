---
name: pitch-deck
description: Draft the pitching deck from a compiled Solution Statement, with a fixed slide map and speaker notes that carry every slide's source. Use for pitch deck, pitching slides, presentation for the pitch, or after problem-to-solution has compiled the statement. Stops if no compliant statement exists.
---

Draft the deck from `pitch/solution-statement.md`. Shared rules: `../../references/rules.md`. Determinism,
pre-flight, placeholders, sourcing, rendering and the internal report: `../../references/drafting-contract.md`.
Run its pre-flight first and stop on any failure.

## Fixed slide map

| Slide | Content | Source |
|---|---|---|
| 1 | Title | `[[HUMAN: title, presenter, date]]` |
| 2 | Your situation (problems in the client's words) | Problem statement |
| 3 | The outcome you want | Outcome |
| 4 | From problem to solution (one-line map) | Traceability index |
| 5 to N | One slide per element: problem, proposal, fit | Solution elements |
| N+1 | Proof: what the demo shows and its status per element | Proof requirement, Proof evidence |
| N+2 | Why us | Why us |
| N+3 | Scope and assumptions | Scope boundaries, Assumptions |
| N+4 | Next steps | Assumption validation steps, Pitch date |
| Appendix | Traceability table; elements beyond the sixth | Traceability index, Solution elements |

More than six elements: the first six (statement order) get main slides; the rest go to the appendix, one slide
each. No commercials slide unless the user asks (`[[HUMAN: commercials slide]]`).

## Slide rules

- The headline is a one-sentence claim from the statement, not a topic label.
- At most three short bullets.
- **Speaker notes carry the source**: the statement line, the deciding ticket, and one line on what to say. A
  slide with no source is deleted.
- The proof slide states `demonstrated`, `pending` or `failed` honestly. A "live demo here" cue appears only for a
  `demonstrated` element, and anything mocked in the live demo is labelled on the slide.
- Visuals are `[[VISUAL: ...]]` placeholders, never invented logos, charts or figures.
- Outcome numbers stay `TBD` until the statement has them.

## Output

- `pitch/pitch-deck.md`: the slide-by-slide outline with speaker notes. The deterministic master.
- The built `.pptx`, when asked, through the pack's `documents.pitch_deck` skill (`gp pack show documents`), else a
  general presentation skill if installed, with the pack's brand tokens (neutral tokens if none). Markdown alone if
  none is installed; say so.
- `pitch/pitch-deck-report.md`: internal, per the drafting contract's report, plus confirmation that every slide
  has a source.

Nothing is sent: a human presents and sends.
