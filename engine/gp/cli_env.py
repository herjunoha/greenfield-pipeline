"""gp preflight, gp build, gp product init: environments, build identity and the product repo."""
from __future__ import annotations

from pathlib import Path

from . import budget, builds, environments, runner
from . import project as proj


def _root() -> Path:
    root = proj.find_project(Path.cwd())
    if root is None:
        raise SystemExit("gp: not inside a greenfield-pipeline project (no greenfield/fence.yaml found). Run gp init first.")
    return root


def cmd_preflight(args) -> int:
    root = _root()
    env = runner.environment(root, args.env)
    record = environments.preflight(root, env)
    if record["ok"]:
        print(f"preflight ok: {record['environment']} ({', '.join(record['checks'])})")
        return 0
    print(f"refused: {record['reason']}")
    return 1


def cmd_build(args) -> int:
    root = _root()
    budget.guard(root, "build")
    entry = builds.record(root, args.component, args.image)
    print(f"recorded {entry['commit'][:12]}" + (f" image {entry['image']}" if entry["image"] else ""))
    return 0


def cmd_product_init(args) -> int:
    lines = builds.init_product(_root(), args.path, args.trunk)
    print(f"product repo ready at {args.path}. The owner adds this to greenfield/fence.yaml "
          "(the engine never writes the fence):")
    for line in lines:
        print(f"  {line}")
    return 0


def register(sub) -> None:
    p = sub.add_parser("preflight", help="start the environment, check health, stop it")
    p.add_argument("--env")
    p.set_defaults(fn=cmd_preflight)
    p = sub.add_parser("build", help="record the product repo's clean HEAD as a build in builds.yaml")
    p.add_argument("component", nargs="?")
    p.add_argument("--image")
    p.set_defaults(fn=cmd_build)
    product = sub.add_parser("product", help="product repo tools").add_subparsers(dest="product_command", required=True)
    p = product.add_parser("init", help="create an empty product repo with one commit")
    p.add_argument("--path", default="product")
    p.add_argument("--trunk", default="main")
    p.set_defaults(fn=cmd_product_init)
