---
name: shape
description: Design a greenfield-pipeline project before any code exists, so there is an interface to test and a short architecture to review. Writes design/architecture.md and design/contracts/ and decides the stack. Use after plate, before the walking skeleton, or when an AC needs a surface that has no contract yet.
---

# shape: design before build

Red first and black-box verdicts need an interface to test before code exists. This part produces it.

## Write
1. **`greenfield/design/architecture.md`**, at most about two pages (`gp check` refuses more than 120 lines). Headings
   for: Components, Data, Runtime (including deploy topology), Stack, Alternatives (what you considered and why
   not). Every surface in the canonical is named in it.
2. **`greenfield/design/contracts/`**, machine-checkable where the surface allows: OpenAPI or JSON Schema for
   `http`, a usage spec for `cli`, a schema file for stored data, a state list for `browser`. gus writes suites
   against these, never against code. Point each surface's `interface:` in the canonical at its file; a contract
   change changes `contract_sha`, which stales its suites until they are rewritten and re-reviewed.
3. **Decisions.** Stack, hosting and data store are product or preference calls: a `ready-for-human` item with your
   pick and its source, unless `gp pack show stack` or the sources settle them (then decide, cite, and
   `gp decide "<decision>" --why "<why>" --item I-n`). Registries are decided with the stack, in one decision,
   and the owner adds them to `fence.yaml` (you never write it).

## The walking skeleton
The first build item, blocking every AC item: a repo (`gp product init`, then the owner adds the printed lines to
`fence.yaml`), a run command, a health endpoint or `--version`, the driver reaching it, and nothing else. It makes
`gp preflight` real. Its own case may be red as "connection refused"; after it, a missing route answering 404
is red.

## Review
rex reviews the shape in one pass: does every AC have a path through the design, and does the design add anything
the canonical does not ask for? Invented features hide in designs. Fix, do not argue.
