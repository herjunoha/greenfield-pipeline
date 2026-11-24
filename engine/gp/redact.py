"""Redaction (plan 8, connectors): phone numbers, emails, tokens and the pack's `redact` patterns are removed from
text BEFORE anything is written to a file or sent. The text never reaches disk unredacted."""
from __future__ import annotations

import re

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
TOKEN = re.compile(r"(?i)\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|"
                   r"AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+)\b|"
                   r"(?i:bearer\s+[A-Za-z0-9._~+/=-]{16,})")
PHONE = re.compile(r"(?<![\w.])\+?\(?\d[\d\s().-]{7,}\d(?![\w])")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def clean(text: str, extra: list[str] | tuple = ()) -> tuple[str, dict]:
    """Returns the redacted text and how many of each kind were removed (never the values)."""
    counts = {"email": 0, "token": 0, "phone": 0, "pack": 0}
    text, counts["token"] = TOKEN.subn("[token]", text)
    text, counts["email"] = EMAIL.subn("[email]", text)

    def swap(match: re.Match) -> str:
        found = match.group(0)
        digits = re.sub(r"\D", "", found)
        if DATE.match(found.strip()) or not 9 <= len(digits) <= 15:
            return found
        counts["phone"] += 1
        return "[phone]"

    text = PHONE.sub(swap, text)
    for pattern in extra:
        text, n = re.subn(pattern, "[redacted]", text)
        counts["pack"] += n
    return text, counts
