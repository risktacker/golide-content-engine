"""Frame rendering: per-shot MP4 segments in parallel (resumable), contact sheets, concat."""
import hashlib, json, math, os, random, subprocess, sys, time
import numpy as np, skia
from .kit import *
from .timeline import Timeline
from .timing import load_audio
from . import shots as SH

_G = {}


class Env:
    """Voice loudness on the output clock -> mouth shapes (open/mid/closed held 3 frames)."""
    def __init__(self, tl, voice_path, cache=None):
        if cache and os.path.exists(cache):
            self.track = json.load(open(cache)); return
        x = load_audio(voice_path, 16000); sr = 16000; N = tl.total_frames; hop = sr / FPS
        rms = np.zeros(N)
        for (a, b, o) in tl.voice_segments():
            seg = x[int(a * sr):int(b * sr)]; f0 = int(round(o * FPS)); n = int(len(seg) / hop)
            for i in range(n):
                f = f0 + i
                if 0 <= f < N: rms[f] = np.sqrt(np.mean(seg[int(i * hop):int((i + 1) * hop)] ** 2) + 1e-12)
        m = np.percentile(rms[rms > 0], 97) if (rms > 0).any() else 1.0; out = []; cur = 'closed'; held = 3
        for v in rms:
            tgt = 'open' if v > .45 * m else 'mid' if v > .14 * m else 'closed'
            if tgt != cur and held >= 3: cur = tgt; held = 0
            held += 1; out.append(cur)
        self.track = out
        if cache:
            json.dump(out, open(cache + ".tmp", "w")); os.replace(cache + ".tmp", cache)

    def mouth(self, t):
        f = int(round(t * FPS)); return self.track[f] if 0 <= f < len(self.track) else 'closed'


def load_project(P):
    story = json.load(open(os.path.join(P, "story.json"), encoding="utf-8"))
    timing = json.load(open(os.path.join(P, "timing.json"), encoding="utf-8"))
    tl = Timeline(story, timing)
    cast = {k: make_look(v) for k, v in story.get("cast", {}).items()}
    for sh in story["shots"]:  # validate cast ids early
        ids = [d.get("id") for d in sh.get("chars", [])] + [sh.get("who")] + [sh.get(s, {}).get("who") for s in ("left", "right")]
        for i in ids:
            if i and i not in cast: raise SystemExit(f"shot uses unknown cast id '{i}'. Cast: {', '.join(cast)}")
    return story, tl, cast


def voice_path(P):
    for f in sorted(os.listdir(P)):
        if f.lower().startswith("voice.") or f.lower().startswith("voiceover."): return os.path.join(P, f)
    raise SystemExit("no voice.* file in project folder")


def setup(P):
    if _G.get("P") == P: return
    story, tl, cast = load_project(P); os.makedirs(os.path.join(P, "work"), exist_ok=True)
    env = Env(tl, voice_path(P), os.path.join(P, "work", "mouth.json"))
    _G.update(P=P, story=story, tl=tl, cast=cast, env=env)


WORLD = ("wide", "dialogue", "walk", "closeup", "skyline", "crowd", "map")
DEFAULT_SET = dict(wide="office", dialogue="office", walk="street", closeup="office", skyline="skyline", crowd="void", map="map")


def whip_flags(tl):
    """Whip pans only on a change of place between two world shots (or into/out of a map or skyline).
    Graphics shots (icon, list, counter, chart, versus, table, title) hard-cut. "whip": true/false overrides."""
    out = []
    for i, s in enumerate(tl.shots):
        sp = s["spec"]; n = tl.shots[i + 1]["spec"] if i + 1 < len(tl.shots) else None; auto = False
        if n and sp.get("kind", "wide") in WORLD and n.get("kind", "wide") in WORLD:
            a = sp.get("set", DEFAULT_SET[sp.get("kind", "wide")]); b = n.get("set", DEFAULT_SET[n.get("kind", "wide")])
            auto = a != b or "map" in (sp.get("kind"), n.get("kind")) or "skyline" in (sp.get("kind"), n.get("kind"))
        out.append(bool(sp.get("whip", auto)) and not sp.get("polaroid"))
    return out


class Frame:
    """Per-shot frame buffers: the main frame plus scratch buffers for the light and glow maps."""
    def __init__(self):
        self.buf, self.surf = np_surface(); self.mbuf, self.msurf = np_surface(); self.gbuf, self.gsurf = np_surface()
        self.frozen = None; self.hero = None

    def image(self): return np_image(self.buf.copy())


def _cam(c, z, fx, fy, rot, dx=0.0, dy=0.0):
    c.save(); c.scale(OS, OS); c.translate(W / 2 + dx, H / 2 + dy); c.scale(z, z); c.rotate(rot); c.translate(-fx, -fy)


def draw_frame(shot, fr_, f, whip_in, whip_out):
    """Draw frame f of a shot into fr_.buf (HxWx4 uint8, native skia order)."""
    c = fr_.surf.getCanvas(); t = f / FPS; u = (f - shot.f0) / max(shot.f1 - shot.f0 - 1, 1)
    z, fx, fy, rot = shot.camera(u); wx = sig = 0
    if whip_out and shot.f1 - f <= 5: wx = -((6 - (shot.f1 - f)) ** 2) * 34; sig = (6 - (shot.f1 - f)) * 16
    if whip_in and f - shot.f0 < 4: wx = (4 - (f - shot.f0)) ** 2 * 52; sig = (4 - (f - shot.f0)) * 18
    shx = shy = 0
    for st in shot.shakes:
        if st <= t < st + .35: d = 1 - (t - st) / .35; shx += 16 * d * math.sin(t * 90); shy += 12 * d * math.cos(t * 77)
    pol = shot.pol
    if pol and t >= pol["t"] and fr_.frozen is not None:
        img = fr_.frozen
    else:
        dx, dy = wx + shx, shy
        c.clear(C((0, 0, 0))); _cam(c, z, fx, fy, rot, dx, dy); shot.world(c, t); c.restore()
        if shot.mask is not None:
            mc = fr_.msurf.getCanvas(); mc.clear(C((255, 255, 255))); _cam(mc, z, fx, fy, rot, dx, dy); mc.drawImage(shot.mask, -SH.PADX, -SH.PADY, LINEAR); mc.restore()
            multiply_into(fr_.buf, fr_.mbuf)
        if shot.glow is not None:
            gc = fr_.gsurf.getCanvas(); gc.clear(C((0, 0, 0))); _cam(gc, z, fx, fy, rot, dx, dy); gc.drawImage(shot.glow, -SH.PADX, -SH.PADY, LINEAR); gc.restore()
            add_into(fr_.buf, fr_.gbuf)
        _cam(c, z, fx, fy, rot, dx, dy); shot.over(c, t); c.restore()
        if not shot.card: finish(fr_.buf, bloom=.4, vig=shot.vig)
        c.save(); c.scale(OS, OS); shot.screen(c, t); c.restore(); img = None
        if pol and t >= pol["t"]:
            fr_.frozen = fr_.image(); a = shot.actor(pol.get("who"))
            fr_.hero = ((a.head[0] - fx) * z + W / 2, (a.head[1] + 60 - fy) * z + H / 2) if a else (W / 2, H / 2)
            img = fr_.frozen
    if img is not None:
        c.clear(C((12, 12, 22))); k = ease_out((t - pol["t"]) / .32)
        c.save(); c.scale(OS, OS); c.translate(W / 2, H / 2 - 56 * k); c.rotate(-4.0 * k); sc = 1 - .33 * k; c.scale(sc, sc)
        for i, a_ in enumerate((40, 30, 22)):  # soft drop shadow without a full-frame blur
            o = 14 + i * 10; c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(-W / 2 - 44 + o, -H / 2 - 44 + o, W / 2 + 44 + o, H / 2 + 170 + o), 12, 12), fp((0, 0, 0), a_))
        c.drawRect(skia.Rect(-W / 2 - 44, -H / 2 - 44, W / 2 + 44, H / 2 + 170), fp('#F7F2E6'))
        c.drawImageRect(img, skia.Rect(-W / 2, -H / 2, W / 2, H / 2), LINEAR)
        c.drawRect(skia.Rect(-W / 2, -H / 2, W / 2, H / 2), ink(4, INK, 160))
        hx_, hy_ = fr_.hero; hx_ -= W / 2; hy_ -= H / 2
        if t > pol["t"] + .3:
            cu = min((t - pol["t"] - .3) / .4, 1); r_ = skia.Path(); r_.addArc(skia.Rect(hx_ - 190, hy_ - 200, hx_ + 200, hy_ + 260), -110, 352.0 * ease(cu)); c.drawPath(r_, ink(18, RED))
        if t > pol["t"] + .68 and pol.get("caption"):
            cap = pol["caption"]; label(c, cap, -W / 2 + 40, H / 2 + 128, fit_size(cap, 118, W - 80, FONT_HAND), RED, font=FONT_HAND, skew=0, alpha=min((t - pol["t"] - .68) / .12, 1))
        c.restore(); fl = max(0, 1 - (t - pol["t"]) / .22)
        if fl > 0: c.drawRect(skia.Rect(0, 0, W, H), fp('#FFFFFF', 255 * fl))
    if sig > 0: hblur(fr_.buf, sig)
    fr_.buf[..., 3] = 255


def seg_hash(tl, i, whips):
    s = tl.shots[i]; prev = whips[i - 1] if i else False
    h = json.dumps([s["spec"], s["f0"], s["f1"], whips[i], prev, VERSION], sort_keys=True, default=str)
    return hashlib.md5(h.encode()).hexdigest()[:12]


VERSION = "rm3"
SEGS = "segs" if RES == 1080 else f"segs{RES}"


def render_shot(args):
    P, i = args; setup(P); tl = _G["tl"]; whips = whip_flags(tl); out = os.path.join(P, "work", SEGS, f"{i:04d}.mp4")
    h = seg_hash(tl, i, whips); stamp_f = out + ".ok"
    if os.path.exists(out) and os.path.exists(stamp_f) and open(stamp_f).read() == h: return i, "cached", 0.0
    t_start = time.time(); shot = SH.build(tl.shots[i], tl, _G["cast"], _G["env"]); fr_ = Frame()
    tmp = out + ".tmp.mp4"
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", PIX_FMT, "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-threads", "2", "-pix_fmt", "yuv420p", "-r", str(FPS), tmp], stdin=subprocess.PIPE)
    for f in range(shot.f0, shot.f1):
        draw_frame(shot, fr_, f, i > 0 and whips[i - 1], whips[i])
        p.stdin.write(fr_.buf.data)
    p.stdin.close()
    if p.wait() != 0: raise RuntimeError(f"ffmpeg failed on shot {i}")
    os.replace(tmp, out); open(stamp_f, "w").write(h)
    return i, "rendered", time.time() - t_start


def render_all(P, jobs=None, only=None):
    setup(P); tl = _G["tl"]; os.makedirs(os.path.join(P, "work", SEGS), exist_ok=True)
    idx = list(range(len(tl.shots))) if only is None else only
    idx.sort(key=lambda i: -(tl.shots[i]["f1"] - tl.shots[i]["f0"]))  # longest first balances the pool
    jobs = jobs or max(1, (os.cpu_count() or 2) - (0 if (os.cpu_count() or 2) <= 2 else 1))
    t0 = time.time(); done = 0; frames = sum(tl.shots[i]["f1"] - tl.shots[i]["f0"] for i in idx); fdone = 0
    if jobs == 1:
        it = (render_shot((P, i)) for i in idx)
    else:
        import multiprocessing as mp
        pool = mp.get_context("spawn").Pool(jobs); it = pool.imap_unordered(render_shot, [(P, i) for i in idx])
    for i, st, dt in it:
        done += 1; fdone += tl.shots[i]["f1"] - tl.shots[i]["f0"]; el = time.time() - t0
        eta = el / max(fdone, 1) * (frames - fdone)
        print(f"[{done}/{len(idx)}] shot {i} {st} {dt:.0f}s | {fdone / FPS:.0f}/{frames / FPS:.0f}s of video | ETA {eta / 60:.1f} min", flush=True)
    if jobs != 1: pool.close(); pool.join()
    concat(P)


def concat(P):
    setup(P); tl = _G["tl"]; segs = os.path.join(P, "work", SEGS)
    missing = [i for i in range(len(tl.shots)) if not os.path.exists(os.path.join(segs, f"{i:04d}.mp4"))]
    if missing: print("not rendered yet:", missing); return False
    lst = os.path.join(P, "work", "list.txt")
    with open(lst, "w") as fh:
        for i in range(len(tl.shots)): fh.write(f"file '{SEGS}/{i:04d}.mp4'\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", os.path.join(P, "work", "video.mp4")], check=True)
    print("video ->", os.path.join(P, "work", "video.mp4")); return True


def stills(P, which=None, fracs=(.5,), per_sheet=24, out_name="sheet"):
    """Contact sheet(s) of mid-frames. which: list of shot indices (default all)."""
    setup(P); tl = _G["tl"]; whips = whip_flags(tl); idx = which if which is not None else list(range(len(tl.shots)))
    tiles = []
    for i in idx:
        shot = SH.build(tl.shots[i], tl, _G["cast"], _G["env"])
        for q in fracs:
            f = shot.f0 + int((shot.f1 - shot.f0 - 1) * q); fr_ = Frame()
            if shot.pol and f / FPS >= shot.pol["t"]: draw_frame(shot, fr_, int(shot.pol["t"] * FPS + 1), False, False)
            draw_frame(shot, fr_, f, False, False); tiles.append((i, shot.kind, f, fr_.image()))
    tw, th, cols = 480, 270, 4; paths = []
    for s0 in range(0, len(tiles), per_sheet):
        chunk = tiles[s0:s0 + per_sheet]; rows = math.ceil(len(chunk) / cols)
        sheet = skia.Surface(cols * tw, rows * (th + 34)); c = sheet.getCanvas(); c.clear(C((20, 20, 26)))
        for j, (i, kind, f, img) in enumerate(chunk):
            x, y = (j % cols) * tw, (j // cols) * (th + 34)
            c.drawImageRect(img, skia.Rect(x + 2, y + 2, x + tw - 2, y + th - 2), skia.SamplingOptions(skia.FilterMode.kLinear))
            c.drawString(f"#{i} {kind}  {f / FPS:.1f}s", x + 8, y + th + 26, skia.Font(KALAM, 22), fp('#FFFFFF'))
        pth = os.path.join(P, "work", f"{out_name}_{s0 // per_sheet + 1}.jpg"); sheet.makeImageSnapshot().save(pth, skia.kJPEG); paths.append(pth)
    print("\n".join(paths)); return paths
