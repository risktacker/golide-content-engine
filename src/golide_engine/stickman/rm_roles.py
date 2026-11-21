"""Who a character is (owner 2026-11-21: "soldiers, workforce, corporate, woman..."): a cast "role" dresses the kit's
own puppet for the job. The base (outfit, colours, hair) goes into the cast before the kit builds the look
(longform.apply_roles); the job's gear (helmet, hard hat and hi-vis vest, stethoscope, badge, crown...) is drawn on
top of the kit's draw_char by install() in the kit's process. The puppet stays the kit's; no likeness of anyone.
"""
from __future__ import annotations

ROLES: dict[str, dict] = {
    "soldier": {"outfit": "sweater", "color": "#5A6B3A", "hair": "short"},
    "worker": {"outfit": "tshirt", "color": "#3B6EA8"},
    "builder": {"outfit": "tshirt", "color": "#8A6A4A"},
    "miner": {"outfit": "tshirt", "color": "#4A4E5A"},
    "corporate": {"outfit": "suit", "color": "#2E3448", "tie": "#A8232B", "hair": "slick"},
    "businesswoman": {"outfit": "suit", "color": "#4A3A5A", "tie": "none", "hair": "bun"},
    "woman": {"outfit": "dress", "color": "#C2563A", "hair": "long"},
    "doctor": {"outfit": "suit", "color": "#F4F4F2", "shirt": "#BFE3F2", "tie": "#3B6EA8"},
    "nurse": {"outfit": "tshirt", "color": "#6FB8B0", "hair": "bun"},
    "scientist": {"outfit": "suit", "color": "#F4F4F2", "shirt": "#BFE3F2", "tie": "none", "glasses": True},
    "police": {"outfit": "suit", "color": "#1E2A4A", "shirt": "#BFD0E8", "tie": "#1E2A4A"},
    "pilot": {"outfit": "suit", "color": "#1E2A4A", "shirt": "#F4F4F2", "tie": "#1C1C22"},
    "chef": {"outfit": "tshirt", "color": "#F4F4F2"},
    "judge": {"outfit": "sweater", "color": "#1C1C22"},
    "astronaut": {"outfit": "tshirt", "color": "#F4F4F2"},
    "farmer": {"outfit": "tshirt", "color": "#B8242F"},
    "firefighter": {"outfit": "tshirt", "color": "#C9A040"},
    "king": {"outfit": "suit", "color": "#6A2A8A", "tie": "#D0A548"},
    "queen": {"outfit": "dress", "color": "#6A2A8A", "hair": "long"},
    "graduate": {"outfit": "sweater", "color": "#1C1C22"},
    "hacker": {"outfit": "hoodie", "color": "#1C1C22", "hair": "short"},
    "student": {"outfit": "hoodie", "color": "#3E9A56"},
}
HEADWEAR = ("helmet", "hardhat", "chef", "cap_police", "cap_pilot", "straw", "crown", "mortarboard", "firehelmet",
            "bubble", "headscarf", "beanie")
ROLE_HEAD = {"soldier": "helmet", "worker": "hardhat", "builder": "hardhat", "miner": "hardhat", "chef": "chef",
             "police": "cap_police", "pilot": "cap_pilot", "farmer": "straw", "king": "crown", "queen": "crown",
             "graduate": "mortarboard", "firefighter": "firehelmet", "astronaut": "bubble", "hacker": "beanie"}


def apply_roles(story: dict) -> list[str]:
    """Fill each cast member's base look from its role (what the writer set itself wins). Returns unknown roles."""
    unknown = []
    for d in (story.get("cast") or {}).values():
        if not isinstance(d, dict) or not d.get("role"):
            continue
        base = ROLES.get(str(d["role"]).lower())
        if base is None:
            unknown.append(str(d["role"]))
            d.pop("role")
            continue
        d["role"] = str(d["role"]).lower()
        for k, v in base.items():
            d.setdefault(k, v)
        if d["role"] in ROLE_HEAD:
            d.setdefault("hat", "none")         # the kit's own hats off; our headwear goes on instead
    return unknown


# ---------------------------------------------------------------- drawing (kit process only)
def install(shots_module) -> None:
    import math
    import skia
    from engine import kit as K

    BT, BB, R, HCY = K.BODY_TOP, K.BODY_BOT, K.HEAD_R, K.HEAD_CY
    original = shots_module.draw_char
    body_rr = skia.RRect.MakeRectXY(skia.Rect(-84, BT, 84, BB), 66, 72)

    def body_gear(c, role, spec, lw):
        body = skia.Path(); body.addRRect(body_rr)
        c.save(); c.clipPath(body, doAntiAlias=True)
        if role == "soldier":
            for (x, y, w, h, colr) in ((-60, BT + 40, 50, 30, "#3E4A2A"), (20, BT + 90, 60, 34, "#7A7A4A"), (-30, BT + 150, 70, 30, "#3E4A2A"),
                                       (40, BT + 20, 40, 26, "#7A7A4A"), (-80, BT + 110, 40, 40, "#7A7A4A")):
                c.drawOval(skia.Rect(x, y, x + w, y + h), K.fp(colr))
            c.drawRect(skia.Rect(-90, BB - 46, 90, BB - 26), K.fp("#2A2A1E"))
        elif role in ("worker", "builder", "miner"):
            for sx in (-1, 1):
                c.drawRect(skia.Rect(min(sx * 84, sx * 26), BT, max(sx * 84, sx * 26), BB), K.fp("#FF8A1E"))
                for yy in (BT + 80, BT + 140): c.drawRect(skia.Rect(min(sx * 84, sx * 26), yy, max(sx * 84, sx * 26), yy + 14), K.fp("#E8ECF2"))
        elif role == "firefighter":
            for yy in (BT + 90, BT + 160): c.drawRect(skia.Rect(-90, yy, 90, yy + 16), K.fp("#F2E24A"))
            c.drawRect(skia.Rect(-90, yy + 4, 90, yy + 10), K.fp("#E8ECF2"))
        elif role == "farmer":
            for k in range(-4, 5):
                c.drawLine(k * 24, BT, k * 24, BB, K.ink(3, "#7A1A22")); c.drawLine(-90, BT + 30 + k * 24 + 90, 90, BT + 30 + k * 24 + 90, K.ink(3, "#7A1A22"))
        c.restore()
        if role in ("doctor", "scientist"):      # lab-coat pockets and, for the doctor, a stethoscope
            K.rect(c, 30, BT + 70, 64, BT + 96, spec["suit"], lw * .5)
            if role == "doctor":
                p = skia.Path(); p.moveTo(-30, BT + 4); p.cubicTo(-46, BT + 70, -20, BT + 110, 0, BT + 120); c.drawPath(p, K.ink(lw * .7, "#3A3F4C"))
                p2 = skia.Path(); p2.moveTo(30, BT + 4); p2.cubicTo(46, BT + 70, 20, BT + 110, 0, BT + 120); c.drawPath(p2, K.ink(lw * .7, "#3A3F4C"))
                K.circ(c, 0, BT + 130, 13, "#B9BDC6", lw * .5)
        elif role == "nurse":
            K.rect(c, -52, BT + 50, -22, BT + 80, "#FFFFFF", lw * .4)
            c.drawRect(skia.Rect(-41, BT + 54, -33, BT + 76), K.fp("#C8242C")); c.drawRect(skia.Rect(-48, BT + 61, -26, BT + 69), K.fp("#C8242C"))
        elif role == "police":
            K.poly(c, [(-56, BT + 50), (-30, BT + 50), (-30, BT + 76), (-43, BT + 88), (-56, BT + 76)], "#D0A548", lw * .5)
        elif role == "pilot":
            K.line(c, -66, BT + 54, -20, BT + 54, lw * 1.2, "#D0A548"); K.circ(c, -43, BT + 54, 7, "#D0A548", lw * .3)
        elif role == "chef":
            for sx in (-18, 18):
                for k in range(4): K.circ(c, sx, BT + 40 + k * 34, 6, "#3A3F4C", 0)
        elif role in ("judge", "graduate"):
            K.poly(c, [(-20, BT + 4), (-4, BT + 4), (-6, BT + 60), (-18, BT + 60)], "#FFFFFF", lw * .4)
            K.poly(c, [(4, BT + 4), (20, BT + 4), (18, BT + 60), (6, BT + 60)], "#FFFFFF", lw * .4)
        elif role == "astronaut":
            K.rect(c, -40, BT + 60, 40, BT + 120, "#B9BDC6", lw * .5, r=8)
            for k, colr in enumerate(("#C8242C", "#3E9A56", "#3B6EA8")): K.circ(c, -22 + k * 22, BT + 90, 7, colr, 0)

    def head_gear(c, kind, spec, face, lw):
        d = 1 if face >= 0 else -1
        if kind == "helmet":
            p = skia.Path(); p.moveTo(-R - 14, -30); p.arcTo(skia.Rect(-R - 14, -R - 34, R + 14, R + 6), 180, 180, False); p.close()
            K.shape(c, p, "#5A6B3A", lw); K.line(c, -R - 18, -30, R + 18, -30, lw * 1.6, "#3E4A2A")
            for (x, y) in ((-40, -90), (30, -70), (-10, -110)): c.drawCircle(x, y, 12, K.fp("#3E4A2A"))
        elif kind in ("hardhat", "firehelmet"):
            colr = "#F2C14E" if kind == "hardhat" else "#C8242C"
            p = skia.Path(); p.moveTo(-R - 4, -40); p.arcTo(skia.Rect(-R - 4, -R - 36, R + 4, R - 4), 180, 180, False); p.close()
            K.shape(c, p, colr, lw); K.rect(c, -R - 30 if kind == "hardhat" else -R - 10, -48, R + 30, -30, colr, lw * .8, r=8)
            K.line(c, 0, -R - 34, 0, -48, lw * 1.2, K.shade(colr, .8))
            if kind == "firehelmet": K.poly(c, [(-24, -110), (24, -110), (18, -64), (-18, -64)], "#F2C14E", lw * .5)
            if spec.get("role") == "miner":
                K.circ(c, 0, -86, 22, "#FFF3C8", lw * .6); c.drawCircle(0, -86, 60, K.fp("#FFF3C8", 60))
        elif kind == "chef":
            for (x, y, r) in ((-56, -R - 40, 46), (0, -R - 62, 54), (56, -R - 40, 46)): K.circ(c, x, y, r, "#FFFFFF", lw * .7)
            K.rect(c, -R + 10, -R - 30, R - 10, -60, "#FFFFFF", lw * .8)
        elif kind in ("cap_police", "cap_pilot"):
            colr = "#1E2A4A"
            K.poly(c, [(-R - 10, -112), (R + 10, -112), (R - 6, -60), (-R + 6, -60)], colr, lw)
            K.rect(c, -R + 4, -78, R - 4, -56, "#1C1C22" if kind == "cap_police" else "#D0A548", lw * .6)
            br = skia.Path(); br.moveTo(d * -40, -60); br.quadTo(d * 30, -26, d * 90, -48); br.lineTo(d * 60, -60); br.close(); K.shape(c, br, "#1C1C22", lw * .7)
            K.circ(c, 0, -92, 12, "#D0A548", lw * .4)
        elif kind == "straw":
            K.oval(c, -R - 70, -78, R + 70, -40, "#E8C27A", lw); K.rect(c, -R + 20, -R - 40, R - 20, -60, "#E8C27A", lw, r=20)
            c.drawRect(skia.Rect(-R + 22, -88, R - 22, -72), K.fp("#B8242F"))
        elif kind == "crown":
            K.poly(c, [(-70, -70), (-80, -150), (-40, -110), (0, -170), (40, -110), (80, -150), (70, -70)], "#F2C14E", lw)
            for x in (-40, 0, 40): K.circ(c, x, -90, 8, "#C8242C", lw * .3)
        elif kind == "mortarboard":
            K.rect(c, -R + 14, -R - 16, R - 14, -60, "#1C1C22", lw)
            K.poly(c, [(-R - 40, -R - 20), (0, -R - 50), (R + 40, -R - 20), (0, -R + 10)], "#1C1C22", lw)
            K.line(c, 0, -R - 20, d * 80, -R + 40, lw * .6, "#F2C14E"); K.circ(c, d * 80, -R + 44, 8, "#F2C14E", lw * .3)
        elif kind == "beanie":
            p = skia.Path(); p.moveTo(-R - 4, -30); p.arcTo(skia.Rect(-R - 4, -R - 30, R + 4, R - 10), 180, 180, False); p.close()
            K.shape(c, p, "#2A2A30", lw); K.rect(c, -R - 6, -50, R + 6, -24, "#3A3A44", lw * .7, r=8)
        elif kind == "headscarf":
            colr = spec.get("scarf_col", "#3B6EA8")
            wrap = skia.Path(); wrap.addCircle(0, -4, R + 18)
            drape = skia.Path(); drape.moveTo(-R - 18, 0); drape.quadTo(-R - 10, 120, -60, 150); drape.lineTo(60, 150); drape.quadTo(R + 10, 120, R + 18, 0); drape.close()
            whole = skia.Op(wrap, drape, skia.PathOp.kUnion_PathOp)
            hole = skia.Path(); hole.addOval(skia.Rect(-74 + face * 30, -70, 74 + face * 30, 96))
            K.shape(c, skia.Op(whole, hole, skia.PathOp.kDifference_PathOp), colr, lw)
        elif kind == "bubble":
            c.drawCircle(0, 0, R + 44, K.fp("#BFE3F2", 70)); c.drawCircle(0, 0, R + 44, K.ink(lw, "#E8ECF2"))
            arc = skia.Path(); arc.addArc(skia.Rect(-R - 24, -R - 24, R + 24, R + 24), 200, 50); c.drawPath(arc, K.ink(lw * 1.4, "#FFFFFF"))
            K.rect(c, -R + 10, R + 20, R - 10, R + 50, "#D9DDE4", lw * .7, r=10)

    def draw_char(c, x, y, s, spec, face=0.0, eyes='dot', mouth='smile', brow=0.0, brow_tilt=0.0, arms=('down', 'down'),
                  tilt=0.0, bob=0.0, squash=0.0, sweat=-1.0, light=-1, rim=None, hat=None, legs=None, pupil=0.0, sparkle=0.0):
        original(c, x, y, s, spec, face=face, eyes=eyes, mouth=mouth, brow=brow, brow_tilt=brow_tilt, arms=arms, tilt=tilt,
                 bob=bob, squash=squash, sweat=sweat, light=light, rim=rim, hat=hat, legs=legs, pupil=pupil, sparkle=sparkle)
        role = spec.get("role"); head = spec.get("headwear") or ROLE_HEAD.get(role or "")
        if spec.get("headscarf"):
            head = "headscarf"
        if not role and not head:
            return
        lw = max(5.2, 4.0 / s)
        c.save(); c.translate(x, y); c.scale(s, s); c.translate(0, -bob); c.scale(1 + squash * .6, 1 - squash)
        if role:
            body_gear(c, role, spec, lw)
        if head in HEADWEAR:
            c.save(); c.translate(0, HCY); c.rotate(tilt); head_gear(c, head, spec, face, lw); c.restore()
        c.restore()

    shots_module.draw_char = draw_char
    _ = math
