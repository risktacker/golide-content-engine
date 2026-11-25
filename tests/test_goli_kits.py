"""Owner 2026-11-25: "each uploaded video he wears something else. That's the rotation."."""
import json
import os

from golide_engine.goli3d import kits


def test_every_upload_wears_the_next_kit(tmp_path):
    records = tmp_path / "records"
    records.mkdir()
    worn = []
    for i in range(9):
        os.environ.pop("GOLIDE_KIT", None)
        kit = kits.choose(tmp_path / f"p{i}" / "edit", records)
        assert kits.choose(tmp_path / f"p{i}" / "edit", records) == kit == kits.current()   # chosen once
        (records / f"p{i}.json").write_text(json.dumps({"recorded_at": f"2026-11-25T10:{i:02d}",
                                                        "generation_parameters": {"kit": kit}}))
        worn.append(kit)
    assert all(a != b for a, b in zip(worn, worn[1:]))
    assert len(set(worn[:7])) == 7 and worn[7] == worn[0]
    assert len({kits.glasses(k) for k in worn[:7]}) >= 5        # the glasses change too
