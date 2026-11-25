# greenfield-pipeline

A company-agnostic plugin for Claude Code that delivers software from literal scratch: requirements, test suites written
and reviewed before the build, a staged build, a verified run and a handover pack, driven by the `gp` command line and a
set of worker agents.

**License: Apache-2.0.** Copyright 2026 Herjuno Hestu Adhimarta, Quality Assurance. See `LICENSE`.

**Status: steps 1 to 8 of 9 built. Validated on fixtures only. No real project has run (step 9), and no live model
session has yet driven the workers end to end: the scratch runs use each fixture's reference implementation in ed's
place and the test author's suites as data. The behavioural half of the hidden-rule check has not been run.**

## Also in this repository: `pitch`

A second plugin, `pitch/`, takes a foggy idea to a won deal (map of decision tickets, Solution Statement, proposal,
deck, optional demo) and hands the win to this plugin's `plate`. It needs this plugin's `gp` and fence. Marketplace
entries: `greenfield-pipeline` and `pitch`. Its status is its own: see `pitch/README.md` (fixture only).

## What exists

- `gp` core: `init`, `new`, `next`, `status`, `close`, `decide`, `doctor`, `pack show|check|accept` (`show` also reads `<key>.md` in the pack, such as `lessons` or `offerings`), `check`, `run`,
  `score`, `acs`, `raise`, `preflight`, `build`, `product init`, `accept-line`, `review`, `quickstart`,
  `handover-data`, `handover`, `feed`, `notify`, `number`, `level`, `budget`, `catchup`, `retro`.
- **Case model and scorer.** Suite schema, the path language, thirteen ops, a small JSON Schema subset. Mechanical
  refusals: no scored check without `from`, no `example:` that is not confirmed, no scored case with nothing to
  check, no unsupported schema keyword. A driver failure is `error`, never `fail`. A step may use an earlier
  observation with `{{0.body.code}}`.
- **Drivers** (stdlib only): `http`, `cli`, `manual`, one command per case, JSON in and out.
- **Canonical and plate.** Full schema (surfaces, glossary, examples, data classes, regulated regimes), the audit,
  the `plate` skill. `gp acs` lists each AC with the shas a suite copies, reports orphans, and says what stops each
  AC from being `done`. A suite whose AC or contract changed is stale and refused.
- **Assumptions and regulated data.** An assumption's `source` is its tag; `memory` and an unconfirmed `public:`
  finding never close one, and an AC with an open assumption shows `assumed`. `gp raise` mints the regulated-data
  item and one stub per unspecified baseline need.
- **Environments and builds.** `environments.yaml` (production is never listed; a local one is loopback; a remote one
  is in the fence's `remote_hosts`), `gp preflight`, a `reset` between cases, credential names checked and never
  values. `gp build` records a clean HEAD. `gp check` blocks a dirty tree or build, a manifest with no lockfile, a
  secret in a committed file, an undocumented dependency, and (`--merge`) a ref with no passing full run on exactly
  its commit.
- **The AC state machine.** `no-suite`, `in-review`, `ready`, `red`, `green`, `done`, `assumed`, `stale`, derived
  from files. `done` needs an accepted suite (rex reviewed, owner accepted at the file's sha), a full run of exactly
  that suite on the current build, rex's review of that run, red seen before the first green, an approved baseline
  and no open assumption.
- **Workers and skills.** `gus`, `rex`, `ed`, `eve`, `tim`, `dora` (agents with tool limits); skills `deliver`,
  `plate`, `shape`, `design`, `build`, `verify`, `handover`. A test checks that every `gp` command they name exists.
- **Handover.** Eight generic markdown documents from `gp handover-data`, including the limits page (what stayed
  unproven, doubles, open assumptions, "compliance: not assessed by this pipeline"). The certificate is left
  unsigned. `gp handover` refuses while a regulated-data item is open. `gp quickstart` runs the README's commands
  in a fresh clone of the build and checks health.
- **The pack.** `gp pack check` validates it and rejects any rule that loosens the core fence; the fence takes the
  union. The pack's hash is recorded in `fence.yaml`; an edited pack file makes every non-read tool call ask until the
  owner runs `gp pack accept`. Feeds are redacted (phone numbers, emails, tokens, the pack's patterns) before any
  file is written.
- **The fence.** All eleven always-pause entries, enforced by a tool-call hook in any project that has
  `greenfield/fence.yaml`, and silent everywhere else. It also asks before `gp accept-line`, `gp pack accept` and
  `gp number`, because accepting and issuing are the owner's.
- **The ladder.** Per part (`plate`, `probe`, `shape`, `design`, `build`, `verify`, `handover`): `hitl` makes its
  items wait for the owner and be worked live, `afk` is the default. It is the owner's: a permanent map in
  `fence.yaml`, or a spoken change for one session (logged). A spoken change cannot loosen a permanent `hitl`;
  `unattended` is specified, not built, and counts as `hitl`. No level reaches the fence.
- **The ceiling.** `budget:` in `fence.yaml`: full runs with no newly passing case on one AC, builds, a deadline.
  Reaching one raises a `ready-for-human` item, and `gp run` or `gp build` then refuse. Token or cost spend is not
  visible to the plugin; set that limit in your own harness or plan.
- **Catch-up and retro.** `gp catchup` (what waits, decisions since last time, Attention flags) and a session-start
  line of pointers. `gp retro begin|finish` refuses if the pack grew, a file is over 30 lines or a lesson names a
  specific; retro writes the pack and the project, and the fence asks before any write into the plugin.
- **Three fixtures.** `acme-linkr` (http and cli), `acme-csv` (cli only, results from captured files) and
  `acme-freight` (business rules and a hidden rule). Each scratch run goes skeleton, red on every AC, a reference
  build, green, reviewed, done; the independence check plants a blind spot the builder's own tests miss and the
  full run turns that AC red.
- **Size budgets as tests.** Each module, skill, agent and driver has a line cap.

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

## Credits

The red-first loop, tracer bullets and vertical slices follow public test-driven-development practice (Kent Beck's
test-driven development; Andy Hunt and Dave Thomas on tracer bullets). Worked examples as the source of expected
values follow specification by example (Gojko Adzic). No text from those works is reproduced.
