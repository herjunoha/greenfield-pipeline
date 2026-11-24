"""gp check, gp run, gp score: the suite side of the command line."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from . import project as proj
from . import audit, budget, codecheck, environments, runner, shape, suite, suitecheck


def _root() -> Path:
    root = proj.find_project(Path.cwd())
    if root is None:
        raise SystemExit("gp: not inside a greenfield-pipeline project (no greenfield/fence.yaml found). Run gp init first.")
    return root


def _load_suites(root: Path) -> tuple[list, list[str]]:
    data, canon_problems = audit.load(root)
    problems, loaded = list(canon_problems), []
    for path in sorted((root / "greenfield" / "suites").glob("*.yaml")):
        try:
            s = suite.load(path)
        except suite.SuiteError as exc:
            problems += [f"{path.name}: {p}" for p in exc.problems]
            continue
        loaded.append(s)
        problems += [f"{path.name}: {p}" for p in suite.verify(s, root)]
        if not canon_problems:
            problems += [f"{path.name}: {p}" for p in suitecheck.suite_problems(s, root, data)]
    return loaded, problems


def cmd_check(args) -> int:
    root = _root()
    loaded, problems = _load_suites(root)
    problems += environments.load_all(root)[1] + shape.check(root)
    code, notes = codecheck.run(root)
    problems += code
    if args.merge:
        problems += codecheck.merge(root, args.merge, args.component)
    for n in notes:
        print(f"note: {n}")
    for p in problems:
        print(f"refused: {p}")
    print(f"{len(loaded)} suite(s) read, {len(problems)} problem(s)")
    return 1 if problems else 0


def cmd_run(args) -> int:
    root = _root()
    loaded, problems = _load_suites(root)
    if problems:
        for p in problems:
            print(f"refused: {p}")
        return 1
    chosen = [s for s in loaded if not args.ac or s.ac in args.ac]
    if not chosen:
        raise SystemExit("gp: no suite matches")
    into = Path(args.into) if args.into else None
    if into and not into.is_absolute():
        into = root / "greenfield" / "runs" / into
    budget.guard(root, "run", [s.ac for s in chosen])
    env = runner.environment(root, args.env)
    try:
        with environments.up(root, env) as pre:
            run_dir = runner.run(root, chosen, env, into, args.rerun_reason, pre)
    except environments.EnvError as exc:
        print(f"refused: {exc}")
        return 1
    print(run_dir.name)
    return 0


def cmd_score(args) -> int:
    root = _root()
    run_dir = Path(args.run)
    if not run_dir.is_absolute() and not run_dir.exists():
        run_dir = root / "greenfield" / "runs" / args.run
    verdicts = runner.score_run(root, run_dir)
    print(f"run {verdicts['run']}  full={str(verdicts['full']).lower()}")
    for ac, v in verdicts["acs"].items():
        counts = ", ".join(f"{n} {s}" for s, n in sorted(Counter(v["cases"].values()).items()))
        print(f"  {ac}  {v['verdict']}  ({counts})")
    return 0


def register(sub) -> None:
    p = sub.add_parser("check", help="refuse suites, environments and code that break the mechanical rules")
    p.add_argument("--merge", metavar="REF", help="also require a passing verdict on this ref before it merges")
    p.add_argument("--component")
    p.set_defaults(fn=cmd_check)
    p = sub.add_parser("run", help="run suites through their drivers")
    p.add_argument("--ac", action="append")
    p.add_argument("--env")
    p.add_argument("--into")
    p.add_argument("--rerun-reason")
    p.set_defaults(fn=cmd_run)
    p = sub.add_parser("score", help="score a run")
    p.add_argument("run")
    p.set_defaults(fn=cmd_score)
