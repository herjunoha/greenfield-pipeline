"""Item files: one markdown file per item, YAML frontmatter, one state (plan section 3)."""
from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import yaml

STATES = ("needs-triage", "needs-info", "ready-for-agent", "ready-for-human", "closed")
REASONS = ("done", "wontfix")
KINDS = ("override", "assumption")
PARTS = ("plate", "probe", "shape", "design", "build", "verify", "handover")   # kinds of work, for the ladder
RESOLVING = ("tried", "sponsor-confirmed", "sponsor-document")   # what may close an assumption (plan 4.2)
ID_RE = re.compile(r"^I-(\d+)$")
FILE_RE = re.compile(r"^I-(\d+)\.md$")
_FRONT = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", re.S)
_KEYS = ("title", "state", "acs", "blocked_by", "source", "reason", "kind", "part")


class ItemError(ValueError):
    pass


@dataclass
class Item:
    id: str
    title: str
    state: str = "needs-triage"
    acs: list = field(default_factory=list)
    blocked_by: list = field(default_factory=list)
    source: str = ""
    reason: str | None = None
    kind: str | None = None
    part: str | None = None
    body: str = ""

    @property
    def number(self) -> int:
        return int(ID_RE.match(self.id).group(1))

    def validate(self) -> None:
        if not ID_RE.match(self.id):
            raise ItemError(f"bad item id {self.id!r}, expected I-<number>")
        if not isinstance(self.title, str) or not self.title.strip():
            raise ItemError(f"{self.id}: title is required")
        if self.state not in STATES:
            raise ItemError(f"{self.id}: state {self.state!r} is not one of {', '.join(STATES)}")
        if self.state == "closed" and self.reason not in REASONS:
            raise ItemError(f"{self.id}: a closed item needs reason: done or wontfix")
        if self.state != "closed" and self.reason is not None:
            raise ItemError(f"{self.id}: reason is only for closed items")
        if self.part is not None and self.part not in PARTS:
            raise ItemError(f"{self.id}: part {self.part!r} is not one of {', '.join(PARTS)}")
        if self.kind is not None and self.kind not in KINDS:
            raise ItemError(f"{self.id}: kind {self.kind!r} is not one of {', '.join(KINDS)}")
        if self.kind == "assumption":
            self._validate_assumption()
        for name in ("acs", "blocked_by"):
            value = getattr(self, name)
            if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                raise ItemError(f"{self.id}: {name} must be a list of strings")
        bad = [b for b in self.blocked_by if not ID_RE.match(b)]
        if bad:
            raise ItemError(f"{self.id}: blocked_by holds non-item ids {bad}")
        if self.id in self.blocked_by:
            raise ItemError(f"{self.id}: an item cannot block itself")

    def _validate_assumption(self) -> None:
        """`source` is the finding's tag. A memory or an unconfirmed public finding stays an assumption: only a
        run (tried) or the sponsor (sponsor-confirmed, sponsor-document) closes one."""
        if self.source not in ("memory", *RESOLVING) and not re.match(r"^public:\S+$", self.source):
            raise ItemError(f"{self.id}: an assumption's source is its tag: memory, tried, public:<url>, "
                            "sponsor-confirmed or sponsor-document")
        if self.state == "closed" and self.reason == "done" and self.source not in RESOLVING:
            raise ItemError(f"{self.id}: an assumption cannot close on a {self.source.split(':')[0]} finding; "
                            "it closes on tried, sponsor-confirmed or sponsor-document")


def parse(text: str, item_id: str) -> Item:
    match = _FRONT.match(text)
    if not match:
        raise ItemError(f"{item_id}: no frontmatter (a file must start with ---)")
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise ItemError(f"{item_id}: frontmatter is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ItemError(f"{item_id}: frontmatter must be a mapping")
    unknown = sorted(set(data) - set(_KEYS))
    if unknown:
        raise ItemError(f"{item_id}: unknown frontmatter keys {unknown}")
    if "title" not in data or "state" not in data:
        raise ItemError(f"{item_id}: title and state are required")
    item = Item(
        id=item_id,
        title=data["title"],
        state=data["state"],
        acs=data.get("acs") or [],
        blocked_by=data.get("blocked_by") or [],
        source=data.get("source") or "",
        reason=data.get("reason"),
        kind=data.get("kind"),
        part=data.get("part"),
        body=match.group(2),
    )
    item.validate()
    return item


def dump(item: Item) -> str:
    item.validate()
    data = {"title": item.title, "state": item.state, "acs": item.acs, "blocked_by": item.blocked_by,
            "source": item.source}
    if item.reason is not None:
        data["reason"] = item.reason
    if item.kind is not None:
        data["kind"] = item.kind
    if item.part is not None:
        data["part"] = item.part
    front = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=1000)
    return f"---\n{front}---\n{item.body}"


def load_all(items_dir: Path) -> dict[str, Item]:
    found = {}
    if items_dir.is_dir():
        for path in items_dir.iterdir():
            match = FILE_RE.match(path.name)
            if match:
                found[path.stem] = parse(path.read_text(encoding="utf-8"), path.stem)
    return dict(sorted(found.items(), key=lambda kv: int(kv[0][2:])))


def frontier(items: dict[str, Item], live: frozenset | set = frozenset()) -> list[Item]:
    """Unblocked ready-for-agent items. A blocker that does not exist counts as open. Items whose part is on the
    ladder's `hitl` level (`live`) are worked with the owner, so they are not the agent's to pick alone."""
    closed = {i.id for i in items.values() if i.state == "closed"}
    return [i for i in items.values()
            if i.state == "ready-for-agent" and i.part not in live and all(b in closed for b in i.blocked_by)]


def mint(items_dir: Path, **fields) -> Item:
    """Create the next item. The file is written whole to a temp name and hard-linked into place, which fails
    if the name exists, so two sessions can never take one number and no reader sees a half-written file."""
    items_dir.mkdir(parents=True, exist_ok=True)
    Item(id="I-0", **fields).validate()
    number = max((int(i[2:]) for i in load_names(items_dir)), default=0) + 1
    while True:
        item = Item(id=f"I-{number}", **fields)
        if item.body and not item.body.endswith("\n"):
            item.body += "\n"
        tmp = items_dir / f".mint-{uuid.uuid4().hex}.tmp"
        tmp.write_text(dump(item), encoding="utf-8", newline="\n")
        try:
            os.link(tmp, items_dir / f"{item.id}.md")
        except FileExistsError:
            number += 1
            continue
        finally:
            tmp.unlink(missing_ok=True)
        return item


def load_names(items_dir: Path) -> list[str]:
    return [p.stem for p in items_dir.iterdir() if FILE_RE.match(p.name)]
