"""A small JSON Schema subset for the `schema` op, stdlib only: type, enum, required, properties,
additionalProperties false, items, minimum, maximum, minLength, maxLength, pattern. Anything else is refused
rather than silently ignored, so a schema that cannot be enforced never reads as a pass."""
from __future__ import annotations

import re

SUPPORTED = {"type", "enum", "required", "properties", "additionalProperties", "items", "minimum", "maximum",
             "minLength", "maxLength", "pattern", "description", "title"}
_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def _is(value, name: str) -> bool:
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, _TYPES[name]) and not (name != "boolean" and isinstance(value, bool))


def unsupported(schema) -> list[str]:
    if not isinstance(schema, dict):
        return ["a schema must be an object"]
    out = [f"schema keyword {k!r} is not supported" for k in schema if k not in SUPPORTED]
    for sub in (schema.get("properties") or {}).values():
        out += unsupported(sub)
    if isinstance(schema.get("items"), dict):
        out += unsupported(schema["items"])
    return out


def validate(value, schema: dict, at: str = "$") -> list[str]:
    errors = []
    kind = schema.get("type")
    if kind and not any(_is(value, t) for t in ([kind] if isinstance(kind, str) else kind)):
        return [f"{at}: expected {kind}, got {type(value).__name__}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{at}: {value!r} is not one of {schema['enum']}")
    if isinstance(value, dict):
        errors += [f"{at}: missing required {k!r}" for k in schema.get("required", []) if k not in value]
        props = schema.get("properties", {})
        for key, sub in props.items():
            if key in value:
                errors += validate(value[key], sub, f"{at}.{key}")
        if schema.get("additionalProperties") is False:
            errors += [f"{at}: unexpected property {k!r}" for k in value if k not in props]
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        for i, item in enumerate(value):
            errors += validate(item, schema["items"], f"{at}[{i}]")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{at}: {value} is below {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{at}: {value} is above {schema['maximum']}")
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{at}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{at}: longer than {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{at}: does not match {schema['pattern']}")
    return errors
