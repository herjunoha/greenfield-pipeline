"""Company packs (plan section 8). Step 1 ships the generic pack only: resolve, hash and read it."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import yaml

GENERIC = "generic"


class PackError(ValueError):
    pass


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[2]


def installed_dir() -> Path:
    return Path(os.environ.get("GP_PACKS_DIR") or Path.home() / ".greenfield-pipeline" / "packs")


def _scan(directory: Path) -> dict[str, Path]:
    if not directory.is_dir():
        return {}
    return {p.parent.name: p.parent for p in sorted(directory.glob("*/pack.yaml"))}


def bundled() -> dict[str, Path]:
    return _scan(plugin_root() / "packs")


def installed() -> dict[str, Path]:
    return {k: v for k, v in _scan(installed_dir()).items() if k != GENERIC}


def resolve(requested: str | None = None) -> tuple[str, Path, str]:
    """--pack, else the only installed pack, else GP_PACK, else generic. Returns name, path, reason."""
    known = {**bundled(), **installed()}
    if requested:
        if requested not in known:
            raise PackError(f"pack {requested!r} not found; known: {', '.join(sorted(known))}")
        return requested, known[requested], "from --pack"
    found = installed()
    if len(found) == 1:
        name, path = next(iter(found.items()))
        return name, path, "the only installed pack"
    env = os.environ.get("GP_PACK")
    if env:
        if env not in known:
            raise PackError(f"GP_PACK={env!r} not found; known: {', '.join(sorted(known))}")
        return env, known[env], "from GP_PACK"
    return GENERIC, bundled()[GENERIC], "no pack chosen, using the bundled generic pack"


def sha256(pack_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in pack_dir.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        digest.update(path.relative_to(pack_dir).as_posix().encode() + b"\0")
        digest.update(path.read_bytes() + b"\0")
    return digest.hexdigest()


def load(pack_dir: Path) -> dict:
    data = yaml.safe_load((pack_dir / "pack.yaml").read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "name" not in data:
        raise PackError(f"{pack_dir / 'pack.yaml'} must be a mapping with a name")
    return data


def show(pack_dir: Path, key: str):
    """A pack.yaml key (dotted), else the text of `<key>.md` in the pack folder (lessons, offerings, standards)."""
    if "." not in key and key.isalpha() and key not in load(pack_dir) and (pack_dir / f"{key}.md").is_file():
        return (pack_dir / f"{key}.md").read_text(encoding="utf-8").rstrip(chr(10))
    value = load(pack_dir)
    for part in key.split("."):
        if not isinstance(value, dict) or part not in value:
            raise PackError(f"pack has no key {key!r}")
        value = value[part]
    return value
