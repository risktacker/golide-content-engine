"""Visual metaphors (owner 2026-11-13, point 3 of the review, modelled on Outskill: balance scales, a lock opening,
a magnifier revealing what is hidden, things pouring into a funnel...). An idea becomes a picture that moves on the
spoken word, instead of a text card. Each is drawn in SVG and moved with GSAP; the words come from the beat.

Every function returns (svg_markup, tweens, cues) for a 1400 x 760 canvas; `at` is when the idea lands (seconds
from the scene start), `items` etc. are the beat's own words."""
from __future__ import annotations

from html import escape

GOLD, BLUE, CYAN, INK, CARD, WHITE, DIM = "#E8C268", "#4C7DFF", "#38BDF8", "#07080B", "#141824", "#F4F1EA", "#8B93A7"
W, H = 1400, 760
KINDS = ("scales", "unlock", "magnify", "funnel", "stack", "gauge", "transform", "iceberg", "cycle")


def _t(x, y, text, size=40, color=WHITE, anchor="middle", weight=800, extra=""):
    return (f'<text x="{x:.0f}" y="{y:.0f}" text-anchor="{anchor}" font-family="Poppins" font-weight="{weight}" '
            f'font-size="{size}" fill="{color}" {extra}>{escape(str(text))}</text>')


def _fit(text: str, width: float, size: float = 44) -> float:
    """A font size that keeps the words inside the given width."""
    return max(22, min(size, width / max(1, len(str(text))) / 0.58))


def _chip(sid, k, x, y, text, fill=CARD, color=WHITE, w=None, size=34):
    w = w or max(180, len(str(text)) * size * 0.6 + 60)
    return (f'<g id="{sid}-{k}"><rect x="{x - w / 2:.0f}" y="{y - 34:.0f}" width="{w:.0f}" height="68" rx="20" '
            f'fill="{fill}" stroke="rgba(232,194,104,.55)" stroke-width="2.5"/>'
            + _t(x, y + size * 0.36, text, size, color) + '</g>')


def scales(sid, at, left="", right="", winner="left", **_):
    """Two things weighed: the heavier side drops on the word."""
    down = -1 if winner == "left" else 1
    ang = 11 * down
    import math
    dy = 430 * math.sin(math.radians(abs(ang)))
    pans = ""
    for side, x, label in (("l", 270, left), ("r", 1130, right)):
        hot = (side == "l") == (winner == "left")
        size = _fit(label, 300, 42)
        pans += (f'<g id="{sid}-pan{side}"><line x1="{x - 120}" y1="250" x2="{x}" y2="430" stroke="{DIM}" stroke-width="3"/>'
                 f'<line x1="{x + 120}" y1="250" x2="{x}" y2="430" stroke="{DIM}" stroke-width="3"/>'
                 f'<path d="M{x - 170} 430 Q{x} 520 {x + 170} 430 Z" fill="{GOLD if hot else CARD}" stroke="{GOLD}" stroke-width="3"/>'
                 + _t(x, 600, label, size, GOLD if hot else WHITE) + '</g>')
    svg = (f'<rect x="680" y="250" width="40" height="420" rx="12" fill="{CARD}" stroke="{GOLD}" stroke-width="2"/>'
           f'<rect x="560" y="660" width="280" height="34" rx="14" fill="{CARD}" stroke="{GOLD}" stroke-width="2"/>'
           f'<g id="{sid}-beam"><rect x="140" y="236" width="1120" height="26" rx="13" fill="{GOLD}"/>'
           f'<circle cx="700" cy="249" r="26" fill="{INK}" stroke="{GOLD}" stroke-width="5"/></g>{pans}')
    tw = [f'tl.fromTo("#{sid}-beam",{{rotation:0,svgOrigin:"700 249"}},{{rotation:{ang},svgOrigin:"700 249",duration:.9,ease:"elastic.out(1,.55)"}},{at:.3f});',
          f'tl.fromTo("#{sid}-panl",{{y:0}},{{y:{dy * (1 if winner == "left" else -1):.0f},duration:.9,ease:"elastic.out(1,.55)"}},{at:.3f});',
          f'tl.fromTo("#{sid}-panr",{{y:0}},{{y:{dy * (-1 if winner == "left" else 1):.0f},duration:.9,ease:"elastic.out(1,.55)"}},{at:.3f});']
    return svg, tw, [("impact", at)]


def unlock(sid, at, label="", **_):
    """A lock that opens on the word, and what it opens."""
    size = _fit(label, 900, 56)
    svg = (f'<g id="{sid}-glow" opacity="0"><circle cx="700" cy="360" r="230" fill="{GOLD}" opacity=".18"/></g>'
           f'<path id="{sid}-sh" d="M590 330 V250 A110 110 0 0 1 810 250 V330" fill="none" stroke="{WHITE}" '
           f'stroke-width="34" stroke-linecap="round"/>'
           f'<rect id="{sid}-body" x="540" y="320" width="320" height="250" rx="40" fill="{CARD}" stroke="{GOLD}" stroke-width="5"/>'
           f'<circle cx="700" cy="420" r="30" fill="{GOLD}"/><rect x="688" y="430" width="24" height="70" rx="10" fill="{GOLD}"/>'
           + _t(700, 690, label, size, GOLD, extra=f'id="{sid}-lb" opacity="0"'))
    tw = [f'tl.to("#{sid}-sh",{{y:-70,duration:.35,ease:"back.out(2)"}},{at:.3f});',
          f'tl.to("#{sid}-sh",{{rotation:-28,svgOrigin:"810 330",duration:.45,ease:"power2.out"}},{at + .3:.3f});',
          f'tl.to("#{sid}-body",{{attr:{{fill:"{GOLD}"}},duration:.3}},{at + .1:.3f});',
          f'tl.fromTo("#{sid}-glow",{{opacity:0,scale:.6,svgOrigin:"700 360"}},{{opacity:1,scale:1.15,duration:.6}},{at:.3f});',
          f'tl.fromTo("#{sid}-lb",{{opacity:0,y:20}},{{opacity:1,y:0,duration:.4}},{at + .35:.3f});']
    return svg, tw, [("riser", max(0, at - .8)), ("click", at), ("shimmer", at + .3)]


def magnify(sid, at, label="", items=(), **_):
    """A magnifier slides over a blurred card and shows what is really there."""
    hidden = label or (items[0] if items else "")
    words = str(hidden).split()
    lines_ = [" ".join(words[:(len(words) + 1) // 2]), " ".join(words[(len(words) + 1) // 2:])] if len(hidden) > 16 else [hidden]
    size = min(_fit(max(lines_, key=len), 360, 56), 56)
    bars = "".join(f'<rect x="{330 + (i % 2) * 40}" y="{250 + i * 70}" width="{740 - (i % 3) * 120}" height="26" rx="13" '
                   f'fill="#2A3042"/>' for i in range(4))
    svg = (f'<defs><clipPath id="{sid}-lens"><circle id="{sid}-lc" cx="300" cy="370" r="215"/></clipPath></defs>'
           f'<rect x="270" y="180" width="860" height="380" rx="30" fill="{CARD}" stroke="rgba(255,255,255,.12)" stroke-width="2"/>'
           f'{bars}'
           f'<g clip-path="url(#{sid}-lens)"><rect x="270" y="180" width="860" height="380" rx="30" fill="#1C2236"/>'
           + "".join(_t(700, 380 + (j - (len(lines_) - 1) / 2) * size * 1.15 + size * .35, ln, size, GOLD)
                     for j, ln in enumerate(lines_)) + '</g>'
           f'<g id="{sid}-mg"><circle cx="300" cy="370" r="215" fill="none" stroke="{WHITE}" stroke-width="18"/>'
           f'<rect x="440" y="530" width="50" height="190" rx="22" fill="{GOLD}" transform="rotate(-40 465 625)"/></g>')
    tw = [f'tl.fromTo("#{sid}-mg",{{x:-60}},{{x:400,duration:{max(.8, at):.2f},ease:"power2.inOut"}},0);',
          f'tl.fromTo("#{sid}-lc",{{attr:{{cx:240}}}},{{attr:{{cx:700}},duration:{max(.8, at):.2f},ease:"power2.inOut"}},0);']
    return svg, tw, [("whoosh", 0.1), ("pop", max(.8, at))]


def funnel(sid, at, items=(), label="", **_):
    """Many things go in, one comes out."""
    items = list(items)[:4] or ["Input"]
    xs = [700 + (i - (len(items) - 1) / 2) * 300 for i in range(len(items))]
    chips = "".join(_chip(sid, f"in{i}", x, 90, it, size=_fit(it, 240, 30)) for i, (x, it) in enumerate(zip(xs, items)))
    svg = (f'<path d="M420 230 H980 L760 470 V560 H640 V470 Z" fill="{CARD}" stroke="{GOLD}" stroke-width="4"/>'
           f'{chips}' + _chip(sid, "out", 700, 660, label or "Result", fill=GOLD, color=INK,
                              size=_fit(label or "Result", 560, 40)))
    tw = []
    step = max(.25, (at - .4) / max(1, len(items)))
    for i, x in enumerate(xs):
        t = .3 + i * step
        tw.append(f'tl.fromTo("#{sid}-in{i}",{{x:0,y:0,scale:1,opacity:1}},{{x:{700 - x:.0f},y:330,scale:.35,opacity:0,'
                  f'duration:.6,ease:"power2.in"}},{t:.3f});')
    tw.append(f'tl.fromTo("#{sid}-out",{{y:-90,scale:.4,opacity:0,transformOrigin:"50% 50%"}},{{y:0,scale:1,opacity:1,'
              f'duration:.5,ease:"back.out(2)"}},{at:.3f});')
    return svg, tw, [("whoosh", .3), ("pop", at)]


def stack(sid, at, items=(), times=None, **_):
    """Layers built one on another (a system and its parts), each on its spoken word."""
    items = list(items)[:5] or ["Layer"]
    n = len(items)
    bh = min(110, 520 / n)
    svg, tw = "", []
    for i, it in enumerate(items):
        y = 680 - (i + 1) * (bh + 10)
        w = 900 - i * 80
        fill = GOLD if i == n - 1 else CARD
        svg += (f'<g id="{sid}-b{i}"><rect x="{700 - w / 2}" y="{y:.0f}" width="{w}" height="{bh:.0f}" rx="18" fill="{fill}" '
                f'stroke="{GOLD}" stroke-width="3"/>' + _t(700, y + bh / 2 + 14, it, _fit(it, w - 60, 40),
                                                            INK if i == n - 1 else WHITE) + '</g>')
        t = (times[i] if times and i < len(times) else .3 + i * max(.35, (at - .3) / n))
        tw.append(f'tl.fromTo("#{sid}-b{i}",{{y:-700,opacity:0}},{{y:0,opacity:1,duration:.55,ease:"bounce.out"}},{t:.3f});')
    return svg, tw, [("pop", (times or [at])[-1] if times else at)]


def gauge(sid, at, value=None, label="", **_):
    """A dial that swings to the level the words name."""
    v = max(0.0, min(100.0, float(value if value is not None else 80)))
    ang = -90 + 180 * v / 100
    svg = (f'<defs><linearGradient id="{sid}-g" x1="0" x2="1"><stop offset="0" stop-color="{BLUE}"/>'
           f'<stop offset=".6" stop-color="{CYAN}"/><stop offset="1" stop-color="{GOLD}"/></linearGradient></defs>'
           f'<path d="M330 560 A370 370 0 0 1 1070 560" fill="none" stroke="#232838" stroke-width="56" stroke-linecap="round"/>'
           f'<path id="{sid}-arc" d="M330 560 A370 370 0 0 1 1070 560" fill="none" stroke="url(#{sid}-g)" stroke-width="56" '
           f'stroke-linecap="round" pathLength="100" stroke-dasharray="100" stroke-dashoffset="100"/>'
           f'<g id="{sid}-nd"><path d="M690 560 L700 250 L710 560 Z" fill="{WHITE}"/></g>'
           f'<circle cx="700" cy="560" r="34" fill="{GOLD}"/>'
           + _t(700, 680, label, _fit(label, 900, 52), GOLD))
    tw = [f'tl.fromTo("#{sid}-nd",{{rotation:-90,svgOrigin:"700 560"}},{{rotation:{ang:.1f},svgOrigin:"700 560",duration:1.1,ease:"elastic.out(1,.6)"}},{at:.3f});',
          f'tl.to("#{sid}-arc",{{attr:{{"stroke-dashoffset":{100 - v:.1f}}},duration:1.0,ease:"power2.out"}},{at:.3f});']
    return svg, tw, [("riser", max(0, at - .6)), ("impact", at + .4)]


def transform(sid, at, left="", right="", **_):
    """One thing breaks apart and rebuilds as another (input becomes output)."""
    a, b = left or "Before", right or "After"
    tiles = ""
    for i in range(12):
        x, y = 190 + (i % 4) * 85, 290 + (i // 4) * 60
        tiles += f'<rect id="{sid}-t{i}" x="{x}" y="{y}" width="75" height="50" rx="10" fill="#2A3042" opacity="0"/>'
    svg = (f'<g id="{sid}-a"><rect x="170" y="270" width="360" height="200" rx="26" fill="{CARD}" stroke="rgba(255,255,255,.2)" stroke-width="2"/>'
           + _t(350, 385, a, _fit(a, 320, 40)) + '</g>' + tiles
           + f'<g id="{sid}-b" opacity="0"><rect x="870" y="250" width="400" height="240" rx="30" fill="{GOLD}"/>'
           + _t(1070, 385, b, _fit(b, 360, 46), INK) + '</g>'
           f'<path d="M600 370 H800" stroke="{GOLD}" stroke-width="6" stroke-dasharray="14 12" opacity=".6"/>')
    tw = [f'tl.to("#{sid}-a",{{opacity:.28,duration:.2}},{at:.3f});']     # the "before" stays, faded
    for i in range(12):
        tw.append(f'tl.fromTo("#{sid}-t{i}",{{opacity:1,x:0,y:0,rotation:0}},{{x:{700 + (i % 4) * 15:.0f},y:{(i // 4 - 1) * 20 - 10:.0f},'
                  f'rotation:{(i * 37) % 90 - 45},opacity:0,duration:.6,ease:"power2.inOut"}},{at + i * .02:.3f});')
    tw.append(f'tl.fromTo("#{sid}-b",{{opacity:0,scale:.7,transformOrigin:"50% 50%"}},{{opacity:1,scale:1,duration:.4,'
              f'ease:"back.out(2)"}},{at + .5:.3f});')
    return svg, tw, [("whoosh", at), ("impact", at + .5)]


def iceberg(sid, at, label="", items=(), times=None, **_):
    """What everyone sees above the water, and the much bigger part below it."""
    hidden = list(items)[:4]
    svg = (f'<rect x="0" y="300" width="1400" height="460" fill="#0E2140" opacity=".75"/>'
           f'<line x1="0" y1="300" x2="1400" y2="300" stroke="{CYAN}" stroke-width="3" opacity=".8"/>'
           f'<path d="M600 300 L680 170 L760 210 L820 300 Z" fill="{WHITE}"/>'
           f'<path id="{sid}-deep" d="M600 300 L820 300 L1010 470 L930 700 L470 720 L360 520 Z" fill="#9CC3F5" opacity=".35"/>'
           + _t(700, 140, label, _fit(label, 700, 44), WHITE))
    tw = [f'tl.fromTo("#{sid}-deep",{{opacity:0}},{{opacity:.35,duration:.6}},{max(.3, at - .3):.3f});']
    for i, it in enumerate(hidden):
        y = 410 + i * 90
        svg += _t(690, y, it, _fit(it, 520, 46), GOLD, extra=f'id="{sid}-h{i}" opacity="0"')
        t = times[i] if times and i < len(times) else at + i * .5
        tw.append(f'tl.fromTo("#{sid}-h{i}",{{opacity:0,y:16}},{{opacity:1,y:0,duration:.35}},{t:.3f});')
    return svg, tw, [("riser", max(0, at - .5))]


def cycle(sid, at, items=(), times=None, **_):
    """A loop: each step leads to the next and back to the start; a light runs round it."""
    import math
    items = list(items)[:5] or ["Step"]
    n = len(items)
    cx, cy, r = 700, 380, 300
    svg = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#2A3042" stroke-width="10" stroke-dasharray="4 18"/>'
    tw = []
    for i, it in enumerate(items):
        a = -math.pi / 2 + 2 * math.pi * i / n
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        svg += _chip(sid, f"n{i}", x, y, it, size=_fit(it, 300, 40))
        t = times[i] if times and i < len(times) else .4 + i * max(.4, (at - .4) / n)
        tw.append(f'tl.fromTo("#{sid}-n{i}",{{scale:.5,opacity:0,transformOrigin:"50% 50%"}},{{scale:1,opacity:1,'
                  f'duration:.35,ease:"back.out(2)"}},{t:.3f});')
    svg += f'<circle id="{sid}-dot" cx="{cx}" cy="{cy - r}" r="16" fill="{GOLD}"/>'
    tw.append(f'tl.fromTo("#{sid}-dot",{{rotation:0,svgOrigin:"{cx} {cy}"}},{{rotation:360,svgOrigin:"{cx} {cy}",duration:2.4,repeat:3,ease:"none"}},{at:.3f});')
    return svg, tw, [("whoosh", at)]


DRAW = {"scales": scales, "unlock": unlock, "magnify": magnify, "funnel": funnel, "stack": stack, "gauge": gauge,
        "transform": transform, "iceberg": iceberg, "cycle": cycle}
