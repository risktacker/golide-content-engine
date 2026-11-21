"""Behaviour: what a character DOES while the story is told (owner 2026-11-21, after Rick's clip and
@afterhourtheories): nod, shake the head, drop the head when he loses, scratch the head and tap a foot while waiting,
laugh, cry, argue, shake hands, type, scroll a phone, call, hold or grab or give a thing, clap, cheer, jump in shock,
shiver, sigh, bow, faint, sleep, look around, walk or run to a spot. Several at once: scratch + tap_foot.

A cast member in a shot carries "acts": [{"do": name, "at": "spoken word", "for": seconds, ...}] (or the shot's
"acts" with "who"). Each act starts on its word. The kit's own Actor still does its poses, emotions, blinks, walks
and lip-sync; an act only adds to it, through the same draw_char (the kit's files are never edited).
"""
from __future__ import annotations

import math

# what each act lasts when "for" is not given; None = until the shot ends
LENGTH = dict(nod=1.2, shake_head=1.2, head_down=None, scratch=None, tap_foot=None, laugh=1.8, cry=None, sob=None,
              angry=1.6, jump=.7, cheer=1.6, clap=1.6, handshake=None, argue=None, type=None, scroll=None, call=None,
              hold=None, give=None, grab=None, shh=1.4, think=None, look_around=1.8, sigh=1.4, slump=None, bow=1.4,
              faint=None, sleep=None, love=1.8, shiver=None, walk_to=None, run_to=None, celebrate=1.6, wave=1.6,
              point=None, facepalm=1.4, shrug=1.2, nervous=None, confused=None, excited=1.6, proud=None)
ACTS = tuple(sorted(LENGTH))

# new arm positions for the kit's ARM table (left arm: elbow, hand, show hand); the right arm is mirrored
ARMS = {
    "scratch": ((-138, -392), (-62, -506), True), "scratch2": ((-128, -398), (-40, -514), True),
    "phone_ear": ((-128, -300), (-98, -420), True), "hold_phone": ((-104, -244), (-30, -300), True),
    "type": ((-112, -236), (-48, -218), True), "type2": ((-112, -240), (-38, -232), True),
    "clap": ((-112, -272), (-8, -306), True), "clap_open": ((-122, -280), (-64, -318), True),
    "fist_up": ((-130, -372), (-112, -480), True), "fist_mid": ((-130, -330), (-118, -408), True),
    "shh": ((-112, -300), (-8, -382), True), "cover_mouth": ((-106, -300), (-6, -372), True),
    "wipe_eye": ((-116, -320), (-34, -424), True), "wipe_eye2": ((-112, -322), (-46, -414), True),
    "reach": ((-138, -262), (-214, -250), True), "reach_hi": ((-136, -270), (-210, -276), True),
    "belly": ((-112, -226), (-40, -198), True), "hands_face": ((-110, -320), (-36, -408), True),
    "bow_arm": ((-74, -222), (-60, -160), True), "point_fwd": ((-140, -300), (-236, -306), True),
    # walking: the arms swing against the legs (owner 2026-11-21: "legs walking and arms swing")
    "swing_out": ((-118, -238), (-150, -176), True), "swing_in": ((-76, -236), (-44, -172), True),
}


def swing(arms, legs):
    """While the legs walk, arms left hanging swing opposite them; an arm doing something keeps doing it."""
    if not legs:
        return arms
    a = max(-1.0, min(1.0, float(legs[0][1]) / 46.0))        # the left leg's stride, -1..1
    k = .5 + .5 * a
    return tuple(("swing_in", "swing_out", k) if arm in ("down", "pocket") else arm for arm in arms)


def _sin(t, hz): return math.sin(2 * math.pi * hz * t)


def act_state(name: str, u: float, tl: float, t: float, d: dict, side: int) -> dict:
    """Overrides for one act at local time tl (u: 0..1 through it). side: +1 when facing right, -1 left.
    arms: (left, right), None keeps the kit's; the arm toward the facing side is the 'front' one."""
    front = 1 if side > 0 else 0          # index of the arm on the facing side (the right arm reaches right)
    o: dict = {}
    def arm(i, a): o.setdefault("arms", [None, None])[i] = a
    if name == "nod":
        o["head_dy"] = 16 * abs(_sin(tl, 2.2)) * (1 - u * .3)
    elif name == "shake_head":
        o["face_add"] = .55 * _sin(tl, 3.0) * (1 - u * .5); o["mouth"] = "flat"; o["brow_tilt"] = .5
    elif name == "head_down":
        k = min(1, tl / .5); o["head_dy"] = 20 * k; o["tilt_add"] = -7 * k; o["emotion"] = "sad"; o["bob_add"] = -5 * k
        o["eyes"] = "half"
    elif name == "scratch":
        arm(1 - front, "scratch" if _sin(tl, 3.2) > 0 else "scratch2"); o["emotion"] = "thinking"; o["fx"] = ["question"]
    elif name == "tap_foot":
        lift = 18 * max(0, _sin(tl, 3.4)); o["legs"] = ((-24, 0, 0), (24 + 10 * side, 8 * side, lift))
        o.setdefault("emotion", "tired"); o["fx"] = ["tap"]
    elif name == "laugh":
        o["bob_add"] = 9 * abs(_sin(tl, 4.2)); o["tilt_add"] = 5 * _sin(tl, 2.1); o["eyes"] = "closed"; o["mouth"] = "open"
        arm(0, "belly"); arm(1, "belly"); o["fx"] = ["ha"]
    elif name in ("cry", "sob"):
        o["eyes"] = "closed"; o["mouth"] = "open" if name == "sob" or _sin(tl, 1.3) > .4 else "o"; o["brow"] = .9
        o["brow_tilt"] = -.9; o["bob_add"] = 2.5 * _sin(tl, 9); arm(1 - front, "wipe_eye" if _sin(tl, 2) > 0 else "wipe_eye2")
        o["fx"] = ["tears"]
    elif name == "angry":
        o["emotion"] = "angry"; o["dx"] = 4 * _sin(tl, 14); arm(0, "hip"); arm(1, "hip"); o["fx"] = ["steam"]
    elif name == "jump":
        o["lift"] = 90 * math.sin(math.pi * min(1, u)); o["emotion"] = "shocked"; arm(0, "up"); arm(1, "up"); o["fx"] = ["shock"]
    elif name in ("cheer", "celebrate"):
        up = _sin(tl, 3.6) > 0; arm(0, "fist_up" if up else "fist_mid"); arm(1, "fist_mid" if up else "fist_up")
        o["lift"] = 22 * abs(_sin(tl, 1.8)); o["eyes"] = "closed"; o["mouth"] = "open"; o["fx"] = ["sparks"]
    elif name == "excited":
        o["lift"] = 30 * abs(_sin(tl, 2.5)); o["emotion"] = "excited"; arm(0, "up"); arm(1, "up")
    elif name == "clap":
        a = "clap" if _sin(tl, 4.5) > 0 else "clap_open"; arm(0, a); arm(1, a); o["emotion"] = "happy"; o["fx"] = ["clap"]
    elif name == "handshake":
        arm(front, "reach" if _sin(tl, 2.6) > 0 else "reach_hi"); o["emotion"] = "happy"
    elif name == "argue":
        arm(front, "point_fwd"); o["emotion"] = "angry"; o["mouth"] = "open" if _sin(tl, 5) > 0 else "flat"
        o["rot"] = 4 * side; o["dx"] = 3 * _sin(tl, 7) * side
    elif name == "type":
        arm(0, "type" if _sin(tl, 7) > 0 else "type2"); arm(1, "type2" if _sin(tl, 7) > 0 else "type"); o["pupil"] = 0
        o["eyes"] = "half"; o["item_front"] = d.get("item", "laptop")
    elif name == "scroll":
        arm(1 - front, "hold_phone"); o["eyes"] = "half"; o["item"] = (1 - front, d.get("item", "phone"), .16); o["fx"] = ["glow"]
        o["head_dy"] = 8
    elif name == "call":
        arm(1 - front, "phone_ear"); o["mouth"] = "open" if _sin(tl, 4) > 0 else "smile"; o["item"] = (1 - front, d.get("item", "phone"), .14)
    elif name == "hold":
        arm(front, "hold_phone"); o["item"] = (front, d.get("item", "moneybag"), d.get("size", .32))
    elif name == "give":
        arm(front, "reach"); o["item"] = (front, d.get("item", "gift"), d.get("size", .32)); o["emotion"] = "smile"
    elif name == "grab":
        arm(front, "reach" if u < .35 or tl < .45 else "hold_phone")
        if tl >= .45: o["item"] = (front, d.get("item", "moneybag"), d.get("size", .32))
        o["emotion"] = "greedy" if tl < 1.2 else "happy"
    elif name == "shh":
        arm(front, "shh"); o["eyes"] = "half"; o["mouth"] = "flat"; o["fx"] = ["shh"]
    elif name in ("think", "confused"):
        arm(front, "chin"); o["emotion"] = "thinking"; o["fx"] = ["question"]
    elif name == "look_around":
        o["face_abs"] = .75 if (tl % 1.2) < .6 else -.75; o["eyes"] = "wide"
    elif name in ("sigh", "slump"):
        k = min(1, tl / .6); o["bob_add"] = -12 * k; o["tilt_add"] = -5 * k; o["emotion"] = "tired"
        if name == "sigh": o["fx"] = ["puff"]
    elif name == "bow":
        o["rot"] = 26 * math.sin(math.pi * min(1, u)) * side; arm(0, "bow_arm"); arm(1, "bow_arm"); o["eyes"] = "closed"
    elif name == "faint":
        k = min(1, tl / .7); o["rot"] = -82 * k * k * side; o["eyes"] = "closed"; o["mouth"] = "o"; o["fx"] = ["dizzy"]
    elif name == "sleep":
        o["eyes"] = "closed"; o["mouth"] = "flat"; o["head_dy"] = 10 + 4 * _sin(tl, .5); o["fx"] = ["zzz"]
    elif name == "love":
        o["emotion"] = "happy"; o["fx"] = ["hearts"]; arm(0, "clap"); arm(1, "clap")
    elif name in ("shiver", "nervous"):
        o["dx"] = 3.5 * _sin(tl, 22); o["emotion"] = "nervous"; arm(0, "hold"); arm(1, "hold")
    elif name == "wave":
        arm(front, "wave" if _sin(tl, 2.5) > 0 else "gesture"); o["emotion"] = "happy"
    elif name == "point":
        arm(front, "point_fwd")
    elif name == "facepalm":
        arm(front, "hands_face"); o["eyes"] = "closed"; o["emotion"] = "tired"; o["head_dy"] = 6
    elif name == "shrug":
        arm(0, "shrug"); arm(1, "shrug"); o["emotion"] = "smug"
    elif name == "proud":
        arm(0, "hip"); arm(1, "hip"); o["emotion"] = "confident"; o["tilt_add"] = 4
    elif name in ("walk_to", "run_to"):
        o["move"] = name
    return o


def install(shots_module) -> None:
    import skia
    from engine import kit as K
    from engine import props as P

    for k, v in ARMS.items():
        K.ARM.setdefault(k, v)
    Actor = shots_module.Actor
    actor_draw, actor_init = Actor.draw, Actor.__init__
    draw_char = shots_module.draw_char
    current: dict = {}

    def __init__(self, shot, d, x, y, s, face):
        actor_init(self, shot, d, x, y, s, face)
        acts = [dict(a) for a in d.get("acts", []) if isinstance(a, dict)]
        acts += [dict(a) for a in shot.spec.get("acts", []) if isinstance(a, dict) and a.get("who") == d["id"]]
        self.acts = []
        for a in acts:
            if a.get("do") not in LENGTH:
                continue
            a["t"] = shot.cue(a.get("at"), .15)
            dur = a.get("for", LENGTH[a["do"]])
            a["t_end"] = shot.t1 + 1 if dur is None else a["t"] + float(dur)
            self.acts.append(a)
            sound = {"jump": "pop", "clap": "pop", "faint": "thud", "angry": "pop", "cheer": "pop"}.get(a["do"])
            if sound:
                shot.events.append((sound, a["t"]))

    def draw(self, c, t):
        live = [a for a in getattr(self, "acts", []) if a["t"] <= t <= a["t_end"]]
        if not live:
            return actor_draw(self, c, t)
        side = 1 if self.face >= 0 else -1
        over: dict = {"arms": [None, None], "fx": []}
        x_saved = self.x
        for a in live:
            tl = t - a["t"]; dur = (a["t_end"] - a["t"]) or 1
            if a["do"] in ("walk_to", "run_to"):
                fast = a["do"] == "run_to"; span = float(a.get("for", 1.0 if fast else 1.8))
                k = min(1, tl / span); to = float(a.get("to", self.x + 500 * side))
                self.x = x_saved + (to - x_saved) * K.ease(k) if not fast else x_saved + (to - x_saved) * k
                side = 1 if to > x_saved else -1
                if k < 1:
                    ph = tl * (18 if fast else 11)
                    over["legs"] = K.walk_legs(ph, 60 if fast else 46, 26 if fast else 20); over["walking"] = True
                    over["bob_add"] = over.get("bob_add", 0) + 7 * abs(math.sin(ph)); over["face_abs"] = .7 * side
                    over["rot"] = 7 * side if fast else 0
                    if fast: over["fx"].append("dust")
                continue
            o = act_state(a["do"], min(1, tl / dur), tl, t, a, side)
            for i in (0, 1):
                if o.get("arms") and o["arms"][i] is not None:
                    over["arms"][i] = o["arms"][i]
            over["fx"] += o.pop("fx", [])
            o.pop("arms", None)
            for k_, v in o.items():
                over[k_] = over.get(k_, 0) + v if k_ in ("head_dy", "tilt_add", "bob_add", "dx", "lift", "rot", "face_add") else v
        over["side"] = side
        current["o"] = over; current["actor"] = self
        try:
            actor_draw(self, c, t)
        finally:
            current.clear(); self.x = x_saved

    def draw_with_acts(c, x, y, s, spec, face=0.0, eyes='dot', mouth='smile', brow=0.0, brow_tilt=0.0, arms=('down', 'down'),
                       tilt=0.0, bob=0.0, squash=0.0, sweat=-1.0, light=-1, rim=None, hat=None, legs=None, pupil=0.0, sparkle=0.0):
        o = current.get("o")
        if not o:
            arms = swing(arms, legs)
            return draw_char(c, x, y, s, spec, face=face, eyes=eyes, mouth=mouth, brow=brow, brow_tilt=brow_tilt, arms=arms,
                             tilt=tilt, bob=bob, squash=squash, sweat=sweat, light=light, rim=rim, hat=hat, legs=legs,
                             pupil=pupil, sparkle=sparkle)
        if o.get("emotion"):
            eyes, mouth, brow, brow_tilt, ex = K.EMOTIONS.get(o["emotion"], K.EMOTIONS["neutral"])
            sparkle = (sparkle or 0) if not ex.get("sparkle") else .5
        eyes = o.get("eyes", eyes); mouth = o.get("mouth", mouth); brow = o.get("brow", brow); brow_tilt = o.get("brow_tilt", brow_tilt)
        pupil = o.get("pupil", pupil)
        arms = tuple(o["arms"][i] if o["arms"][i] is not None else arms[i] for i in (0, 1))
        legs = o.get("legs", legs)
        walking = o.get("walking") or "legs" not in o          # not a foot tap: the kit's walk or our walk_to/run_to
        arms = swing(arms, legs) if walking and legs and not any(o["arms"]) else arms
        face = o["face_abs"] if "face_abs" in o else face + o.get("face_add", 0)
        x += o.get("dx", 0); y -= o.get("lift", 0) * s
        tilt += o.get("tilt_add", 0); bob += o.get("bob_add", 0)
        rot = o.get("rot", 0)
        head0 = K.HEAD_CY; K.HEAD_CY = head0 + o.get("head_dy", 0)
        c.save()
        if rot:
            c.rotate(rot, x, y)
        try:
            draw_char(c, x, y, s, spec, face=face, eyes=eyes, mouth=mouth, brow=brow, brow_tilt=brow_tilt, arms=arms, tilt=tilt,
                      bob=bob, squash=squash, sweat=sweat, light=light, rim=rim, hat=hat, legs=legs, pupil=pupil, sparkle=sparkle)
            hx, hy = x, y + (K.HEAD_CY - bob) * s
            from golide_engine.stickman.rm_art import art
            art(_items)(c, o, x, y, s, arms, bob)
            art(_fx)(c, o, hx, hy, x, y, s, face, current.get("actor"))
        finally:
            K.HEAD_CY = head0
            c.restore()

    def _hand(arm, side_i, x, y, s, bob):
        e, h, show = K._arm(arm); m = 1 if side_i == 0 else -1
        return x + h[0] * m * s, y + (h[1] - bob) * s

    def _items(c, o, x, y, s, arms, bob):
        if o.get("item"):
            i, name, size = o["item"]
            if name in P.ICONS:
                hx, hy = _hand(arms[i], i, x, y, s, bob)
                out = -1 if i == 0 else 1                    # held beside the hand, never over the face
                P.draw_prop(c, name, hx + out * 70 * s, hy + 40 * s, s * size, 0.0)
        if o.get("item_front") and o["item_front"] in P.ICONS:
            P.draw_prop(c, o["item_front"], x, y - 190 * s, s * .36, 0.0)

    def _fx(c, o, hx, hy, x, y, s, face, actor):
        t = getattr(actor, "_t", 0.0) if actor else 0.0
        R = K.HEAD_R * s; ph = (sum(map(ord, str(id(actor)))) % 7) * .3
        for f in o.get("fx", []):
            if f == "tears":
                for ex0 in (-30, 30):
                    for k in range(3):
                        u = ((t * 1.6 + k / 3 + ph) % 1)
                        cx = hx + (ex0 + face * 40) * s + (6 * s if ex0 > 0 else -6 * s); cy = hy + (10 + u * 130) * s
                        p = skia.Path(); r = 7 * s
                        p.moveTo(cx, cy - 2 * r); p.cubicTo(cx + r, cy - r, cx + r, cy + r * .6, cx, cy + r * .6)
                        p.cubicTo(cx - r, cy + r * .6, cx - r, cy - r, cx, cy - 2 * r); p.close()
                        c.drawPath(p, K.fp("#7FC8F8", int(255 * (1 - u)))); c.drawPath(p, K.ink(1.5 * s, "#3B6EA8", int(200 * (1 - u))))
            elif f == "zzz":
                for k in range(3):
                    u = (t * .6 + k / 3) % 1
                    K.label(c, "z", hx + (60 + u * 60) * s, hy - (90 + u * 120) * s, (30 + 20 * k) * s * (1 - u * .3), "#FFFFFF",
                            align="center", stroke=6 * s, alpha=1 - u)
            elif f == "question":
                bob_ = 8 * math.sin(t * 4); K.label(c, "?", hx + 110 * s, hy - 110 * s + bob_ * s, 90 * s, K.GOLD if hasattr(K, "GOLD") else "#F2C14E",
                                                   align="center", stroke=8 * s, skew=0)
            elif f == "steam":
                for sx in (-1, 1):
                    for k in range(3):
                        u = (t * 1.4 + k / 3) % 1
                        c.drawCircle(hx + sx * (R + 10 * s + u * 40 * s), hy - R * .6 - u * 70 * s, (12 + 14 * u) * s, K.fp("#FFFFFF", int(220 * (1 - u))))
            elif f == "hearts":
                for k in range(4):
                    u = (t * .8 + k / 4) % 1; cx = hx + (-80 + k * 55) * s + 14 * s * math.sin(t * 3 + k); cy = hy - R - u * 160 * s
                    _heart(c, cx, cy, (18 + 8 * (k % 2)) * s, int(255 * (1 - u)))
            elif f == "ha":
                for k in range(2):
                    u = (t * 1.5 + k / 2) % 1
                    K.label(c, "HA", hx + (k * 2 - 1) * (R + 30 * s), hy - R * .4 - u * 60 * s, 46 * s, "#FFFFFF", align="center",
                            stroke=7 * s, alpha=1 - u, skew=0)
            elif f == "shock":
                for k in range(6):
                    a = math.radians(200 + k * 28); r0, r1 = R + 20 * s, R + 60 * s
                    c.drawLine(hx + r0 * math.cos(a), hy + r0 * math.sin(a), hx + r1 * math.cos(a), hy + r1 * math.sin(a), K.ink(6 * s))
            elif f == "sparks":
                for k in range(8):
                    a = k * math.pi / 4 + t; r = R + (30 + 20 * math.sin(t * 6 + k)) * s
                    c.drawCircle(hx + r * math.cos(a), hy - 40 * s + r * math.sin(a) * .7, 6 * s, K.fp("#FFE26A"))
            elif f == "clap":
                if math.sin(t * 2 * math.pi * 4.5) > .7:
                    for k in range(5):
                        a = math.radians(200 + k * 35); c.drawLine(x + 70 * s * math.cos(a), y - 320 * s + 70 * s * math.sin(a),
                                                                  x + 100 * s * math.cos(a), y - 320 * s + 100 * s * math.sin(a), K.ink(4 * s))
            elif f == "tap":
                if math.sin(t * 2 * math.pi * 3.4) < -.6:
                    K.label(c, "tap", x + 110 * s, y - 20 * s, 34 * s, "#FFFFFF", align="center", stroke=6 * s, skew=0)
            elif f == "glow":
                c.drawCircle(hx, hy + 30 * s, 120 * s, K.fp("#7FC8F8", 40))
            elif f == "shh":
                K.label(c, "shh", hx + 130 * s, hy - 40 * s, 44 * s, "#FFFFFF", align="center", stroke=7 * s, skew=0)
            elif f == "puff":
                u = (t * .8) % 1; c.drawCircle(hx + 90 * s + u * 50 * s, hy + 40 * s, (14 + 20 * u) * s, K.fp("#FFFFFF", int(200 * (1 - u))))
            elif f == "dizzy":
                for k in range(3):
                    a = t * 5 + k * 2.1; K.label(c, "*", hx + 70 * s * math.cos(a), hy - R - 20 * s + 22 * s * math.sin(a), 50 * s, "#FFE26A",
                                                 align="center", stroke=5 * s, skew=0)
            elif f == "dust":
                for k in range(3):
                    u = (t * 3 + k / 3) % 1; side = o.get("side", 1)
                    c.drawCircle(x - side * (60 + u * 80) * s, y - 10 * s - u * 20 * s, (10 + 16 * u) * s, K.fp("#D8D2C2", int(200 * (1 - u))))

    def _heart(c, x, y, r, a):
        p = skia.Path(); p.moveTo(x, y + r); p.cubicTo(x - 2 * r, y - .2 * r, x - r, y - 1.6 * r, x, y - .6 * r)
        p.cubicTo(x + r, y - 1.6 * r, x + 2 * r, y - .2 * r, x, y + r); p.close()
        c.drawPath(p, K.fp("#FF4FA0", a)); c.drawPath(p, K.ink(2, K.INK, a))

    def draw_timed(self, c, t):
        self._t = t
        return draw(self, c, t)

    Actor.__init__ = __init__
    Actor.draw = draw_timed
    shots_module.draw_char = draw_with_acts
