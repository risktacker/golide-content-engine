"""Pango, the GOLIDE host (owner approved the design 2026-11-11).

An original pangolin character in a GOLIDE hoodie with gold glasses, drawn entirely in code (SVG with
3D-style shading), so it costs nothing and nobody else owns it. He replaces the presenter that big
channels film or pay an AI avatar for: he talks with the owner's own voice (lip sync from Rhubarb Lip
Sync, MIT), points at the proof, reacts to facts and asks viewers to follow.

`character(pose, expression, uid)` returns one SVG group (viewBox 0 0 400 540) with every mouth shape
and the blink lids inside it, ids prefixed by `uid`, so the composer only switches what is shown.
Mouth shapes follow Rhubarb: A closed (M B P), B teeth (most consonants), C open (EH AE), D wide (AA),
E round (AO ER), F pucker (UW OW W), G F/V, H L, X rest.
"""

from __future__ import annotations

VIEW = (400, 540)
MOUTHS = "ABCDEFGHX"

DEFS = """<defs>
<radialGradient id="pg-plate" cx=".35" cy=".25" r=".9"><stop offset="0" stop-color="#FFD27A"/><stop offset=".45" stop-color="#F5A623"/><stop offset="1" stop-color="#B85F0C"/></radialGradient>
<radialGradient id="pg-headbase" cx=".4" cy=".3" r=".8"><stop offset="0" stop-color="#F7B347"/><stop offset="1" stop-color="#A9520A"/></radialGradient>
<radialGradient id="pg-mask" cx=".45" cy=".3" r=".8"><stop offset="0" stop-color="#FFF6E6"/><stop offset=".7" stop-color="#FFE2B8"/><stop offset="1" stop-color="#E9B97C"/></radialGradient>
<radialGradient id="pg-nose" cx=".35" cy=".3" r=".8"><stop offset="0" stop-color="#6B4A3A"/><stop offset="1" stop-color="#1C110C"/></radialGradient>
<radialGradient id="pg-eye" cx=".4" cy=".35" r=".75"><stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#DCE3EE"/></radialGradient>
<radialGradient id="pg-iris" cx=".4" cy=".35" r=".7"><stop offset="0" stop-color="#8A5A2B"/><stop offset=".6" stop-color="#4A2C12"/><stop offset="1" stop-color="#1A0E06"/></radialGradient>
<linearGradient id="pg-hoodie" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#4C7DFF"/><stop offset=".55" stop-color="#2450E6"/><stop offset="1" stop-color="#14309A"/></linearGradient>
<linearGradient id="pg-sleeve" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#1A3BB8"/><stop offset=".45" stop-color="#3D6CFF"/><stop offset="1" stop-color="#1A3BB8"/></linearGradient>
<linearGradient id="pg-gold" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFE7A3"/><stop offset=".5" stop-color="#F2C14E"/><stop offset="1" stop-color="#B07D1C"/></linearGradient>
<radialGradient id="pg-paw" cx=".4" cy=".3" r=".8"><stop offset="0" stop-color="#FFE9C8"/><stop offset="1" stop-color="#D99A55"/></radialGradient>
<linearGradient id="pg-shoe" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#C9CED8"/></linearGradient>
<radialGradient id="pg-shadow"><stop offset="0" stop-color="#000" stop-opacity=".6"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
<filter id="pg-drop" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="8" stdDeviation="7" flood-color="#000" flood-opacity=".45"/></filter>
<filter id="pg-ao" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="3" stdDeviation="3" flood-color="#5A2A04" flood-opacity=".55"/></filter>
<clipPath id="pg-headclip"><ellipse cx="200" cy="150" rx="104" ry="86"/></clipPath>
</defs>"""

# arms: (left upper, left fore, right upper, right fore) in degrees; positive swings toward screen left.
# hand: what the right paw does (None, "point", "thumb"). The left/right are the viewer's.
POSES: dict[str, dict] = {
    "talk":     {"arms": (14, -12, -14, 12), "hand": None, "tilt": 0, "face": "neutral"},
    "explain":  {"arms": (34, -78, -34, 78), "hand": None, "tilt": 0, "face": "neutral"},
    "point":    {"arms": (14, -12, -112, -8), "hand": "point", "tilt": -4, "face": "sure", "look": (8, -3)},
    "point_up": {"arms": (14, -12, -168, 4), "hand": "point", "tilt": -3, "face": "sure", "look": (4, -7)},
    "point_left": {"arms": (112, 8, -14, 12), "hand": "point_left", "tilt": 4, "face": "sure", "look": (-8, -3)},
    "shock":    {"arms": (140, 22, -140, -22), "hand": None, "tilt": 0, "face": "shock"},
    "think":    {"arms": (14, -12, 40, 113), "hand": None, "tilt": 6, "face": "think", "look": (-5, -7)},
    "thumbs_up": {"arms": (14, -12, -36, -104), "hand": "thumb", "tilt": 4, "face": "happy"},
    "shrug":    {"arms": (58, -104, -58, 104), "hand": None, "tilt": 8, "face": "skeptic"},
    "wave":     {"arms": (14, -12, -128, -30), "hand": None, "tilt": -3, "face": "happy"},
}
FACES = {  # brow lift, brow tilt, eye scale, lid line, default look
    "neutral": (0, 0, 1.0, True, (3, 2)),
    "sure": (-4, -10, 1.0, True, (6, -2)),
    "shock": (-14, 0, 1.22, False, (0, 0)),
    "think": (-2, 12, 1.0, True, (-5, -7)),
    "happy": (-5, -4, 1.0, False, (2, 1)),
    "skeptic": (-8, 16, 1.0, True, (4, 0)),
}


def _plate(cx, cy, w, h):
    return (f'<path d="M{cx - w / 2} {cy} Q{cx - w * .46} {cy + h * .7} {cx} {cy + h} Q{cx + w * .46} {cy + h * .7} '
            f'{cx + w / 2} {cy} Q{cx} {cy - h * .25} {cx - w / 2} {cy} Z" fill="url(#pg-plate)" stroke="#8A4206" '
            f'stroke-width="2.5" filter="url(#pg-ao)"/>'
            f'<path d="M{cx - w * .28} {cy + h * .25} Q{cx - w * .1} {cy + h * .12} {cx + w * .05} {cy + h * .18}" '
            f'stroke="#FFF1C9" stroke-width="3" stroke-linecap="round" fill="none" opacity=".8"/>')


def _paw(hand: str | None, w: float) -> str:
    r = w * .52
    claws = "".join(f'<path d="M{-w * .08 + dx} {r * .7} L{dx} {r * 1.25} L{w * .08 + dx} {r * .7} Z" fill="#3A2416"/>'
                    for dx in (-r * .55, 0, r * .55))
    extra = ""
    if hand in ("point", "point_left"):
        extra = (f'<rect x="{-w * .15}" y="{r * .2}" width="{w * .3}" height="{w * 1.15}" rx="{w * .15}" fill="url(#pg-paw)" '
                 f'stroke="#B9783A" stroke-width="2"/><path d="M{-w * .09} {r * .2 + w * 1.12} L0 {r * .2 + w * 1.4} '
                 f'L{w * .09} {r * .2 + w * 1.12} Z" fill="#3A2416"/>')
        claws = ""
    if hand == "thumb":
        extra = (f'<rect x="{-w * .15}" y="{-r * 1.9}" width="{w * .3}" height="{w * 1.0}" rx="{w * .15}" fill="url(#pg-paw)" '
                 f'stroke="#B9783A" stroke-width="2"/>')
    return f'{extra}<circle cx="0" cy="0" r="{r}" fill="url(#pg-paw)"/>{claws}'


def _arm(x, y, upper, fore, hand, w=46, l1=54, l2=50):
    # thumb points up on screen whatever the arm angle: counter-rotate the paw
    paw_turn = -(upper + fore) if hand == "thumb" else 0
    return (f'<g transform="translate({x} {y}) rotate({upper})" filter="url(#pg-drop)">'
            f'<rect x="{-w / 2}" y="{-w * .25}" width="{w}" height="{l1 + w * .5}" rx="{w / 2}" fill="url(#pg-sleeve)"/>'
            f'<g transform="translate(0 {l1}) rotate({fore})">'
            f'<rect x="{-w * .46}" y="{-w * .3}" width="{w * .92}" height="{l2 + w * .3}" rx="{w * .46}" fill="url(#pg-sleeve)"/>'
            f'<rect x="{-w * .52}" y="{l2 - w * .32}" width="{w * 1.04}" height="{w * .34}" rx="{w * .17}" fill="#1A3BB8"/>'
            f'<g transform="translate(0 {l2 + w * .2}) rotate({paw_turn})">{_paw(hand, w)}</g></g></g>')


def _mouths(uid: str, default: str) -> str:
    """All nine Rhubarb shapes stacked; only one is visible at a time."""
    ink, lip, tongue, teeth = "#4A1A14", "#4A1A14", "#FF7A88", "#FFFFFF"
    shapes = {
        "A": f'<path d="M184 268 Q200 274 216 268" stroke="{lip}" stroke-width="6" fill="none" stroke-linecap="round"/>',
        "B": (f'<path d="M180 264 Q200 282 220 264 Q200 268 180 264 Z" fill="{ink}"/>'
              f'<path d="M184 265 L216 265 L213 270 L187 270 Z" fill="{teeth}"/>'),
        "C": (f'<path d="M178 262 Q200 292 222 262 Q200 268 178 262 Z" fill="{ink}"/>'
              f'<path d="M188 276 Q200 284 212 276 Q200 272 188 276 Z" fill="{tongue}"/>'),
        "D": (f'<path d="M176 260 Q200 304 224 260 Q200 266 176 260 Z" fill="{ink}"/>'
              f'<path d="M182 261 L218 261 L215 267 L185 267 Z" fill="{teeth}"/>'
              f'<path d="M186 284 Q200 296 214 284 Q200 278 186 284 Z" fill="{tongue}"/>'),
        "E": f'<ellipse cx="200" cy="272" rx="15" ry="13" fill="{ink}"/><ellipse cx="200" cy="278" rx="9" ry="5" fill="{tongue}"/>',
        "F": f'<ellipse cx="200" cy="271" rx="9" ry="9" fill="{ink}"/><ellipse cx="200" cy="271" rx="11" ry="11" fill="none" stroke="#C9714A" stroke-width="3"/>',
        "G": (f'<path d="M182 266 Q200 278 218 266 Q200 270 182 266 Z" fill="{ink}"/>'
              f'<path d="M186 264 L214 264 L212 270 L188 270 Z" fill="{teeth}"/>'),
        "H": (f'<path d="M180 262 Q200 290 220 262 Q200 268 180 262 Z" fill="{ink}"/>'
              f'<path d="M192 266 Q200 262 208 266 L206 276 L194 276 Z" fill="{tongue}"/>'),
        "X": f'<path d="M182 266 Q200 278 218 266" stroke="{lip}" stroke-width="6" fill="none" stroke-linecap="round"/>',
    }
    return "".join(f'<g id="{uid}-m{k}" style="opacity:{1 if k == default else 0}">{v}</g>' for k, v in shapes.items())


def character(pose: str = "talk", uid: str = "pg", mouth: str = "X", expression: str | None = None,
              look: tuple[float, float] | None = None, blink: bool = False) -> str:
    """Pango in one pose. Ids: {uid}-head (for nods), {uid}-m<shape> (mouths), {uid}-lid (blink)."""
    p = POSES[pose]
    lift, tilt, es, lid_line, face_look = FACES[expression or p["face"]]
    look = look or p.get("look") or face_look
    la, lf, ra, rf = p["arms"]
    g = '<ellipse cx="200" cy="520" rx="140" ry="18" fill="url(#pg-shadow)"/>'
    for x in (164, 236):
        g += (f'<rect x="{x - 20}" y="430" width="40" height="70" rx="20" fill="#C46A12"/>'
              f'<path d="M{x - 34} 512 Q{x - 34} 488 {x - 10} 486 L{x + 22} 486 Q{x + 38} 490 {x + 36} 512 Z" '
              f'fill="url(#pg-shoe)" filter="url(#pg-drop)"/><rect x="{x - 34}" y="506" width="70" height="8" rx="4" fill="url(#pg-gold)"/>'
              f'<path d="M{x - 12} 494 L{x + 16} 494" stroke="#2450E6" stroke-width="5" stroke-linecap="round"/>')
    left_hand = "point" if p["hand"] == "point_left" else None
    g += _arm(104, 338, la, lf, left_hand)
    g += ('<path d="M92 356 Q96 300 200 294 Q304 300 308 356 L304 452 Q200 478 96 452 Z" fill="url(#pg-hoodie)" filter="url(#pg-drop)"/>'
          '<path d="M118 372 Q130 318 172 308" stroke="#8FB0FF" stroke-width="8" fill="none" stroke-linecap="round" opacity=".55"/>'
          '<path d="M150 410 L250 410 L240 446 L160 446 Z" fill="#1E43C8" opacity=".9"/>'
          '<path d="M148 300 Q200 340 252 300 Q240 318 200 324 Q160 318 148 300 Z" fill="#1A3BB8"/>'
          '<path d="M178 318 L174 366" stroke="url(#pg-gold)" stroke-width="5" stroke-linecap="round"/>'
          '<path d="M222 318 L226 366" stroke="url(#pg-gold)" stroke-width="5" stroke-linecap="round"/>'
          '<circle cx="174" cy="370" r="6" fill="url(#pg-gold)"/><circle cx="226" cy="370" r="6" fill="url(#pg-gold)"/>'
          '<circle cx="200" cy="380" r="25" fill="url(#pg-gold)" filter="url(#pg-drop)"/>'
          '<text x="200" y="391" text-anchor="middle" font-family="Poppins" font-weight="900" font-size="29" fill="#0E1A4A">G</text>')
    for (x, y, r) in [(128, 302, -32), (272, 302, 32)]:       # gold scale plates on the shoulders
        g += f'<g transform="rotate({r} {x} {y})">{_plate(x, y - 14, 46, 44)}</g>'
    h = f'<g id="{uid}-head" transform="rotate({p["tilt"]} 200 300)">'
    for sx in (-1, 1):
        h += (f'<ellipse cx="{200 + sx * 88}" cy="104" rx="20" ry="24" fill="url(#pg-headbase)" filter="url(#pg-drop)"/>'
              f'<ellipse cx="{200 + sx * 86}" cy="106" rx="10" ry="13" fill="#FFC9A0"/>')
    h += '<ellipse cx="200" cy="150" rx="104" ry="86" fill="url(#pg-headbase)" filter="url(#pg-drop)"/>'
    crown = "".join(_plate(x, y, w, 52) for (y, xs, w) in
                    [(112, (112, 156, 200, 244, 288), 50), (90, (134, 178, 222, 266), 50), (68, (156, 200, 244), 50),
                     (50, (178, 222), 46)] for x in xs)
    h += f'<g clip-path="url(#pg-headclip)">{crown}</g>'
    h += ('<path d="M104 168 Q104 132 150 128 Q200 122 250 128 Q296 132 296 168 Q296 214 274 240 Q256 280 238 300 '
          'Q200 320 162 300 Q144 280 126 240 Q104 214 104 168 Z" fill="url(#pg-mask)" filter="url(#pg-ao)"/>')
    h += ('<ellipse cx="200" cy="248" rx="22" ry="14" fill="url(#pg-nose)"/>'
          '<ellipse cx="193" cy="243" rx="7" ry="4" fill="#fff" opacity=".55"/>')
    h += _mouths(uid, mouth)
    lids = ""
    for s in (-1, 1):
        x = 200 + s * 40
        h += (f'<ellipse cx="{x}" cy="176" rx="{19 * es}" ry="{21 * es}" fill="url(#pg-eye)"/>'
              f'<circle cx="{x + look[0]}" cy="{178 + look[1]}" r="{12 * min(es, 1.05)}" fill="url(#pg-iris)"/>'
              f'<circle cx="{x + look[0]}" cy="{178 + look[1]}" r="6.5" fill="#0B0603"/>'
              f'<circle cx="{x + look[0] + 4}" cy="{178 + look[1] - 5}" r="4" fill="#fff"/>')
        if lid_line:
            h += f'<path d="M{x - 19 * es} 168 Q{x} 157 {x + 19 * es} 168 L{x + 19 * es} 160 L{x - 19 * es} 160 Z" fill="#FFE9C8"/>'
        lids += f'<ellipse cx="{x}" cy="176" rx="{21 * es}" ry="{23 * es}" fill="#F6D6A8"/>'
        h += (f'<path d="M{x - 26} {140 + lift} Q{x} {128 + lift} {x + 26} {138 + lift} L{x + 24} {149 + lift} '
              f'Q{x} {141 + lift} {x - 24} {152 + lift} Z" fill="#5A2A04" '
              f'transform="rotate({s * (tilt + 6)} {x} {142 + lift})"/>')
    h += (f'<g id="{uid}-lid" style="transform-origin:200px 176px;transform-box:view-box" '
          f'transform="scale(1 {1 if blink else 0.001})">{lids}</g>')
    h += ('<g filter="url(#pg-drop)"><circle cx="160" cy="176" r="33" fill="#fff" fill-opacity=".08" stroke="url(#pg-gold)" stroke-width="7"/>'
          '<circle cx="240" cy="176" r="33" fill="#fff" fill-opacity=".08" stroke="url(#pg-gold)" stroke-width="7"/>'
          '<path d="M193 172 Q200 164 207 172" stroke="url(#pg-gold)" stroke-width="6" fill="none"/>'
          '<path d="M127 170 L112 162 M273 170 L288 162" stroke="url(#pg-gold)" stroke-width="6" stroke-linecap="round"/></g>'
          '<path d="M140 156 Q150 148 162 150" stroke="#fff" stroke-width="5" stroke-linecap="round" fill="none" opacity=".7"/>'
          '<path d="M220 156 Q230 148 242 150" stroke="#fff" stroke-width="5" stroke-linecap="round" fill="none" opacity=".7"/>')
    h += "</g>"
    right_hand = p["hand"] if p["hand"] in ("point", "thumb") else None
    return g + h + _arm(296, 338, ra, rf, right_hand)


def svg(pose: str = "talk", width: int = 400, mouth: str = "X", **kw) -> str:
    """A standalone SVG of Pango (for stills, thumbnails and checks)."""
    w, h = VIEW
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{width * h / w:.0f}" viewBox="0 0 {w} {h}">'
            f'{DEFS}{character(pose, mouth=mouth, **kw)}</svg>')
