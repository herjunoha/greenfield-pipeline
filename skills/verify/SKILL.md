---
name: verify
description: Run the reviewed suites of a greenfield-pipeline project against the current build, judge the rule checks, score, and have rex review the run. Use after a build, for the red run before one, and for "run the tests", "is it green", "verify AC-n".
---

# verify: preflight, run, judge, score, review

1. **preflight**: `gp preflight` starts the environment, checks health and credential names, and stops it. If it
   fails, the reason is the result; fix the environment (ed, or the owner for a runner choice), do not run.
2. **run** (eve-the-executor): `gp check`, `gp build`, `gp run`, `gp score <run>`. Read the verdicts as printed:
   `pass`, `fail`, `error` (a driver failed; nothing was observed), `pending` (a rule check waits for tim),
   `manual` (the owner attests), `incomplete`.
3. **judge** (tim-the-triager): only `rule:` checks, blind to the builder; then `gp score <run>` again. tim writes a
   bug report for every failing case.
4. **review** (rex-the-reviewer): every full run, whatever its result: `gp review run <run> --by rex ...`. Rex also
   disputes any case judged wrongly, and writes the Attention section of the evidence README.
5. Read `gp acs`: an AC is `done` only when its suite is accepted, a full run of exactly that suite passed on the
   current build, rex reviewed that run, red was seen before its first green, the baseline is approved and no
   assumption is open. The `stops done:` lines say which is missing.

Fix and re-run until green, or stop at the budget with a `ready-for-human` item that says why. A skipped or
disabled check is never a pass; a new commit needs a new verdict; loosening a check needs rex's countersign.
