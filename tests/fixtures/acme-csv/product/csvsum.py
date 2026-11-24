"""acme-csv walking skeleton: a run command and --version, nothing else."""
import sys

VERSION = "0.0.1"


def main(argv):
    if "--version" in argv:
        print(VERSION)
        return 0
    print("not built yet", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
