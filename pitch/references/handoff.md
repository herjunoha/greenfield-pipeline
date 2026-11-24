# Hand-off at the win

## Trigger

A human writes `pitch/OUTCOME.md` as `won` (with the date and the deciding role) and places the signed proposal,
contract or approval record in `pitch/sources/`. Lost or parked: set the statement's status to `closed <date>`,
write nothing else, keep the folder (deleting evidence is on the always-pause list).

## What crosses, in order of weight

1. **The Solution Statement: the main hand-off, always present.** Everything greenfield-pipeline plates comes
   from it. A deal with no statement has nothing to hand off: stop and point to `problem-to-solution`.
2. **The prototype, second and only if one was built.** `pitch/demo-notes.md` is a supporting source. It never
   adds a requirement the statement lacks, and where the two disagree the statement wins. If it says
   `reusable: yes` and a human accepts a **copy** (no history) as a diff, the product repo's skeleton starts from
   it; otherwise it is a reference, the skeleton is built fresh, and the prototype's checks run as the first
   tracer's reference.

The signed document supplies **contract facts only** (item names, effort, legal entity, sign-off roles), from the
document or a human. A scope difference from the statement becomes a `ready-for-human` item; it is not plated
quietly.

## Steps

1. **Freeze the statement.** Set Status to `handed over <date>`. Later changes go to the canonical.
2. **Copy** the frozen statement and the signed document into `greenfield/sources/` as received. Plate with
   `greenfield-pipeline:plate`, the statement as the primary source:

   | Statement | Canonical |
   |---|---|
   | Outcome | `project.objectives` |
   | Problem statement | a source with aliases P1, P2...; the client's words go in the excerpts each AC cites |
   | Solution elements | `requirements` (`statement` from the MUST line, `acceptance` from its acceptance line, `surface`, `source: solution-statement.md#<element heading>`) |
   | Each element's Surface | `project.surfaces` (`name`, `kind`) |
   | Domain terms | `project.glossary` (`term`, `meaning`, `source`, `confirmed`) |
   | Domain rules | the context of the requirement they bind |
   | Worked examples | `examples` (`source: sponsor-confirmed` only when confirmed by a role and date; otherwise `agent`) |
   | Data handled | `project.data_classes` |
   | Each regime the client named | `project.regulated`, plus one `ready-for-human` item |
   | Scope Out | `project.out_of_scope` |
   | Assumptions | `project.assumptions`; those with `client must confirm: yes` also become `needs-info` items with `--kind assumption` (one item per question: an open `needs-info` ticket that already is that question is the item) |
   | Approved commitments | one `ready-for-human` item each ("carry into the baseline"), since baseline scope is a one-way door; a timeline commitment lands in `project.timeline` once accepted |
   | Gaps | one `needs-info` or `ready-for-human` item each, except a gap an open ticket or assumption item already covers, and a gap about why-us or deal factors, which stays in `pitch/` |
   | Open `needs-info` tickets | `needs-info` items, keeping what is settled and what is still needed |
   | Why us, deal factors, win themes | not carried; they stay in `pitch/` |

   Ticket states are greenfield-pipeline's own, so they cross unchanged. A ticket marked `Commits us: yes` that
   was never approved is a commitment candidate: a `ready-for-human` item, not a timeline entry.
3. **Attach the prototype**, if any, as above. Its own result is never evidence in greenfield-pipeline.
4. **Items** are created with `gp new` (one per row above that says "item"), each with a full brief.
5. **Report:** what was plated (`gp acs` prints `orphans: none`), the items created, the prototype status, and the
   next step `greenfield-pipeline:deliver`.

`pitch` writes nothing in the folder after the hand-off.

## Checks

- The mapping above is complete for a statement.
- Why us and deal factors appear nowhere in the canonical.
- `gp acs` reports zero orphans and no `refused:` line.
- Every open `needs-info` ticket, client-confirm assumption, approved commitment, gap and named regime exists as
  an item in the right state.
