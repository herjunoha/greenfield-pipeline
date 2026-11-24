"""The generic pack's handover documents: plain markdown rendered from `handover.data` (plan 4.7, 8). A pack may map
each document to a nicer renderer; this is the complete fallback. Every document opens by saying an AI drafted it.
Roles, never names. The certificate is left unsigned: a signature is the owner's and cannot be taken back."""
from __future__ import annotations

from pathlib import Path

from . import handover

NOTICE = ("> This document was drafted by an AI agent (greenfield-pipeline) from the project's files. "
          "A person has not yet reviewed it.\n\n")


def _bullets(items) -> str:
    return "\n".join(f"- {i}" for i in items) or "- none"


def baseline(d: dict) -> str:
    p = d["project"]
    surfaces = _bullets(f"{s['name']} ({s['kind']})" for s in p["surfaces"])
    terms = _bullets(f"{g['term']}: {g['meaning']}" + ("" if g["confirmed"] else " (not yet confirmed)") for g in p["glossary"])
    acs = "\n".join(f"- **{a['id']}** ({a['dimension']}, {a['surface']}): {a['statement']}\n  - acceptance: {a['acceptance']}"
                    for a in d["acs"])
    state = "approved by the owner" if p["approved"] else "NOT approved: a draft"
    return (f"{NOTICE}# Requirements baseline: {p['name']}\n\nStatus: {state}.\n\n## Objectives\n{_bullets(p['objectives'])}\n\n"
            f"## Out of scope\n{_bullets(p['out_of_scope'])}\n\n## Surfaces\n{surfaces}\n\n## Terms\n{terms}\n\n"
            f"## Acceptance criteria\n{acs}\n")


def design(d: dict) -> str:
    rows = _bullets(r.replace("\t", " | ") for r in d["decisions"])
    return (f"{NOTICE}# Design record\n\n{d['design'] or '(no architecture document was written)'}\n\n## Contracts\n"
            f"{_bullets(d['contracts'])}\n\n## Decisions (time | item | decision | why | evidence | result)\n{rows}\n")


def acceptance(d: dict) -> str:
    lines = []
    for a in d["acs"]:
        builds = ", ".join(f"{c} {str(b)[:8]}" for c, b in a["build"].items()) or "no build recorded"
        lines.append(f"- **{a['id']}**: {a['state']}. Latest full run: {a['run'] or 'none'} ({a['run_verdict'] or 'n/a'}), "
                     f"build {builds}. Suite reviewed: {'yes' if a['suite_reviewed'] else 'no'}."
                     + "".join(f"\n  - still missing: {m}" for m in a["missing"]))
    return f"{NOTICE}# Acceptance record\n\nAn AC is done only when a full run of its accepted suite passed on the current build, " \
           f"a second reviewer checked that run, red was seen first and the baseline is approved.\n\n" + "\n".join(lines) + "\n"


def test_sheet(d: dict) -> str:
    rows = "\n".join(f"- {t['ac']} / {t['case']} [{t['type']}, {t['severity']}] {t['name']}: **{t['status']}** (run {t['run']})"
                     for t in d["tests"]) or "- no full run recorded"
    return f"{NOTICE}# Test sheet\n\n{rows}\n"


def certificate(d: dict) -> str:
    done = [a["id"] for a in d["acs"] if a["state"] == "done"]
    rest = [a["id"] for a in d["acs"] if a["state"] != "done"]
    owner, sponsor = d["roles"].get("owner", "owner"), d["roles"].get("sponsor", "sponsor")
    return (f"{NOTICE}# Acceptance certificate: {d['project']['name']}\n\nAcceptance criteria met: {', '.join(done) or 'none'}.\n"
            f"Not met or not proven: {', '.join(rest) or 'none'} (see the limits page).\n\nThis certificate is unsigned. "
            f"A signature cannot be taken back, so it is the {owner}'s and the {sponsor}'s to give.\n\n"
            f"{owner}: ____________  Date: ________\n\n{sponsor}: ____________  Date: ________\n")


def release_notes(d: dict) -> str:
    parts = [f"## {comp}\n{_bullets(log)}" for comp, log in d["releases"].items()]
    return f"{NOTICE}# Release notes\n\n" + ("\n\n".join(parts) or "No product repo is declared.") + "\n"


def rollback(d: dict) -> str:
    parts = [f"- {comp}: return to commit {prev}" if prev else f"- {comp}: no earlier commit to return to"
             for comp, prev in d["rollback"].items()]
    return (f"{NOTICE}# Rollback note\n\nNothing is deployed by this pipeline unless the owner declared a lane. To go back, "
            f"check out the earlier commit and run the same quickstart.\n\n{_bullets(parts)}\n")


def limits(d: dict) -> str:
    lim = d["limits"]
    regimes = ", ".join(lim["regimes"]) or "none"
    stops = "\n".join(f"- {n['id']} is {n['state']}" + "".join(f"\n  - {s}" for s in n["stops"]) for n in lim["not_done"])
    assume = "\n".join(f"- {a['id']} {a['title']} (tag: {a['tag']}, {a['state']}; ACs: {', '.join(a['acs']) or 'none'})"
                       for a in lim["assumptions"])
    return (f"{NOTICE}# Limits: what stayed unproven\n\nA green verdict means the suites passed on one build. It is not a "
            f"guarantee of quality outside what they check.\n\n## Not done\n{stops or '- none'}\n\n"
            f"## Verified by a person only (no driver observed it)\n{_bullets(lim['manual'])}\n\n"
            f"## Doubles: not proven against the real service\n{_bullets(lim['doubles'])}\n\n"
            f"## Open assumptions\n{assume or '- none'}\n\n## Notes\n{_bullets(lim['notes'])}\n\n## Compliance\n"
            f"compliance: not assessed by this pipeline; regimes named by the sponsor: {regimes}\n"
            f"Data classes handled: {', '.join(lim['data_classes'])}.\n")


DOCUMENTS = {"01-requirements-baseline.md": baseline, "02-design-record.md": design, "03-acceptance-record.md": acceptance,
             "04-test-sheet.md": test_sheet, "05-acceptance-certificate.md": certificate, "06-release-notes.md": release_notes,
             "07-rollback-note.md": rollback, "08-limits.md": limits}


def write(root: Path) -> list[str]:
    """Render every document into greenfield/handover/. Raises HandoverError; writes nothing when it refuses."""
    d = handover.data(root)
    folder = root / "greenfield" / "handover"
    folder.mkdir(parents=True, exist_ok=True)
    for name, render in DOCUMENTS.items():
        (folder / name).write_text(render(d), encoding="utf-8", newline="\n")
    return list(DOCUMENTS)
