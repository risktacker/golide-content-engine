"""Goli's studio (owner 2026-11-11): the set the GOLIDE host talks from.

A 1920x1080 set drawn in SVG, in two layers so Goli sits between them:
- back: slatted wall with a warm LED uplight, GOLIDE neon sign, shelves (plant, books, award, glowing
  cube), a curved high-tech video wall that carries the scene's words and live-looking data, the chair;
- front: the desk with a gold edge light, laptop with the GOLIDE mark, mug, the podcast mic on a boom
  arm in front of him.
Everything is original and drawn in code. Ids are prefixed so several studio shots can share a page.
"""

from __future__ import annotations

from .mascot import logo_mark

W, H = 1920, 1080
DESK_Y = 772                      # desk top on screen
SEAT_X = 640                      # Goli's centre line

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


def back(sid: str) -> str:
    """Wall, neon sign, shelves, video wall and chair (behind Goli)."""
    slats = "".join(f'<rect x="{x}" y="0" width="58" height="{H}" fill="url(#st-slat)"/>'
                    f'<rect x="{x + 58}" y="0" width="8" height="{H}" fill="#070A12"/>' for x in range(0, W, 66))
    books = ""
    bx = 120
    for w_, h_, c in ((26, 92, "#E8462F"), (20, 104, "#2450E6"), (30, 86, "#F2C14E"), (22, 98, "#12A36B"), (18, 80, "#7B3FE4")):
        books += (f'<rect x="{bx}" y="{470 - h_}" width="{w_}" height="{h_}" rx="3" fill="{c}"/>'
                  f'<rect x="{bx + 3}" y="{470 - h_ + 10}" width="{w_ - 6}" height="5" fill="#fff" opacity=".35"/>')
        bx += w_ + 4
    bars = "".join(f'<rect id="{sid}-bar{i}" x="{1196 + i * 46}" y="{600 - h_}" width="30" height="{h_}" rx="6" '
                   f'fill="{"#F2C14E" if i == 5 else "#3D6CFF"}" opacity=".55"/>'
                   for i, h_ in enumerate((40, 56, 46, 74, 64, 100, 84)))
    ticks = "".join(f'<rect x="{1560 + i * 26}" y="{200 + (i % 3) * 4}" width="16" height="4" rx="2" fill="#3D6CFF" '
                    f'opacity="{.3 + .1 * (i % 4)}"/>' for i in range(9))
    return f"""<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" style="position:absolute;left:0;top:0">
<rect width="{W}" height="{H}" fill="url(#st-wall)"/>{slats}
<rect width="{W}" height="{H}" fill="url(#st-up)"/>
<rect y="{H - 40}" width="{W}" height="40" fill="#F2C14E" opacity=".25" filter="url(#st-blur)"/>
<ellipse cx="{SEAT_X}" cy="380" rx="460" ry="380" fill="url(#st-glowb)"/>
<g filter="url(#st-neon)" id="{sid}-neon">
  <rect x="70" y="110" width="430" height="120" rx="60" fill="none" stroke="#F2C14E" stroke-width="5" opacity=".9"/>
  {logo_mark(140, 170, 70, "#FFF4D6", "#F2C14E")}
  <text x="190" y="192" font-family="Poppins" font-weight="900" font-size="64" letter-spacing="6" fill="#FFF4D6">GOLIDE</text>
</g>
<g filter="url(#st-drop)">
  <rect x="96" y="470" width="300" height="14" rx="4" fill="#2A2F3D"/><rect x="96" y="640" width="300" height="14" rx="4" fill="#2A2F3D"/>
  {books}
  <path d="M290 470 L300 420 L340 420 L350 470 Z" fill="#E8C268"/><circle cx="320" cy="398" r="26" fill="#F2C14E"/>
  {logo_mark(320, 398, 30, "#0E1A4A", "#FFF4D6")}
  <rect x="120" y="580" width="60" height="60" rx="10" fill="#3D6CFF" opacity=".85"/><rect x="128" y="588" width="44" height="44" rx="6" fill="#8FB0FF" opacity=".5"/>
  <path d="M268 640 L276 590 L332 590 L340 640 Z" fill="#E9E2D3"/>
  <ellipse cx="290" cy="575" rx="22" ry="34" fill="url(#st-leaf)" transform="rotate(-25 290 575)"/>
  <ellipse cx="318" cy="566" rx="22" ry="40" fill="url(#st-leaf)"/>
  <ellipse cx="344" cy="578" rx="20" ry="32" fill="url(#st-leaf)" transform="rotate(25 344 578)"/>
</g>
<g filter="url(#st-drop)" id="{sid}-wall">
  <path d="M1110 110 Q1500 80 1860 120 L1860 640 Q1500 680 1110 650 Z" fill="#05070D" stroke="#2A3354" stroke-width="10"/>
  <path d="M1124 124 Q1500 96 1846 132 L1846 626 Q1500 664 1124 636 Z" fill="url(#st-screen)"/>
  <path d="M1124 124 Q1500 96 1846 132 L1846 200 Q1500 170 1124 190 Z" fill="#fff" opacity=".035"/>
  <circle cx="1160" cy="160" r="7" fill="#E8462F"/><text x="1176" y="167" font-family="Inter" font-weight="600" font-size="20" fill="#E8462F">LIVE</text>
  {ticks}{bars}
  <path id="{sid}-line" d="M1180 590 L1260 566 L1330 578 L1420 536 L1500 548 L1590 500 L1680 512 L1800 450" fill="none"
        stroke="#F2C14E" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="900" stroke-dashoffset="900"/>
  {logo_mark(1806, 594, 40, "#8FA0C8", "#F2C14E")}
</g>
<rect x="1100" y="660" width="770" height="40" fill="#3D6CFF" opacity=".22" filter="url(#st-blur)"/>
<g filter="url(#st-drop)">
  <path d="M{SEAT_X - 250} {DESK_Y} L{SEAT_X - 230} 330 Q{SEAT_X} 280 {SEAT_X + 230} 330 L{SEAT_X + 250} {DESK_Y} Z" fill="url(#st-chair)"/>
  <path d="M{SEAT_X - 212} {DESK_Y - 20} L{SEAT_X - 196} 360 Q{SEAT_X} 316 {SEAT_X + 196} 360 L{SEAT_X + 212} {DESK_Y - 20}"
        fill="none" stroke="#E8C268" stroke-width="4" opacity=".75"/>
</g>
</svg>"""


def front(sid: str) -> str:
    """Desk, laptop, mug and the podcast mic (in front of Goli)."""
    return f"""<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" style="position:absolute;left:0;top:0">
<g filter="url(#st-drop)">
  <path d="M-20 {DESK_Y} L{W + 20} {DESK_Y} L{W + 20} {DESK_Y + 30} L-20 {DESK_Y + 30} Z" fill="url(#st-top)"/>
  <rect x="-20" y="{DESK_Y + 30}" width="{W + 40}" height="{H - DESK_Y}" fill="url(#st-desk)"/>
  <rect id="{sid}-edge" x="-20" y="{DESK_Y + 28}" width="{W + 40}" height="5" fill="url(#st-edge)"/>
  <rect x="-20" y="{DESK_Y + 33}" width="{W + 40}" height="60" fill="#F2C14E" opacity=".12" filter="url(#st-blur)"/>
  {logo_mark(W / 2 + 330, DESK_Y + 150, 90, "#2E3445", "#8A6A22")}
</g>
<g filter="url(#st-drop)">
  <path d="M930 {DESK_Y + 4} L1210 {DESK_Y + 4} L1236 {DESK_Y + 22} L904 {DESK_Y + 22} Z" fill="#9AA1B1"/>
  <path d="M948 {DESK_Y + 4} L962 {DESK_Y - 186} L1178 {DESK_Y - 186} L1192 {DESK_Y + 4} Z" fill="url(#st-laptop)"/>
  <ellipse cx="1070" cy="{DESK_Y - 92}" rx="60" ry="60" fill="url(#st-glowg)"/>
  {logo_mark(1070, DESK_Y - 92, 74, "#F4F1EA", "#F2C14E")}
</g>
<g filter="url(#st-drop)">
  <rect x="230" y="{DESK_Y - 96}" width="78" height="96" rx="12" fill="#F4F1EA"/>
  <path d="M308 {DESK_Y - 76} Q348 {DESK_Y - 70} 340 {DESK_Y - 40} Q334 {DESK_Y - 18} 306 {DESK_Y - 22}" fill="none" stroke="#F4F1EA" stroke-width="12"/>
  {logo_mark(268, DESK_Y - 50, 40, "#16181F", "#E8C268")}
  <path id="{sid}-steam" d="M254 {DESK_Y - 110} Q244 {DESK_Y - 140} 258 {DESK_Y - 165} Q272 {DESK_Y - 190} 262 {DESK_Y - 215}"
        fill="none" stroke="#fff" stroke-width="6" stroke-linecap="round" opacity=".18"/>
</g>
<g filter="url(#st-drop)">
  <rect x="380" y="{DESK_Y - 6}" width="54" height="22" rx="6" fill="#16181F"/>
  <path d="M407 {DESK_Y - 6} L330 {DESK_Y - 150} L434 {DESK_Y - 195}" fill="none" stroke="url(#st-metal)" stroke-width="14" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="330" cy="{DESK_Y - 150}" r="12" fill="#3A3F4D"/>
  <g transform="rotate(25 455 {DESK_Y - 240})">
    <rect x="424" y="{DESK_Y - 340}" width="62" height="150" rx="31" fill="url(#st-mic)"/>
    <rect x="420" y="{DESK_Y - 296}" width="70" height="14" rx="7" fill="#E8C268"/>
    <path d="M430 {DESK_Y - 328} L480 {DESK_Y - 328} M430 {DESK_Y - 312} L480 {DESK_Y - 312}" stroke="#555B6B" stroke-width="3"/>
  </g>
</g>
</svg>"""


def motion(sid: str, t0: float, dur: float) -> list[str]:
    """Life in the set: chart draws, bars breathe, LED edge pulses, steam rises, a slow camera push."""
    tw = [f'tl.to("#{sid}-line",{{attr:{{"stroke-dashoffset":0}},duration:{min(2.5, dur * .6):.2f},ease:"power2.inOut"}},{t0 + .4:.3f});']
    for i in range(7):
        tw.append(f'tl.fromTo("#{sid}-bar{i}",{{scaleY:.3,transformOrigin:"50% 100%"}},{{scaleY:1,duration:.7,'
                  f'ease:"back.out(1.6)"}},{t0 + .3 + .08 * i:.3f});')
    n = max(1, int(dur / 1.4))
    tw.append(f'tl.to("#{sid}-edge",{{opacity:.55,duration:.7,yoyo:true,repeat:{2 * n - 1},ease:"sine.inOut"}},{t0:.3f});')
    tw.append(f'tl.fromTo("#{sid}-steam",{{y:0,opacity:.18}},{{y:-40,opacity:0,duration:{min(3.0, dur):.2f},ease:"none"}},{t0:.3f});')
    return tw
