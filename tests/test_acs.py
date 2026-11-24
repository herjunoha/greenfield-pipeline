import json

import yaml

from conftest import edit_canonical, run_gf, suite_dict, write_suite


def acs(project, *args):
    return run_gf(project, "acs", *args)


def rows(project):
    return {r["id"]: r for r in json.loads(acs(project, "--json").stdout)["acs"]}


def raised(project):
    r = run_gf(project, "raise")
    assert r.returncode == 0, r.stdout + r.stderr
    return [line.split("\t") for line in r.stdout.strip().splitlines() if "\t" in line]


def item(project, number):
    from gp import items
    return items.load_all(project / "greenfield" / "items")[f"I-{number}"]


def close(project, number, source, reason="done"):
    from gp import items
    it = item(project, number)
    it.state, it.reason, it.source = "closed", reason, source
    (project / "greenfield" / "items" / f"I-{number}.md").write_text(items.dump(it), encoding="utf-8")


def new_assumption(project, ac="AC-2", source="memory", *more):
    return run_gf(project, "new", "assumed fact", "--kind", "assumption", "--source", source, "--acs", ac, *more)


def suite_for(project, ac="AC-2"):
    return write_suite(project, suite_dict(ac=ac, surface="linkr-api"), name=ac)


# --- the audit on acme-linkr --------------------------------------------------------------------------------

def test_zero_orphan_requirements_on_acme_linkr(linkr):
    r = acs(linkr)
    assert r.returncode == 0, r.stdout
    assert "orphans: none" in r.stdout and "refused" not in r.stdout
    assert len(rows(linkr)) == 8 and all(row["state"] == "no-suite" for row in rows(linkr).values())


def test_a_requirement_with_no_source_is_an_orphan(linkr):
    edit_canonical(linkr, lambda d: d["requirements"][2].pop("source"))
    r = acs(linkr)
    assert r.returncode == 1 and "AC-3: orphan, no source" in r.stdout and "orphans: none" not in r.stdout


def test_a_source_that_does_not_exist_is_an_orphan(linkr):
    edit_canonical(linkr, lambda d: d["requirements"][0].update(source="notes.md#create"))
    edit_canonical(linkr, lambda d: d["requirements"][1].update(source="item:I-9"))
    out = acs(linkr).stdout
    assert "AC-1: orphan, source notes.md is not under greenfield/sources/" in out
    assert "AC-2: orphan, item:I-9 is not a closed item" in out


def test_a_closed_item_is_a_source_an_open_one_is_not(linkr):
    run_gf(linkr, "new", "owner accepted authentication", "--state", "ready-for-human")
    edit_canonical(linkr, lambda d: d["requirements"][0].update(source="item:I-1"))
    assert "AC-1: orphan" in acs(linkr).stdout
    close(linkr, 1, "brief.md")
    assert acs(linkr).returncode == 0


def test_an_invalid_canonical_is_refused_before_anything_is_judged(linkr):
    edit_canonical(linkr, lambda d: d["requirements"][0].update(dimension="vibes"))
    r = acs(linkr)
    assert r.returncode == 1 and "dimension must be" in r.stdout
    assert run_gf(linkr, "check").returncode == 1


def test_no_canonical_and_two_canonicals(project):
    assert "no canonical yet" in acs(project).stdout and acs(project).returncode == 0
    for name in ("a", "b"):
        (project / "greenfield" / "requirements" / f"{name}.canonical.yaml").write_text("project: {}\n", encoding="utf-8")
    assert "one canonical per project" in acs(project).stdout


# --- shas and staleness -------------------------------------------------------------------------------------

def test_a_sha_follows_its_own_ac_only(linkr):
    before = rows(linkr)
    edit_canonical(linkr, lambda d: d["requirements"][1].update(acceptance="GET /<code> answers 301."))
    after = rows(linkr)
    assert after["AC-2"]["baseline_sha"] != before["AC-2"]["baseline_sha"]
    assert all(after[k]["baseline_sha"] == before[k]["baseline_sha"] for k in before if k != "AC-2")


def test_a_contract_sha_follows_the_contract_file(linkr):
    before = rows(linkr)
    contract = linkr / "greenfield" / "design" / "contracts" / "links.yaml"
    contract.write_text(contract.read_text(encoding="utf-8") + "# changed\n", encoding="utf-8")
    after = rows(linkr)
    assert after["AC-1"]["contract_sha"] != before["AC-1"]["contract_sha"]
    assert after["AC-7"]["contract_sha"] == before["AC-7"]["contract_sha"] == "none"   # the cli has no contract


def test_line_endings_do_not_change_a_contract_sha(linkr):
    before = rows(linkr)["AC-1"]["contract_sha"]
    contract = linkr / "greenfield" / "design" / "contracts" / "links.yaml"
    contract.write_bytes(contract.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    assert rows(linkr)["AC-1"]["contract_sha"] == before


def test_a_current_suite_passes_and_a_changed_ac_stales_it(linkr):
    suite_for(linkr)
    assert run_gf(linkr, "check").returncode == 0 and rows(linkr)["AC-2"]["suite"] == "current"
    edit_canonical(linkr, lambda d: d["requirements"][1].update(acceptance="GET /<code> answers 301."))
    r = run_gf(linkr, "check")
    assert r.returncode == 1 and "baseline_sha is stale" in r.stdout
    assert run_gf(linkr, "run", "--ac", "AC-2").returncode == 1
    assert rows(linkr)["AC-2"]["suite"] == "stale" and rows(linkr)["AC-2"]["state"] == "stale"


def test_a_changed_contract_stales_its_suites(linkr):
    suite_for(linkr)
    contract = linkr / "greenfield" / "design" / "contracts" / "links.yaml"
    contract.write_text(contract.read_text(encoding="utf-8") + "# changed\n", encoding="utf-8")
    assert "contract_sha is stale" in run_gf(linkr, "check").stdout


def test_a_suite_must_match_its_ac_surface_and_dimension(linkr):
    write_suite(linkr, suite_dict(ac="AC-2", surface="linkr-cli"), name="AC-2")
    assert "suite surface 'linkr-cli' differs" in run_gf(linkr, "check").stdout
    write_suite(linkr, suite_dict(ac="AC-2", surface="linkr-api", dimension="security"), name="AC-2")
    assert "suite dimension 'security' differs" in run_gf(linkr, "check").stdout


def test_a_suite_for_an_ac_the_canonical_does_not_have_is_refused(linkr):
    write_suite(linkr, suite_dict(ac="AC-42", surface="linkr-api"), name="AC-42")
    assert "AC-42: is not a requirement id" in run_gf(linkr, "check").stdout


# --- regulated data -----------------------------------------------------------------------------------------

def test_personal_and_credentials_raise_no_regulated_item(linkr):
    edit_canonical(linkr, lambda d: d["project"].update(data_classes=["personal", "credentials"]))
    assert not [r for r in raised(linkr) if "Regulated" in r[2]]
    assert "handover blocked" not in acs(linkr).stdout


def test_a_regulated_data_class_raises_one_item_once_and_blocks_handover(linkr):
    edit_canonical(linkr, lambda d: d["project"].update(data_classes=["personal", "health", "children"]))
    assert "handover blocked: regulated data: children, health" in acs(linkr).stdout
    made = [r for r in raised(linkr) if "Regulated" in r[2]]
    assert len(made) == 1 and made[0][1] == "ready-for-human"
    it = item(linkr, int(made[0][0][2:]))
    assert it.source == "canonical:regulated:children+health" and "The agent's pick." in it.body
    assert not [r for r in raised(linkr) if "Regulated" in r[2]]                  # idempotent
    assert "handover blocked" in acs(linkr).stdout                                # an open item still blocks
    close(linkr, int(made[0][0][2:]), it.source)
    assert "handover blocked" not in acs(linkr).stdout


def test_a_sponsor_named_regime_raises_the_item_even_for_benign_data(linkr):
    edit_canonical(linkr, lambda d: d["project"].update(regulated=["GDPR"]))
    assert "handover blocked: regulated data: GDPR" in acs(linkr).stdout
    assert len([r for r in raised(linkr) if "Regulated" in r[2]]) == 1


def test_a_new_regulated_class_after_closing_raises_a_fresh_item(linkr):
    edit_canonical(linkr, lambda d: d["project"].update(data_classes=["health"]))
    first = [r for r in raised(linkr) if "Regulated" in r[2]][0][0]
    close(linkr, int(first[2:]), "canonical:regulated:health")
    edit_canonical(linkr, lambda d: d["project"].update(data_classes=["health", "biometric"]))
    assert "handover blocked" in acs(linkr).stdout
    assert len([r for r in raised(linkr) if "Regulated" in r[2]]) == 1


# --- baseline needs -----------------------------------------------------------------------------------------

def test_unspecified_baseline_needs_become_one_triage_item_each(linkr):
    notes = [line for line in acs(linkr).stdout.splitlines() if line.startswith("note: baseline need")]
    assert len(notes) == 4                              # AC-5 states authentication, AC-6 rough_load
    made = raised(linkr)
    assert len(made) == 4 and {m[1] for m in made} == {"needs-triage"}
    assert not raised(linkr) and "baseline need" not in acs(linkr).stdout


# --- assumptions --------------------------------------------------------------------------------------------

def test_memory_cannot_close_an_assumption(linkr):
    for source in ("memory", "public:https://example.com/x"):
        r = new_assumption(linkr, "AC-2", source, "--state", "closed", "--reason", "done")
        assert r.returncode != 0 and "cannot close" in r.stderr + r.stdout, source
    assert not list((linkr / "greenfield" / "items").iterdir())


def test_a_run_or_the_sponsor_can_close_an_assumption(linkr):
    for source in ("tried", "sponsor-confirmed", "sponsor-document"):
        assert new_assumption(linkr, "AC-2", source, "--state", "closed", "--reason", "done").returncode == 0, source


def test_an_assumption_needs_a_tag_as_its_source(linkr):
    r = new_assumption(linkr, "AC-2", "brief, para 2")
    assert r.returncode != 0 and "its tag" in r.stderr + r.stdout


def test_a_hand_edited_memory_closure_is_refused_on_read(linkr):
    assert new_assumption(linkr, "AC-2", "memory").returncode == 0
    path = linkr / "greenfield" / "items" / "I-1.md"
    path.write_text(path.read_text(encoding="utf-8").replace("state: needs-triage", "state: closed\nreason: done"),
                    encoding="utf-8")
    r = run_gf(linkr, "status")
    assert r.returncode == 2 and "cannot close" in r.stderr


def test_an_open_assumption_makes_its_ac_assumed_whatever_the_suite_says(linkr):
    suite_for(linkr)
    assert rows(linkr)["AC-2"]["state"] == "in-review"
    assert new_assumption(linkr, "AC-2", "memory").returncode == 0
    row = rows(linkr)["AC-2"]
    assert row["state"] == "assumed" and row["suite"] == "current" and row["assumptions"] == ["I-1"]
    assert "assumed  assumes I-1" in acs(linkr).stdout
    assert "acs: 1 assumed, 7 no-suite" in run_gf(linkr, "status").stdout
    assert rows(linkr)["AC-3"]["state"] == "no-suite"


def test_resolving_the_assumption_releases_the_ac_and_wontfix_does_not(linkr):
    assert new_assumption(linkr, "AC-2", "memory").returncode == 0
    assert new_assumption(linkr, "AC-3", "memory").returncode == 0
    close(linkr, 1, "tried")
    close(linkr, 2, "memory", reason="wontfix")
    assert rows(linkr)["AC-2"]["state"] == "no-suite"
    assert rows(linkr)["AC-3"]["state"] == "assumed"          # dropping a fact is not proving it


def test_unconfirmed_glossary_terms_and_examples_are_noted(linkr):
    edit_canonical(linkr, lambda d: d["project"]["glossary"][0].update(confirmed=False))
    edit_canonical(linkr, lambda d: d["examples"][1].pop("confirmed_by"))
    out = acs(linkr).stdout
    assert "AC-1 uses the unconfirmed term 'short code'" in out
    assert "example EX-2 is not confirmed" in out
    assert acs(linkr).returncode == 0                          # notes never fail
