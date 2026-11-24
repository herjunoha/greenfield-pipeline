"""The path language checks use over a JSON observation: $.a.b[0].c and $['odd key']. A path that cannot be
read returns MISSING, which no check except `absent` may treat as a pass."""
from __future__ import annotations

import re

MISSING = object()
_TOKEN = re.compile(r"\.([^.\[\]]+)|\[(-?\d+)\]|\['([^']*)'\]|\[\"([^\"]*)\"\]")


class PathError(ValueError):
    pass


def parse(path: str) -> list:
    if not isinstance(path, str) or not path.startswith("$"):
        raise PathError(f"path {path!r} must start with $")
    tokens, pos = [], 1
    while pos < len(path):
        match = _TOKEN.match(path, pos)
        if not match:
            raise PathError(f"path {path!r} is not valid at position {pos}")
        name, index, single, double = match.groups()
        tokens.append(int(index) if index is not None else next(t for t in (name, single, double) if t is not None))
        pos = match.end()
    return tokens


def get(obj, path: str):
    node = obj
    for token in parse(path):
        if isinstance(token, int):
            if not isinstance(node, list) or not -len(node) <= token < len(node):
                return MISSING
            node = node[token]
        else:
            if not isinstance(node, dict) or token not in node:
                return MISSING
            node = node[token]
    return node
