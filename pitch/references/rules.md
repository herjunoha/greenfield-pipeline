# Pitch rules

Written once. Every pitch skill points here and does not restate it.

## What the greenfield-pipeline fence already covers

The `greenfield-pipeline` always-pause list applies as written, and its fence enforces it inside the deal folder
(it has `greenfield/fence.yaml`): anything a client receives, production, scope, irreversible records, data
leaving this machine, credentials, deleting evidence and `fence.yaml`. That is why every pitch artifact is a
draft: nothing reaches the client without a human's send.

Each skill checks first that `gp` runs (`gp --version`). If it does not, stop with one line: pitch needs
greenfield-pipeline installed.

## The four pitch rules

1. **No pricing, contract terms or named individuals in artifacts.** Use roles ("client sponsor") and
   placeholders; our own people by role. Confidential items go under a "Needs human review" heading, not
   reproduced.
2. **Commitments are a human's call.** Anything promising timeline, SLA, price or scope is decided only by a
   human on our side. Agents propose options, never decide.
3. **Never speak for the client.** Client facts come only from a human (a reply, a call note, a new MoM),
   recorded with source and date. Missing values are `TBD`; gaps stay visible.
4. **Demos and prototypes use synthetic or sample data** and run only in a declared local environment unless a
   human approves otherwise.
