"""acme-linkr command line: create, open and stats, kept in a small JSON file. Stdlib only."""
import json
import os
import random
import string
import sys


def load(path):
    return json.load(open(path)) if os.path.exists(path) else {}


def main(argv):
    if "--db" not in argv:
        print("usage: linkr --db FILE create|open|stats ...", file=sys.stderr)
        return 2
    i = argv.index("--db")
    db, rest = argv[i + 1], argv[:i] + argv[i + 2:]
    data = load(db)
    command, args = rest[0], [a.strip() for a in rest[1:]]
    if command == "create":
        code = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6))
        data[code] = {"url": args[0], "visits": 0}
        print(code)
    elif command == "open" and args[0] in data:
        data[args[0]]["visits"] += 1
        print(data[args[0]]["url"])
    elif command == "stats" and args[0] in data:
        print(data[args[0]]["visits"])
    else:
        print("unknown code or command", file=sys.stderr)
        return 1
    json.dump(data, open(db, "w"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
