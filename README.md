# greenfield-pipeline

A company-agnostic plugin for Claude Code that takes a software idea from scattered sources to a verified build and a
handover pack. It assumes no company, industry or stack. It ships as a command-line engine (`gp`), nine skills, six
worker agents with limited tools, and a hook that pauses risky tool calls until the owner decides.

**Explainer page:** linked as this repository's website on GitHub (source: `docs/index.html`).

**License: Apache-2.0.** Copyright 2026 Herjuno Hestu Adhimarta, Quality Assurance. See `LICENSE`.

**Status: steps 1 to 8 of 9 built. Validated on fixtures only. No real project has run (step 9), and no live model
session has yet driven the workers end to end: the scratch runs use each fixture's reference implementation in ed's
place and the test author's suites as data. The behavioural half of the hidden-rule check has not been run.**

## The whole idea

Six rules.

1. **One tracker, one state.** Asks, findings, failed runs and work are all items, each a file in one of five states:
   needs-triage, needs-info, ready-for-agent, ready-for-human, closed. The agent works the ones it can do alone
   (`gp next`).
2. **Red before green.** Every acceptance criterion (AC) gets a test suite before any code exists, and the suite is
   seen failing before the build. An AC is done only on a passing full run of its accepted suite, on the current build.
3. **The writer never judges.** `gus` writes the suites and never reads product code. `ed` builds and never edits a
   suite. `tim` judges the run blind to the builder's notes. `rex` reviews every suite version and every full run,
   whatever its result.
4. **People confirm the examples.** Expected values come from examples a person confirmed. An open assumption keeps an
   AC from being done, and a guess from memory never closes one.
5. **One-way doors are the owner's.** A hook pauses a fixed list of risky tool calls. Accepting a suite, accepting a
   pack change and issuing numbers are the owner's, and so is how much of each part runs unattended. Nothing goes to
   production.
6. **Every handover says what stayed unproven.** The pack includes a limits page: what no suite checked, which doubles
   stood in for real services, which assumptions are open. The certificate is left unsigned.

Not goals: production deploy or operations, inventing requirements (it asks), a no-human mode, any compliance claim,
and mobile, desktop or embedded testing out of the box.

## The loop for one AC

1. **Plate.** Scattered sources become one canonical requirement file. What it cannot settle is raised as an item for a
   person.
2. **Shape.** Architecture and interface contracts are written and the stack is decided, before any code.
3. **Design.** `gus` writes the suite for the AC, tracer case first. `rex` reviews it and the owner accepts that version.
4. **Red.** The suite runs before any build and must fail.
5. **Build.** `ed` builds test-first, one AC at a time, on a recorded commit.
6. **Verify.** `eve` runs the suites, `tim` judges, `gp score` combines, `rex` reviews the run. Failures go back to build.
7. **Handover.** `dora` drafts the sponsor documents as local files. The owner signs and sends.

## Who decides

- **The agent alone:** write and review suites, build, run, judge, score, draft handover documents.
- **The owner only:** accept a suite version (`gp accept-line`), accept a change to the pack (`gp pack accept`), issue
  numbers (`gp number`), sign and send the certificate, anything on the always-pause list, and the ladder: which parts
  wait for the owner and which may run on their own.

## Also in this repository: `pitch`

A second plugin, `pitch/`, takes a foggy idea to a won deal (map of decision tickets, Solution Statement, proposal,
deck, optional demo) and hands the win to this plugin's `plate`. It needs this plugin's `gp` and fence. Marketplace
entries: `greenfield-pipeline` and `pitch`. Its status is its own: see `pitch/README.md` (fixture only).

## What does not exist yet, and what is not proven

- **A real project** (step 9): one small real tool, chosen by the owner. Until it passes this plugin is not called
  proven.
- **A live end-to-end run of the workers.** The agent and skill files are tested for structure (tool limits, every
  `gp` command they name exists, size caps), not for how a model behaves on them.
- **The behavioural half of the hidden-rule check** (`tests/fixtures/acme-freight/README.md`): whether the
  dangerous-goods rule surfaces before the build when a simulated sponsor answers questions, run three times. The
  structural half and the scorer are tested; the live sessions were not run.
- **The container runner path** on a machine with a runtime; the `browser` driver; tier 2 surfaces.
- **The hook in a live Claude Code session.** The tests drive it by stdin.
- The `unattended` level, which needs a scheduler the machine's owner chooses.

## Use

```
python bin/gp init <folder>      # Windows: bin\gp.cmd init <folder>
python bin/gp doctor
python -m pytest -q
```

Needs Python 3.10+, PyYAML and git; optional: a container runtime, a browser automation library, Node. The hook command
is `python`; where only `python3` exists, edit `hooks/hooks.json`. **The hook has not yet been loaded by a live
Claude Code session; the tests drive it by stdin.**

## Install and platforms tested

- **Tested:** Windows 11, Python 3.13, git 2.55, PyYAML. Not tested: Python 3.10 to 3.12, Linux, macOS. The tests assume
  `python` is on the PATH.
- **Run the engine alone** (no Claude Code needed): `python bin/gp init <folder>`, then the commands under Use.
- **As a Claude Code plugin** (**not yet tried in a live session**): the repo root is a plugin and a one-plugin local
  marketplace. In Claude Code: `/plugin marketplace add <path to this folder>`, then
  `/plugin install greenfield-pipeline@greenfield-pipeline-local`. It adds the skills, the agents and the fence hook; a
  project is any folder where you have run `gp init`. If the hook does not load, the fence does not act, so check it
  before trusting a project to it.
- **License:** Apache-2.0 (see `LICENSE`).

## Surface tiers and the limits of a green verdict

- Tier 1, driven by core: `http`, `cli` (including batch jobs through captured files and libraries through a test
  command), `manual`. `browser` is an optional adapter. Tier 2 surfaces (mobile, desktop, embedded) have no driver
  yet: their ACs are manual and the handover says so.
- A green verdict means the accepted suites passed on one build. It does not prove quality outside what they check,
  and a suite is only as good as the examples a person confirmed. Doubles are not the real service.
- `runner: container` needs a runtime and a container start command; `runner: process` needs the owner's accepted
  fence diff. The container path has not been exercised on a machine with a runtime.
- The fence is regex on command text and tool names. It is conservative and not a sandbox.
- Secret matching is pattern-based and misses what it does not know.

## Reference

The full list of commands and mechanisms (case model and scorer, drivers, the pack, the fence, the ladder, the ceiling,
handover) is in `docs/reference.md`.

## Credits

The red-first loop, tracer bullets and vertical slices follow public test-driven-development practice (Kent Beck's
test-driven development; Andy Hunt and Dave Thomas on tracer bullets). Worked examples as the source of expected
values follow specification by example (Gojko Adzic). No text from those works is reproduced.
