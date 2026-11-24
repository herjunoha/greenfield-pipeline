from concurrent.futures import ThreadPoolExecutor

import pytest

from gp import items
from gp.items import Item, ItemError


def make(**kw):
    base = dict(id="I-1", title="Redirect a short link", state="ready-for-agent")
    base.update(kw)
    return Item(**base)


def test_round_trip_every_field():
    item = make(acs=["AC-1", "AC-2"], blocked_by=["I-0"], source="memory", kind="assumption",
                body="Why now.\n\n---\nA rule line inside the body.\nUnicode: → café\n")
    again = items.parse(items.dump(item), "I-1")
    assert again == item


def test_round_trip_closed_with_reason():
    item = make(state="closed", reason="wontfix", body="Asked again in March; same answer.\n")
    assert items.parse(items.dump(item), "I-1") == item


@pytest.mark.parametrize("fields,message", [
    (dict(state="done"), "state"),
    (dict(state="closed"), "reason"),
    (dict(state="ready-for-agent", reason="done"), "only for closed"),
    (dict(kind="guess"), "kind"),
    (dict(title="  "), "title"),
    (dict(blocked_by=["banana"]), "blocked_by"),
    (dict(blocked_by=["I-1"]), "block itself"),
    (dict(acs="AC-1"), "acs"),
])
def test_validation_refuses(fields, message):
    with pytest.raises(ItemError, match=message):
        make(**fields).validate()


def test_parse_refuses_unknown_key_and_missing_frontmatter():
    with pytest.raises(ItemError, match="unknown"):
        items.parse("---\ntitle: x\nstate: closed\nreasno: done\n---\n", "I-1")
    with pytest.raises(ItemError, match="frontmatter"):
        items.parse("just text", "I-1")


def test_mint_numbers_in_order_and_survives_gaps(tmp_path):
    d = tmp_path / "items"
    a = items.mint(d, title="a")
    b = items.mint(d, title="b")
    (d / "I-9.md").write_text(items.dump(make(id="I-9", title="gap")), encoding="utf-8")
    c = items.mint(d, title="c")
    assert [a.id, b.id, c.id] == ["I-1", "I-2", "I-10"]
    assert not list(d.glob(".mint-*"))


def test_parallel_mints_never_share_a_number(tmp_path):
    d = tmp_path / "items"
    with ThreadPoolExecutor(16) as pool:
        ids = list(pool.map(lambda n: items.mint(d, title=f"t{n}").id, range(60)))
    assert len(set(ids)) == 60
    assert sorted(int(i[2:]) for i in ids) == list(range(1, 61))
    assert len(items.load_all(d)) == 60


def test_mint_rejects_invalid_before_writing(tmp_path):
    d = tmp_path / "items"
    with pytest.raises(ItemError):
        items.mint(d, title="x", state="closed")
    assert not list(d.glob("*.md"))


def test_load_all_sorts_numerically(tmp_path):
    d = tmp_path / "items"
    for _ in range(11):
        items.mint(d, title="t")
    assert list(items.load_all(d))[-2:] == ["I-10", "I-11"]


def test_frontier():
    def mk(n, state, blocked=()):
        return make(id=f"I-{n}", title=f"t{n}", state=state, blocked_by=list(blocked),
                    reason="done" if state == "closed" else None)
    all_ = {i.id: i for i in [
        mk(1, "closed"), mk(2, "ready-for-agent", ["I-1"]), mk(3, "ready-for-agent", ["I-2"]),
        mk(4, "ready-for-human"), mk(5, "ready-for-agent", ["I-99"]), mk(6, "ready-for-agent")]}
    assert [i.id for i in items.frontier(all_)] == ["I-2", "I-6"]
