"""Shared by the drivers: `{{N.path}}` in a step's strings is replaced by what step N observed (stdlib only).
`{{0.body.code}}` is the first step's observed body.code. A value that is not there is an error for the case, never
a guess, so a product that returns no code leaves an error after the failed check, not an invented path."""
import re

_TEMPLATE = re.compile(r"\{\{\s*(\d+)((?:\.\w+|\[-?\d+\])*)\s*\}\}")


def _pick(node, trail):
    for part in re.findall(r"\.(\w+)|\[(-?\d+)\]", trail):
        key, index = part
        try:
            node = node[key] if key else node[int(index)]
        except (KeyError, IndexError, TypeError):
            raise ValueError("template value is not there: " + trail)
    return node


def fill(value, steps):
    """Return `value` with every template resolved against the observations so far."""
    if isinstance(value, str):
        def swap(match):
            n = int(match.group(1))
            if n >= len(steps):
                raise ValueError(f"template {match.group(0)} refers to a step that did not run")
            got = _pick(steps[n]["observed"], match.group(2))
            if isinstance(got, (dict, list)):
                raise ValueError(f"template {match.group(0)} is not a single value")
            return str(got)
        return _TEMPLATE.sub(swap, value)
    if isinstance(value, dict):
        return {k: fill(v, steps) for k, v in value.items()}
    if isinstance(value, list):
        return [fill(v, steps) for v in value]
    return value
