# Drafting contract

Shared by `business-proposal` and `pitch-deck`. Written once.

## Determinism

- Same statement plus same human inputs gives the same sections, in the same order, with the same source
  mapping; only wording may vary. No added sections, no reordering, no new claims, no "improving" the solution.
- Both skills read only the Solution Statement (`pitch/solution-statement.md`) and human inputs given in the
  conversation. Never raw notes, never the map.

## Pre-flight (stop and report on any failure)

1. A statement exists and follows `solution-statement-spec.md`. Otherwise point to `problem-to-solution`; never
   reconstruct one from raw notes.
2. Read Gaps. If non-empty, list them and ask whether to proceed. If proceeding, gaps appear only in the
   internal report.
3. Only commitments listed in the statement's Commitments section may appear as commitments.
4. `demonstrated` counts only with an attestation line (role, date, demo-notes link); otherwise treat the proof
   as `pending`.
5. Status is `DRAFT` or later; a `closed` statement is not drafted from.
6. **Every sentence about what our company can do traces to an offering id or a human source in the statement.**
   One that does not is deleted, or listed as `[[HUMAN: ...]]` in the internal report.

## Placeholders

- `[[HUMAN: ...]]` for an input only a human can give.
- `[[VISUAL: ...]]` for a visual to be supplied.
- `TBD` for a missing fact.

## Sourcing

- Every client-facing sentence has a source in the statement, otherwise it is deleted.
- Never soften a failed proof and never hide a gap from the internal report.
- Keep P/E/A ids out of client-facing text; use their names.

## Rendering

The markdown is the deterministic master. Build a file from it with the skill the pack names (`gp pack show
documents`: `proposal` or `pitch_deck`), else a general document or presentation skill if one is installed, else
stop at markdown and say so. Brand tokens come from `gp pack show brand`; with none, use neutral tokens. Never
invent branding. Client-facing text is in the pack's `language`; internal reports follow the owner's working
language.

## Internal report (every draft)

Every placeholder; statement items not used and why; gaps; `pending` and `failed` proofs; confirmation that zero
client-facing sentences lack a source.
