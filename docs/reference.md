# Reference: what exists

The inventory behind the idea in the main README. It lists commands and mechanisms, not the reasons for them. Status:
validated on fixtures only; see the main README for what is and is not proven.

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
