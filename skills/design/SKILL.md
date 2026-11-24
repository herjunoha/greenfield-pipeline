---
name: design
description: Have gus write or edit the acceptance suite of one AC and rex review that suite version. Use for "write the suite", "design the tests", "the AC changed, update its suite", or when gp acs shows an AC as no-suite, stale or in-review.
---

# design: suites, reviewed

One suite per AC, `greenfield/suites/<AC>.yaml`. The author never reviews it, and a version counts only after rex
reviews it and the owner accepts its line.

1. `gp acs`: pick the AC whose state is `no-suite`, `stale` or `in-review`. A stale suite follows its changed AC or
   contract: rewrite it from the new `baseline_sha` and `contract_sha`.
2. Brief **gus-the-generator** in a fresh context: the AC id, nothing about the product's code. gus writes the
   tracer case first. If a business rule has no confirmed example, gus stops: set the item to `needs-info`
   and ask the sponsor for the example (one line to confirm beats an abstract question), then resume.
3. `gp check` must be clean before review.
4. Brief **rex-the-reviewer** for the suite version. On `reject`, send the note back to gus; do not edit the suite
   yourself and do not argue with rex's finding.
5. On `approve`, ask the owner to accept the line: they run `gp accept-line suite:<AC>`. You never run it.
6. Later, add the AC's other cases (clauses, negatives, edges). Each edit is a new suite version: review and
   acceptance start over for it.

Never weaken a check to make a run pass. A disagreement is a defect in the product or a question for the owner.
