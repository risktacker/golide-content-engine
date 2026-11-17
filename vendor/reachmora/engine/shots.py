"""Shot library. Each shot is built from its story.json spec + timeline, and drawn per frame:
world (cached background + actors + world props) -> lighting -> overlays -> grade -> screen overlays."""
import math, random
import skia
from .kit import *
from .sets import SETS, block
from .props import DOCS, draw_prop, sleeve, bills, arrow
from .fx import poplabel, stamp, tag, lower_third, typed, ring, bubble, number_badge

PADX, PADY = 420, 260
LABEL_SLOTS = [(330, -5), (560, 4), (780, -3), (200, 5)]


def colr(v, d=LIME): return NAMED.get(v, v) if v else d


class Actor:
    """A cast member in a shot, with pose/emotion beats, idle motion, blinks and voice lip-sync."""
    def __init__(self, shot, d, x, y, s, face):
        self.sh = shot; self.d = d; self.look = shot.cast[d["id"]]; self.x = d.get("x", x); self.y = y; self.s = d.get("s", s)
        self.face = d.get("face", face); self.ph = (sum(map(ord, d["id"])) % 17) / 3.0
        self.base = dict(pose=d.get("pose", "idle"), emotion=d.get("emotion", "neutral"), face=self.face)
        self.beats = sorted([dict(b, t=shot.cue(b.get("at"))) for b in shot.spec.get("beats", []) if b.get("who", d["id"]) == d["id"]]
                            + [dict(b, t=shot.cue(b.get("at"))) for b in d.get("beats", [])], key=lambda b: b["t"])
        self.talk = shot.tl.talk_spans(shot.sh, d.get("talk", shot.spec.get("talk") if shot.spec.get("who") == d["id"] else None))
        self.walk = d.get("walk"); self.enter = d.get("enter"); self.exit = d.get("exit")
        self.head = (self.x, self.y - 420 * self.s)

    def state(self, t):
        st = dict(self.base); prev = dict(self.base); tb = self.sh.t0
        for b in self.beats:
            if t >= b["t"]:
                prev = dict(st); tb = b["t"]
                for k in ("pose", "emotion", "face"):
                    if k in b: st[k] = b[k]
        return st, prev, tb

    def mouth_at(self, t):
        for a, b in self.talk:
            if a - .02 <= t <= b: return self.sh.mouth(t)
        return None

    def draw(self, c, t):
        st, prev, tb = self.state(t); t0, t1 = self.sh.t0, self.sh.t1
        eyes, mouth, brow, btilt, ex = EMOTIONS.get(st["emotion"], EMOTIONS["neutral"])
        k = K(t, tb, .3); pa = POSES.get(prev["pose"], POSES["idle"]); pb = POSES.get(st["pose"], POSES["idle"])
        arms = tuple((pa[i], pb[i], k) if pa[i] != pb[i] and k < 1 else pb[i] for i in range(2))
        face = lerp(prev["face"], st["face"], back(k, 1.2)) if prev["face"] != st["face"] else st["face"]
        x = self.x; legs = None; walking = False; bob = 2 + 2 * math.sin(t * 3 + self.ph); tilt = 1.4 * math.sin(t * 2.2 + self.ph)
        if self.walk:
            u = K(t, t0 + .1, max(.5, (t1 - t0) - .4)); x = lerp(self.walk[0], self.walk[1], u); walking = 0 < u < 1
        elif self.enter:
            u = K(t, t0, 1.1); x0 = -260 if self.enter == "left" else W + 260; x = lerp(x0, self.x, ease_out(u)); walking = u < .97
        if self.exit:
            u = K(t, t1 - 1.1, 1.0); x1 = -300 if self.exit == "left" else W + 300
            if u > 0: x = lerp(x, x1, u * u); walking = True
        if walking:
            ph = (t - t0) * 11; legs = walk_legs(ph); bob = 7 * abs(math.sin(ph)); tilt = 3 * math.sin(ph)
            face = .7 if (self.walk and self.walk[1] > self.walk[0]) or self.enter == "left" or (self.exit == "right" and K(t, t1 - 1.1, 1) > 0) else -.7
        m = self.mouth_at(t)
        if m: mouth = {'open': 'open', 'mid': 'mid', 'closed': mouth if mouth in ('smile', 'smirk', 'flat') else 'flat'}[m]; bob += 3 if m == 'open' else 0
        if eyes != 'closed' and blink(t, 2.5, self.ph): eyes = 'closed'
        if st["pose"] in ("facepalm",): eyes = 'closed'
        sq = .06 * math.sin(K(t, t0, .26) * math.pi) + (.06 * math.sin(K(t, tb, .26) * math.pi) if tb > t0 else 0)
        sweat = (t - t0) * 1.1 if ex.get('sweat') else -1
        sparkle = (t - tb) / .3 if ex.get('sparkle') and t - tb < 1.2 else 0
        if self.sh.dark_ok:
            c.drawOval(skia.Rect(x - 110 * self.s, self.y - 22 * self.s, x + 110 * self.s, self.y + 22 * self.s), fp((0, 0, 0), 110, blur=8))
        draw_char(c, x, self.y, self.s, self.look, face=face, eyes=eyes, mouth=mouth, brow=brow, brow_tilt=btilt, arms=arms,
                  tilt=tilt + (-4 if st["emotion"] in ("smug", "sad", "tired") else 0), bob=bob, squash=sq, sweat=sweat,
                  light=1 if face < 0 else -1, rim='#FFE6B0' if self.sh.night else None, legs=legs, pupil=ex.get('pupil', 0), sparkle=sparkle)
        self.head = (x, self.y + HEAD_CY * self.s)


class Shot:
    kind = "base"; card = False; vig = .64

    def __init__(self, sh, tl, cast, env):
        self.sh = sh; self.spec = sh["spec"]; self.tl = tl; self.cast = cast; self.env = env
        self.t0, self.t1 = sh["t0"], sh["t1"]; self.f0, self.f1 = sh["f0"], sh["f1"]
        self.time = self.spec.get("time", "night"); self.night = self.time == "night"; self.dark_ok = True
        self.setname = self.spec.get("set"); self.info = None; self.bg = None; self.mask = None
        self.actors = []; self.cam = self.spec.get("cam", {}); self.shakes = []; self.events = []
        self.labels = []
        for i, L in enumerate(self.spec.get("labels", [])):
            y, rot = LABEL_SLOTS[i % len(LABEL_SLOTS)]
            self.labels.append(dict(L, t=self.cue(L.get("at"), .25 + .2 * i), y=L.get("y", y), rot=L.get("rot", rot)))
            self.events.append(("pop", self.labels[-1]["t"]))
        st = self.spec.get("stamp")
        if st:
            self.stamp = dict(st, t=self.cue(st.get("at"), .6)); self.shakes.append(self.stamp["t"]); self.events.append(("thud", self.stamp["t"]))
        else: self.stamp = None
        self.extra_sfx = [(e["name"], self.cue(e.get("at"))) for e in self.spec.get("sfx", [])]
        pol = self.spec.get("polaroid")
        self.pol = dict(pol, t=self.cue(pol.get("at"), .7)) if pol else None
        if self.pol: self.events.append(("shutter", self.pol["t"]))
        self.frozen = None

    def cue(self, at, default=0.0):
        return self.tl.cue(self.sh, at, default * (self.t1 - self.t0) if default <= 1 else default)

    def mouth(self, t): return self.env.mouth(t)

    # --- background + light caching
    def build_bg(self, c):  # override for non-set shots
        o = dict(self.spec); o.setdefault("time", self.time)
        self.info = SETS[self.setname or "void"](c, o)

    def prepare(self):
        """Cache the static background, the light map (multiply) and the glow map (add) for the whole shot."""
        PW, PH = W + 2 * PADX, H + 2 * PADY
        a, surf = np_surface(PW, PH); c = surf.getCanvas(); c.clear(C((0, 0, 0))); c.save(); c.translate(PADX, PADY); self.build_bg(c); c.restore()
        self.bg = np_image(a); info = self.info or {}; self.glow = None
        if info.get("ambient") and info.get("lights") is not None and self.light_on():
            m, ms = np_surface(PW, PH); mc = ms.getCanvas(); mc.clear(C((255, 255, 255))); mc.save(); mc.translate(PADX, PADY)
            night(mc, info["lights"] + self.extra_lights(), info["ambient"]); mc.restore(); self.mask = np_image(m)
        bulbs = list(info.get("bulbs", [])) + self.extra_glow()
        if bulbs:
            g, gs = np_surface(PW, PH); gc = gs.getCanvas(); gc.clear(C((0, 0, 0))); gc.save(); gc.translate(PADX, PADY)
            for b in bulbs: add_light(gc, *b)
            gc.restore(); self.glow = np_image(g)

    def light_on(self): return True
    def extra_lights(self): return [('pool', a.x, a.y - 300 * a.s, 330 * a.s, .55) for a in self.actors]
    def extra_glow(self): return []

    def draw_bg(self, c): c.drawImage(self.bg, -PADX, -PADY, LINEAR)

    # --- per-frame layers
    def world(self, c, t):
        self.draw_bg(c)
        for a in sorted(self.actors, key=lambda a: a.y): a.draw(c, t)
        self.world_props(c, t)

    def world_props(self, c, t):
        for p in self.spec.get("props", []):
            tt = self.cue(p.get("at"), 0); u = K(t, tt, .35)
            if t >= tt: draw_prop(c, p["icon"], p.get("x", 1500), p.get("y", 760), p.get("s", .6) * back(u, 1.5), t, rot=p.get("rot", 0), **{k: v for k, v in p.items() if k not in ("icon", "x", "y", "s", "at", "rot")})

    def over(self, c, t):
        for L in self.labels:
            font = MARKER if L.get("font") == "marker" else None; x = L.get("x", self.label_x()); mw = max(400, min(1500, 2 * min(x, W - x) - 140))
            poplabel(c, L["text"], x, L["y"], t - L["t"], L.get("size", 120), colr(L.get("color"), LIME if len(self.labels) < 2 or self.labels.index(L) % 2 else CREAM), L["rot"], font, max_w=mw)
        if self.stamp:
            s = self.stamp; x = s.get("x", self.label_x()); mw = max(400, min(1100, 2 * min(x, W - x) - 260))
            stamp(c, s["text"], x, s.get("y", 640 if self.labels else 420), (t - s["t"]) / .9, s.get("rot", -9), s.get("size", 130), colr(s.get("color"), RED), max_w=mw)
        b = self.spec.get("bubble")
        if b:
            a = self.actor(b.get("who")); tb = self.cue(b.get("at"), .1)
            hx_, hy_ = (a.head if a else (960, 600)); bx = b.get("x", hx_ + (380 if hx_ < 1000 else -380)); by = b.get("y", max(220, hy_ - 260))
            bubble(c, bx, by, b.get("w", 560), b.get("h", 360), t - tb, b.get("text"), b.get("icon"), (hx_ + (60 if bx > hx_ else -60), hy_ - 60), t, b.get("thought", True))

    def screen(self, c, t):
        if self.spec.get("tag"): tag(c, self.spec["tag"], (t - self.t0 - .2) / 1.0)
        lt = self.spec.get("lower_third")
        if lt: lower_third(c, lt["name"], lt.get("sub", ""), t - self.cue(lt.get("at"), .15), lt.get("x", 90), lt.get("y", 930))

    def label_x(self):
        xs = [a.x for a in self.actors]
        if not xs: return 1420
        return 1440 if sum(xs) / len(xs) < 960 else 480

    def actor(self, id_):
        for a in self.actors:
            if a.d["id"] == id_: return a
        return self.actors[0] if self.actors else None

    def camera(self, u):
        z = self.cam.get("zoom", [1.0, self.default_zoom()]); f = self.cam.get("focus", [[960, 545], [960, 545]])
        if isinstance(f[0], (int, float)): f = [f, f]
        e = ease(u); return lerp(z[0], z[1], e), lerp(f[0][0], f[1][0], e), lerp(f[0][1], f[1][1], e), self.cam.get("rot", 0) * (e - .5)

    def default_zoom(self): return 1.07

    def sfx_events(self): return self.events + [(n, t) for n, t in self.extra_sfx]


# ---------------------------------------------------------------- kinds
class Wide(Shot):
    kind = "wide"

    def __init__(self, *a):
        super().__init__(*a); self.setname = self.setname or "office"
        floor = {"office": 1024, "home": 1030, "street": 1000, "skyline": 1000, "board": 1060, "void": 1010}.get(self.setname, 1010)
        chars = self.spec.get("chars", [])
        default_x = {1: [1000], 2: [700, 1250], 3: [520, 960, 1400]}.get(len(chars), [300 + i * 300 for i in range(len(chars))])
        for i, d in enumerate(chars):
            x = default_x[i] if i < len(default_x) else 960; face = .7 if x < 960 else -.7
            if len(chars) == 1: face = d.get("face", -.3)
            self.actors.append(Actor(self, d, x, d.get("y", floor), d.get("s", 1.0), face))
            if d.get("enter") or d.get("walk"): self.events.append(("steps", self.t0))


class Walk(Wide):
    kind = "walk"

    def __init__(self, sh, tl, cast, env):
        sh["spec"].setdefault("set", "street")
        for d in sh["spec"].get("chars", []): d.setdefault("walk", [80, 1700])
        super().__init__(sh, tl, cast, env)


class Closeup(Shot):
    kind = "closeup"; vig = .6

    def __init__(self, *a):
        super().__init__(*a); self.setname = self.setname or "office"
        side = self.spec.get("side", "left"); x = 840 if side == "left" else 1080; face = .72 if side == "left" else -.72
        d = {k: v for k, v in self.spec.items() if k not in ("s", "x", "y", "labels", "props", "stamp", "beats")}
        d["id"] = self.spec["who"]; d["beats"] = []
        d.setdefault("talk", self.spec.get("talk")); d.setdefault("x", x)
        self.actors.append(Actor(self, d, x, 1390, 2.15, d.get("face", face))); self.dark_ok = False

    def build_bg(self, c):
        blur_begin(c, 13); c.save(); c.translate(-900 if self.spec.get("side", "left") == "right" else -1500, -200); c.scale(1.5, 1.5)
        o = dict(self.spec); o.setdefault("time", self.time); info = SETS[self.setname](c, o); c.restore(); c.restore()
        if info.get("ambient"): night(c, [('pool', 960, 520, 900, .55)], info["ambient"] if self.time != "day" else '#E8E2DA')
        self.info = dict(info, lights=None, bulbs=[])

    def extra_glow(self):
        a = self.actors[0]; return [(a.x - (600 if a.x > 960 else -420), 380, 700, '#FFD98A', 36 if self.night else 18)]

    def default_zoom(self): return 1.05


class Title(Shot):
    kind = "title"; card = True

    def build_bg(self, c): SETS["black"](c, {"color": self.spec.get("bg", "#000000")}); self.info = {}

    def world(self, c, t):
        self.draw_bg(c); txt = self.spec.get("text", ""); sub = self.spec.get("sub")
        if self.sh["sents"]:
            a, b = self.tl.sent_span(self.sh["sents"][0]); b = self.tl.sent_span(self.sh["sents"][-1])[1]; t0, d = a, max(.3, b - a - .15)
        else: t0, d = self.t0 + .15, .45
        typed(c, txt, t, t0, d, self.spec.get("size", 140), colr(self.spec.get("color"), '#FFFFFF'), y=H / 2 - (40 if sub else 0))
        if sub and t > t0 + d: label(c, sub, W / 2, H / 2 + 150, fit_size(sub, 64, 1500), GOLD, align='center', skew=-0.1, alpha=K(t, t0 + d, .3))

    def default_zoom(self): return 1.03


class Skyline(Shot):
    kind = "skyline"

    def __init__(self, *a):
        super().__init__(*a); self.setname = "skyline"

    def default_zoom(self): return 1.1


class Table(Shot):
    kind = "table"; vig = .46

    def __init__(self, *a):
        super().__init__(*a); self.setname = "table"; self.dark_ok = False
        self.items = [dict(it, t=self.cue(it.get("at"), .02 + .3 * i)) for i, it in enumerate(self.spec.get("items", [{"type": "newspaper"}]))]
        for it in self.items:
            self.events.append(("paper", it["t"]))
            if it.get("stamp"): it["st"] = self.cue(it["stamp"].get("at"), .65); self.shakes.append(it["st"]); self.events.append(("thud", it["st"]))
            if it.get("ring_at") is not None: it["rt"] = self.cue(it["ring_at"]); self.events.append(("scribble", it["rt"]))
        hid = self.spec.get("hand"); self.hand = make_look(self.cast[hid]) if hid in self.cast else make_look({})

    def light_on(self): return False

    def world(self, c, t):
        self.draw_bg(c); n = len(self.items)
        # slow drift-rotate only the paper layer (a rotated full-frame background is very slow to draw)
        r = self.cam.get("rot", 1.6) * (ease(K(t, self.t0, self.t1 - self.t0)) - .5)
        c.save(); c.translate(960, 540); c.rotate(r); c.translate(-960, -540); self._items(c, t, n); c.restore()

    def _items(self, c, t, n):
        slots = {1: [(760, 545, 4)], 2: [(560, 560, -5), (1300, 520, 6)], 3: [(480, 560, -6), (1000, 520, 4), (1480, 580, -3)]}.get(n, [(400 + i * 360, 540, (-1) ** i * 5) for i in range(n)])
        for i, it in enumerate(self.items):
            if t < it["t"]: continue
            x, y, rot = slots[i % len(slots)]; k = back(K(t, it["t"], .5), 1.3); fromx = -900 if x < 960 else W + 900; px = lerp(fromx, x, k)
            c.save(); c.translate(px, y); c.rotate(rot); sc = it.get("scale", .82 if n > 1 else 1.0); c.scale(sc, sc)
            DOCS[it.get("type", "newspaper")](c, it, t, K(t, it.get("rt", 1e9), .45))
            if it.get("stamp"): stamp(c, it["stamp"]["text"], it["stamp"].get("x", -60), it["stamp"].get("y", 220), (t - it["st"]) / .9, -14, it["stamp"].get("size", 96), colr(it["stamp"].get("color"), RED))
            c.restore()
            if i == 0 and t - it["t"] < 2.2:
                hx_ = px - (480 if fromx < 0 else -480); sv = 1 if fromx < 0 else -1
                sleeve(c, hx_ - 560 * sv, 700, hx_, 640, 170, self.hand['suit'], skin=self.hand['skin'])

    def label_x(self): return 1440 if len(self.items) < 2 else 960

    def default_zoom(self): return 1.08

    def camera(self, u):
        z, fx, fy, r = super().camera(u); return z, fx, fy, 0.0


class Map(Shot):
    kind = "map"; vig = .55

    def __init__(self, *a):
        super().__init__(*a); self.setname = "map"; self.dark_ok = False
        pl = self.spec.get("places", [{"name": "A"}, {"name": "B"}]); n = len(pl)
        for i, p in enumerate(pl):
            p.setdefault("x", 420 + i * (1080 / max(1, n - 1)) if n > 1 else 960); p.setdefault("y", 640 - (i % 2) * 110)
        self.places = pl; self.rt = self.cue(self.spec.get("at"), .15); self.events.append(("whoosh", self.rt))

    def light_on(self): return False

    def world(self, c, t):
        self.draw_bg(c); pl = self.places; dur = max(1.2, min(2.6, (self.t1 - self.rt) * .7)); u = ease(K(t, self.rt, dur)) * (len(pl) - 1)
        for p in pl:
            for k_, a_ in ((46, 30), (28, 60)): c.drawCircle(p["x"], p["y"], k_, fp('#FFD98A', a_))
            circ(c, p["x"], p["y"], 13, '#FFE9A0', LW * .7); label(c, p["name"], p["x"], p["y"] + 90, fit_size(p["name"], 62, 440), CREAM, align='center', stroke=10)
        def arc(P0, P1, f): return lerp(P0["x"], P1["x"], f), lerp(P0["y"], P1["y"], f) - 190 * math.sin(math.pi * f)
        for j in range(len(pl) - 1):
            seg = min(max(u - j, 0), 1)
            for i in range(0, 41, 2):
                if i / 40 <= seg: c.drawCircle(*arc(pl[j], pl[j + 1], i / 40), 7, fp(RED))
        if u > 0 and len(pl) > 1:
            j = min(int(u), len(pl) - 2); self.vehicle(c, arc(pl[j], pl[j + 1], min(u - j, 1)), t)

    def vehicle(self, c, pos, t):
        v = self.spec.get("vehicle", "train"); c.save(); c.translate(pos[0], pos[1] - 34)
        if v == "plane":
            poly(c, [(-70, 0), (60, -10), (80, 0), (60, 10)], '#E8E8F0', LW * .8); poly(c, [(-10, -4), (20, -60), (34, -60), (20, -4)], '#C8242C', LW * .7); poly(c, [(-60, -2), (-50, -34), (-40, -34), (-44, -2)], '#C8242C', LW * .7)
        elif v == "ship":
            poly(c, [(-80, 0), (80, 0), (60, 30), (-60, 30)], '#C8242C', LW * .8); rect(c, -30, -40, 30, 0, '#F4EFE2', LW * .7); rect(c, -8, -66, 8, -40, INK, LW * .5)
        elif v == "car":
            from .props import ICONS
            c.scale(.35, .35); ICONS['car'](c, t, {})
        else:
            rect(c, -60, -34, 40, 20, '#2B2D3C', LW * .8); rect(c, 40, -50, 76, 20, '#C8242C', LW * .8); rect(c, -44, -58, -20, -34, '#2B2D3C', LW * .7)
            for wx in (-36, 6, 54): circ(c, wx, 24, 13, '#D0A548', LW * .6)
            for i in range(3): c.drawCircle(-34 - i * 26 - (t * 40 % 26), -76 - i * 16, 14 + i * 5, fp('#C9D4FF', 90 - i * 25))
        c.restore()

    def default_zoom(self): return 1.06


class Chart(Shot):
    kind = "chart"; vig = .5

    def __init__(self, *a):
        super().__init__(*a); self.setname = "board"; self.time = self.spec.get("time", "day"); self.night = False
        self.ch = self.spec.get("chart", {}); self.ct = self.cue(self.ch.get("at"), .08)
        if self.spec.get("who"):
            d = dict(id=self.spec["who"], x=140, face=.7, pose=self.spec.get("pose", "point"), emotion=self.spec.get("emotion", "confident"))
            self.actors.append(Actor(self, d, 140, 1060, .95, .7))
        self.events.append(("tick", self.ct))

    def world(self, c, t):
        super().world(c, t); x0, y0, x1, y1 = self.info["board"]; chalk = self.info["chalk"]
        inkc = '#F4F2E8' if chalk else INK; ch = self.ch; vals = ch.get("values", [1, 2, 3]); labs = ch.get("labels", [""] * len(vals))
        title = ch.get("title", ""); unit = ch.get("unit", ""); suf = ch.get("suffix", "")
        if title: label(c, title, (x0 + x1) / 2, y0 + 86, fit_size(title, 70, x1 - x0 - 120), inkc, font=FONT_HAND, align='center', skew=0)
        gx0, gy0, gx1, gy1 = x0 + 120, y0 + 140, x1 - 80, y1 - 90
        c.drawLine(gx0, gy1, gx1, gy1, ink(5, inkc)); c.drawLine(gx0, gy0, gx0, gy1, ink(5, inkc))
        vmax = max(max(vals), 1e-9) * 1.12; n = len(vals); hi = colr(ch.get("color"), '#FF6F61' if ch.get("trend") == "down" else '#5FCB72')
        if ch.get("type", "bar") == "bar":
            bw = (gx1 - gx0) / n * .56
            for i, v in enumerate(vals):
                u = ease_out(K(t, self.ct + i * .18, .7)); cx = gx0 + (i + .5) * (gx1 - gx0) / n; hgt = (gy1 - gy0) * v / vmax * u
                rect(c, cx - bw / 2, gy1 - hgt, cx + bw / 2, gy1, hi if i == ch.get("highlight", n - 1) else ('#8FB8D8' if not chalk else '#A8C8B8'), LW * .8)
                if u > .05 and ch.get("show_values", True): label(c, f"{unit}{fmt(v * u)}{suf}", cx, gy1 - hgt - 18, fit_size(f"{unit}{fmt(v)}{suf}", 48, bw * 1.6), inkc, align='center', skew=0)
                label(c, str(labs[i]) if i < len(labs) else "", cx, gy1 + 56, fit_size(str(labs[i]) if i < len(labs) else "", 42, bw * 1.8), inkc, align='center', skew=0)
        else:
            u = ease(K(t, self.ct, min(2.4, (self.t1 - self.ct) * .7))); pts = [(gx0 + 30 + i * (gx1 - gx0 - 60) / max(1, n - 1), gy1 - (gy1 - gy0) * v / vmax) for i, v in enumerate(vals)]
            p = skia.Path(); p.moveTo(*pts[0]); last = pts[0]; prev = pts[0]
            for i in range(1, n):
                seg = min(max(u * (n - 1) - (i - 1), 0), 1)
                if seg <= 0: break
                q = (lerp(pts[i - 1][0], pts[i][0], seg), lerp(pts[i - 1][1], pts[i][1], seg)); p.lineTo(*q); prev, last = pts[i - 1], q
            c.drawPath(p, ink(12, hi))
            if u > 0 and n > 1: arrow(c, prev, last, hi, 40)
            for i, (px, py) in enumerate(pts):
                if i < len(labs): label(c, str(labs[i]), px, gy1 + 56, fit_size(str(labs[i]), 42, 200), inkc, align='center', skew=0)

    def default_zoom(self): return 1.05


def fmt(v):
    if abs(v) >= 1e9: return f"{v / 1e9:.1f}B".replace(".0B", "B")
    if abs(v) >= 1e6: return f"{v / 1e6:.1f}M".replace(".0M", "M")
    if abs(v) >= 1e4: return f"{v / 1e3:.0f}K"
    if abs(v - round(v)) < 1e-6 or abs(v) >= 100: return f"{round(v):,}"
    return f"{v:.1f}"


class Counter(Shot):
    kind = "counter"; vig = .5

    def __init__(self, *a):
        super().__init__(*a); self.setname = "void"; self.night = False
        self.v = self.spec.get("value", {"to": 100}); self.ct = self.cue(self.v.get("at"), .1)
        cmp_ = self.spec.get("compare"); self.cmp = dict(cmp_, t=self.cue(cmp_.get("at"), .6)) if cmp_ else None
        self.events += [("tick", self.ct)] + ([("pop", self.cmp["t"])] if self.cmp else [])

    def build_bg(self, c): self.info = SETS["void"](c, {"color": self.spec.get("color", "#F3E6C8"), "floor": False})

    def world(self, c, t):
        self.draw_bg(c); v = self.v; u = ease_out(K(t, self.ct, v.get("dur", 1.3)))
        if t < self.ct: return
        nf = fmt if v.get("short") else (lambda q: f"{round(q):,}" if abs(v["to"]) >= 100 else f"{q:.1f}".rstrip("0").rstrip("."))
        val = lerp(v.get("from", 0), v["to"], u); txt = f"{v.get('prefix', '')}{nf(val)}{v.get('suffix', '')}"
        full = f"{v.get('prefix', '')}{nf(v['to'])}{v.get('suffix', '')}"; size = fit_size(full, 240, 1500, MARKER); pu = pop(K(t, self.ct, .3))
        y = 470 if self.cmp or self.spec.get("caption") else 600
        c.save(); c.translate(960, y); c.rotate(-3); c.scale(pu, pu); label(c, txt, 0, 0, size, colr(v.get("color"), LIME), font=MARKER, align='center', stroke=0, skew=0)
        c.restore()
        if self.spec.get("icon"): draw_prop(c, self.spec["icon"], 300, 560, .9 * back(K(t, self.ct, .4), 1.5), t)
        cap = self.spec.get("caption")
        if cap: label(c, cap, 960, y + 130, fit_size(cap, 80, 1500), INK, align='center', skew=-0.1, alpha=K(t, self.ct + .3, .3))
        if self.cmp and t >= self.cmp["t"]:
            k = back(K(t, self.cmp["t"], .35), 1.4); c.save(); c.translate(960, 860); c.scale(k, k); c.rotate(2)
            s_ = self.cmp["text"]; size = fit_size(s_, 70, 1400); w = text_w(s_, size)
            rect(c, -w / 2 - 50, -size, w / 2 + 50, size * .55, '#FFFFFF', LW, r=20); label(c, s_, 0, 0, size, RED, align='center', skew=-0.08)
            c.restore()
            if self.cmp.get("icon"): draw_prop(c, self.cmp["icon"], 1640, 560, .8 * back(K(t, self.cmp["t"], .4), 1.5), t)

    def default_zoom(self): return 1.06


class Icon(Shot):
    kind = "icon"; vig = .5

    def __init__(self, *a):
        super().__init__(*a); self.setname = "void"; self.night = False
        ic = self.spec.get("icons", [{"name": "bulb"}]); n = len(ic); xs = {1: [960], 2: [620, 1300], 3: [460, 960, 1460]}.get(n, [300 + i * 1320 / max(1, n - 1) for i in range(n)])
        self.icons = [dict(d, t=self.cue(d.get("at"), .05 + .25 * i), x=d.get("x", xs[i]), y=d.get("y", 470)) for i, d in enumerate(ic)]
        self.events += [("pop", d["t"]) for d in self.icons]
        for d in self.spec.get("chars", []): self.actors.append(Actor(self, d, d.get("x", 1650), 1010, d.get("s", .8), d.get("face", -.6)))

    def build_bg(self, c): self.info = SETS["void"](c, {"color": self.spec.get("color", "#F3E6C8"), "floor": bool(self.spec.get("chars"))})

    def world(self, c, t):
        super().world(c, t)
        for d in self.icons:
            if t < d["t"]: continue
            k = back(K(t, d["t"], .4), 1.6); fl = 8 * math.sin((t - d["t"]) * 2.2); sc = d.get("s", 1.6 if len(self.icons) == 1 else 1.2 if len(self.icons) == 2 else .95)
            draw_prop(c, d["name"], d["x"], d["y"] + fl, sc * k, t, **{x: v for x, v in d.items() if x not in ("name", "x", "y", "s", "at", "t", "label")})
            if d.get("label"):
                s_ = d["label"]; label(c, s_, d["x"], d["y"] + 210 * sc + 70, fit_size(s_, 80, 620 if len(self.icons) < 3 else 520), INK, align='center', skew=-0.1, alpha=K(t, d["t"] + .2, .2))

    def label_x(self): return 960 if len(self.icons) > 1 else 1440

    def default_zoom(self): return 1.06


class ListItem(Shot):
    kind = "list"; vig = .5

    def __init__(self, *a):
        super().__init__(*a); self.setname = "void"; self.night = False
        if self.spec.get("who"):
            d = dict(id=self.spec["who"], emotion=self.spec.get("emotion", "confident"), pose=self.spec.get("pose", "explain"), beats=self.spec.get("char_beats", []))
            self.actors.append(Actor(self, d, 1500, 1010, 1.0, -.6))
        self.events.append(("pop", self.t0 + .1))

    def build_bg(self, c): self.info = SETS["void"](c, {"color": self.spec.get("color", "#F3E6C8"), "floor": bool(self.spec.get("who"))})

    def world(self, c, t):
        super().world(c, t); n = self.spec.get("number", 1); txt = self.spec.get("text", "")
        cx = 700 if self.actors else 960; number_badge(c, n, cx, 300, t - self.t0 - .1, colr(self.spec.get("badge"), GOLD))
        lines = wrap(txt, 110, 1000 if self.actors else 1500)
        size = 110 if len(lines) <= 2 else 84; lines = wrap(txt, size, 1000 if self.actors else 1500)
        for i, ln in enumerate(lines[:3]):
            a = K(t, self.t0 + .35 + i * .15, .25); label(c, ln, cx, 560 + i * size * 1.1, size, INK, font=FONT_HAND, align='center', skew=0, alpha=a)
        u = K(t, self.t0 + .5, .5)
        if u > 0 and lines:
            w_ = min(1300, text_w(lines[0], size, FONT_HAND)) * ease(u); y = 560 + (min(3, len(lines)) - 1) * size * 1.1 + 40
            c.drawLine(cx - w_ / 2, y, cx + w_ / 2, y + 6, ink(14, colr(self.spec.get("badge"), GOLD)))

    def default_zoom(self): return 1.05


class Versus(Shot):
    kind = "versus"; vig = .45

    def __init__(self, *a):
        super().__init__(*a); self.setname = "void"; self.night = False
        self.sides = []
        for side, x, face in (("left", 520, .5), ("right", 1400, -.5)):
            d = dict(self.spec.get(side, {})); d.setdefault("x", x); d.setdefault("face", face)
            if d.get("who"):
                d["id"] = d["who"]; self.actors.append(Actor(self, d, x, 1000, d.get("s", 1.0), face))
            self.sides.append(dict(d, t=self.cue(d.get("at"), .05 if side == "left" else .45)))
        self.events += [("pop", s_["t"]) for s_ in self.sides]

    def build_bg(self, c):
        lc, rc = self.spec.get("colors", ['#BFD9F2', '#F6C7B6'])
        c.drawRect(skia.Rect(-900, -700, 960, H + 700), fp(lc)); c.drawRect(skia.Rect(960, -700, W + 900, H + 700), fp(rc))
        c.drawRect(skia.Rect(-900, 1000, W + 900, H + 700), fp((0, 0, 0), 40)); line(c, -900, 1000, W + 900, 1000, LW)
        self.info = dict(floor=1000, ambient=None, lights=[], bulbs=[])

    def world(self, c, t):
        self.draw_bg(c)
        for a in self.actors:
            side = next(s_ for s_ in self.sides if s_.get("id") == a.d["id"])
            if t >= side["t"] - .05: a.draw(c, t)
        zz = skia.Path(); zz.moveTo(960, -700)
        for i in range(30): zz.lineTo(960 + (24 if i % 2 else -24), -700 + i * 80)
        c.drawPath(zz, ink(LW * 1.4)); u = K(t, self.t0 + .2, .35)
        if u > 0:
            c.save(); c.translate(960, 520); k = back(u, 1.6); c.scale(k, k); circ(c, 0, 0, 92, RED, LW * 1.2); label(c, "VS", 0, 34, 100, '#FFFFFF', font=MARKER, align='center', skew=0); c.restore()
        for s_ in self.sides:
            if s_.get("title"): poplabel(c, s_["title"], s_["x"], 180, t - s_["t"], 100, CREAM if s_["x"] < 960 else LIME, -3 if s_["x"] < 960 else 3)

    def default_zoom(self): return 1.04


class Crowd(Shot):
    kind = "crowd"; vig = .55

    def __init__(self, *a):
        super().__init__(*a); self.setname = self.setname or "void"
        n = int(self.spec.get("count", 21)); r = random.Random(n); palette = ['#3B4660', '#7A5A3C', '#5A6B4A', '#6A4A6A', '#3F5F72', '#8A3A3A', '#C9A04A', '#2F6B9A']
        self.people = []
        rows = 3; per = math.ceil(n / rows)
        for i in range(n):
            row = i // per; x = 160 + (i % per) * (1600 / max(1, per - 1)) + (row % 2) * 40; y = 760 + row * 120; s = .42 + row * .1
            look = make_look(dict(skin=r.choice(list(SKINS)), outfit=r.choice(['suit', 'hoodie', 'tshirt', 'dress']), color=r.choice(palette),
                                  hair=r.choice(['short', 'slick', 'bun', 'long', 'curly', 'bald']), hair_col=r.choice(['#1C1B22', '#6B4A2A', '#C9A04A', '#8A8A92'])))
            self.people.append((x, y, s, look, r.uniform(-.6, .6), r.uniform(0, 6)))
        hid = self.spec.get("highlight"); self.hl = None
        if hid:
            self.hl = dict(t=self.cue(self.spec.get("at"), .5)); mid = len(self.people) // 2 + per // 2
            x, y, s, _, f, ph = self.people[min(mid, n - 1)]; self.people[min(mid, n - 1)] = (x, y, s, self.cast[hid], f, ph); self.hl.update(x=x, y=y, s=s)
            self.events.append(("scribble", self.hl["t"]))

    def build_bg(self, c):
        o = dict(self.spec); o.setdefault("time", self.time); o["floor"] = False; self.info = SETS[self.setname](c, o)

    def world(self, c, t):
        self.draw_bg(c); em = self.spec.get("emotion", "neutral"); e = EMOTIONS.get(em, EMOTIONS["neutral"])
        for (x, y, s, look, f, ph) in self.people:
            draw_char(c, x, y, s, look, face=f, eyes='closed' if blink(t, 2.6, ph) else e[0], mouth=e[1], brow=e[2], brow_tilt=e[3],
                      bob=3 * abs(math.sin(t * 2 + ph)), tilt=2 * math.sin(t * 1.7 + ph), light=-1)
        if self.hl: ring(c, self.hl["x"], self.hl["y"] - 330 * self.hl["s"], 190 * self.hl["s"] + 40, 330 * self.hl["s"] + 40, (t - self.hl["t"]) / .45)

    def light_on(self): return self.time != "day"
    def extra_lights(self): return []


KINDS = dict(wide=Wide, dialogue=Wide, walk=Walk, closeup=Closeup, title=Title, skyline=Skyline, table=Table, map=Map, chart=Chart,
             counter=Counter, icon=Icon, list=ListItem, versus=Versus, crowd=Crowd)


def build(sh, tl, cast, env):
    k = sh["spec"].get("kind", "wide")
    if k not in KINDS: raise SystemExit(f"shot {sh['k']}: unknown kind '{k}'. Kinds: {', '.join(KINDS)}")
    s = KINDS[k](sh, tl, cast, env); s.prepare(); return s
