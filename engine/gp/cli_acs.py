"""gp acs (the audit and the shas a suite copies) and gp raise (mint the items the canonical demands)."""
from __future__ import annotations

import json
from pathlib import Path

from . import audit, items
from . import project as proj


def _root() -> Path:
    root = proj.find_project(Path.cwd())
    if root is None:
        raise SystemExit("gp: not inside a greenfield-pipeline project (no greenfield/fence.yaml found). Run gp init first.")
    return root


def cmd_acs(args) -> int:
    report = audit.run(_root())
    if args.json:
        print(json.dumps({"acs": report.rows, "problems": report.problems, "notes": report.notes,
                          "handover_blockers": report.blockers}, indent=2))
        return 1 if report.problems else 0
    if report.data is None and not report.problems:
        print("no canonical yet (greenfield/requirements/<name>.canonical.yaml); plate the sources first")
        return 0
    for row in report.rows:
        extra = f"  assumes {','.join(row['assumptions'])}" if row["assumptions"] else ""
        for why in row["missing"]:
            extra += "\n      stops done: " + why
        print(f"{row['id']}  {row['dimension']}  {row['surface']}  baseline_sha={row['baseline_sha']}  "
              f"contract_sha={row['contract_sha']}  suite={row['suite']}  {row['state']}{extra}")
    for problem in report.problems:
        print(f"refused: {problem}")
    orphans = [p for p in report.problems if ": orphan," in p]
    if report.data is not None and not orphans:
        print("orphans: none")
    for note in report.notes:
        print(f"note: {note}")
    for blocker in report.blockers:
        print(f"handover blocked: {blocker}")
    return 1 if report.problems else 0


def cmd_raise(_args) -> int:
    root = _root()
    report = audit.run(root)
    if report.problems or report.data is None:
        for problem in report.problems or ["no canonical to raise items from"]:
            print(f"refused: {problem}")
        return 1
    for entry in report.raises:
        item = items.mint(root / "greenfield" / "items", **entry)
        print(f"{item.id}\t{item.state}\t{item.title}")
    if not report.raises:
        print("nothing to raise")
    return 0


def register(sub) -> None:
    p = sub.add_parser("acs", help="audit the canonical: orphans, shas, assumptions, handover blockers")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_acs)
    sub.add_parser("raise", help="mint the items the canonical demands (regulated data, baseline needs)") \
        .set_defaults(fn=cmd_raise)
