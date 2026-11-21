"""The puppet's finish (owner 2026-11-21, after @afterhourtheories' city Stickman): thick round arms with round
hands, thick legs ending in round "thumb" feet, and textured hair (strands and a soft shine) for men and women.

Drawn over the kit's own draw_char (the kit's file is never edited): the kit draws the character, then these
layers go on top, clipped so they never cover the body, the dress or the face.
"""
from __future__ import annotations

import math

LIMB = "#34343E"      # arm and leg colour (dark, like the model's)


def install(shots_module) -> None:
    import skia
    from engine import kit as K

    BT, BB, R, HCY = K.BODY_TOP, K.BODY_BOT, K.HEAD_R, K.HEAD_CY
    original = shots_module.draw_char

    def tube(c, path, w, lw):
        c.drawPath(path, _stroke(skia, w + 2 * lw, K.INK)); c.drawPath(path, _stroke(skia, w, LIMB))

    def body_shape(spec):
        p = skia.Path(); p.addRRect(skia.RRect.MakeRectXY(skia.Rect(-84, BT, 84, BB), 66, 72))
        if spec.get("outfit") == "dress":
            sk = skia.Path(); sk.moveTo(-70, BB - 70); sk.lineTo(70, BB - 70); sk.lineTo(104, BB + 30); sk.quadTo(0, BB + 46, -104, BB + 30); sk.close()
            p = skia.Op(p, sk, skia.PathOp.kUnion_PathOp)
        return p

    def hair_texture(c, spec, face, lw):
        hair = spec.get("hair", "short"); colr = spec.get("hair_col", "#1C1B22")
        if hair in ("bald", "none"):
            return
        hi = K.shade(colr, 2.4) if K.rgb(colr)[0] < 60 else K.shade(colr, 1.35)
        lo = K.shade(colr, .62)
        fs = face * 14
        if hair in ("short", "bun", "long", "curly", "slick"):
            cap = skia.Path()
            if hair == "slick":
                cap.moveTo(-R - 4, -4); cap.arcTo(skia.Rect(-R - 4, -R - 5, R + 4, R + 3), 181, 178, False)
                cap.cubicTo(R - 6, -40, 56 + fs, -70, 4 + fs, -62); cap.cubicTo(-36 + fs, -58, -78, -44, -R - 4, -4)
            else:
                fr = -58 if hair != "curly" else -66
                cap.moveTo(-R - 4, -14); cap.arcTo(skia.Rect(-R - 4, -R - 6, R + 4, R + 4), 188, 164, False)
                cap.cubicTo(R - 8, -44, 46 + fs, fr - 8, fs, fr); cap.cubicTo(-44 + fs, fr + 4, -R + 6, -40, -R - 4, -14)
            cap.close()
            c.save(); c.clipPath(cap, doAntiAlias=True)
            for k in range(-5, 6):                     # strands sweeping from the crown to the fringe
                p = skia.Path(); x0 = k * 20 + fs * .6
                p.moveTo(x0 * .4, -R - 6); p.quadTo(x0 * 1.1 + 10, -R * .7, x0 + 14 * (1 if k >= 0 else -1), -40)
                c.drawPath(p, _stroke(skia, lw * .55, lo))
            sh = skia.Path(); sh.addArc(skia.Rect(-R + 18, -R + 6, R - 18, R - 10), 214 if face <= 0 else 276, 52)
            c.drawPath(sh, _stroke(skia, lw * 2.2, hi, 150))
            c.restore()
        if hair == "bun":
            c.save(); b = skia.Path(); b.addCircle(0, -R - 26, 44); c.clipPath(b, doAntiAlias=True)
            for k in range(-3, 4):
                p = skia.Path(); p.addArc(skia.Rect(-44 + k * 6, -R - 70 + abs(k) * 4, 44 + k * 6, -R + 18 - abs(k) * 4), 200, 140)
                c.drawPath(p, _stroke(skia, lw * .5, lo))
            c.drawCircle(-14, -R - 44, 12, K.fp(hi, 140)); c.restore()
            c.drawRect(skia.Rect(-30, -R - 2, 30, -R + 10), K.fp(lo))
        if hair == "curly":
            for i in range(11):
                a = math.radians(165 + i * 21); cx, cy = (R + 4) * math.cos(a), (R + 4) * math.sin(a) + 6
                arc = skia.Path(); arc.addArc(skia.Rect(cx - 20, cy - 20, cx + 20, cy + 20), 200, 120)
                c.drawPath(arc, _stroke(skia, lw * .55, hi, 170))

    def long_hair_texture(c, spec, lw, head_tilt):
        colr = spec.get("hair_col", "#1C1B22"); lo = K.shade(colr, .62)
        panel = skia.Path(); panel.addRRect(skia.RRect.MakeRectXY(skia.Rect(-R - 14, HCY - 40, R + 14, HCY + 150), 60, 60))
        head = skia.Path(); head.addCircle(0, HCY, R + 2)
        vis = skia.Op(skia.Op(panel, head, skia.PathOp.kDifference_PathOp), body_shape(spec), skia.PathOp.kDifference_PathOp)
        c.save(); c.clipPath(vis, doAntiAlias=True)
        for x in range(-R - 4, R + 8, 16):
            p = skia.Path(); p.moveTo(x, HCY - 30); p.quadTo(x + (8 if x < 0 else -8), HCY + 60, x, HCY + 150)
            c.drawPath(p, _stroke(skia, lw * .5, lo))
        c.restore()

    def draw_char(c, x, y, s, spec, face=0.0, eyes='dot', mouth='smile', brow=0.0, brow_tilt=0.0, arms=('down', 'down'),
                  tilt=0.0, bob=0.0, squash=0.0, sweat=-1.0, light=-1, rim=None, hat=None, legs=None, pupil=0.0, sparkle=0.0):
        original(c, x, y, s, spec, face=face, eyes=eyes, mouth=mouth, brow=brow, brow_tilt=brow_tilt, arms=arms, tilt=tilt,
                 bob=bob, squash=squash, sweat=sweat, light=light, rim=rim, hat=hat, legs=legs, pupil=pupil, sparkle=sparkle)
        lw = max(5.2, 4.0 / s); d = 1 if face >= 0 else -1
        c.save(); c.translate(x, y); c.scale(s, s)
        # legs and thumb feet: in the kit's leg frame (before the bob), never over the body or a dress
        keep = body_shape(spec); m = skia.Matrix(); m.setTranslate(0, -bob); m.preScale(1 + squash * .6, 1 - squash)
        keep.transform(m)
        c.save(); c.clipPath(keep, skia.ClipOp.kDifference, True)
        for (hx0, fx, lift) in (legs or ((-24, 0, 0), (24, 0, 0))):
            p = skia.Path(); p.moveTo(hx0, BB - 8); p.lineTo(hx0 + fx, -lift - 10)
            tube(c, p, 15, lw)
        c.restore()
        for (hx0, fx, lift) in (legs or ((-24, 0, 0), (24, 0, 0))):
            fx0, fy0 = hx0 + fx, -lift
            foot = skia.Path(); foot.addOval(skia.Rect(fx0 - 22 + d * 12, fy0 - 20, fx0 + 22 + d * 12, fy0 + 6))
            K.shape(c, foot, LIMB, lw * .8)
            c.drawOval(skia.Rect(fx0 - 10 + d * 16, fy0 - 16, fx0 + 4 + d * 16, fy0 - 9), K.fp("#FFFFFF", 60))
        # arms: thick and round, never over the face (the head is drawn after the arms in the kit)
        c.translate(0, -bob); c.scale(1 + squash * .6, 1 - squash)
        head = skia.Path(); head.addCircle(0, HCY, R + 6)
        if spec.get("hair") == "bun":
            head.addCircle(0, HCY - R - 26, 46)
        c.save(); c.clipPath(head, skia.ClipOp.kDifference, True)
        for side, a in ((-1, arms[0]), (1, arms[1])):
            e, h, show = K._arm(a); mm = 1 if side < 0 else -1
            sx, sy = K.SHOULDER[0] * mm, K.SHOULDER[1]; ex, ey, hx_, hy_ = e[0] * mm, e[1], h[0] * mm, h[1]
            ap = skia.Path(); ap.moveTo(sx, sy); ap.quadTo(1.35 * ex - .175 * (sx + hx_), 1.35 * ey - .175 * (sy + hy_), hx_, hy_)
            if spec.get("outfit") in ("suit", "hoodie", "sweater") and spec.get("role") != "astronaut":
                c.drawPath(ap, _stroke(skia, 22 + 2 * lw, K.INK)); c.drawPath(ap, _stroke(skia, 22, spec["suit"]))   # a sleeve
            else:
                tube(c, ap, 16, lw)
            if show:
                K.circ(c, hx_, hy_, 19, spec["skin"], lw * .8)
                c.drawCircle(hx_ - 6, hy_ - 7, 5, K.fp("#FFFFFF", 70))
        c.restore()
        if spec.get("hair") == "long":
            long_hair_texture(c, spec, lw, tilt)
        c.translate(0, HCY); c.rotate(tilt)
        from .rm_roles import ROLE_HEAD
        covered = spec.get("headscarf") or spec.get("headwear") or ROLE_HEAD.get(spec.get("role") or "")
        if not covered and (hat or spec.get("hat") or "none") == "none":
            hair_texture(c, spec, face, lw)
        c.restore()

    shots_module.draw_char = draw_char


def _stroke(skia, w, colr, a=255):
    from engine import kit as K
    p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=w, StrokeCap=skia.Paint.kRound_Cap,
                   StrokeJoin=skia.Paint.kRound_Join)
    p.setColor(K.col(colr, a))
    return p
