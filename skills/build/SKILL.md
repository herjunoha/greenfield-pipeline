---
name: build
description: Have ed build or fix the software for one AC test-first, in the declared product repo, and record the build. Use for "build AC-n", "fix the red AC", or when gp acs shows an AC as red or ready and its suite has been seen to fail.
---

# build: ed writes the software

1. Check red first: the AC's latest scored run is `fail` with preflight green (`gp acs` shows `red`). If the AC
   is `ready` (accepted suite, never run), have eve run it first. If the run was an `error`, diagnose why the
   product was not reached; that is not red and not a reason to build.
2. Brief **ed-the-engineer** in a fresh context: the AC, the failing result, the contract. ed works on a branch of
   the repo declared under `code_repos`, test-first, one slice at a time.
3. Dependencies: only from registries `fence.yaml` lists, each a row in `deps.tsv`; a license outside the pack's
   policy is a `ready-for-human` item. Docs that ship (README, run notes) are build items with a quickstart case.
4. When ed says it is ready: `gp check` (no dirty tree, lockfile, no secret, every dependency documented),
   `gp preflight`, `gp build`. Then hand to **verify**.
5. Merge to trunk only with `gp check --merge <branch>` passing: a full run on exactly that commit passed every AC.
   A push or deploy goes only through a lane the owner declared; with none, a local repo is the delivery.

ed never closes an AC and never edits a suite. If ed reports a suite looks wrong, that is a finding for rex.
