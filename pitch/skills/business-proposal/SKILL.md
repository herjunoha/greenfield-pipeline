---
name: business-proposal
description: Draft the business proposal from a compiled Solution Statement, with a fixed section map so the same statement always yields the same proposal structure. Use for business proposal, technical proposal, draft the proposal, proposal document for the pitch, or after problem-to-solution has compiled the statement. Stops if no compliant statement exists.
---

Draft the proposal from `pitch/solution-statement.md`. Shared rules: `../../references/rules.md`. Determinism,
pre-flight, placeholders, sourcing, rendering and the internal report: `../../references/drafting-contract.md`.
Run its pre-flight first and stop on any failure.

## Fixed section map

| # | Section | Source | Rule |
|---|---|---|---|
| 1 | Executive summary | Outcome, Problem statement, element names, Why us | Four short paragraphs: problem, outcome, approach, why us. |
| 2 | Your situation | Problem statement | Each problem in the client's words with source; keep P-ids out of client text. |
| 3 | Outcome and success measures | Outcome | `TBD` stays `TBD`. |
| 4 | Proposed solution | Solution elements | One subsection per element in statement order: problem, need, proposal, fit. |
| 5 | How we will prove it | Proof requirement, Proof evidence | Per element; `failed` stated plainly with what it changes; `pending` says so. |
| 6 | Why us | Why us | Theme, criterion, delivering elements. |
| 7 | Scope | Scope boundaries | In and Out as written. |
| 8 | Assumptions and dependencies | Assumptions | Owner role and validation step. |
| 9 | Commercials, timeline, team, terms | none | `[[HUMAN: ...]]` placeholders only; an approved commitment may fill one, marked `(approved commitment)`. |
| 10 | Next steps | Assumption validation steps, Pitch date | A human completes the rest. |
| A | Appendix: traceability | Traceability index | Client-facing names. |

Section 9 is never derived: pricing, timeline, team and terms are human inputs.

## Output

- `pitch/proposal.md`: client-facing, marked DRAFT. The deterministic master.
- The built file, when asked, through the pack's `documents.proposal` skill (`gp pack show documents`), else a
  general document skill if installed, with the pack's brand tokens (neutral tokens if none). Markdown alone if
  none is installed; say so.
- `pitch/proposal-draft-report.md`: internal, per the drafting contract's report.

After a win the proposal is not reused as the requirement: the canonical is plated from the statement, and the
signed proposal is a source for contract facts only. Nothing is sent: a human sends.
