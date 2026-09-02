from pathlib import Path


def test_primary_stills_loop_for_the_full_scene_duration():
    source = Path("src/golide_engine/render.py").read_text(encoding="utf-8")
    assert '"-loop", "1", "-framerate", str(project.fps)' in source
    assert '"-t", f"{clip_duration:.3f}", "-i", str(scene.media)' in source


def test_production_blocks_narration_duration_mismatch():
    source = Path("src/golide_engine/orchestration/production.py").read_text(
        encoding="utf-8"
    )
    assert "render-full-duration-v3" in source
    assert "does not match narration" in source
