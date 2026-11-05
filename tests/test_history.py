import json

from golide_engine.orchestration.history import title_key, used_source_videos, used_titles, video_key


def test_same_video_never_twice_same_title_never_twice(tmp_path):
    old = {"id": "golide-long-2026-11-03", "title": "My F-You To Cloud AI", "model_title": "My F-You To Cloud AI",
           "platform_demand": {"verdict": "pass"},
           "source_breakout": {"url": "https://www.youtube.com/watch?v=vDmjw-c_R2k"}}
    (tmp_path / "golide-long-2026-11-03.completed.json").write_text(json.dumps(old))
    today = dict(old, id="golide-long-2026-11-05")
    (tmp_path / "golide-long-2026-11-05.json").write_text(json.dumps(today))
    used = used_source_videos("golide-long-2026-11-05", tmp_path)
    assert video_key("https://youtu.be/vDmjw-c_R2k?t=3") in used
    assert video_key("https://www.youtube.com/watch?v=AAAAAAAAAAA") not in used   # same channel, other video: fine
    assert title_key("My F-you to cloud AI!") in used_titles("golide-long-2026-11-05", tmp_path)
