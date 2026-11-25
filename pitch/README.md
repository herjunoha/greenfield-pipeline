# pitch

A company-agnostic plugin that takes a foggy software idea, often one discovery MoM or one sentence, to a won
deal: a traceable **Solution Statement**, a proposal, a pitch deck, an optional proof-of-concept demo, and a
hand-off into `greenfield-pipeline` at the win. No industry, company, product or stack is assumed.

Adapted from Matt Pocock's `wayfinder` skill (`mattpocock/skills`, engineering): its map of decision tickets, fog
of war and one-ticket-at-a-time loop are kept; the issue tracker and claiming are replaced by files in the deal
folder, and a traceability spine, a deal lens, a client loop, a deadline rule, a domain pass and a hand-off are
added.

Copyright 2026 Herjuno Hestu Adhimarta. License: Apache-2.0, see `../LICENSE`.

**Status: version 0.1.0, validated on a fixture only (`acme-freight`, fictional).** The structure, the statement
against its spec and the seam to `greenfield-pipeline` (a statement plated by the hand-off mapping passes `gp acs`
with no orphan) are tested. No live model session has run the skills end to end, and no real deal has passed.

## Skills

- `pitch:problem-to-solution`: chart the map from a MoM or a sentence, work tickets, compile the statement, hand
  off at the win. Judgment-driven, user-invoked.
- `pitch:deal-factor`: research buying committee, criteria, competitors and risks; sourced findings and client
  questions. Research only.
- `pitch:business-proposal`: draft the proposal from the statement. Deterministic.
- `pitch:pitch-deck`: draft the deck from the statement. Deterministic.
- `pitch:proof-of-concept`: the smallest working demo of named proof requirements. User-invoked.
- `pitch:retro`: propose small changes to the pack from a finished deal. User-invoked.

```
discovery MoM or one sentence
   |
   v
problem-to-solution <--- deal-factor           (research tickets)
   |  \
   |   prototype ticket --> proof-of-concept --> attested demo back into the map
   v
Solution Statement   (the only interface between the pitch skills)
   |--> business-proposal
   |--> pitch-deck
   v
win --> hand-off --> greenfield-pipeline canonical + items --> greenfield-pipeline:deliver
OUTCOME written --> retro (suggested)
```

Shared rules: `references/rules.md`. The statement: `references/solution-statement-spec.md`. Drafting:
`references/drafting-contract.md`. The win hand-off: `references/handoff.md`.

## Dependencies, and what degrades without each

- **`greenfield-pipeline`: required.** Its `gp` command (`init`, `new`, `acs`, `pack show`, `retro`) and its fence
  guard the deal folder, so every artifact is a draft by enforcement, not by hope. Without it the skills stop at
  their first line.
- **A pack** (the bundled generic pack counts). `gp pack show <key>` reads a `pack.yaml` key, or the text of
  `<key>.md` in the pack folder. `pitch` reads `language`, `brand`, `documents`, `lessons` and `offerings`; a key
  that is missing means none.
- **`offerings.md`** (optional, in the pack): where "why us" comes from. A human at the company writes or approves
  it, with an `Approved by:` line; an unapproved file is treated as absent. Without it the plugin runs, `Why us` is
  human-only, and the reports say so. Shape: per offering `O1`, what we deliver, reference stacks, team shape (roles
  only), approved proof points, how it differs from alternatives, and `Does not do` (these feed Gaps).
- **Document skills** (optional): the pack's `documents.proposal`, `documents.pitch_deck` and `documents.mockup`.
  Without them the drafting skills write markdown only.

## The deal folder

```
<alias>/
├── pitch/   sources/  pitch-map.md  tickets.md  deal-factors.md  domain/  solution-statement.md
│            proposal.md  pitch-deck.md  poc/  demo-notes.md  OUTCOME.md
└── greenfield/fence.yaml
```

The same folder carries into `greenfield-pipeline` on a win. A lost or parked deal keeps its folder.

## Checks

`python -m pytest tests/test_pitch.py` (from the repository root) runs the structure checks, the statement fixture
against its spec, the seam to the core and the pack-file reads. The core's leak test also scans this folder.

## Not built, not proven

A live end-to-end run of the skills; a real deal; the whole chain (MoM to a release candidate); the offerings
handling beyond the pack read and the redact check.
