---
name: proof-of-concept
description: Make the smallest working demo that proves named proof requirements in front of the client, and report honestly what it proved. A sales asset, not test evidence. Invoke deliberately with /pitch:proof-of-concept for a prototype ticket in a pitch map that needs a live demonstration.
disable-model-invocation: true
---

Build a pitch demo for named proof requirements. It is a sales asset: greenfield-pipeline never treats it as
verified. Shared rules: `../../references/rules.md` (rule 4 governs data).

## Input

A `prototype` ticket that needs a working demo, with its question and the named proof requirements from the
Solution Statement. If they are not named precisely, ask once; never invent what to prove.

## Where it is built

In `pitch/poc/`, its own git repo, **not** the future product repo. The deal's `greenfield/fence.yaml` needs a
`code_repos` entry for it and a `local` environment, both accepted by the human. If either is missing, stop and
say so. The fence declares no deploy lane, so nothing leaves the machine. Dependencies follow the fence's
registry and lockfile rule; the runner is the declared one.

## Scope, data and safety

- Build only what a named proof requirement needs: the smallest runnable thing, never described as
  production-grade. A human sets the time-box in the ticket; a requirement that cannot be shown inside it gets a
  lower-fidelity answer (a described wireframe, a recorded walkthrough) instead of a half-build.
- Synthetic or sample data only. No client personal or confidential data, no real credentials, no calls to client
  systems. Commitment-like numbers in the demo (SLA, performance) are flagged for a human, never asserted.

## Workflow

1. Restate each proof requirement as a pass/fail check an observer can see, **before** building.
2. Plan the smallest build; name what is mocked.
3. Build and run as you go.
4. Run the checks and record the result per requirement.
5. A human on our side watches the demo run against the checks and attests it (role, date). Only then is a
   requirement `demonstrated`; never on the agent's own run. A failing one stays `failed`.
6. Write `pitch/demo-notes.md` and report back.

## `demo-notes.md`

- Per requirement: the check, the result and who attested it (or "unattested").
- What is real and what is mocked; what the demo does not prove.
- How to open it: one command.
- A three-to-five-step demo script tied to the client's problems.
- **For greenfield-pipeline**: where the build lives, what is reusable, and `reusable: yes | no` (default `no`:
  prototype code is written fast to be shown).

## Honesty

Label what is real and what is mocked, in the notes and on screen where it matters. Never present a hard-coded
result as live behaviour. A live demo that relies on a mock is approved by a human before the pitch, and the deck
labels it.

## Report to the caller

The result per requirement, the consequence for the statement, and the demo location. `problem-to-solution`
records it as the ticket's answer and updates Proof evidence; this skill never edits the map or the statement.
