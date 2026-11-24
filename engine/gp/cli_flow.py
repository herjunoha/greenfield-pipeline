"""gp accept-line, gp review, gp close, gp decide: the decisions and reviews that move work forward."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from . import acceptance, items, reviews
from . import project as proj


def _root() -> Path:
    root = proj.find_project(Path.cwd())
    if root is None:
        raise SystemExit("gp: not inside a greenfield-pipeline project (no greenfield/fence.yaml found). Run gp init first.")
    return root


def _decide(root: Path, item: str, decision: str, why: str, evidence: str = "", result: str = "") -> None:
    row = "\t".join([datetime.now(timezone.utc).isoformat(timespec="milliseconds"), item, decision, why, evidence, result])
    with (root / "greenfield" / "decisions.tsv").open("a", encoding="utf-8", newline="\n") as f:
        f.write(row.replace("\n", " ") + "\n")


def cmd_accept(args) -> int:
    entry = acceptance.record(_root(), args.ref)
    print(f"accepted {entry['ref']} at {entry['sha'][:12]}")
    return 0


def cmd_review(args) -> int:
    entry = reviews.record(_root(), args.kind, args.ref, args.by, args.verdict, args.note or "")
    print(f"{entry['verdict']} {entry['kind']} {entry['ref']} by {entry['by']} at {entry['sha'][:12]}")
    return 0


def cmd_close(args) -> int:
    root = _root()
    folder = root / "greenfield" / "items"
    item = items.load_all(folder).get(args.item)
    if item is None:
        raise SystemExit(f"gp: no item {args.item}")
    if item.state == "closed":
        raise SystemExit(f"gp: {args.item} is already closed")
    if item.state == "ready-for-human" and not acceptance.accepted(root, args.item):
        raise SystemExit(f"gp: {args.item} waits on the owner; it closes only when they accept its line "
                         f"(gp accept-line {args.item}). Editing it after acceptance un-accepts it.")
    item.state, item.reason = "closed", args.reason
    (folder / f"{item.id}.md").write_text(items.dump(item), encoding="utf-8", newline="\n")
    _decide(root, item.id, f"closed: {args.reason}", args.why)
    print(f"closed {item.id} ({args.reason})")
    return 0


def cmd_decide(args) -> int:
    _decide(_root(), args.item or "-", args.decision, args.why, args.evidence or "", args.result or "")
    return 0


def register(sub) -> None:
    p = sub.add_parser("accept-line", help="the owner accepts an item, suite:<AC> or canonical at its current sha")
    p.add_argument("ref")
    p.set_defaults(fn=cmd_accept)
    p = sub.add_parser("review", help="record rex's review of a suite version or a scored run")
    p.add_argument("kind", choices=("suite", "run"))
    p.add_argument("ref")
    p.add_argument("--by", required=True)
    p.add_argument("--verdict", required=True, choices=("approve", "reject"))
    p.add_argument("--note")
    p.set_defaults(fn=cmd_review)
    p = sub.add_parser("close", help="close an item; a ready-for-human item needs the owner's accepted line")
    p.add_argument("item")
    p.add_argument("--reason", choices=items.REASONS, default="done")
    p.add_argument("--why", required=True)
    p.set_defaults(fn=cmd_close)
    p = sub.add_parser("decide", help="append a row to decisions.tsv")
    p.add_argument("decision")
    p.add_argument("--why", required=True)
    p.add_argument("--item")
    p.add_argument("--evidence")
    p.add_argument("--result")
    p.set_defaults(fn=cmd_decide)
