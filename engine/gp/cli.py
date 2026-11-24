"""The gp command line: init, new, next, status, doctor, pack show; check, run, score live in cli_suite."""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from . import __version__, acceptance, audit, budget, builds, retro, cli_acs, cli_env, cli_flow, cli_loop, cli_pack, cli_suite, doctor, ladder, reviews, items, packs, project, runner, suite


def _need_project() -> Path:
    root = project.find_project(Path.cwd())
    if root is None:
        raise SystemExit("gp: not inside a greenfield-pipeline project (no greenfield/fence.yaml found). Run gp init first.")
    return root


def _items_dir(root: Path) -> Path:
    return root / "greenfield" / "items"


def cmd_init(args) -> int:
    root = Path(args.path).resolve()
    if (root / project.FENCE_REL).exists():
        print(f"gp: {root} is already a greenfield-pipeline project; nothing changed")
        return 0
    name, path, why = packs.resolve(args.pack)
    made = project.init_project(root, name, path, packs.sha256(path))
    print(f"pack: {name} ({why})")
    print(f"initialised {root}")
    for entry in made:
        print(f"  {entry}")
    return 0


def cmd_new(args) -> int:
    root = _need_project()
    body = Path(args.body_file).read_text(encoding="utf-8") if args.body_file else ""
    split = lambda v: [x.strip() for x in v.split(",") if x.strip()] if v else []  # noqa: E731
    state = args.state
    if args.part and state == "ready-for-agent" and ladder.effective(root, args.part)[0] == "hitl":
        state = "ready-for-human"          # a hitl part is worked live: its items wait for the owner
    try:
        item = items.mint(_items_dir(root), title=args.title, state=state, acs=split(args.acs),
                          blocked_by=split(args.blocked_by), source=args.source or "", reason=args.reason,
                          kind=args.kind, part=args.part, body=body)
    except items.ItemError as exc:
        raise SystemExit(f"gp: {exc}")
    print(item.id)
    return 0


def cmd_next(_args) -> int:
    root = _need_project()
    everything, live = items.load_all(_items_dir(root)), ladder.live_parts(root)
    for item in items.frontier(everything, live):
        print(f"{item.id}\t{item.title}")
    for item in items.frontier(everything):
        if item.part in live:
            print(f"{item.id}\t{item.title}\t(worked live with the owner: {item.part} is hitl)")
    return 0


def cmd_status(_args) -> int:
    everything = items.load_all(_items_dir(_need_project()))
    counts = Counter(i.state for i in everything.values())
    print(f"items: {len(everything)}")
    for state in items.STATES:
        print(f"  {state}: {counts.get(state, 0)}")
    print(f"frontier (unblocked ready-for-agent): {len(items.frontier(everything))}")
    rows = audit.run(_need_project()).rows
    if rows:
        by_state = Counter(r["state"] for r in rows)
        print("acs: " + ", ".join(f"{n} {s}" for s, n in sorted(by_state.items())))
    waiting = [i for i in everything.values() if i.state in ("ready-for-human", "needs-info")]
    if waiting:
        print("waiting on a person:")
        for i in waiting:
            print(f"  {i.id}\t{i.state}\t{i.title}")
    return 0


def cmd_doctor(_args) -> int:
    text, ok = doctor.report()
    print(text)
    return 0 if ok else 1


def cmd_pack_show(args) -> int:
    root = _need_project()
    fence = project.load_fence(root)
    path = Path(fence["pack_path"]) if fence.get("pack_path") else packs.bundled()[packs.GENERIC]
    try:
        print(packs.show(path, args.key))
    except packs.PackError as exc:
        raise SystemExit(f"gp: {exc}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gp", description="greenfield-pipeline engine")
    parser.add_argument("--version", action="version", version=f"gp {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init", help="scaffold a project in a folder")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("--pack")
    p.set_defaults(fn=cmd_init)
    p = sub.add_parser("new", help="mint the next item")
    p.add_argument("title")
    p.add_argument("--state", default="needs-triage", choices=items.STATES)
    p.add_argument("--acs")
    p.add_argument("--blocked-by")
    p.add_argument("--source")
    p.add_argument("--reason", choices=items.REASONS)
    p.add_argument("--kind", choices=items.KINDS)
    p.add_argument("--part", choices=items.PARTS, help="the kind of work, for the ladder")
    p.add_argument("--body-file")
    p.set_defaults(fn=cmd_new)
    sub.add_parser("next", help="list the frontier").set_defaults(fn=cmd_next)
    sub.add_parser("status", help="items by state and what waits on a person").set_defaults(fn=cmd_status)
    sub.add_parser("doctor", help="prerequisites").set_defaults(fn=cmd_doctor)
    cli_suite.register(sub)
    cli_acs.register(sub)
    cli_env.register(sub)
    cli_flow.register(sub)
    cli_loop.register(sub)
    pack = sub.add_parser("pack", help="pack tools").add_subparsers(dest="pack_command", required=True)
    p = pack.add_parser("show", help="print one pack key")
    p.add_argument("key")
    p.set_defaults(fn=cmd_pack_show)
    cli_pack.register(sub, pack)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except (packs.PackError, items.ItemError, suite.SuiteError, runner.RunError, builds.BuildError,
            acceptance.AcceptError, reviews.ReviewError, budget.BudgetError, ladder.LadderError, retro.RetroError) as exc:
        print(f"gp: {exc}", file=sys.stderr)
        return 2
