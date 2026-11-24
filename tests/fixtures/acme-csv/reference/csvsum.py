"""acme-csv reference implementation. Stdlib only."""
import csv
import json
import sys

VERSION = "0.1.0"


def number(text):
    try:
        return float(text) if "." in text else int(text)
    except ValueError:
        return None


def summarize(path):
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        sums = {name: 0 for name in (reader.fieldnames or [])}
        numeric = set(sums)
        rows = 0
        for row in reader:
            rows += 1
            for name in list(numeric):
                value = number(row.get(name) or "")
                if value is None:
                    numeric.discard(name)
                else:
                    sums[name] += value
    return {"rows": rows, "sums": {name: total for name, total in sums.items() if name in numeric}}


def main(argv):
    if "--version" in argv:
        print(VERSION)
        return 0
    if len(argv) >= 4 and argv[0] == "summarize" and argv[2] == "--out":
        try:
            result = summarize(argv[1])
        except OSError:
            print(f"file not found: {argv[1]}", file=sys.stderr)
            return 2
        with open(argv[3], "w", encoding="utf-8") as out:
            json.dump(result, out, sort_keys=True)
        return 0
    print("usage: csvsum summarize <input.csv> --out <summary.json>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
