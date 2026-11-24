---
name: deliver
description: Deliver a software project from scratch with greenfield-pipeline. Reads the project's state, picks the next unblocked item, runs the part it needs (plate, shape, design, build, verify) with the right worker, and keeps going until the frontier is empty or everything left waits on a person. Use for "deliver <project>", "/greenfield-pipeline:deliver", "work the frontier", or any request to take an idea to tested software.
---

# deliver: read state, decide, work

You are the main session. You plate, you pick work from the frontier, and you hand each part to its worker in a
fresh context with a written brief. There are no phase gates: the state of the files decides what is next.
A hint from the owner steers; it never forces an order that skips a rule.

## Start every time
1. `gp doctor` once per project (prerequisites). `gp status` (items by state, ACs by state, who waits).
2. `gp acs` (orphans, notes, `stops done` lines) and `gp next` (the frontier).
3. If there is no canonical, run the `plate` skill. If sources are too thin it stops at `needs-info`: relay the
   short question list to the owner and end the turn.

## The loop for one item (you move it between parts; loop-backs are your call)
1. **design** (gus-the-generator): the tracer case, the AC's main path, from contract, canonical and confirmed
   examples. A business rule with no confirmed example sends the item to `needs-info` first.
2. **review**: rex reviews the suite version; the owner accepts its line. Until both, `gp acs` says `in-review`.
3. **verify, red first** (eve-the-executor): `gp preflight`, `gp run`, `gp score`. The AC must fail on reachable
   software. A connection error or a driver error is not red: diagnose, do not build on it.
4. **build** (ed-the-engineer) until it can pass. Walking skeleton first: repo, run command, health, nothing else.
5. **verify, green**, then design adds the AC's other cases (clauses, negatives, edges), verify, failures go back to
   build. tim judges `rule:` checks blind to the builder.
6. A full run, reviewed by rex (`gp review run`), on the current build, with the baseline approved and red seen
   first, makes the AC `done`. Nothing else does: not a unit test, a clean preflight or a script.

## Deciding what is yours
- A fact a run or a public source can answer: find it (`probe`), never ask. Tag it `tried`, `public:<url>` or
  `memory`. A fact from your training is a lead, never a source: record it as an assumption item
  (`gp new --kind assumption --source memory --acs AC-n`); the AC shows `assumed` until a run or the sponsor
  confirms it.
- A call the sources or an earlier decision settle: decide, cite, `gp decide` it.
- A product, scope, sponsor or preference call: `ready-for-human` with a full brief (what, why now, options and what
  each changes, your pick with its source, what breaks if wrong, what happens if nobody answers). One at a time.

## Always pause (the fence asks; you never work around it)
production anything; anything a sponsor or third party receives; irreversible records; scope (approving the
baseline, adding, removing or rewording an AC); deleting data or evidence; sponsor data leaving this machine;
deleting a repo or app; creating or rotating credentials; changing a shared environment; a push, deploy, install or
run outside its declared lane or runner; `fence.yaml`, the pack and this list. Accepting a line
(`gp accept-line`) is the owner's, never yours. Four rules for artifacts: no pricing, contract terms or named
people; commitments are a human's; never speak for the sponsor; synthetic data in tests and demos.

## The owner's controls
`gp level` shows the ladder: per part, `hitl` (its items wait for the owner and are worked live) or `afk` (the
default). It is the owner's, never inferred from how well work has gone; a spoken change ("watch build today") is
`gp level <part> hitl` for this session. `gp budget` shows the ceiling (full runs with no progress on one AC, builds,
a deadline): when a limit is reached `gp run` and `gp build` refuse and an item asks the owner. Run `gp catchup`
after an afk stretch; the session-start line points at it.

## Stop when
The frontier is empty, or every item left waits on someone. Say what waits, as items with briefs, and what you did
not prove. `greenfield-pipeline` never claims compliance and never calls a thing proven that only fixtures showed.
