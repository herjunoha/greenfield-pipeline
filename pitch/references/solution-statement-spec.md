# Solution Statement spec

The contract between the pitch skills. `problem-to-solution` writes the statement; `business-proposal`,
`pitch-deck`, `proof-of-concept` and the hand-off read it. Ids (P1, E1, EX1, A1) are allowed for stable
cross-reference, always next to a readable name.

Fields marked *(plates)* are shaped so greenfield-pipeline's `plate` skill takes them without rewording: a
surface kind is one of the canonical's (`http`, `cli`, `browser`, `manual`, or a kind a pack driver supports), a
proof requirement is one MUST statement plus an observable acceptance line (it becomes an AC `statement` and
`acceptance`), and a worked example is the only source of an expected business value.

```markdown
# Solution Statement: [alias]
Status: DRAFT, needs human review | handed over <date> | closed <date>
Pitch date: <date or TBD>

## Outcome
<[Role] can [achieve what] by [when], measured by [metric]. Baseline: <value or TBD>. Target: <value or TBD>.> (plates)

## Problem statement
- P1 <name>: <the problem in the client's words> (source, date) [stated | inferred]

## Domain
### Terms
- <term>: <meaning> | source: client | client-document | public:<url> | memory | confirmed: yes | no (plates)
### Rules
- R1 <name>: <a business rule the software must respect> | source: ... | confirmed: yes | no

## Worked examples
- EX1 <name>: rule R1 | given: <inputs> | expect: <outputs> | confirmed by <role>, <date> | serves: E1 (plates)

## Solution elements
### E1 <name>
- Solves: P1, P2
- Need: <what must be true for those problems to go away>
- Element: <what we propose and how it works, in plain terms>
- Surface: <name> (<kind: http | cli | browser | manual | a pack kind>) (plates)
- Fit: <how it meets the client's stated decision criteria>
- Proof requirement: <one MUST statement> | acceptance: <what an observer sees> (plates)
- Proof evidence: pending | demonstrated (attested by <role>, <date>, demo-notes link) | failed (one line, link)
- Decided in: <closed ticket title, or several separated by "; ">

## Why us
- <win theme> | criterion: <client decision criterion> | delivered by: E1, E3 | basis: O<n> | human (role, date)

## Assumptions
- A1 <name>: <what we assume> | owner: <role> | validate by: <step and date> | client must confirm: yes | no

## Data and regulation
Data handled: <personal | financial | health | children | biometric | credentials | none> (plates)
Regimes named by the client: <list or none>. We make no compliance claim.

## Scope boundaries
In: <list>
Out: <list, with why>

## Commitments
<only human-approved ones, each with who approved (role) and date. Empty if none.>

## Gaps (internal, never client-facing)
- <stated problem with no element, element with no traced problem, business rule with no confirmed example,
  unresolved ticket, element outside our offerings, regulated data with no named regime>

## Traceability index
<generated at compile time; never hand-edited>
| Problem | Need | Element | Proof requirement | Proof evidence |
|---|---|---|---|---|
```

## Writer rules

- Every element names the problems it solves; an element that solves none is not written.
- Every stated problem appears in some element's `Solves`, in `Out` with a reason, or in `Gaps`.
- Gaps list only what is still open; a decided matter goes in Scope or Commitments, pending proof on its element.
- Missing facts are `TBD`. A failed proof is recorded as `failed`, never omitted.
- `demonstrated` needs a human attestation, because whoever builds a demo must not be the one who declares it works.
- A business rule with no confirmed example is a Gap: greenfield-pipeline refuses an expected business value that
  no human confirmed.
- A `Why us` line with neither an offering id (`basis: O<n>`) nor a human source is not written.
- Once `handed over` the statement is frozen: changes go to the canonical.
