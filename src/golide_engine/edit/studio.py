"""Goli's studio (owner 2026-11-11): the set the GOLIDE host talks from.

2026-11-21: the set is the real 3D studio from Blender (goli3d/studio_model.py, rendered once to
assets/goli3d/studio/). There is no flat fallback: missing plates stop the run before rendering. Two layers so Goli
sits between them:
- back: slatted wall with a warm LED uplight, GOLIDE neon sign, shelves (plant, books, award, glowing
  cube), a curved high-tech video wall that carries the scene's words and live-looking data, the chair;
- front: the desk with a gold edge light, laptop with the GOLIDE mark, mug, the podcast mic on a boom
  arm in front of him.
Everything is original and drawn in code. Ids are prefixed so several studio shots can share a page.
"""


from __future__ import annotations

from pathlib import Path

from .mascot import logo_mark

W, H = 1920, 1080
DESK_Y = 772                      # desk top on screen (long)
SEAT_X = 640                      # Goli's centre line (long)

# Where each piece of the set sits per format. Pieces are drawn in the long frame's coordinates and
# moved as groups: (translate x, translate y, scale). The Short stacks the set: video wall on top,
# Goli at the desk below it.
LAYOUTS = {
    "long": {"w": 1920, "h": 1080, "desk_y": 772, "seat_x": 640, "size": 820,
             "wall": (0, 0, 1.0), "neon": (0, 0, 1.0), "shelf": (0, 0, 1.0),
             "words": (1190, 230, 600, 72)},
    "short": {"w": 1080, "h": 1920, "desk_y": 1560, "seat_x": 540, "size": 900,
              "wall": (-1361, 48, 1.28), "neon": None, "shelf": (-80, 540, 1.0),
              "words": (130, 300, 820, 92)},
}


LAYOUTS["lower"] = {"w": 1080, "h": 1920, "desk_y": 1752, "seat_x": 540, "size": 640, "top": 1250}


# 2026-11-21 (owner, approved): the real 3D studio from Blender (goli3d/studio_model.py). Rendered once as pictures
# (assets/goli3d/studio/<fmt>/back.webp behind Goli, front.webp in front of him); the live parts stay layers on top:
# the TV's chart, LIVE and words, the steam over the mug and the table's pulsing gold edge.
PLATES = Path(__file__).resolve().parents[3] / "assets" / "goli3d" / "studio"


def plates(fmt: str) -> dict | None:
    f = PLATES / fmt / "meta.json"
    if not f.exists():
        return None
    import json
    return json.loads(f.read_text())


def need(fmt: str) -> dict:
    """The 3D studio for this format, or a clear stop before rendering (owner 2026-11-21: no fallbacks)."""
    m = plates(fmt)
    files = [PLATES / fmt / f for f in ("back.webp", "front.webp")]
    if not m or not all(f.exists() for f in files):
        raise FileNotFoundError(f"3D studio plates missing for {fmt!r} in {PLATES}; run goli3d-library.yml kind=studio")
    return m


def _img(path: Path, at, asset, w=None, h=None, extra="") -> str:
    from PIL import Image
    with Image.open(path) as im:
        iw, ih = im.size
    return (f'<img src="{asset(path)}" style="position:absolute;left:{at[0]}px;top:{at[1]}px;'
            f'width:{w or iw}px;height:{h or ih}px{extra}">')


def layout(fmt: str) -> dict:
    return LAYOUTS[fmt] if fmt in ("short", "lower") else LAYOUTS["long"]


def screen_rect(fmt: str) -> tuple[float, float, float, float]:
    """The TV screen on the frame (x0, y0, x1, y1), from the rendered set (owner 2026-11-25: the boardroom screen)."""
    m = plates("short" if fmt == "short" else "long") or {}
    pts = m.get("screen") or [[1124, 124], [1846, 124], [1846, 636], [1124, 636]]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def lower_back(sid: str, asset=None) -> str:
    """The Short's lower third: a slice of the studio behind Goli while the proof plays on top."""
    m = need("lower")
    return f'<div id="{sid}-low">{_img(PLATES / "lower" / "back.webp", m["back_at"], asset)}</div>'

DEFS = """<svg width="0" height="0" style="position:absolute"><defs>
<linearGradient id="st-wall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0A0E1A"/><stop offset=".7" stop-color="#121A30"/><stop offset="1" stop-color="#1A1408"/></linearGradient>
<linearGradient id="st-slat" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#151C30"/><stop offset=".5" stop-color="#1F2942"/><stop offset="1" stop-color="#121829"/></linearGradient>
<linearGradient id="st-up" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#F2C14E" stop-opacity=".55"/><stop offset=".55" stop-color="#F2C14E" stop-opacity="0"/></linearGradient>
<linearGradient id="st-desk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2A2F3D"/><stop offset=".08" stop-color="#1A1E28"/><stop offset="1" stop-color="#0B0D12"/></linearGradient>
<linearGradient id="st-top" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3A4256"/><stop offset="1" stop-color="#232837"/></linearGradient>
<linearGradient id="st-edge" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#F2C14E" stop-opacity="0"/><stop offset=".2" stop-color="#FFE7A3"/><stop offset=".8" stop-color="#FFE7A3"/><stop offset="1" stop-color="#F2C14E" stop-opacity="0"/></linearGradient>
<linearGradient id="st-screen" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0E1B3D"/><stop offset="1" stop-color="#050913"/></linearGradient>
<linearGradient id="st-metal" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#2B2F3A"/><stop offset=".5" stop-color="#6A7184"/><stop offset="1" stop-color="#22252E"/></linearGradient>
<linearGradient id="st-mic" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#15171D"/><stop offset=".45" stop-color="#3A3F4D"/><stop offset="1" stop-color="#101217"/></linearGradient>
<linearGradient id="st-chair" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#101219"/><stop offset=".5" stop-color="#262B38"/><stop offset="1" stop-color="#0E1016"/></linearGradient>
<linearGradient id="st-laptop" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#C9CED8"/><stop offset="1" stop-color="#8C93A3"/></linearGradient>
<radialGradient id="st-glowb" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#3D6CFF" stop-opacity=".55"/><stop offset="1" stop-color="#3D6CFF" stop-opacity="0"/></radialGradient>
<radialGradient id="st-glowg" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#F2C14E" stop-opacity=".5"/><stop offset="1" stop-color="#F2C14E" stop-opacity="0"/></radialGradient>
<radialGradient id="st-leaf" cx=".4" cy=".3" r=".8"><stop offset="0" stop-color="#5BE39A"/><stop offset="1" stop-color="#127A47"/></radialGradient>
<filter id="st-blur"><feGaussianBlur stdDeviation="18"/></filter>
<filter id="st-neon" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="st-drop" x="-20%" y="-20%" width="140%" height="160%"><feDropShadow dx="0" dy="14" stdDeviation="14" flood-opacity=".6"/></filter>
</defs></svg>"""


def back(sid: str, fmt: str = "long", asset=None) -> str:
    """Wall, neon sign, shelves, video wall and chair (behind Goli): the 3D studio plate and the TV's live content."""
    return back3d(sid, fmt, need(fmt), asset)


def front(sid: str, fmt: str = "long", asset=None) -> str:
    """The table, laptop, mug and the podcast mic (in front of Goli): the 3D studio plate, steam and the lit edge."""
    return front3d(sid, fmt, need(fmt), asset)


def back3d(sid: str, fmt: str, m: dict, asset) -> str:
    """The 3D set behind Goli, with the TV's live content (chart, bars, LIVE) drawn on its screen."""
    L = layout(fmt)
    W, H = L["w"], L["h"]
    # owner 2026-11-25: no decoration chart on the TV ("that nonsensical graph that has no meaning"): only LIVE and
    # the logo; the screen itself shows the real thing being said (editor._screen_pictures)
    x0, y0, x1, y1 = screen_rect(fmt)
    screen = (f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" style="position:absolute;left:0;top:0">'
              f'<g id="{sid}-wall">'
              f'<circle cx="{x0 + 30}" cy="{y0 + 30}" r="7" fill="#E8462F"/><text x="{x0 + 46}" y="{y0 + 37}" font-family="Inter" '
              f'font-weight="600" font-size="20" fill="#E8462F">LIVE</text>{logo_mark(x1 - 36, y1 - 36, 34, "#8FA0C8", "#F2C14E")}'
              f'</g><g id="{sid}-neon"></g></svg>')
    return _img(PLATES / fmt / "back.webp", [0, 0], asset, W, H) + screen


def front3d(sid: str, fmt: str, m: dict, asset) -> str:
    """The 3D table in front of Goli, the steam over the mug and the table's pulsing gold edge."""
    L = layout(fmt)
    W, H = L["w"], L["h"]
    mx, my = m["mug_top"]
    x0, ey, x1, _ = m["edge"]
    steam = (f'<path id="{sid}-steam" d="M{mx - 8:.0f} {my - 8:.0f} Q{mx - 18:.0f} {my - 38:.0f} {mx - 4:.0f} {my - 63:.0f} '
             f'Q{mx + 10:.0f} {my - 88:.0f} {mx:.0f} {my - 113:.0f}" fill="none" stroke="#fff" stroke-width="6" '
             f'stroke-linecap="round" opacity=".18"/>')
    edge = (f'<rect id="{sid}-edge" x="{max(0, x0):.0f}" y="{ey - 3:.0f}" width="{min(W, x1) - max(0, x0):.0f}" height="6" '
            f'fill="url(#st-edge)" opacity=".35" style="mix-blend-mode:screen"/>') if ey < H else f'<g id="{sid}-edge"></g>'
    return (_img(PLATES / fmt / "front.webp", m["front_at"], asset)
            + f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" style="position:absolute;left:0;top:0">{steam}{edge}</svg>')


def motion(sid: str, t0: float, dur: float) -> list[str]:
    """Life in the set: LED edge pulses, steam rises, a slow camera push (the TV's chart is gone, owner 2026-11-25)."""
    tw = []
    n = max(1, int(dur / 1.4))
    tw.append(f'tl.to("#{sid}-edge",{{opacity:.55,duration:.7,yoyo:true,repeat:{2 * n - 1},ease:"sine.inOut"}},{t0:.3f});')
    tw.append(f'tl.fromTo("#{sid}-steam",{{y:0,opacity:.18}},{{y:-40,opacity:0,duration:{min(3.0, dur):.2f},ease:"none"}},{t0:.3f});')
    return tw
