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
import re
import json
import shutil
from pathlib import Path
from typing import Any

from PIL import Image

from . import studio
from .mascot import logo_mark

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
.card{box-sizing:border-box;background:rgba(17,20,26,.92);border:1px solid rgba(255,255,255,.08);border-radius:18px;
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
.studio{position:absolute;inset:0;overflow:hidden}
.studio .wall{position:absolute;left:0;right:0;top:6%;text-align:center;font:900 260px/1 Poppins;letter-spacing:.08em;
 color:rgba(232,194,104,.035);-webkit-text-stroke:2px rgba(232,194,104,.16)}
.studio .floor{position:absolute;left:-50%;right:-50%;bottom:-8%;height:62%;transform-origin:50% 100%;
 transform:perspective(900px) rotateX(64deg);background-image:linear-gradient(rgba(232,194,104,.42) 3px,transparent 3px),
 linear-gradient(90deg,rgba(232,194,104,.42) 3px,transparent 3px);background-size:90px 90px;
 -webkit-mask-image:linear-gradient(to top,#000 10%,transparent 85%);mask-image:linear-gradient(to top,#000 25%,transparent 95%)}
.studio .horizon{position:absolute;left:0;right:0;top:52%;height:3px;background:linear-gradient(90deg,transparent,
 rgba(232,194,104,.7),transparent);box-shadow:0 0 40px 10px rgba(232,194,104,.18)}
.studio .spot{position:absolute;top:-10%;width:900px;height:1150px;background:radial-gradient(ellipse 50% 60% at 50% 30%,
 rgba(76,125,255,.38),rgba(76,125,255,0) 70%)}
.studio .disc{position:absolute;border-radius:50%;background:radial-gradient(ellipse at 50% 40%,#1B2340,#0A0D16 70%);
 box-shadow:0 0 0 3px rgba(232,194,104,.7),0 0 60px 12px rgba(232,194,104,.28),inset 0 -10px 30px rgba(0,0,0,.6)}
.studio .panel{position:absolute;border-radius:22px;background:rgba(22,27,40,.55);border:1px solid rgba(255,255,255,.12);
 box-shadow:0 30px 80px rgba(0,0,0,.5)}
.studio .dotp{position:absolute;width:6px;height:6px;border-radius:50%;background:#E8C268;box-shadow:0 0 12px #E8C268}
#brand{position:absolute;inset:0;z-index:45;pointer-events:none}
#caps{position:absolute;inset:0;z-index:46;pointer-events:none}
.cap{position:absolute;left:60px;right:60px;text-align:center;opacity:0;font:800 60px/1.16 Poppins;color:#F4F1EA;
 text-shadow:0 4px 18px rgba(0,0,0,.85),0 0 2px #000}
.cap span{display:inline-block;margin:0 .14em;opacity:.38}
.cap span.key{color:#E8C268}
#brand .logo{position:absolute;left:44px;top:34px;display:flex;align-items:center;gap:12px;font:900 30px Poppins;color:#F4F1EA;
 letter-spacing:.06em;opacity:.92}
#brand .logo i{width:40px;height:40px;border-radius:50%;background:linear-gradient(#FFE7A3,#B07D1C);color:#0E1A4A;
 display:grid;place-items:center;font:900 24px Poppins;font-style:normal}
#brand .chap{position:absolute;right:44px;top:38px;padding:8px 20px;border-radius:999px;background:rgba(17,20,26,.8);
 border:1px solid rgba(232,194,104,.45);color:#E8C268;font:600 24px Inter;opacity:0}
#brand .prog{position:absolute;left:0;bottom:0;height:5px;width:0;background:linear-gradient(90deg,#B07D1C,#FFE7A3)}
"""


def _is_dark(image: Path) -> bool:
    from PIL import Image, ImageStat

    with Image.open(image) as im:
        return ImageStat.Stat(im.convert("L").resize((64, 40))).mean[0] < 110


def _e(text: Any) -> str:
    return html.escape(str(text), quote=True)


class Composer:
    """Collects scene markup and one GSAP timeline."""

    def __init__(self, fmt: str = "long", outfit: str = "royal"):
        # a Short splits the frame: the proof on top (centred here), Goli at his desk below (LOWER_TOP down)
        self.cy = SIZES[fmt][1] // 2 if fmt == "long" else 580
        self.outfit = outfit
        self.outfits: set[str] = set()
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
        """A real source page as a floating card (never full screen): it grows in, the camera zooms
        inside the card to the fact, the highlighter draws over the exact words, a callout names the
        fact beside the card and a source tag sits under it. edge: "glass" (clean cut, gold rim,
        browser bar) or "fade" (no bar, edges melt into the background)."""
        sid = self._id("page")
        edge = data.get("edge", "glass")
        spots = [dict(sp) for sp in (data.get("highlights") or [])[:2]]
        if not spots and data.get("headline"):
            # 2026-11-11 (owner): no screenshot without a zoom and a mark: the headline is the fact
            spots = [{"rect": data["headline"], "at": 0.9, "sweep": True}]
        callout = next((sp for sp in spots if sp.get("label")), None)
        zoomed = bool(data.get("zoomed"))           # the second, closer beat of the same page
        if zoomed:
            for sp in spots:
                sp["at"] = min(float(sp.get("at", 0.5)), 0.45)
        bar = 44 if edge == "glass" else 0
        if self.fmt == "long":
            fw = 1180 if callout else 1320
            fx = 130 if callout else (self.w - fw) // 2
        else:
            fw, fx = 940, 70                          # inside the Short's safe margins
        page_w = float(data.get("page_width", 1440))
        k = fw / page_w                                   # css px of the page -> card px
        with Image.open(data["image"]) as im:
            img_h = fw * im.height / im.width
        ph = min(img_h, fw * 0.6)                         # visible page height inside the card
        fh = ph + bar
        fy = (self.h - fh) / 2 - 20 if self.fmt == "long" else 150
        img = self.asset(data["image"])
        marks, hl_tweens = "", []
        dark = _is_dark(Path(data["image"]))
        for j, spot in enumerate(spots):
            x, y, w, h = spot["rect"]
            hx, hy, hw, hh = x * k - 6, y * k - 4, w * k + 12, h * k + 8
            if dark or spot.get("sweep"):   # dark page or a headline: a gold underline sweep
                marks += (f'<div class="hl dark" id="{sid}-hl{j}" style="left:{hx:.0f}px;top:{hy + hh * 0.8:.0f}px;'
                          f'width:0px;height:{max(4, hh * 0.09):.0f}px"></div>')
            else:
                marks += (f'<div class="hl" id="{sid}-hl{j}" style="left:{hx:.0f}px;top:{hy:.0f}px;'
                          f'width:0px;height:{hh:.0f}px"></div>')
            at = t0 + float(spot.get("at", 1.2 + j * 1.0))
            hl_tweens.append(f'tl.to("#{sid}-hl{j}",{{width:{hw:.0f},duration:.35,ease:"none"}},{at:.3f});')
            self.cue("click", at)
            if j == 0:      # a pointer glides in and clicks on the fact
                px, py = hx + min(hw, 220) * 0.5, hy + hh * 0.75
                marks += (f'<div id="{sid}-cur" style="position:absolute;left:{px:.0f}px;top:{py:.0f}px;width:46px;height:46px;'
                          f'opacity:0;z-index:5"><svg viewBox="0 0 24 24" width="46" height="46"><path d="M4 2 L4 19 L8.5 15 '
                          f'L11.5 22 L14.5 20.6 L11.6 13.8 L18 13.8 Z" fill="#fff" stroke="#111" stroke-width="1.6" '
                          f'stroke-linejoin="round"/></svg></div><div id="{sid}-rip" style="position:absolute;left:{px - 30:.0f}px;'
                          f'top:{py - 30:.0f}px;width:60px;height:60px;border-radius:50%;border:4px solid #E8C268;opacity:0"></div>')
                hl_tweens.append(f'tl.fromTo("#{sid}-cur",{{x:160,y:120,opacity:0}},{{x:0,y:0,opacity:1,duration:.45,'
                                 f'ease:"power2.out"}},{max(t0 + 0.05, at - 0.5):.3f});')
                hl_tweens.append(f'tl.fromTo("#{sid}-cur",{{scale:1}},{{scale:.8,duration:.08,yoyo:true,repeat:1,'
                                 f'immediateRender:false}},{at - 0.05:.3f});')
                hl_tweens.append(f'tl.fromTo("#{sid}-rip",{{scale:.3,opacity:1}},{{scale:1.8,opacity:0,duration:.45,'
                                 f'ease:"power2.out"}},{at - 0.02:.3f});')
            if spot.get("ring"):
                r = max(hw, hh) * 0.85
                marks += (f'<div class="ring" id="{sid}-ring{j}" style="left:{hx + hw / 2 - r:.0f}px;'
                          f'top:{hy + hh / 2 - r:.0f}px;width:{2 * r:.0f}px;height:{2 * r:.0f}px"></div>')
                hl_tweens.append(f'tl.fromTo("#{sid}-ring{j}",{{scale:1.6,opacity:0}},{{scale:1,opacity:1,'
                                 f'duration:.4,ease:"back.out(2)"}},{at + 0.3:.3f});')
        chrome = ""
        if bar:
            chrome = (f'<div class="bar"><div class="dot" style="background:#ff5f57"></div><div class="dot" '
                      f'style="background:#febc2e"></div><div class="dot" style="background:#28c840"></div>'
                      f'<div class="url">{_e(data.get("url", ""))}</div></div>')
        look = ("border:1.5px solid rgba(232,194,104,.55);box-shadow:0 0 0 1px rgba(0,0,0,.4),0 30px 90px rgba(0,0,0,.7),"
                "0 0 60px rgba(232,194,104,.18)" if edge == "glass" else
                "border-radius:28px;-webkit-mask-image:radial-gradient(ellipse 72% 70% at 50% 50%,#000 58%,transparent 100%);"
                "mask-image:radial-gradient(ellipse 72% 70% at 50% 50%,#000 58%,transparent 100%);box-shadow:none")
        domain = re.sub(r"^https?://(www\.)?", "", str(data.get("url", ""))).split("/")[0]
        inner = (f'<div class="frame" id="{sid}-f" style="left:{fx}px;top:{fy:.0f}px;width:{fw}px;height:{fh:.0f}px;{look}">'
                 f'{chrome}<div class="page" style="top:{bar}px"><div id="{sid}-pg" style="position:absolute;left:0;top:0;'
                 f'width:{fw}px;height:{img_h:.0f}px"><img src="{img}">{marks}</div></div></div>')
        if domain:
            inner += (f'<div class="chip" id="{sid}-src" style="position:absolute;left:{fx}px;top:{fy + fh + 26:.0f}px;'
                      f'font-size:24px">Source · {_e(domain)}</div>')
        if callout and self.fmt == "short":
            inner += (f'<div class="card" id="{sid}-co" style="position:absolute;left:{fx}px;top:{fy + fh + 100:.0f}px;'
                      f'width:{fw}px;box-sizing:border-box;padding:30px 36px;border-color:rgba(232,194,104,.5)">'
                      f'<div style="font:900 84px/1 Poppins;color:#E8C268">{_e(callout["label"])}</div>'
                      f'<div class="label" style="margin-top:14px;font-size:32px">{_e(callout.get("sub", ""))}</div></div>')
        elif callout:
            cx0 = fx + fw + 60
            inner += (f'<div class="card" id="{sid}-co" style="position:absolute;left:{cx0}px;top:{self.h * .24:.0f}px;'
                      f'width:{self.w - cx0 - 70}px;box-sizing:border-box;padding:30px 32px;border-color:rgba(232,194,104,.5)">'
                      f'<div style="font:900 84px/1 Poppins;color:#E8C268">{_e(callout["label"])}</div>'
                      f'<div class="label" style="margin-top:14px;font-size:30px">{_e(callout.get("sub", ""))}</div></div>')
        self.scene(sid, t0, dur, inner)
        if zoomed:      # a hard cut to the closer shot
            self.cue("click", t0)
        else:           # the card grows in from small (house rule: sources never slam in full screen)
            self.tw(f'tl.fromTo("#{sid}-f",{{scale:.62,y:70,opacity:0}},{{scale:1,y:0,opacity:1,duration:.6,'
                    f'ease:"back.out(1.3)"}},{t0:.3f});')
            self.cue("whoosh", t0)
        if domain:
            self.tw(f'tl.fromTo("#{sid}-src",{{y:20,opacity:0}},{{y:0,opacity:1,duration:.4,ease:"power3.out"}},{t0 + 0.5:.3f});')
        if spots:   # camera zooms INSIDE the card to the facts, page edges never show
            x0 = min(sp["rect"][0] for sp in spots) * k; y0 = min(sp["rect"][1] for sp in spots) * k
            x1 = max(sp["rect"][0] + sp["rect"][2] for sp in spots) * k
            y1 = max(sp["rect"][1] + sp["rect"][3] for sp in spots) * k
            ox, oy = (x0 + x1) / 2, (y0 + y1) / 2
            z = max(1.0, min(float(data.get("zoom", 1.9)), 0.75 * fw / max(1.0, x1 - x0)))
            dx = min(max((fw / 2 - ox), -(fw - ox) * (z - 1)), ox * (z - 1))
            dy = min(max((ph / 2 - oy), ph - oy - (img_h - oy) * z), oy * (z - 1))
            if zoomed:
                z2 = z * 1.08
                dx2 = min(max((fw / 2 - ox), -(fw - ox) * (z2 - 1)), ox * (z2 - 1))
                dy2 = min(max((ph / 2 - oy), ph - oy - (img_h - oy) * z2), oy * (z2 - 1))
                self.tw(f'tl.fromTo("#{sid}-pg",{{x:{dx:.0f},y:{dy:.0f},scale:{z:.3f},transformOrigin:"{ox:.0f}px {oy:.0f}px"}},'
                        f'{{x:{dx2:.0f},y:{dy2:.0f},scale:{z2:.3f},duration:{dur:.2f},ease:"none"}},{t0:.3f});')
            else:
                at = max(t0 + 0.45, t0 + float(spots[0].get("at", 1.2)) - 0.5)
                self.tw(f'tl.to("#{sid}-pg",{{x:{dx:.0f},y:{dy:.0f},scale:{z:.3f},transformOrigin:"{ox:.0f}px {oy:.0f}px",'
                        f'duration:.8,ease:"power2.inOut"}},{at:.3f});')
        if callout:
            at = t0 + float(callout.get("at", 1.2)) + 0.35
            self.tw(f'tl.fromTo("#{sid}-co",{{x:60,opacity:0}},{{x:0,opacity:1,duration:.55,ease:"back.out(1.5)"}},{at:.3f});')
            self.cue("pop", at)
        if self.fmt == "long":
            self.drift(sid, t0, dur, 0.006)
        for js in hl_tweens:
            self.tw(js)

    def photo(self, t0, dur, data, how="rise"):
        """The source's own picture as a block: framed, slow Ken Burns push, source tag."""
        sid = self._id("photo")
        with Image.open(data["image"]) as im:
            ratio = im.height / im.width
        fw = 940 if self.fmt == "short" else 1300
        fh = min(fw * ratio, 760 if self.fmt == "short" else 760)
        fx, fy = (self.w - fw) / 2, (self.cy - fh / 2 - 20)
        img = self.asset(data["image"])
        domain = re.sub(r"^https?://(www\.)?", "", str(data.get("url", ""))).split("/")[0]
        inner = (f'<div class="frame" id="{sid}-f" style="left:{fx:.0f}px;top:{fy:.0f}px;width:{fw}px;height:{fh:.0f}px;'
                 f'border:2px solid rgba(232,194,104,.6);box-shadow:0 30px 90px rgba(0,0,0,.7),0 0 60px rgba(232,194,104,.2)">'
                 f'<img id="{sid}-i" src="{img}" style="position:absolute;left:0;top:50%;width:100%;transform-origin:50% 50%"></div>')
        if domain:
            inner += (f'<div class="chip" id="{sid}-src" style="position:absolute;left:{fx:.0f}px;top:{fy + fh + 24:.0f}px;'
                      f'font-size:24px">Source · {_e(domain)}</div>')
        self.scene(sid, t0, dur, inner)
        self.tw(f'tl.fromTo("#{sid}-f",{{scale:.7,rotation:-3,opacity:0}},{{scale:1,rotation:0,opacity:1,duration:.5,'
                f'ease:"back.out(1.5)"}},{t0:.3f});')
        self.tw(f'tl.fromTo("#{sid}-i",{{yPercent:-50,scale:1.04,x:0}},{{yPercent:-50,scale:1.16,x:-20,duration:{dur:.2f},'
                f'ease:"none"}},{t0:.3f});')
        self.cue("whoosh", t0)

    def stat_counter(self, t0, dur, data, how="whip"):
        """A real number counts up, punches and sits on a label (impact sound)."""
        sid = self._id("stat")
        value = float(data["value"])
        prefix, suffix = data.get("prefix", ""), data.get("suffix", "")
        decimals = int(data.get("decimals", 0))
        source = f'<div class="chip" style="margin-top:26px">{_e(data["source"])}</div>' if data.get("source") else ""
        cw = min(1100, self.w - 100)
        digits = len(f"{prefix}{value:,.{decimals}f}{suffix}")
        size = int(min(220, cw * 1.55 / max(1, digits)))
        inner = (f'<div class="card" style="position:absolute;left:50%;top:{self.cy}px;width:{cw}px;height:{760 if self.fmt == "short" else 560}px;'
                 f'margin:-{380 if self.fmt == "short" else 280}px 0 0 -{cw // 2}px;display:flex;flex-direction:column;align-items:center;justify-content:center;'
                 f'text-align:center;box-sizing:border-box;padding:0 40px">'
                 f'<div class="num" style="font-size:{size}px"><span>{_e(prefix)}</span><span id="{sid}-n">0</span><span>{_e(suffix)}</span></div>'
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
        m = 120 if self.fmt == "long" else 70
        inner = (f'<div style="position:absolute;left:{m}px;right:{m}px;top:{self.cy}px;transform:translateY(-50%)">'
                 f'<div class="title" style="text-align:left;font-size:{112 if self.fmt == "long" else 104}px">{spans}</div>'
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
        m = 140 if self.fmt == "long" else 80
        inner = (f'<div style="position:absolute;left:{m}px;right:{m}px;top:{self.cy}px;transform:translateY(-50%)">'
                 f'<div class="chip" id="{sid}-c">{_e(data.get("number", ""))}</div>'
                 f'<div class="title" id="{sid}-t" style="margin-top:26px;font-size:{128 if self.fmt == "long" else 104}px">{_e(data["title"])}</div>'
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
        cw = min(1300, self.w - 100)
        inner = (f'<div class="card" style="position:absolute;left:50%;top:{self.cy}px;width:{cw}px;margin-left:-{cw // 2}px;'
                 f'transform:translateY(-50%);padding:70px 70px;box-sizing:border-box">'
                 f'<div style="font:900 120px/0.6 Poppins;color:#E8C268">&ldquo;</div>'
                 f'<div style="font:800 {58 if self.fmt == "long" else 66}px/1.22 Poppins">{body}</div>'
                 f'<div class="label" style="margin-top:34px">{_e(data.get("who", ""))}</div></div>')
        self.scene(sid, t0, dur, inner)
        self.entrance(sid, t0, how)
        self.drift(sid, t0, dur, 0.012)

    def comparison(self, t0, dur, data, how="wipe"):
        """Two sides; the rows build one by one; the winning value glows gold."""
        sid = self._id("compare")
        left, right = data["left"], data["right"]
        lw, vw = (420, 330) if self.fmt == "long" else (290, 320)
        big = self.fmt == "short"
        cw = lw + 2 * vw + 120
        rows = ""
        for i, (label, a, b) in enumerate(data["rows"]):
            win = data.get("winners", [None] * len(data["rows"]))[i]
            rows += (f'<div class="row" id="{sid}-r{i}" style="padding:{34 if big else 18}px 0;border-top:1px solid rgba(255,255,255,.08)">'
                     f'<div class="label" style="width:{lw}px;font-size:{40 if big else 34}px">{_e(label)}</div>'
                     f'<div style="width:{vw}px;font:800 {60 if big else 46}px Poppins;{"color:#E8C268" if win == "left" else ""}">{_e(a)}</div>'
                     f'<div style="width:{vw}px;font:800 {60 if big else 46}px Poppins;{"color:#E8C268" if win == "right" else ""}">{_e(b)}</div></div>')
        inner = (f'<div class="card" style="position:absolute;left:50%;top:{self.cy}px;width:{cw}px;margin-left:-{cw // 2}px;'
                 f'transform:translateY(-50%);padding:{70 if big else 50}px 60px;box-sizing:border-box">'
                 f'<div class="row" style="padding-bottom:14px"><div style="width:{lw}px"></div>'
                 f'<div style="width:{vw}px;font:900 {52 if big else 50}px Poppins">{_e(left)}</div>'
                 f'<div style="width:{vw}px;font:900 {52 if big else 50}px Poppins;color:#38BDF8">{_e(right)}</div></div>{rows}</div>')
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
                        f'<div style="font:800 {68 if self.fmt == "short" else 54}px/1.1 Poppins">{_e(s)}</div></div>' for i, s in enumerate(data["items"]))
        m = 180 if self.fmt == "long" else 70
        inner = (f'<div style="position:absolute;left:{m}px;right:{m}px;top:{self.cy}px;transform:translateY(-50%)">'
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
        if self.fmt == "short":
            return self._timeline_vertical(sid, t0, dur, pts, how)
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

    def _timeline_vertical(self, sid, t0, dur, pts, how):
        n = len(pts)
        top, span = 260, 820
        rows = "".join(f'<div id="{sid}-p{i}" style="position:absolute;left:150px;right:70px;top:{top + span * i / max(1, n - 1) - 34:.0f}px">'
                       f'<div style="position:absolute;left:-74px;top:22px;width:30px;height:30px;border-radius:50%;'
                       f'background:#E8C268;box-shadow:0 0 30px rgba(232,194,104,.7)"></div>'
                       f'<div style="font:900 60px/1 Poppins">{_e(p["when"])}</div>'
                       f'<div class="label" style="font-size:34px;margin-top:10px">{_e(p["what"])}</div></div>' for i, p in enumerate(pts))
        inner = (f'<div id="{sid}-line" style="position:absolute;left:89px;top:{top}px;width:4px;height:0;'
                 f'background:linear-gradient(#E8C268,rgba(232,194,104,.3))"></div>{rows}')
        self.scene(sid, t0, dur, inner)
        self.entrance(sid, t0, how)
        run = min(2.4, dur - 0.6)
        self.tw(f'tl.to("#{sid}-line",{{height:{span},duration:{run:.2f},ease:"power2.inOut"}},{t0 + 0.2:.3f});')
        for i in range(n):
            at = t0 + 0.25 + run * (i / max(1, n - 1))
            self.tw(f'tl.fromTo("#{sid}-p{i}",{{x:40,opacity:0}},{{x:0,opacity:1,duration:.45,ease:"back.out(1.6)"}},{at:.3f});')
            self.cue("click", at)
        self.drift(sid, t0, dur, 0.012)

    def flow(self, t0, dur, data, how="wipe"):
        """How it works: nodes appear one by one, joined by arrows that draw themselves (vertical on a Short)."""
        sid = self._id("flow")
        nodes = [str(n) for n in data["nodes"]][:4]
        n = len(nodes)
        vertical = self.fmt == "short"
        nw, nh = (760, 150) if vertical else (min(420, (self.w - 200) / n - 70), 170)
        gap = (self.h * 0.0 + 70) if vertical else 70
        total = n * nh + (n - 1) * gap if vertical else n * nw + (n - 1) * gap
        x0 = (self.w - (nw if vertical else total)) / 2
        y0 = self.cy - (total if vertical else nh) / 2
        html_, arrows = "", ""
        for i, text in enumerate(nodes):
            x = x0 if vertical else x0 + i * (nw + gap)
            y = y0 + i * (nh + gap) if vertical else y0
            gold = i == n - 1
            html_ += (f'<div class="card" id="{sid}-n{i}" style="position:absolute;left:{x:.0f}px;top:{y:.0f}px;width:{nw:.0f}px;'
                      f'height:{nh}px;display:flex;align-items:center;justify-content:center;text-align:center;padding:0 24px;'
                      f'border-color:{"rgba(232,194,104,.8)" if gold else "rgba(255,255,255,.12)"};'
                      f'box-shadow:0 20px 60px rgba(0,0,0,.6){",0 0 40px rgba(232,194,104,.35)" if gold else ""}">'
                      f'<div style="font:800 {54 if vertical else 46}px/1.1 Poppins;{"color:#E8C268" if gold else ""}">{_e(text)}</div></div>')
            if i < n - 1:
                if vertical:
                    ax, ay, aw, ah = x0 + nw / 2 - 4, y + nh + 8, 8, gap - 16
                else:
                    ax, ay, aw, ah = x + nw + 8, y0 + nh / 2 - 4, gap - 16, 8
                arrows += (f'<div id="{sid}-a{i}" style="position:absolute;left:{ax:.0f}px;top:{ay:.0f}px;width:{aw:.0f}px;'
                           f'height:{ah:.0f}px;background:#E8C268;border-radius:4px;transform-origin:{"50% 0" if vertical else "0 50%"}"></div>')
        self.scene(sid, t0, dur, arrows + html_)
        step = min(0.6, max(0.25, (dur - 0.5) / max(1, n)))
        for i in range(n):
            at = t0 + 0.1 + i * step
            self.tw(f'tl.fromTo("#{sid}-n{i}",{{scale:.6,opacity:0}},{{scale:1,opacity:1,duration:.35,ease:"back.out(1.8)"}},{at:.3f});')
            self.cue("pop", at)
            if i < n - 1:
                prop = "scaleY" if vertical else "scaleX"
                self.tw(f'tl.fromTo("#{sid}-a{i}",{{{prop}:0}},{{{prop}:1,duration:{step * 0.8:.2f},ease:"power2.out"}},{at + 0.25:.3f});')
        self.drift(sid, t0, dur, 0.01)

    def logo_tiles(self, t0, dur, data, how="rise"):
        """The real 3D logo tiles (rendered by vector.thumb_styles) float in with parallax."""
        sid = self._id("logos")
        tiles = data["tiles"]                               # [{"image": path}]
        n = len(tiles)
        gap = min(360, (self.w - 60) / max(1, n))
        ts = min(300, gap - 30) if not data.get("big") else (560 if self.fmt == "short" else 480)
        x0 = self.w / 2 - gap * (n - 1) / 2
        inner = "".join(f'<div class="tile" id="{sid}-t{i}" style="left:{x0 + gap * i - ts / 2:.0f}px;top:{self.cy - (ts / 2 + 70 if data.get("big") else 190):.0f}px;'
                        f'width:{ts:.0f}px;height:{ts:.0f}px">'
                        f'<img src="{self.asset(t["image"])}"></div>' for i, t in enumerate(tiles))
        if data.get("caption"):
            inner += (f'<div class="title" style="position:absolute;left:0;right:0;top:{self.cy + (ts / 2 - 30 if data.get("big") else 170):.0f}px;'
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
        fw = 960 if self.fmt == "short" else 900
        inner = (f'<div class="card" id="{sid}-c" style="position:absolute;left:50%;top:{self.cy}px;width:{fw}px;margin-left:-{fw // 2}px;'
                 f'transform:translateY(-50%);padding:60px;text-align:center">'
                 f'<div style="margin:0 auto 26px;width:150px;height:150px"><svg viewBox="-32 -32 64 64" width="150" height="150">{logo_mark(0, 0, 60, "#F4F1EA")}</svg></div>'
                 f'<div class="title" style="font-size:{104 if self.fmt == "short" else 86}px">Follow <span class="gold">GOLIDE</span></div>'
                 f'<div class="label" style="margin-top:20px;font-size:{40 if self.fmt == "short" else 34}px">{_e(data.get("reason", ""))}</div></div>')
        self.scene(sid, t0, dur, inner)
        self.entrance(sid, t0, "rise")
        self.cue("click", t0 + 0.4)

    def host(self, t0, dur, data, how="rise"):
        """Pango, the GOLIDE host, talking with the owner's voice. place: full (left half, the scene's
        words on the right), left/right (standing beside another scene), corner (small bubble over a
        screenshot). Poses change on words; the mouth follows Rhubarb cues; he blinks and breathes."""
        from . import mascot

        sid = self._id("host")
        self.uses_mascot = True
        place = data.get("place", "full")
        poses = data.get("poses") or [{"pose": "talk", "at": 0}]
        cues = data.get("cues") or []
        outfit = data.get("outfit") or self.outfit
        self.outfits.add(outfit)
        side = 560 if self.fmt == "short" else 600
        size = {"full": 1000, "left": 860, "right": 860, "corner": 420, "studio": studio.layout(self.fmt)["size"],
                "lower": studio.layout("lower")["size"], "side": side}[place]
        w = size * mascot.VIEW[0] / mascot.VIEW[1]
        x = {"full": self.w * 0.27 - w / 2, "left": 40, "right": self.w - w - 40, "corner": self.w - w - 50,
             "studio": studio.layout(self.fmt)["seat_x"] - w / 2, "lower": studio.layout("lower")["seat_x"] - w / 2,
             "side": 10 if self.fmt == "short" else self.w - w - 30}[place]
        y = self.h - size - (30 if place != "corner" else 20)
        if place == "side":   # standing beside the block; on a Short his feet stay above YouTube's caption area
            y = (1700 if self.fmt == "short" else self.h - 20) - size
        if place in ("studio", "lower"):      # seated: desk top at his waist
            y = studio.layout(self.fmt if place == "studio" else "lower")["desk_y"] - 430 * size / 540
        layers = ""
        for k, p in enumerate(poses):
            uid = f"{sid}-p{k}"
            layers += (f'<svg id="{uid}" class="{sid}-pose" viewBox="0 0 400 540" width="{w:.0f}" height="{size}" '
                       f'style="position:absolute;left:0;top:0;opacity:{1 if k == 0 else 0}">'
                       f'{mascot.character(p["pose"], uid=uid, expression=p.get("face"), outfit=outfit)}</svg>')
        bubble = ""
        if place == "studio":
            self.uses_studio = True
            bubble = studio.back(sid, self.fmt)
        elif place == "lower":
            self.uses_studio = True
            bubble = studio.lower_back(sid)
        elif place != "corner":     # open stage: back-wall wordmark, spotlight, floor grid to the horizon, glow disc
            cxp = x + w / 2
            panels = "".join(
                f'<div class="panel" id="{sid}-pn{i}" style="left:{px:.0f}px;top:{py:.0f}px;width:{pw}px;height:{ph_}px">{body}</div>'
                for i, (px, py, pw, ph_, body) in enumerate([
                    (max(40, cxp - w * .95), self.h * .2, 190, 130,
                     '<div style="display:flex;gap:12px;align-items:flex-end;height:100%;padding:0 26px 22px">'
                     + "".join(f'<div style="width:22px;height:{hb}px;border-radius:6px;background:{c}"></div>'
                               for hb, c in ((30, "#2450E6"), (52, "#4C7DFF"), (78, "#E8C268"), (64, "#4C7DFF")))
                     + '</div>'),
                    (min(self.w * .46, cxp + w * .62), self.h * .12, 170, 110,
                     '<div style="font:900 52px/110px Poppins;color:#E8C268;text-align:center">&lt;/&gt;</div>'),
                ]))
            dots = "".join(f'<div class="dotp" id="{sid}-d{i}" style="left:{dx_:.0f}px;top:{dy_:.0f}px;opacity:{op}"></div>'
                           for i, (dx_, dy_, op) in enumerate([(cxp - 320, 300, .7), (cxp + 300, 380, .5), (cxp - 180, 180, .4),
                                                               (cxp + 420, 220, .6), (cxp - 420, 520, .5)]))
            bubble = (f'<div class="studio" id="{sid}-set"><div class="wall">GOLIDE</div>'
                      f'<div class="spot" style="left:{cxp - 450:.0f}px"></div><div class="horizon"></div><div class="floor"></div>'
                      f'{panels}{dots}'
                      f'<div class="disc" style="left:{cxp - w * .62:.0f}px;top:{y + size * .9:.0f}px;width:{w * 1.24:.0f}px;'
                      f'height:{size * .13:.0f}px"></div></div>')
        if place == "side":
            bubble = (f'<div class="disc" style="left:{x + w * .12:.0f}px;top:{y + size * .93:.0f}px;width:{w * .76:.0f}px;'
                      f'height:{size * .09:.0f}px"></div>')
        if place == "corner":
            bubble = (f'<div class="card" id="{sid}-bub" style="position:absolute;left:{x - 24:.0f}px;top:{y + size * .14:.0f}px;'
                      f'width:{w + 48:.0f}px;height:{size * .88:.0f}px;border-radius:36px;background:radial-gradient('
                      f'circle at 50% 35%,#1E3A9E,#0B0F1E 75%);border:2px solid rgba(232,194,104,.55)"></div>')
        title = ""
        if place in ("full", "studio") and data.get("words"):
            spans = "".join(f'<span class="word{" gold" if w_["text"].lower().strip(".,!?") == str(data.get("punch", "")).lower() else ""}" '
                            f'id="{sid}-w{i}">{_e(w_["text"])}</span>' for i, w_ in enumerate(data["words"]))
            if place == "studio":       # the words appear on the studio's video wall
                wx, wy, ww, wf = studio.layout(self.fmt)["words"]
                title = (f'<div style="position:absolute;left:{wx}px;width:{ww}px;top:{wy}px">'
                         f'<div class="title" style="font-size:{wf}px;line-height:1.05">{spans}</div></div>')
            else:
                title = (f'<div style="position:absolute;left:{self.w * 0.52:.0f}px;right:110px;top:50%;margin-top:-170px">'
                         f'<div class="title" style="font-size:96px">{spans}</div></div>')
        front = (studio.front(sid, self.fmt) if place == "studio" else studio.front(sid, "lower") if place == "lower" else "")
        inner = (f'{bubble}{title}<div id="{sid}-ch" style="position:absolute;left:{x:.0f}px;top:{y:.0f}px;width:{w:.0f}px;'
                 f'height:{size}px">{layers}</div>{front}')
        self.parts.append(f'<section id="{sid}" class="scene clip" data-start="{t0:.3f}" data-duration="{dur:.3f}" '
                          f'style="z-index:{40 if place in ("corner", "lower", "side") else 1}"><div class="stage"><div class="cam">{inner}</div></div></section>')
        # entrance: he pops up from below the frame (in the studio he is already seated; the set eases in)
        if place == "lower":
            self.tw(f'tl.fromTo("#{sid}-ch",{{y:{size * 0.4:.0f}}},{{y:0,duration:.5,ease:"back.out(1.4)"}},{t0:.3f});')
            self.tw(f'tl.fromTo("#{sid}-low",{{opacity:0}},{{opacity:1,duration:.35}},{t0:.3f});')
        if place == "studio":
            self.tweens.extend(studio.motion(sid, t0, dur))
            # the set has its own neon GOLIDE sign: the corner mark steps aside while we are in the studio
            self.tw(f'tl.to("#brand .logo",{{opacity:0,duration:.2}},{t0:.3f});tl.to("#brand .logo",{{opacity:.92,duration:.3}},{t0 + dur:.3f});')
            self.tw(f'tl.fromTo("#{sid} .cam",{{scale:1.06}},{{scale:1.0,duration:{min(2.0, dur):.2f},ease:"power2.out"}},{t0:.3f});')
        elif place == "side":
            self.tw(f'tl.fromTo("#{sid}-ch",{{x:{-w if self.fmt == "short" else w:.0f},opacity:0}},{{x:0,opacity:1,duration:.45,'
                    f'ease:"back.out(1.5)"}},{t0:.3f});')
        elif place != "lower":
            self.tw(f'tl.fromTo("#{sid}-ch",{{y:{size * 0.5:.0f},opacity:0}},{{y:0,opacity:1,duration:.55,ease:"back.out(1.5)"}},{t0:.3f});')
        if place == "corner":
            self.tw(f'tl.fromTo("#{sid}-bub",{{scale:.6,opacity:0}},{{scale:1,opacity:1,duration:.4,ease:"back.out(1.8)"}},{t0:.3f});')
        self.cue("pop", t0 + 0.1)
        if place in ("full", "left", "right"):
            for i in range(2):
                self.tw(f'tl.fromTo("#{sid}-pn{i}",{{y:{30 + 20 * i},opacity:0}},{{y:0,opacity:1,duration:.8,ease:"power3.out"}},{t0 + 0.2 + 0.15 * i:.3f});')
                self.tw(f'tl.to("#{sid}-pn{i}",{{y:{-14 + 28 * i},duration:{max(0.5, dur - 1):.2f},ease:"sine.inOut"}},{t0 + 1.0:.3f});')
            for i in range(5):
                self.tw(f'tl.to("#{sid}-d{i}",{{y:{-40 - 12 * i},x:{(-1) ** i * 18},duration:{dur:.2f},ease:"none"}},{t0:.3f});')
            self.tw(f'tl.fromTo("#{sid}-set .floor",{{backgroundPositionY:"0px"}},{{backgroundPositionY:"90px",duration:{dur:.2f},'
                    f'ease:"none"}},{t0:.3f});')
        # breathing: a slow bob for the whole scene
        n = max(1, int(dur / 1.6))
        self.tw(f'tl.to("#{sid}-ch .{sid}-pose",{{y:-6,duration:.8,ease:"sine.inOut",yoyo:true,repeat:{2 * n - 1}}},{t0 + 0.6:.3f});')
        # pose changes on their words, with a small squash so the change reads as movement
        for k in range(1, len(poses)):
            at = t0 + float(poses[k]["at"])
            self.tw(f'tl.set("#{sid}-p{k - 1}",{{opacity:0}},{at:.3f});tl.set("#{sid}-p{k}",{{opacity:1}},{at:.3f});')
            self.tw(f'tl.fromTo("#{sid}-p{k}",{{scaleY:.96,scaleX:1.03,transformOrigin:"50% 100%"}},'
                    f'{{scaleY:1,scaleX:1,duration:.25,ease:"back.out(3)",immediateRender:false}},{at:.3f});')
        # lip sync: show one mouth shape at a time, in every pose layer
        last = None
        for c in cues:
            at = t0 + float(c["start"])
            if at >= t0 + dur:
                break
            v = c["value"]
            if v == last:
                continue
            if last:
                self.tw(f'tl.set("#{sid} [id$=-m{last}]",{{opacity:0}},{at:.3f});')
            else:
                self.tw(f'tl.set("#{sid} [id$=-mX]",{{opacity:0}},{at:.3f});')
            self.tw(f'tl.set("#{sid} [id$=-m{v}]",{{opacity:1}},{at:.3f});')
            last = v
        # eyes alive (owner 2026-11-11): small glances on a fixed pattern, up to what he points at,
        # back to the viewer; never static
        looks = {"point_up": (1, -7), "point_left": (-8, -2), "point": (8, -3), "think": (-5, -7), "shock": (0, -1)}
        glance = [(4, 1), (-4, 2), (0, 0), (5, -2), (-3, -1), (0, 0)]
        marks_ = sorted([(t0 + float(p["at"]), looks.get(p["pose"])) for p in poses if looks.get(p["pose"])])
        at, i = t0 + 0.7, 0
        while at < t0 + dur - 0.2:
            gx, gy = glance[i % len(glance)]
            self.tw(f'tl.to("#{sid} [id$=-eyes]",{{x:{gx},y:{gy},duration:.12,ease:"power2.out"}},{at:.3f});')
            at += (1.4, 1.9, 1.1, 2.3)[i % 4]
            i += 1
        for at_, (gx, gy) in marks_:
            self.tw(f'tl.to("#{sid} [id$=-eyes]",{{x:{gx},y:{gy},duration:.1,ease:"power2.out"}},{at_ + 0.05:.3f});')
        # blinks every 2.8 to 4.2 s (fixed pattern, so renders repeat exactly)
        at, gaps, i = t0 + 1.2, (3.1, 2.8, 4.2, 3.5), 0
        while at < t0 + dur - 0.3:
            self.tw(f'tl.to("#{sid} [id$=-lid]",{{scaleY:1,duration:.06,yoyo:true,repeat:1,transformOrigin:"50% 50%"}},{at:.3f});')
            at += gaps[i % len(gaps)]
            i += 1
        for i, w_ in enumerate(data.get("words") or []):
            wat = t0 + float(w_.get("at", 0.3 + i * 0.2))
            self.tw(f'tl.fromTo("#{sid}-w{i}",{{y:50,opacity:0}},{{y:0,opacity:1,duration:.4,ease:"back.out(1.6)"}},{wat:.3f});')

    # ---- output
    def build(self, edit: dict[str, Any], out: Path) -> Path:
        self.uses_mascot = False
        self.uses_studio = False
        for s in edit["scenes"]:
            getattr(self, s["type"])(float(s["start"]), float(s["duration"]), s["data"], s.get("in", "rise"))
        duration = float(edit.get("duration") or max(float(s["start"]) + float(s["duration"]) for s in edit["scenes"]))
        audio = ""
        if edit.get("audio"):
            name = self.asset(Path(edit["audio"]))
            audio = (f'<audio id="voice" class="clip" src="{name}" data-start="0" data-duration="{duration:.3f}" '
                     f'data-volume="1"></audio>')
        if self.uses_mascot:
            from .mascot import DEFS as MASCOT_DEFS

            from .mascot import outfit_defs

            audio += f'<svg width="0" height="0" style="position:absolute">{MASCOT_DEFS}</svg>'
            audio += "".join(outfit_defs(o) for o in sorted(self.outfits))
        if self.uses_studio:
            audio += studio.DEFS
        out.mkdir(parents=True, exist_ok=True)
        shutil.copytree(ASSETS / "fonts", out / "fonts", dirs_exist_ok=True)
        shutil.copy(ASSETS / "gsap.min.js", out / "gsap.min.js")
        (out / "media").mkdir(exist_ok=True)
        for name, src in self.files.items():
            shutil.copy(src, out / name)
        # captions (owner 2026-11-11: as in the illustration videos): the spoken words, each lighting up as
        # it is said, key terms in gold. Shorts: a band between the proof and Goli; long: low centre.
        caps = ""
        top = 1062 if self.fmt == "short" else self.h - 150
        size = 60 if self.fmt == "short" else 50
        for i, c in enumerate(edit.get("captions") or []):
            spans = "".join(f'<span id="c{i}w{j}" class="{"key" if j in c.get("keys", []) else ""}">{_e(w["text"])}</span>'
                            for j, w in enumerate(c["words"]))
            caps += f'<div class="cap" id="c{i}" style="top:{top}px;font-size:{size}px">{spans}</div>'
            self.tw(f'tl.set("#c{i}",{{opacity:1}},{float(c["start"]):.3f});tl.set("#c{i}",{{opacity:0}},{float(c["end"]):.3f});')
            for j, w in enumerate(c["words"]):
                at = max(float(c["start"]), float(w["at"]))
                self.tw(f'tl.fromTo("#c{i}w{j}",{{opacity:.38,scale:1}},{{opacity:1,scale:1.12,duration:.08,immediateRender:false}},{at:.3f});'
                        f'tl.to("#c{i}w{j}",{{scale:1,duration:.12}},{at + 0.08:.3f});')
        caps = f'<div id="caps">{caps}</div>' if caps else ""
        if caps and self.fmt == "short":   # in the studio the captions sit on the desk front, clear of Goli's face
            for sc in edit["scenes"]:
                if sc["type"] == "host" and (sc.get("data") or {}).get("place") == "studio":
                    a, b = float(sc["start"]), float(sc["start"]) + float(sc["duration"])
                    self.tw(f'tl.set("#caps",{{y:530}},{a:.3f});tl.set("#caps",{{y:0}},{b:.3f});')
        chapters = edit.get("chapters") or []
        from .mascot import logo_mark

        brand = ('<div id="brand"><div class="logo"><svg width="44" height="44" viewBox="-32 -32 64 64">'
                 f'{logo_mark(0, 0, 60, "#F4F1EA")}</svg>GOLIDE</div>')
        brand += "".join(f'<div class="chap" id="chap{i}">{_e(c["title"])}</div>' for i, c in enumerate(chapters))
        brand += '<div class="prog" id="prog"></div></div>'
        btw = [f'tl.fromTo("#prog",{{width:"0%"}},{{width:"100%",duration:{duration:.3f},ease:"none"}},0);']
        for i, c in enumerate(chapters):
            at = float(c["at"])
            if i:
                btw.append(f'tl.to("#chap{i - 1}",{{opacity:0,y:-10,duration:.25}},{at:.3f});')
            btw.append(f'tl.fromTo("#chap{i}",{{opacity:0,y:10}},{{opacity:1,y:0,duration:.35,ease:"power3.out"}},{at + 0.1:.3f});')
        self.tweens.extend(btw)
        page = f"""<!doctype html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width={self.w}, height={self.h}"><script src="gsap.min.js"></script>
<style>{CSS}</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-width="{self.w}" data-height="{self.h}" data-duration="{duration:.3f}">
<div class="bg" id="bg"></div><div class="glow" id="glow"></div>
{''.join(self.parts)}
{audio}
{caps}
{brand}
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
