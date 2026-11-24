---
name: plate
description: Plate scattered project sources (a brief, notes, replies, documents) into the canonical requirement greenfield/requirements/<name>.canonical.yaml, then raise the items it demands. Use for "plate the requirements", "write the canonical", or when the owner drops new sources into greenfield/sources/.
---

# plate: sources to the canonical

The canonical is the one source of truth for what is being built. You write it from `greenfield/sources/`; the
engine refuses what is malformed or unsourced. You never invent a requirement, a business value or a source.

## Steps

1. **Read every file in `greenfield/sources/`.** Note what each says and where (a heading or paragraph).
2. **Stop if the sources are too thin to plate** (one sentence, no outcome anyone could observe). Do not guess.
   Write one item with `gp new "Questions before planning" --state needs-info --body-file <file>`: a short list
   of what the sponsor must answer, and what is already settled so nothing is asked twice. Then end the turn.
3. **Write the canonical.** Fields (the schema is `gp/canonical_schema.py`; `gp acs` reports every problem):
   - `project`: `name`, `status: draft`, `objectives`, `out_of_scope`, `assumptions`, `timeline`, `surfaces`
     (`{name, kind, interface}`; `kind` is `http | cli | browser | manual`, or `mobile | desktop | embedded |
     other` for surfaces that need a pack driver; `interface` is a file name under `design/contracts/` or `null`
     until `shape` writes it), `glossary` (`{term, meaning, source, confirmed}`), `data_classes`
     (`personal | financial | health | children | biometric | credentials | none`), `regulated` (regimes the
     sponsor named, else `[]`).
   - `requirements`: `id` (AC-1...), `statement`, `acceptance` (**one observable line a stranger could check**),
     `dimension` (`functional | security | performance | accessibility | reliability`), `surface`, `source`.
     `source` is `<file under sources/>#<heading>` or `item:I-n` (a closed item that recorded an accepted
     decision). A requirement a source does not support is not written.
   - `examples`: the only legitimate source of an expected business value. `{id: EX-1, rule, given, expect,
     source, confirmed_by, confirmed_on, serves: [AC-n]}`. `source` is `sponsor-confirmed | sponsor-document |
     public:<url> | agent`. Anything you propose is `source: agent` with no `confirmed_by`: it is a proposal and
     suites cannot cite it until the sponsor confirms it. `confirmed_by` is a role (`sponsor`), never a name.
4. **Run `gp acs`.** Fix every `refused:` line. An `orphan` means the requirement has no resolvable source:
   cite the right one or remove the requirement. Never write a source to make the audit pass.
5. **Run `gp raise`.** It creates the regulated-data item (any data class beyond `personal` and `credentials`, or
   any regime the sponsor named) and one `needs-triage` stub per baseline need nobody specified (authentication,
   data retention, rough load, accessibility, supported platforms, backup).
6. **Write each baseline stub's brief, one at a time.** What, why now, the options and what each changes, your
   pick with its source, what breaks if the pick is wrong, what happens if nobody answers. Then set the item to
   `ready-for-human`. A need the sponsor stated, or accepted, becomes an AC with `baseline: <need>`.
7. **Missing facts.** If a business rule has no confirmed example, say so: the item goes `needs-info` and asks
   for an example (one line to confirm beats an abstract question). A fact you only know from training is a lead,
   not a source: record it as `gp new "<fact>" --kind assumption --source memory --acs AC-n`. An assumption
   closes only on `tried` (a run showed it), `sponsor-confirmed` or `sponsor-document`; `memory` and an
   unconfirmed `public:<url>` never close one, and an AC that depends on an open assumption shows `assumed`.

## Rules

- `status: approved` is the owner's, an accepted diff. Never set it. Editing an approved canonical starts the next
  draft; ACs whose text changed lose their suite's review (their shas change, see `gp acs`).
- Adding, removing or rewording an AC is a scope change: the fence asks.
- No names of people in any artifact: roles only. No pricing or contract terms.
- `greenfield-pipeline` never claims compliance. Name the regime or record that none applies, and move on.
- Write nothing in a sponsor's voice. Their facts come from a human, with a source and a date.

Done when `gp acs` prints `orphans: none` with no `refused:` line, and every raised item is either closed or
waiting on a person with a full brief.
