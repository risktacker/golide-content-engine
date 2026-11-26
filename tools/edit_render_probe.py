"""Times every 3D layer of a split-render job's composition on its own (the first draw and the next), so a frame that
hangs the filming is found by name. Used by edit-render-probe.yml; prints one line per layer."""
from __future__ import annotations

import io
import json
import subprocess
import sys
import tarfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from golide_engine.edit import remote  # noqa: E402

job = sys.argv[1]
work = Path("probe"); work.mkdir(exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(remote.get(job, "bundle.tgz")), mode="r:gz") as tar:
    tar.extractall(work, filter="data")
srv = subprocess.Popen([sys.executable, "-m", "http.server", "8802"], cwd=work / "composition", stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
time.sleep(1)
from playwright.sync_api import sync_playwright  # noqa: E402
try:
    with sync_playwright() as p:
        br = p.chromium.launch(executable_path="/usr/bin/google-chrome",
                               args=["--use-angle=swiftshader", "--use-gl=angle", "--enable-unsafe-swiftshader"])
        pg = br.new_page(viewport={"width": 1920, "height": 1080})
        pg.add_init_script("window.__timelines = {};")
        t0 = time.time()
        pg.goto("http://localhost:8802/index.html")
        while not pg.evaluate("!!(window.__timelines && window.__timelines.main)"):
            time.sleep(2)
        pg.evaluate("window.__timelines.main.pause()")
        print(json.dumps({"ready_s": round(time.time() - t0, 1)}), flush=True)
        keys = pg.evaluate("Object.keys(window.__g3d||{})")
        for k in keys:
            for t in (0.5, 1.0, 3.0):
                s = time.time()
                pg.evaluate(f"window.__g3d[{k!r}]({t})")
                print(json.dumps({"layer": k, "t": t, "s": round(time.time() - s, 2)}), flush=True)
        br.close()
finally:
    srv.kill()
