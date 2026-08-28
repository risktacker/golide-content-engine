import argparse
import json
from pathlib import Path

from .manifest import load_project, validate_assets
from .render import render
from .pipeline import build_plan
from .scoring import score_concept


def main() -> int:
    parser = argparse.ArgumentParser(prog="golide")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "render"):
        item = sub.add_parser(command)
        item.add_argument("manifest")
    score_parser = sub.add_parser("score")
    score_parser.add_argument("spec")
    plan_parser = sub.add_parser("plan")
    plan_parser.add_argument("spec")
    plan_parser.add_argument("--output", default="build")
    args = parser.parse_args()

    if args.command in {"score", "plan"}:
        spec_path = Path(args.spec).resolve()
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        if args.command == "score":
            result = score_concept(spec["format"], spec["concept"]["scores"])
            print(json.dumps({"score": result.total, "verdict": result.verdict, "blockers": result.blockers}, indent=2))
            return 0 if result.verdict != "reject" else 3
        plan = build_plan(spec, Path(args.output).resolve())
        print(json.dumps({"score": plan.score, "verdict": plan.verdict, "output": plan.output_directory}, indent=2))
        return 0

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
