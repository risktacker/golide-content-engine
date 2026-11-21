"""Print what a goli3d render run draws (one job per item): python tools/goli3d_plan.py library|video|studio [items]."""
import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent


def names(path: str, start: str) -> list[str]:
    s = (TOOLS / path).read_text()
    i = s.index(start)
    return re.findall(r'"(\w+)"', s[i:s.index(")" if start.endswith("(") else "}", i)])


kind = sys.argv[1] if len(sys.argv) > 1 else "library"
given = [a for a in sys.argv[2:] if a]
if given:
    items = given
elif kind == "studio":
    items = ["short", "long", "lower"]
elif kind == "video":
    items = re.findall(r'"(\w+)": "', (TOOLS / "goli3d_video.py").read_text().split("FACE = {", 1)[1].split("}", 1)[0])
else:
    items = names("goli3d_library.py", "POSES = (")
if not items:
    sys.exit("no items to draw")
print(" ".join(items))
