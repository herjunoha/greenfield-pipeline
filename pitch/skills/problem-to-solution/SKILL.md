---
name: problem-to-solution
description: Plan a pitch from very little (often one discovery MoM, or one sentence of an idea) as a shared map of decision tickets, resolve them one at a time until the way to a rigorous Solution Statement is clear, compile the statement, and hand a won deal to greenfield-pipeline. Adapted from Matt Pocock's wayfinder for pre-sales. Invoke deliberately with /pitch:problem-to-solution when a discovery MoM or a loose idea arrives, or to work the next ticket, compile the statement, or hand off.
disable-model-invocation: true
---

A discovery MoM has arrived, or a loose idea. The way from the client's problems to a solution we can pitch and
prove is wrapped in fog. This skill charts that way as a **map** of decision tickets, works the tickets one
sitting at a time, compiles the **Solution Statement**, and at a win hands it to greenfield-pipeline.

Shared rules: `../../references/rules.md`. The statement's shape: `../../references/solution-statement-spec.md`.

## Plan, don't do

Each ticket resolves a decision; the map is done when nothing is left to decide before the pitch. The pull to
just build or write is usually the signal you have reached the edge of the map. One named exception: a
`prototype` ticket (below) may make something to react to, at the lowest fidelity that answers its question.

## Two hard rules

1. **Traceability.** Every element traces: problem (client's words), need, element, proof requirement. No element
   without a need, no need without a stated problem. Cut the element or open a ticket asking which problem it
   serves. No stated problem is left without an element or an explicit out-of-scope decision. Only `stated`
   problems anchor an element; `inferred` ones are confirmed first. This is what makes the statement platable:
   the canonical refuses a requirement with no source.
2. **Deadline.** Record a pitch date. As it nears, every open ticket becomes resolved, an explicit assumption in
   the statement (owner and validation step), or out of scope. Nothing silently vanishes, and an assumption is
   never presented as a fact.

Everything else is guidance. Use judgment; synthesis, spotting gaps, proposing hypotheses, drafting client
questions and parallel research are the point.

## Where things live

```
<alias>/
├── pitch/   sources/  pitch-map.md  tickets.md  deal-factors.md  domain/  solution-statement.md
│            proposal.md  pitch-deck.md  poc/  demo-notes.md  OUTCOME.md
└── greenfield/fence.yaml        (from `gp init`; no deploy lanes)
```

The map is an **index, not a store**: a decision lives in exactly one place, its ticket; the map gists it and
points there. Refer to tickets by title, not a bare id. No tool outside the folder is assumed; do not ask where
to keep the map. `OUTCOME.md` is written by a human only.

## Map template (`pitch/pitch-map.md`)

```markdown
# Pitch Map: [alias]  (DRAFT, needs human review)
## Destination        <Solution Statement ready to pitch. Client outcome: ... Pitch date: ...>
## Problem statement  <the client's problems in their terms, each with source/date and [stated | inferred]>
## Notes              <industry; preferences; deal-factor facts with sources; our decision-makers by role>
## Decisions so far   <closed ticket title: one-line gist (source, date)>
## Needs info         <ticket title: asked <date>, owner <role>, next nudge <date>>
## Not yet specified  <in-scope fog not yet sharp enough to ticket>
## Out of scope       <ruled beyond the destination, with why>
## Needs human review <confidential items, commitments, unresolved conflicts>
```

Open tickets live in `tickets.md` grouped by state, not in the map. Traceability is `Traces to` on each ticket,
assembled at compile time.

## Ticket template (`pitch/tickets.md`)

```markdown
### <Ticket title: the question>
Type: research | prototype | grilling | task
State: ready-for-agent | ready-for-human | needs-info | closed (done | wontfix)
Commits us: yes                      (only when the answer would commit us)
Owner / Blocked by / Traces to: <role; ticket titles or none; the problem or need it serves>
Answer: <on resolution, with source and date>
Asked / next nudge / Settled / Still needed / Questions for a human to send   (needs-info only)
```

- States are greenfield-pipeline's, so a ticket crosses at hand-off unchanged. No triage state, no claim step:
  one main session works the map. `Blocked by:` lists titles; no cycles. A ticket that traces to nothing is
  suspect. Size a ticket to one sitting or one client conversation.
- A ticket whose answer would commit us carries `Commits us: yes` and is `ready-for-human`.
- The **frontier** is the unblocked `ready-for-agent` and `ready-for-human` tickets; `needs-info` stay listed.

## Fog of war

The test: can you **state the question precisely now** (not "can you answer it now")? Sharp but blocked is a
ticket. Not sharp is fog, written loosely under "Not yet specified"; do not pre-slice it. Fog gathers only toward
the destination; ruled-out work closes `wontfix` with why.

## Ticket types

`ready-for-human` is worked with a human; `ready-for-agent` is the agent alone. The agent can grill our own team
live but cannot interview the client.

- **Research** (agent): outside facts a decision waits on, **including the domain**: terms, standard workflows,
  typical business rules and regulations of the client's industry. Tag every finding `public:<url>`, `from MoM`,
  `human-provided` or `memory`. `memory` is a lead, never a source: a rule resting on it or on an unconfirmed
  `public` note is `confirmed: no` and becomes a client question. Notes go to `pitch/domain/`. Deal-factor
  questions are resolved by `pitch:deal-factor`. Run research tickets in parallel.
- **Prototype** (human): make something to react to, at the lowest fidelity that answers the question: a described
  wireframe, or a screen through the pack's `documents.mockup` skill if it names one; a working demo through
  `pitch:proof-of-concept` only when the pitch needs live behaviour. The answer records what was proved, what
  failed to prove and the consequence for the statement. `failed` is a legitimate answer.
- **Grilling** (human): conversation, the default (use a grilling skill if one is installed, else do the same).
  **Worked examples are collected here**: for each business rule, one concrete input and output the client
  confirms. An example costs the client one line and is the only legitimate source of an expected business value.
- **Task** (either): manual work that unblocks a decision (a sample export, mapping the buying committee,
  booking the stakeholder who owns the answer).

## Deal-winning lens (guidance, not a form)

While charting and after each answer, consider who is on the buying committee and what each cares about, how the
client will judge options, alternatives (competitors, do-nothing, build in-house, buy off the shelf), the budget
signal (no amounts), timeline and forcing events, why us, and what could make us lose despite a good solution.
Known facts go in Notes with a source; a sharp unknown becomes a ticket; a vague one stays fog. Read the pack's
lessons at chart time (`gp pack show lessons`; no such key means none) as guidance, never a checklist.

## Client loop

When a ticket needs the client, write two to five plain-language questions with a line on why we ask, for a
human to send. Set the ticket `needs-info` (asked: "not yet sent" until the human sends; next nudge date). Waiting
never stops the map. Accept answers only from a human, recorded with source and date and saved under
`pitch/sources/`; a partial answer becomes a new, sharper ticket; contradictions are kept with dates and flagged.

## Four modes

### Chart the map
The user supplies a MoM or a sentence.
0. Create the deal folder, save the source under `pitch/sources/`, and run `gp init` (it writes
   `greenfield/fence.yaml` with no deploy lanes). Show the fence to the owner: `fence.yaml` is a decision file, and
   from now on any change to it asks.
1. Read the source. Extract problems, expectations, constraints and deadlines, each `stated` or `inferred`; note
   conflicts and vague claims. Ask at most one clarifying question. From a one-sentence idea, ask only for the
   minimum needed to name the problem; invent no requirement.
2. Name the destination with our team: pitch date and client outcome.
3. Map the frontier by grilling breadth-first across problems, needs, **domain** and the deal lens. If no fog
   surfaces, stop and ask how to proceed.
4. Create the map, then the sharp tickets, wiring `Blocked by` in a second pass. A vague claim ("faster, better")
   becomes a metric question. A request that would be a commitment becomes a `Commits us: yes` ticket. A
   contradiction is kept with both sources under "Needs human review". Unfamiliar terms and likely business rules
   become research tickets and a grilling ticket for worked examples.
5. Prepare client questions; start research tickets in parallel.
6. Stop: charting resolves nothing. Report the frontier in priority order, the needs-info list, and recommend one
   ticket first.

### Work through the map
Load the map, not every ticket. Take the user's ticket or the first frontier ticket. Resolve it by type, record
the answer with source and date, close it, add a gist to "Decisions so far". Then update the map: new tickets,
graduate fog, rule out of scope, fix invalidated tickets, check traceability, flag orphans. Reopen tickets when the
world changes (new sponsor, competitor, budget shift, moved deadline, a failed proof). Watch the pitch date.

### Compile the Solution Statement
When the way is clear or the deadline rule has run, write `pitch/solution-statement.md` to the spec, from **closed
tickets only**. An element with no closed ticket and no traced problem is not written, whoever asks; the refusal
goes under Gaps. A business rule with no confirmed example is a Gap. `Why us` lines need an offering id or a human
source: read `gp pack show offerings`, and treat a file with no `Approved by:` line (or no such key) as absent,
so `Why us` is human-only and the report says so. An element whose natural stack lies outside every reference
stack in the offerings goes to Gaps for a human to decide. Fill the Traceability index from the elements. Record
proof honestly: `demonstrated` only with a human attestation, a failed proof stays `failed`. The map is done when
the statement is compiled and every ticket is closed, an assumption, or out of scope. Then point to
`pitch:business-proposal` and `pitch:pitch-deck`.

### Hand off
Runs when a human has written `pitch/OUTCOME.md`. Lost or parked: set the statement's status to `closed <date>`,
write nothing else, keep the folder. Won: follow `../../references/handoff.md`.

## Out of scope for this skill

Production-grade build; work after the hand-off (that is `greenfield-pipeline:deliver`); drafting the proposal and
deck (sibling skills); pricing and estimates; CRM integration.
