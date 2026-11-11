"""GOLIDE edit engine: turns an edit list into a HyperFrames composition (production plan step 3).

An edit list is the editor's decision for every moment of the video: which scene template, which real
asset or data, when it starts, how long it holds, which spoken words trigger its moves, and how it
comes in. This module writes one standalone HyperFrames `index.html` (HTML + GSAP, rendered in headless
Chrome by `npx hyperframes render`) following the house skill (skills/golide-edit/SKILL.md).

Scenes: browser_shot, stat_counter, quote_card, comparison, steps, timeline, logo_tiles,
kinetic_title, chapter_card, follow_cta.
"""

from __future__ import annotations

import html
import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "assets" / "edit"
SIZES = {"long": (1920, 1080), "short": (1080, 1920)}

GOLD, TEXT, CYAN, RED, HL = "#E8C268", "#F4F1EA", "#38BDF8", "#EF4444", "rgba(250,204,21,.38)"

CSS = """
@font-face{font-family:Poppins;font-weight:800;src:url(fonts/poppins-latin-800-normal.woff)}
@font-face{font-family:Poppins;font-weight:900;src:url(fonts/poppins-latin-900-normal.woff)}
@font-face{font-family:Inter;font-weight:500;src:url(fonts/inter-latin-500-normal.woff)}
@font-face{font-family:Inter;font-weight:600;src:url(fonts/inter-latin-600-normal.woff)}
html,body{margin:0;background:#07080B}
#root{position:relative;width:100%;height:100%;overflow:hidden;background:#07080B;font-family:Inter;color:#F4F1EA}
.bg{position:absolute;inset:-4%;background-image:linear-gradient(rgba(255,255,255,.04) 1px,transparent 1px),
 linear-gradient(90deg,rgba(255,255,255,.04) 1px,transparent 1px);background-size:48px 48px}
.glow{position:absolute;width:1400px;height:820px;left:40%;top:-10%;border-radius:50%;
 background:radial-gradient(closest-side,rgba(40,52,78,.95),rgba(7,8,11,0));filter:blur(10px)}
.finish{position:absolute;inset:0;pointer-events:none;z-index:50;
 background:radial-gradient(ellipse at center,rgba(0,0,0,0) 62%,rgba(0,0,0,.42) 100%)}
.grain{position:absolute;inset:0;z-index:51;opacity:.05;pointer-events:none;
 background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='220' height='220'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>")}
.scene{position:absolute;inset:0}
.stage,.cam{position:absolute;inset:0;transform-origin:50% 50%}
.card{background:rgba(17,20,26,.92);border:1px solid rgba(255,255,255,.08);border-radius:18px;
 box-shadow:0 40px 120px rgba(0,0,0,.6)}
.frame{position:absolute;border-radius:18px;overflow:hidden;background:#fff;
 box-shadow:0 40px 120px rgba(0,0,0,.65),0 0 0 1px rgba(255,255,255,.1)}
.frame .bar{height:44px;background:#1C1F26;display:flex;align-items:center;gap:8px;padding:0 16px;
 font:500 18px Inter;color:rgba(244,241,234,.6)}
.frame .dot{width:12px;height:12px;border-radius:50%}
.frame .url{margin-left:18px;background:#0F1116;border-radius:8px;padding:4px 14px;flex:1;white-space:nowrap;overflow:hidden}
.frame .page{position:absolute;left:0;top:44px;right:0;bottom:0;overflow:hidden}
.frame .page img{position:absolute;left:0;top:0;width:100%}
.hl{position:absolute;background:rgba(250,204,21,.38);border-radius:4px;mix-blend-mode:multiply}
.hl.dark{background:#E8C268;mix-blend-mode:normal;box-shadow:0 0 18px rgba(232,194,104,.8)}
.ring{position:absolute;border:5px solid #E8C268;border-radius:50%}
.title{font:900 112px/1.02 Poppins;letter-spacing:-.01em}
.label{font:600 34px Inter;color:rgba(244,241,234,.72)}
.gold{color:#E8C268}
.word{display:inline-block;margin-right:.26em}
.num{font:900 220px/1 Poppins;color:#E8C268}
.chip{display:inline-block;padding:10px 22px;border-radius:999px;background:rgba(232,194,104,.14);
 border:1px solid rgba(232,194,104,.5);color:#E8C268;font:600 28px Inter}
.row{display:flex;align-items:center}
.tile{position:absolute;width:300px;height:300px}
.tile img{width:100%;height:100%}
"""


def _is_dark(image: Path) -> bool:
    from PIL import Image, ImageStat

    with Image.open(image) as im:
        return ImageStat.Stat(im.convert("L").resize((64, 40))).mean[0] < 110


def _e(text: Any) -> str:
    return html.escape(str(text), quote=True)


class Composer:
    """Collects scene markup and one GSAP timeline."""

    def __init__(self, fmt: str = "long"):
        self.fmt = fmt
        self.w, self.h = SIZES[fmt]
        self.parts: list[str] = []
        self.tweens: list[str] = []
        self.files: dict[str, Path] = {}
        self.sfx: list[dict[str, Any]] = []
        self.n = 0

    # ---- helpers
    def _id(self, kind: str) -> str:
        self.n += 1
        return f"s{self.n}-{kind}"

    def asset(self, path: Path) -> str:
        name = f"media/{len(self.files):02d}-{Path(path).name}"
        self.files[name] = Path(path)
        return name

    def tw(self, js: str) -> None:
        self.tweens.append(js)

    def cue(self, kind: str, t: float) -> None:
        self.sfx.append({"kind": kind, "t": round(t, 3)})

    def entrance(self, sid: str, t0: float, how: str) -> None:
        """How a scene comes in, chosen by the story beat (house skill: no dissolves)."""
        sel = f"#{sid} .stage"
        if how == "whip":
            self.tw(f'tl.fromTo("{sel}",{{x:{self.w * 0.9:.0f},filter:"blur(14px)"}},'
                    f'{{x:0,filter:"blur(0px)",duration:.32,ease:"power3.out"}},{t0:.3f});')
            self.cue("whoosh", t0 - 0.05)
        elif how == "wipe":
            self.tw(f'tl.fromTo("{sel}",{{clipPath:"inset(0 100% 0 0)"}},'
                    f'{{clipPath:"inset(0 0% 0 0)",duration:.45,ease:"power2.inOut"}},{t0:.3f});')
            self.cue("whoosh", t0)
        elif how == "rise":
            self.tw(f'tl.fromTo("{sel}",{{y:90,scale:.94,opacity:0}},'
                    f'{{y:0,scale:1,opacity:1,duration:.7,ease:"back.out(1.4)"}},{t0:.3f});')
        # "cut": nothing, the clip simply starts

    def drift(self, sid: str, t0: float, dur: float, amount: float = 0.02) -> None:
        """Never a static frame: a slow push-in through the shot."""
        self.tw(f'tl.fromTo("#{sid} .cam",{{scale:1}},{{scale:{1 + amount * dur:.3f},duration:{dur:.3f},'
                f'ease:"none"}},{t0:.3f});')

    def scene(self, sid: str, t0: float, dur: float, inner: str) -> None:
        self.parts.append(f'<section id="{sid}" class="scene clip" data-start="{t0:.3f}" data-duration="{dur:.3f}">'
                          f'<div class="stage"><div class="cam">{inner}</div></div></section>')

    # ---- templates
    def browser_shot(self, t0, dur, data, how="rise"):
        """A real source page in a browser frame: it lands, the camera pushes to the fact, the
        highlighter draws over the exact words, then a gold ring if it is a single number."""
        sid = self._id("page")
        fw, fh = (1500, 900) if self.fmt == "long" else (980, 1300)
        fx, fy = (self.w - fw) // 2, (self.h - fh) // 2 + 10
        img = self.asset(data["image"])
        page_w = float(data.get("page_width", 1440))
        k = fw / page_w                                   # css px of the page -> frame px
        marks = ""
        hl_tweens = []
        dark = _is_dark(Path(data["image"]))
        for j, spot in enumerate(data.get("highlights", [])[:2]):
            x, y, w, h = spot["rect"]
            hx, hy, hw, hh = x * k - 6, y * k - 4, w * k + 12, h * k + 8
            if dark:      # a highlighter vanishes on a dark page: a gold underline stroke instead
                marks += (f'<div class="hl dark" id="{sid}-hl{j}" style="left:{hx:.0f}px;top:{hy + hh * 0.8:.0f}px;'
                          f'width:0px;height:{max(6, hh * 0.09):.0f}px"></div>')
            else:
                marks += (f'<div class="hl" id="{sid}-hl{j}" style="left:{hx:.0f}px;top:{hy:.0f}px;'
                          f'width:0px;height:{hh:.0f}px"></div>')
            at = t0 + float(spot.get("at", 0.9 + j * 1.0))
            hl_tweens.append(f'tl.to("#{sid}-hl{j}",{{width:{hw:.0f},duration:.35,ease:"none"}},{at:.3f});')
            self.cue("click", at)
            if spot.get("ring"):
                r = max(hw, hh) * 0.9
                marks += (f'<div class="ring" id="{sid}-ring{j}" style="left:{hx + hw / 2 - r:.0f}px;'
                          f'top:{hy + hh / 2 - r:.0f}px;width:{2 * r:.0f}px;height:{2 * r:.0f}px"></div>')
                hl_tweens.append(f'tl.fromTo("#{sid}-ring{j}",{{scale:1.6,opacity:0}},{{scale:1,opacity:1,'
                                 f'duration:.4,ease:"back.out(2)"}},{at + 0.3:.3f});')
        inner = (f'<div class="frame" id="{sid}-f" style="left:{fx}px;top:{fy}px;width:{fw}px;height:{fh}px">'
                 f'<div class="bar"><div class="dot" style="background:#ff5f57"></div><div class="dot" '
                 f'style="background:#febc2e"></div><div class="dot" style="background:#28c840"></div>'
                 f'<div class="url">{_e(data.get("url", ""))}</div></div>'
                 f'<div class="page"><div id="{sid}-pg" style="position:absolute;inset:0">'
                 f'<img src="{img}">{marks}</div></div></div>')
        self.scene(sid, t0, dur, inner)
        self.entrance(sid, t0, how)
        spots = data.get("highlights") or []
        if spots:                                          # targeted push to the facts (centre of all of them)
            x0 = min(sp["rect"][0] for sp in spots[:2]); y0 = min(sp["rect"][1] for sp in spots[:2])
            x1 = max(sp["rect"][0] + sp["rect"][2] for sp in spots[:2])
            y1 = max(sp["rect"][1] + sp["rect"][3] for sp in spots[:2])
            cx, cy = fx + (x0 + x1) / 2 * k, fy + 44 + (y0 + y1) / 2 * k
            z = min(float(data.get("zoom", 1.8)), 0.8 * self.w / max(1.0, (x1 - x0) * k))
            at = t0 + float(spots[0].get("at", 0.9)) - 0.5
            self.tw(f'tl.to("#{sid}-f",{{x:{(self.w / 2 - cx) * (z - 1) / z:.0f},y:{(self.h / 2 - cy) * (z - 1) / z:.0f},'
                    f'scale:{z},duration:1.1,ease:"power2.inOut",transformOrigin:"{cx - fx:.0f}px {cy - fy:.0f}px"}},'
                    f'{at:.3f});')
        else:
            self.drift(sid, t0, dur)
        for js in hl_tweens:
            self.tw(js)

    def stat_counter(self, t0, dur, data, how="whip"):
        """A real number counts up, punches and sits on a label (impact sound)."""
        sid = self._id("stat")
        value = float(data["value"])
        prefix, suffix = data.get("prefix", ""), data.get("suffix", "")
        decimals = int(data.get("decimals", 0))
        source = f'<div class="chip" style="margin-top:26px">{_e(data["source"])}</div>' if data.get("source") else ""
        inner = (f'<div class="card" style="position:absolute;left:50%;top:50%;width:1100px;height:560px;'
                 f'margin:-280px 0 0 -550px;display:flex;flex-direction:column;align-items:center;justify-content:center">'
                 f'<div class="num"><span>{_e(prefix)}</span><span id="{sid}-n">0</span><span>{_e(suffix)}</span></div>'
                 f'<div class="label" id="{sid}-l" style="margin-top:22px">{_e(data.get("label", ""))}</div>'
                 f'{source}</div>')
        self.scene(sid, t0, dur, inner)
        self.entrance(sid, t0, how)
        at = t0 + 0.35
        self.tw(f'(function(){{const o={{v:0}};const el=document.getElementById("{sid}-n");'
                f'tl.to(o,{{v:{value},duration:.9,ease:"power2.out",onUpdate:()=>{{el.textContent='
                f'o.v.toLocaleString("en-US",{{minimumFractionDigits:{decimals},maximumFractionDigits:{decimals}}})}}}},{at:.3f});}})();')
        self.tw(f'tl.fromTo("#{sid} .num",{{scale:1}},{{scale:1.08,duration:.12,yoyo:true,repeat:1,ease:"power2.out"}},{at + 0.9:.3f});')
        self.tw(f'tl.fromTo("#{sid}-l",{{y:24,opacity:0}},{{y:0,opacity:1,duration:.5,ease:"power3.out"}},{at + 0.3:.3f});')
        self.cue("impact", at + 0.9)
        self.drift(sid, t0, dur, 0.012)

    def kinetic_title(self, t0, dur, data, how="cut"):
        """Words build on their spoken times; the punch word scales up and turns gold."""
        sid = self._id("title")
        words = data["words"]                             # [{"text":..,"at":..}]
        punch = str(data.get("punch", "")).lower()
        sub = f'<div class="label" style="margin-top:28px">{_e(data["sub"])}</div>' if data.get("sub") else ""
        spans = "".join(f'<span class="word{" gold" if w["text"].lower().strip(".,!?") == punch else ""}" '
                        f'id="{sid}-w{i}">{_e(w["text"])}</span>' for i, w in enumerate(words))
        inner = (f'<div style="position:absolute;left:120px;right:120px;top:50%;transform:translateY(-50%)">'
                 f'<div class="title" style="text-align:left">{spans}</div>'
                 f'{sub}</div>')
        self.scene(sid, t0, dur, inner)
        for i, w in enumerate(words):
            at = t0 + float(w.get("at", i * 0.18))
            self.tw(f'tl.fromTo("#{sid}-w{i}",{{y:60,opacity:0,clipPath:"inset(0 0 100% 0)"}},'
                    f'{{y:0,opacity:1,clipPath:"inset(0 0 0% 0)",duration:.45,ease:"back.out(1.6)"}},{at:.3f});')
            if w["text"].lower().strip(".,!?") == punch:
                self.tw(f'tl.fromTo("#{sid}-w{i}",{{scale:1}},{{scale:1.15,duration:.18,yoyo:true,repeat:1,'
                        f'ease:"power2.out"}},{at + 0.45:.3f});')
                self.cue("impact", at + 0.45)
        self.drift(sid, t0, dur, 0.015)

    def chapter_card(self, t0, dur, data, how="whip"):
        sid = self._id("chapter")
        inner = (f'<div style="position:absolute;left:140px;top:50%;transform:translateY(-50%)">'
                 f'<div class="chip" id="{sid}-c">{_e(data.get("number", ""))}</div>'
                 f'<div class="title" id="{sid}-t" style="margin-top:26px;font-size:128px">{_e(data["title"])}</div>'
                 f'<div id="{sid}-u" style="height:10px;width:0;background:#E8C268;margin-top:26px;border-radius:5px"></div></div>')
        self.scene(sid, t0, dur, inner)
        self.entrance(sid, t0, how)
        self.cue("riser", t0 - 1.2)
        self.tw(f'tl.fromTo("#{sid}-t",{{clipPath:"inset(0 100% 0 0)"}},{{clipPath:"inset(0 0% 0 0)",duration:.6,ease:"power2.inOut"}},{t0 + 0.2:.3f});')
        self.tw(f'tl.to("#{sid}-u",{{width:420,duration:.5,ease:"power3.out"}},{t0 + 0.6:.3f});')
        self.drift(sid, t0, dur, 0.02)

    def quote_card(self, t0, dur, data, how="rise"):
        sid = self._id("quote")
        words = str(data["text"]).split()
        mark = {w.lower().strip(".,") for w in data.get("mark", [])}
        body = " ".join(f'<span class="{"gold" if w.lower().strip(".,") in mark else ""}">{_e(w)}</span>' for w in words)
        inner = (f'<div class="card" style="position:absolute;left:50%;top:50%;width:1300px;margin-left:-650px;'
                 f'transform:translateY(-50%);padding:70px 80px">'
                 f'<div style="font:900 120px/0.6 Poppins;color:#E8C268">&ldquo;</div>'
                 f'<div style="font:800 58px/1.25 Poppins">{body}</div>'
                 f'<div class="label" style="margin-top:34px">{_e(data.get("who", ""))}</div></div>')
        self.scene(sid, t0, dur, inner)
        self.entrance(sid, t0, how)
        self.drift(sid, t0, dur, 0.012)

    def comparison(self, t0, dur, data, how="wipe"):
        """Two sides; the rows build one by one; the winning value glows gold."""
        sid = self._id("compare")
        left, right = data["left"], data["right"]
        rows = ""
        for i, (label, a, b) in enumerate(data["rows"]):
            win = data.get("winners", [None] * len(data["rows"]))[i]
            rows += (f'<div class="row" id="{sid}-r{i}" style="padding:18px 0;border-top:1px solid rgba(255,255,255,.08)">'
                     f'<div class="label" style="width:420px">{_e(label)}</div>'
                     f'<div style="width:330px;font:800 48px Poppins;{"color:#E8C268" if win == "left" else ""}">{_e(a)}</div>'
                     f'<div style="width:330px;font:800 48px Poppins;{"color:#E8C268" if win == "right" else ""}">{_e(b)}</div></div>')
        inner = (f'<div class="card" style="position:absolute;left:50%;top:50%;width:1220px;margin-left:-610px;'
                 f'transform:translateY(-50%);padding:50px 60px">'
                 f'<div class="row" style="padding-bottom:14px"><div style="width:420px"></div>'
                 f'<div style="width:330px;font:900 54px Poppins">{_e(left)}</div>'
                 f'<div style="width:330px;font:900 54px Poppins;color:#38BDF8">{_e(right)}</div></div>{rows}</div>')
        self.scene(sid, t0, dur, inner)
        self.entrance(sid, t0, how)
        for i in range(len(data["rows"])):
            at = t0 + 0.5 + i * float(data.get("gap", 0.55))
            self.tw(f'tl.fromTo("#{sid}-r{i}",{{x:-40,opacity:0}},{{x:0,opacity:1,duration:.45,ease:"back.out(1.4)"}},{at:.3f});')
            self.cue("click", at)
        self.drift(sid, t0, dur, 0.01)

    def steps(self, t0, dur, data, how="wipe"):
        sid = self._id("steps")
        items = "".join(f'<div class="row" id="{sid}-i{i}" style="gap:28px;margin:22px 0">'
                        f'<div style="width:86px;height:86px;border-radius:24px;background:#E8C268;color:#07080B;'
                        f'display:grid;place-items:center;font:900 46px Poppins">{i + 1}</div>'
                        f'<div style="font:800 54px Poppins">{_e(s)}</div></div>' for i, s in enumerate(data["items"]))
        inner = (f'<div style="position:absolute;left:180px;top:50%;transform:translateY(-50%)">'
                 f'<div class="label" style="margin-bottom:18px">{_e(data.get("heading", ""))}</div>{items}</div>')
        self.scene(sid, t0, dur, inner)
        self.entrance(sid, t0, how)
        for i in range(len(data["items"])):
            at = t0 + float((data.get("at") or [0.3 + 0.7 * j for j in range(len(data["items"]))])[i])
            self.tw(f'tl.fromTo("#{sid}-i{i}",{{clipPath:"inset(0 100% 0 0)",x:-30}},{{clipPath:"inset(0 0% 0 0)",x:0,'
                    f'duration:.45,ease:"power2.out"}},{at:.3f});')
            self.cue("click", at)
        self.drift(sid, t0, dur, 0.012)

    def timeline(self, t0, dur, data, how="whip"):
        sid = self._id("time")
        pts = data["points"]                                # [{"when":..,"what":..}]
        n = len(pts)
        span = self.w - 360
        dots = ""
        for i, p in enumerate(pts):
            x = 180 + span * (i / max(1, n - 1))
            dots += (f'<div id="{sid}-p{i}" style="position:absolute;left:{x - 150:.0f}px;top:410px;width:300px;text-align:center">'
                     f'<div style="width:30px;height:30px;border-radius:50%;background:#E8C268;margin:0 auto 26px;'
                     f'box-shadow:0 0 30px rgba(232,194,104,.7)"></div>'
                     f'<div style="font:900 52px Poppins">{_e(p["when"])}</div>'
                     f'<div class="label" style="font-size:28px;margin-top:10px">{_e(p["what"])}</div></div>')
        inner = (f'<div id="{sid}-line" style="position:absolute;left:180px;top:424px;height:4px;width:0;'
                 f'background:linear-gradient(90deg,#E8C268,rgba(232,194,104,.3))"></div>{dots}')
        self.scene(sid, t0, dur, inner)
        self.entrance(sid, t0, how)
        self.tw(f'tl.to("#{sid}-line",{{width:{span},duration:{min(2.4, dur - 0.6):.2f},ease:"power2.inOut"}},{t0 + 0.2:.3f});')
        for i in range(n):
            at = t0 + 0.25 + min(2.4, dur - 0.6) * (i / max(1, n - 1))
            self.tw(f'tl.fromTo("#{sid}-p{i}",{{y:40,opacity:0}},{{y:0,opacity:1,duration:.45,ease:"back.out(1.6)"}},{at:.3f});')
            self.cue("click", at)
        self.drift(sid, t0, dur, 0.012)

    def logo_tiles(self, t0, dur, data, how="rise"):
        """The real 3D logo tiles (rendered by vector.thumb_styles) float in with parallax."""
        sid = self._id("logos")
        tiles = data["tiles"]                               # [{"image": path}]
        n = len(tiles)
        gap = 360
        x0 = self.w / 2 - gap * (n - 1) / 2
        inner = "".join(f'<div class="tile" id="{sid}-t{i}" style="left:{x0 + gap * i - 150:.0f}px;top:{self.h / 2 - 190:.0f}px">'
                        f'<img src="{self.asset(t["image"])}"></div>' for i, t in enumerate(tiles))
        if data.get("caption"):
            inner += (f'<div class="title" style="position:absolute;left:0;right:0;top:{self.h / 2 + 170:.0f}px;'
                      f'text-align:center;font-size:84px">{_e(data["caption"])}</div>')
        self.scene(sid, t0, dur, inner)
        for i in range(n):
            at = t0 + 0.12 * i
            self.tw(f'tl.fromTo("#{sid}-t{i}",{{y:220,rotation:{-14 + 9 * i},scale:.6,opacity:0}},{{y:0,rotation:{-6 + 4 * i},'
                    f'scale:1,opacity:1,duration:.8,ease:"back.out(1.5)"}},{at:.3f});')
            self.tw(f'tl.to("#{sid}-t{i}",{{y:{-18 - 8 * i},duration:{dur:.2f},ease:"sine.inOut"}},{at + 0.8:.3f});')
        self.cue("whoosh", t0)

    def follow_cta(self, t0, dur, data, how="rise"):
        sid = self._id("follow")
        inner = (f'<div class="card" id="{sid}-c" style="position:absolute;left:50%;top:50%;width:900px;margin-left:-450px;'
                 f'transform:translateY(-50%);padding:60px;text-align:center">'
                 f'<div class="title" style="font-size:86px">Follow <span class="gold">GOLIDE</span></div>'
                 f'<div class="label" style="margin-top:20px">{_e(data.get("reason", ""))}</div></div>')
        self.scene(sid, t0, dur, inner)
        self.entrance(sid, t0, "rise")
        self.cue("click", t0 + 0.4)

    # ---- output
    def build(self, edit: dict[str, Any], out: Path) -> Path:
        for s in edit["scenes"]:
            getattr(self, s["type"])(float(s["start"]), float(s["duration"]), s["data"], s.get("in", "rise"))
        duration = float(edit.get("duration") or max(float(s["start"]) + float(s["duration"]) for s in edit["scenes"]))
        out.mkdir(parents=True, exist_ok=True)
        shutil.copytree(ASSETS / "fonts", out / "fonts", dirs_exist_ok=True)
        shutil.copy(ASSETS / "gsap.min.js", out / "gsap.min.js")
        (out / "media").mkdir(exist_ok=True)
        for name, src in self.files.items():
            shutil.copy(src, out / name)
        page = f"""<!doctype html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width={self.w}, height={self.h}"><script src="gsap.min.js"></script>
<style>{CSS}</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-width="{self.w}" data-height="{self.h}" data-duration="{duration:.3f}">
<div class="bg" id="bg"></div><div class="glow" id="glow"></div>
{''.join(self.parts)}
<div class="finish"></div><div class="grain"></div>
</div>
<script>
const tl=gsap.timeline({{paused:true}});
tl.fromTo("#glow",{{x:0,y:0}},{{x:-{self.w * 0.18:.0f},y:{self.h * 0.12:.0f},duration:{duration:.3f},ease:"sine.inOut"}},0);
tl.fromTo("#bg",{{x:0}},{{x:-48,duration:{duration:.3f},ease:"none"}},0);
{chr(10).join(self.tweens)}
window.__timelines["main"]=tl;
</script></body></html>"""
        (out / "index.html").write_text(page, encoding="utf-8")
        (out / "sfx.json").write_text(json.dumps(sorted(self.sfx, key=lambda c: c["t"])), encoding="utf-8")
        return out / "index.html"
