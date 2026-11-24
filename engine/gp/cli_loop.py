"""gp level, gp budget, gp catchup, gp retro: the owner's controls and the loop's bookkeeping."""
from __future__ import annotations

from pathlib import Path

from . import budget, catchup, ladder, retro
from . import project as proj
from .items import PARTS


def _root() -> Path:
    root = proj.find_project(Path.cwd())
    if root is None:
        raise SystemExit("gp: not inside a greenfield-pipeline project (no greenfield/fence.yaml found). Run gp init first.")
    return root


def cmd_level(args) -> int:
    root = _root()
    if args.part and args.level:
        ladder.set_session(root, args.part, args.level)
        print(f"{args.part} is {args.level} for this session (logged; a permanent change is the owner's edit of fence.yaml)")
        return 0
    for part in PARTS:
        level, why = ladder.effective(root, part)
        print(f"{part}\t{level}\t({why})")
    return 0


def cmd_budget(_args) -> int:
    root = _root()
    cfg, hits = budget.config(root), budget.reached(root)
    print(f"runs_per_ac {cfg['runs_per_ac']}, builds {budget.builds_made(root)}/{cfg['builds_total']}, "
          f"deadline {cfg['deadline'] or 'none'}")
    if hits:
        ids = budget.raise_items(root, hits)
        for hit, item in zip(hits, ids):
            print(f"reached: {hit['what']} Item {item} waits on the owner.")
    print("token or cost spend is not visible to this plugin: set that limit in your own harness or plan")
    return 1 if hits else 0


def cmd_catchup(args) -> int:
    root = _root()
    print("\n".join(catchup.build(root)))
    if not args.keep:
        catchup.mark(root)
    return 0


def cmd_retro(args) -> int:
    root = _root()
    if args.step == "begin":
        snap = retro.begin(root)
        print(f"retro begun: {snap['bytes']} bytes in {retro.targets(root)[0].name}; it must finish no larger")
        return 0
    problems = retro.finish(root)
    for problem in problems:
        print(f"refused: {problem}")
    print("retro finished, the pack is no larger" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


def register(sub) -> None:
    p = sub.add_parser("level", help="show the ladder, or say a part's level for this session (the owner's)")
    p.add_argument("part", nargs="?", choices=PARTS)
    p.add_argument("level", nargs="?", choices=ladder.LEVELS)
    p.set_defaults(fn=cmd_level)
    sub.add_parser("budget", help="show the ceiling; raise an item for any limit reached").set_defaults(fn=cmd_budget)
    p = sub.add_parser("catchup", help="what waits on the owner, decisions since last time, Attention flags")
    p.add_argument("--keep", action="store_true", help="do not move the since-marker")
    p.set_defaults(fn=cmd_catchup)
    p = sub.add_parser("retro", help="begin or finish a retro; it leaves the pack no larger")
    p.add_argument("step", choices=("begin", "finish"))
    p.set_defaults(fn=cmd_retro)
