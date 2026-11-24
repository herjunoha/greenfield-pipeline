"""Handover, pack and connector commands: handover, handover-data, pack check/accept, feed, notify, number, quickstart."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from . import handover, handover_docs, items, packcheck, packs, quickstart, redact, runner
from . import project as proj


def _root() -> Path:
    root = proj.find_project(Path.cwd())
    if root is None:
        raise SystemExit("gp: not inside a greenfield-pipeline project (no greenfield/fence.yaml found). Run gp init first.")
    return root


def _pack(root: Path) -> Path:
    path = packcheck.pack_dir_of(proj.load_fence(root))
    return path if path and path.is_dir() else packs.bundled()[packs.GENERIC]


def _connectors(root: Path) -> dict:
    path = _pack(root) / "connectors.yaml"
    return (yaml.safe_load(path.read_text(encoding="utf-8")) or {}) if path.is_file() else {}


def _run(command: list, cwd: Path, stdin: str | None = None) -> str:
    done = subprocess.run([str(c) for c in command], cwd=cwd, input=stdin, capture_output=True, text=True,
                          encoding="utf-8", timeout=120)
    if done.returncode != 0:
        raise SystemExit(f"gp: connector command failed (exit {done.returncode}): {done.stderr.strip()[-200:]}")
    return done.stdout


def cmd_handover_data(_args) -> int:
    try:
        print(json.dumps(handover.data(_root()), indent=2, default=str))
    except handover.HandoverError as exc:
        for problem in exc.problems:
            print(f"refused: {problem}")
        return 1
    return 0


def cmd_handover(_args) -> int:
    try:
        written = handover_docs.write(_root())
    except handover.HandoverError as exc:
        for problem in exc.problems:
            print(f"refused: {problem}")
        return 1
    print("wrote greenfield/handover/: " + ", ".join(written))
    return 0


def cmd_pack_check(_args) -> int:
    root = _root()
    problems = packcheck.check(_pack(root))
    note = packcheck.tampered(proj.load_fence(root))
    problems += [note] if note else []
    for p in problems:
        print(f"refused: {p}")
    print(f"pack checked, {len(problems)} problem(s)")
    return 1 if problems else 0


def cmd_pack_accept(_args) -> int:
    root = _root()
    problems = packcheck.check(_pack(root))
    if problems:
        for p in problems:
            print(f"refused: {p}")
        return 1
    fence = root / proj.FENCE_REL
    new = packs.sha256(_pack(root))
    fence.write_text(re.sub(r"(?m)^pack_sha256:.*$", f"pack_sha256: {new}", fence.read_text(encoding="utf-8")),
                     encoding="utf-8", newline="\n")
    print(f"accepted the pack at {new[:12]}")
    return 0


def cmd_feed(args) -> int:
    root, pack = _root(), _pack(_root())
    extra = packs.load(pack).get("redact") or []
    made = 0
    for feed in _connectors(root).get("feeds") or []:
        if args.name and feed.get("name") != args.name:
            continue
        raw = json.loads(_run(feed["command"], pack) or "[]")        # held in memory only until redacted
        for note in raw if isinstance(raw, list) else []:
            title, _ = redact.clean(str(note.get("title") or "feed note"), extra)
            body, counts = redact.clean(str(note.get("body") or ""), extra)
            key = f"feed:{feed.get('name')}:{hashlib.sha256((title + body).encode()).hexdigest()[:8]}"
            if any(i.source == key for i in items.load_all(root / "greenfield" / "items").values()):
                continue
            items.mint(root / "greenfield" / "items", title=title[:100], state="needs-triage", source=key,
                       body=body + f"\n\n(redacted before writing: {counts})\n")
            made += 1
    print(f"{made} needs-triage item(s) from feeds")
    return 0


def cmd_notify(args) -> int:
    root = _root()
    message, _ = redact.clean(f"{args.message}\nRecommended action: {args.action}", packs.load(_pack(root)).get("redact") or [])
    stamp = root / "greenfield" / "notify-turns.txt"
    seen = stamp.read_text(encoding="utf-8").split() if stamp.is_file() else []
    if args.turn and args.turn in seen:
        raise SystemExit("gp: one message per agent turn; this turn already notified")
    command = (_connectors(root).get("notify") or {}).get("command")
    if command:
        _run(command, _pack(root), message)
    else:
        print(message)
    if args.turn:
        stamp.write_text(" ".join([*seen, args.turn]), encoding="utf-8")
    return 0


def cmd_number(args) -> int:
    root = _root()
    log = root / "greenfield" / "numbers.tsv"
    rows = log.read_text(encoding="utf-8").splitlines() if log.is_file() else []
    command = (_connectors(root).get("numbering") or {}).get("command")
    number = _run(command, _pack(root), args.kind).strip() if command else \
        f"{args.kind.upper()}-{date.today().year}-{len([r for r in rows if r.split(chr(9))[1:2] == [args.kind]]) + 1:03d}"
    with log.open("a", encoding="utf-8", newline="\n") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}\t{args.kind}\t{number}\n")
    print(number)
    return 0


def cmd_quickstart(args) -> int:
    root = _root()
    try:
        result = quickstart.run(root, runner.environment(root, args.env))
    except quickstart.QuickstartError as exc:
        print(f"refused: {exc}")
        return 1
    (root / "greenfield" / "quickstart.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("quickstart ok" if result["ok"] else f"quickstart failed: {result['reason']}")
    return 0 if result["ok"] else 1


def register(sub, pack) -> None:
    sub.add_parser("handover-data", help="the data the handover documents are written from").set_defaults(fn=cmd_handover_data)
    sub.add_parser("handover", help="render the generic markdown handover documents").set_defaults(fn=cmd_handover)
    p = sub.add_parser("feed", help="run the pack's feeds; redact; mint needs-triage items")
    p.add_argument("name", nargs="?")
    p.set_defaults(fn=cmd_feed)
    p = sub.add_parser("notify", help="tell the owner something (one per turn, redacted)")
    p.add_argument("message")
    p.add_argument("--action", required=True)
    p.add_argument("--turn")
    p.set_defaults(fn=cmd_notify)
    p = sub.add_parser("number", help="issue the next document number (irreversible)")
    p.add_argument("kind")
    p.set_defaults(fn=cmd_number)
    p = sub.add_parser("quickstart", help="run the README quickstart in a fresh clone of the build")
    p.add_argument("--env")
    p.set_defaults(fn=cmd_quickstart)
    pack.add_parser("check", help="validate the pack and its recorded hash").set_defaults(fn=cmd_pack_check)
    pack.add_parser("accept", help="record the pack's current hash (the owner's decision)").set_defaults(fn=cmd_pack_accept)
