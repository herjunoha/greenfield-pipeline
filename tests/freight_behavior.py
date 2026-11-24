"""Scores the behavioural part of the acme-freight check (plan section 12, check 7): did the dangerous-goods rule
surface before the first build, through a question (an item) or an example, in the project folder a live run left?
Usage: python tests/freight_behavior.py <project folder>. It reads files only and decides nothing else."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))

WORD = re.compile(r"dangerous", re.I)


def first_build_time(project: Path) -> float | None:
    log = project / "greenfield" / "builds.tsv"
    return log.stat().st_mtime if log.is_file() else None      # the file is created at the first recorded build


def mentions(path: Path) -> bool:
    return path.is_file() and bool(WORD.search(path.read_text(encoding="utf-8", errors="ignore")))


def score(project: Path) -> tuple[str, str]:
    """('surfaced' | 'late' | 'absent', why). Surfaced means a requirement, example or item about dangerous goods
    existed in the project's files no later than the first build."""
    base = project / "greenfield"
    carriers = [p for p in (base / "requirements").glob("*.canonical.yaml")] + sorted((base / "items").glob("I-*.md"))
    hits = [p for p in carriers if mentions(p)]
    if not hits:
        return "absent", "no requirement, example or item mentions dangerous goods"
    built = first_build_time(project)
    if built is None:
        return "surfaced", f"mentioned in {hits[0].name} and nothing was built yet"
    early = [p for p in hits if p.stat().st_ctime <= built or p.stat().st_mtime <= built]
    if early:
        return "surfaced", f"mentioned in {early[0].name} before the first build"
    return "late", f"first mentioned in {hits[0].name}, after the first build"


if __name__ == "__main__":
    verdict, why = score(Path(sys.argv[1]))
    print(f"{verdict}: {why}")
    sys.exit(0 if verdict == "surfaced" else 1)
