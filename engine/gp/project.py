"""A project is any folder with greenfield/fence.yaml. This module finds it and scaffolds it (plan section 2)."""
from __future__ import annotations

from pathlib import Path

import yaml

FENCE_REL = Path("greenfield") / "fence.yaml"
SUBDIRS = ("sources", "requirements", "items", "design/contracts", "domain", "doubles", "suites", "runs",
           "evidence", "handover")
FILES = {
    "builds.yaml": "{}\n",
    "deps.tsv": "name\tversion\tlicense\tregistry\titem\n",
    "decisions.tsv": "ts\titem\tdecision\twhy\tevidence\tresult\n",
    "acceptances.jsonl": "",
}
FENCE_TEMPLATE = """\
# The fence: what may be touched. Writing this file is always-pause; the owner accepts the diff.
version: 1
pack: {pack}
pack_path: {pack_path}
pack_sha256: {pack_sha}
# Repos the agent may commit to. runner: container (default) | process (owner accepted).
code_repos: []            # - {{path: product, runner: container}}
# Registries installs may use, by host. Anything else asks.
registries: []            # - {{name: pypi, host: pypi.org}}
# Hosts a remote environment may be reached at. Production is never listed.
remote_hosts: []
# Declared push and deploy lanes. A command matching `match` goes through without asking.
lanes: []                 # - {{name: staging, kind: deploy, match: "^deploy-staging\\\\b"}}
# The project ceiling. Reaching a limit raises a ready-for-human item and stops that line of work.
budget: {{runs_per_ac: 3, builds_total: 200, deadline: null}}
# The ladder, the owner's: part -> hitl | afk (default afk). `unattended` is specified and not built.
ladder: {{}}
# Extra regexes that mark a command or argument as production.
production_markers: []
"""


def find_project(start: str | Path) -> Path | None:
    path = Path(start).resolve()
    for candidate in (path, *path.parents):
        if (candidate / FENCE_REL).is_file():
            return candidate
    return None


def load_fence(project: Path) -> dict:
    data = yaml.safe_load((project / FENCE_REL).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("fence.yaml must be a mapping")
    return data


def init_project(root: Path, pack_name: str, pack_path: Path, pack_sha: str) -> list[str]:
    base = root / "greenfield"
    made = []
    for sub in SUBDIRS:
        (base / sub).mkdir(parents=True, exist_ok=True)
        made.append(f"greenfield/{sub}/")
    for name, content in FILES.items():
        target = base / name
        if not target.exists():
            target.write_text(content, encoding="utf-8", newline="\n")
            made.append(f"greenfield/{name}")
    fence = FENCE_TEMPLATE.format(pack=pack_name, pack_path=pack_path.as_posix(), pack_sha=pack_sha)
    (base / "fence.yaml").write_text(fence, encoding="utf-8", newline="\n")
    made.append("greenfield/fence.yaml")
    return made
