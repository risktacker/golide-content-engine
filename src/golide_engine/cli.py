import argparse
from pathlib import Path

from .manifest import load_project, validate_assets
from .render import render


def main() -> int:
    parser = argparse.ArgumentParser(prog="golide")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "render"):
        item = sub.add_parser(command)
        item.add_argument("manifest")
    args = parser.parse_args()

    project = load_project(args.manifest)
    missing = validate_assets(project)
    if missing:
        print("Missing assets:")
        for path in missing:
            print(f"- {path}")
        return 2
    if args.command == "validate":
        print(f"Valid: {project.id} ({project.format}, {len(project.scenes)} scenes)")
        return 0
    output = render(project, Path.cwd())
    print(output)
    return 0

