from pathlib import Path

path = Path("src/golide_engine/orchestration/production.py")
source = path.read_text(encoding="utf-8")

import_marker = "from ..quality.runner import QualityRunner\n"
editorial_import = "from ..quality.editorial import check_editorial\n"
if editorial_import not in source:
    if import_marker not in source:
        raise SystemExit("quality import marker changed; refusing patch")
    source = source.replace(import_marker, editorial_import + import_marker, 1)

preflight_marker = '''        if normalized_storyboard != storyboard:
            storyboard = normalized_storyboard
            storyboard_path.write_text(
                json.dumps(storyboard, indent=2) + "\\n", encoding="utf-8"
            )
        self._budget(spec)
'''
preflight_replacement = '''        if normalized_storyboard != storyboard:
            storyboard = normalized_storyboard
            storyboard_path.write_text(
                json.dumps(storyboard, indent=2) + "\\n", encoding="utf-8"
            )
        # Editorial structure must pass locally before the first paid image request.
        # This catches repetitive assets, weak layering, motion spam and missing SFX
        # while the only sunk cost is the already-checkpointed planning/narration work.
        editorial_failures, editorial_metrics = check_editorial(
            storyboard, spec["format"], qa_policy
        )
        (work / "storyboard-preflight.json").write_text(
            json.dumps({
                "passed": not editorial_failures,
                "failures": editorial_failures,
                "metrics": editorial_metrics,
            }, indent=2) + "\\n",
            encoding="utf-8",
        )
        if editorial_failures:
            raise RuntimeError(
                "storyboard failed zero-image-spend editorial preflight: "
                + "; ".join(editorial_failures)
            )
        self._budget(spec)
'''
if "storyboard-preflight.json" not in source:
    if preflight_marker not in source:
        raise SystemExit("storyboard preflight marker changed; refusing patch")
    source = source.replace(preflight_marker, preflight_replacement, 1)

batch_marker = '''        image_batch = []
        for asset_key in unique_assets:
            is_hero = asset_key in hero_keys and asset_key not in secondary_keys
            image_batch.append((
                hero_image_cost_model if is_hero else support_image_cost_model,
                Usage(images=1),
            ))
        self.budget.reserve_batch(
            spec, image_batch, provider="openai", stage="planned-visual-asset-batch"
        )
'''
batch_replacement = '''        image_batch = []
        for asset_key in unique_assets:
            target = asset_dir / f"{asset_key}.png"
            if target.exists():
                # Checkpointed paid media is never charged a second time in preflight.
                continue
            is_hero = asset_key in hero_keys and asset_key not in secondary_keys
            image_batch.append((
                hero_image_cost_model if is_hero else support_image_cost_model,
                Usage(images=1),
            ))
        # Reserve room for the one thumbnail as part of the same visual-spend plan.
        # The later thumbnail stage still performs its own exact reservation; this
        # batch check only guarantees we do not knowingly consume the asset budget
        # and discover at the end that the release thumbnail cannot be finished.
        thumbnail_checkpoint = work / "thumbnail.png"
        if not thumbnail_checkpoint.exists():
            image_batch.append((thumbnail_cost_model, Usage(images=1)))
        self.budget.reserve_batch(
            spec, image_batch, provider="openai", stage="planned-visual-and-thumbnail-batch"
        )
'''
if "planned-visual-and-thumbnail-batch" not in source:
    if batch_marker not in source:
        raise SystemExit("image batch marker changed; refusing patch")
    source = source.replace(batch_marker, batch_replacement, 1)

path.write_text(source, encoding="utf-8")
print("final production guards applied")
