"""Text-only report of what a filmed composition shows every half second (owner 2026-11-27: "check every 0.5 s").

For each moment: the scenes on screen (not Goli), and whether they hold anything visible. Moments where only Goli or
nothing is on screen are listed with the scene that should be there, so a black block can be traced to its cause."""
import json, sys, tarfile, tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

PROBE = r"""(t) => { window.__hf && window.__hf.seek ? window.__hf.seek(t) : window.__timelines.main.seek(t, false);
  const out = [];
  for (const sec of document.querySelectorAll('section.scene')) {
    const s = parseFloat(sec.dataset.start), d = parseFloat(sec.dataset.duration);
    if (!(t >= s && t < s + d) || sec.id.includes('-host') || sec.id.startsWith('live-')) continue;
    const cs = getComputedStyle(sec);
    let seen = 0, kids = [];
    for (const el of sec.querySelectorAll('img,video,canvas,svg,div,span')) {
      const r = el.getBoundingClientRect(), st = getComputedStyle(el);
      if (r.width < 20 || r.height < 20 || st.visibility === 'hidden' || st.display === 'none') continue;
      let o = 1, p = el; while (p && p !== document.body) { o *= parseFloat(getComputedStyle(p).opacity || 1); p = p.parentElement; }
      if (o < 0.05) continue;
      if (r.right < 0 || r.left > innerWidth || r.bottom < 0 || r.top > innerHeight) continue;
      const tag = el.tagName.toLowerCase();
      if (tag === 'img' && !(el.complete && el.naturalWidth)) { kids.push('img-not-loaded:' + (el.getAttribute('src')||'').slice(-40)); continue; }
      if (tag === 'video' && el.readyState < 2) { kids.push('video-not-ready:' + (el.getAttribute('src')||'').slice(-40)); }
      seen++;
    }
    out.push({id: sec.id, opacity: cs.opacity, vis: cs.visibility, seen, notes: kids.slice(0, 3)});
  }
  const room = document.getElementById('live-room');
  const roomOn = room ? getComputedStyle(room).visibility !== 'hidden' && parseFloat(getComputedStyle(room).opacity) > 0.05 : false;
  const hosts = [...document.querySelectorAll('section.scene')].filter((sec) => { const s = parseFloat(sec.dataset.start), d = parseFloat(sec.dataset.duration); return t >= s && t < s + d && sec.id.includes('-host'); }).map((x) => x.id);
  return {out, roomOn, hosts}; }"""


def main(bundle: str, duration: float) -> None:
    work = Path(tempfile.mkdtemp())
    with tarfile.open(bundle) as tf:
        tf.extractall(work)
    index = next(work.rglob("index.html"))
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"])
        page = b.new_page(viewport={"width": 1920, "height": 1080})
        page.add_init_script("window.__timelines = {};")
        page.goto(index.as_uri())
        page.wait_for_function("() => !!(window.__timelines && window.__timelines.main)", timeout=300000)
        t, last = 0.0, None
        while t < duration:
            res = page.evaluate(PROBE, t)
            got = res["out"]
            bad = [g for g in got if g["seen"] == 0 or float(g["opacity"]) < 0.05 or g["vis"] == "hidden" or g["notes"]]
            line = None
            if not got:
                line = None if res["roomOn"] else f"EMPTY: no block, no studio (hosts {res['hosts']})"
            elif bad:
                line = "; ".join(f"{g['id']} op={g['opacity']} vis={g['vis']} seen={g['seen']} {g['notes']}" for g in bad)
            if line != last:
                print(f"{t:6.1f}  {line or 'ok'}", flush=True)
            last = line
            t = round(t + 0.5, 1)
        b.close()


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]))
