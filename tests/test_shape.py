from conftest import run_gf

DESIGN = """# Design
## Components
linkr-api and linkr-cli.
## Data
A links table.
## Runtime
One process.
## Stack
Python standard library.
## Alternatives
A framework: more than the toy needs.
"""


def put(project, text):
    (project / "greenfield" / "design" / "architecture.md").write_text(text, encoding="utf-8")


def out(project):
    r = run_gf(project, "check")
    return r.returncode, r.stdout


def test_no_design_no_shape_rules(linkr):
    assert out(linkr)[0] == 0


def test_a_good_design_with_a_logged_decision_passes(linkr):
    put(linkr, DESIGN)
    assert "decisions.tsv has no rows" in out(linkr)[1]
    run_gf(linkr, "decide", "standard library only", "--why", "a toy")
    assert out(linkr)[0] == 0


def test_the_design_must_stay_short_and_cover_the_parts(linkr):
    run_gf(linkr, "decide", "x", "--why", "y")
    put(linkr, "# Design\n## Components\nlinkr-api only.\n" + "line\n" * 130)
    text = out(linkr)[1]
    assert "lines; two pages is about 120" in text and "has no heading for: data, runtime, stack, alternatives" in text
    assert "never mentions the surface linkr-cli" in text
