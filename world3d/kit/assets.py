"""Free shared media is downloaded once into a local cache, never stored in git."""
import os
import urllib.request
from pathlib import Path

CACHE = Path(os.environ.get("WORLD3D_CACHE", Path.home() / ".cache" / "golide-world3d"))
BASE = "https://raw.githubusercontent.com/turban/webgl-earth/master/images/"
FILES = {
    "earth_day": BASE + "2_no_clouds_4k.jpg",
    "earth_clouds": BASE + "fair_clouds_4k.png",
    "earth_water": BASE + "water_4k.png",
    "earth_bump": BASE + "elev_bump_4k.jpg",
}


def fetch(name):
    url = FILES[name]
    path = CACHE / (name + Path(url).suffix)
    if not path.exists() or path.stat().st_size == 0:
        CACHE.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".part")
        urllib.request.urlretrieve(url, tmp)
        tmp.replace(path)
    return str(path)
