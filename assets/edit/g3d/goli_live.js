// Goli alive (living studio plan, owner 2026-11-25): the rigged Goli (assets/goli3d/live/goli.glb, built once in
// Blender by tools/goli3d_rig.py) played in the video by three.js. He is never frozen: he breathes, blinks (half,
// closed, half; a double blink now and then), glances, nods while he talks, lip-syncs from the Rhubarb cues, and plays
// the moves the storyboard asks for (explain, point at the screen, type, think, wave, shrug, lean in, glasses push).
// Deterministic: the same plan and time always give the same frame (seeded blinks and glances, no clocks).
//
// Coordinates in this file are Blender's (x right, y away from the camera, z up); three.js is x, z, -y.
import * as THREE from 'three';
import { GLTFLoader } from '../examples/jsm/loaders/GLTFLoader.js';
import { RoomEnvironment } from '../examples/jsm/environments/RoomEnvironment.js';

const D = Math.PI / 180;
const ease = (t) => { t = Math.min(1, Math.max(0, t)); return t * t * (3 - 2 * t); };
const V = (b) => new THREE.Vector3(b[0], b[2], -b[1]);
const rand = (seed) => () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };

// the camera of the sprite library (goli3d/model.py "full"): he drops in where the sprites stood
const CAMERA = { pos: [0.5, -7.0, 1.55], target: [0, 0, 1.2], lens: 80, sensor: 36 };

// where he can look (Blender coordinates, in his own space; the studio TV is to his left on the long set: screen
// right from the camera, so his left/our right)
export const TARGETS = {
  camera: [0.5, -7.0, 1.55], screen: [3.2, 1.5, 2.6], laptop: [0, -1.1, 0.95], mug: [-1.0, -1.2, 1.0],
  up: [0.6, -3, 4.2], down: [0, -2.5, 0.4], left: [-3.5, -3, 1.9], right: [3.5, -3, 1.9],
};

// moves: arm directions (aim), bone turns in degrees (rot: [nod, turn, tilt] on the bone), mouth or lids held,
// keyed at seconds from the move's start; they blend in and out of his idle smoothly
const arm = (side, upper, fore) => ({ [`upper_arm${side}`]: upper, [`forearm${side}`]: fore });
const both = (upper, fore) => ({ ...arm('L', [-upper[0], upper[1], upper[2]], [-fore[0], fore[1], fore[2]]), ...arm('R', upper, fore) });
export const MOVES = {
  explain: { dur: 1.8, keys: [
    { t: 0.35, aim: both([0.35, -0.55, -0.75], [-0.15, -1, 0.3]) },
    { t: 0.9, aim: both([0.4, -0.6, -0.7], [0.05, -1, 0.42]), rot: { head: [4, 0, 0] } },
    { t: 1.45, aim: both([0.35, -0.55, -0.75], [-0.1, -1, 0.3]) }] },
  open_palms: { dur: 1.6, keys: [{ t: 0.4, aim: both([0.55, -0.45, -0.7], [0.55, -0.8, 0.2]), rot: { head: [-3, 0, 0] } },
    { t: 1.2, aim: both([0.6, -0.45, -0.65], [0.65, -0.75, 0.25]) }] },
  // reach: the arm points at a real thing in the room, wherever he stands or faces
  point_screen: { paws: { R: 'point' }, dur: 2.0, look: 'screen', reach: { side: 'R', target: 'screen' }, keys: [
    { t: 0.45, rot: { head: [0, 18, 0], chest: [0, 5, 0] } }, { t: 1.6, rot: { head: [0, 20, 0], chest: [0, 5, 0] } }] },
  point_up: { paws: { R: 'point' }, dur: 1.6, keys: [{ t: 0.4, aim: arm('R', [0.45, -0.2, 0.85], [0.1, -0.15, 1]) }, { t: 1.2, aim: arm('R', [0.45, -0.2, 0.85], [0.1, -0.15, 1]) }] },
  count: { paws: { R: 'point' }, dur: 1.6, keys: [{ t: 0.4, aim: arm('R', [0.3, -0.75, -0.45], [0.05, -0.5, 0.86]) }, { t: 1.2, aim: arm('R', [0.3, -0.75, -0.45], [0.05, -0.5, 0.86]) }] },
  type: { dur: 2.4, look: 'laptop', keys: [
    { t: 0.4, aim: both([0.12, -0.7, -0.7], [-0.3, -1, -0.05]), rot: { head: [12, 0, 0], spine: [5, 0, 0] } },
    { t: 0.7, aim: both([0.12, -0.72, -0.68], [-0.32, -1, -0.12]) },
    { t: 1.0, aim: both([0.12, -0.7, -0.7], [-0.28, -1, -0.02]) },
    { t: 1.3, aim: both([0.12, -0.72, -0.68], [-0.32, -1, -0.12]) },
    { t: 1.6, aim: both([0.12, -0.7, -0.7], [-0.28, -1, -0.02]), rot: { head: [12, 0, 0], spine: [5, 0, 0] } },
    { t: 2.0, aim: both([0.12, -0.7, -0.7], [-0.3, -1, -0.05]) }] },
  think: { paws: { R: 'fist' }, dur: 2.2, look: 'up', keys: [{ t: 0.5, aim: arm('R', [0.2, -0.8, -0.55], [-0.5, -0.45, 0.75]), rot: { head: [-6, 8, 6] } },
    { t: 1.8, aim: arm('R', [0.2, -0.8, -0.55], [-0.5, -0.45, 0.75]), rot: { head: [-6, 8, 6] } }] },
  wave: { dur: 1.8, look: 'camera', keys: [
    { t: 0.4, aim: arm('R', [0.6, -0.1, 0.8], [0.25, -0.1, 1]) }, { t: 0.7, aim: arm('R', [0.6, -0.1, 0.8], [-0.15, -0.1, 1]) },
    { t: 1.0, aim: arm('R', [0.6, -0.1, 0.8], [0.25, -0.1, 1]) }, { t: 1.3, aim: arm('R', [0.6, -0.1, 0.8], [-0.1, -0.1, 1]) }] },
  shrug: { dur: 1.4, keys: [{ t: 0.4, aim: both([0.7, -0.3, -0.6], [0.8, -0.55, 0.2]), rot: { head: [0, 0, 8], neck: [-4, 0, 0] } },
    { t: 0.95, aim: both([0.7, -0.3, -0.6], [0.8, -0.55, 0.2]), rot: { head: [0, 0, 8] } }] },
  lean_in: { dur: 2.2, look: 'camera', keys: [{ t: 0.5, rot: { spine: [8, 0, 0], chest: [6, 0, 0], head: [-6, 0, 0] }, aim: both([0.15, -0.75, -0.65], [-0.3, -1, 0]) },
    { t: 1.7, rot: { spine: [8, 0, 0], chest: [6, 0, 0], head: [-6, 0, 0] }, aim: both([0.15, -0.75, -0.65], [-0.3, -1, 0]) }] },
  glasses_push: { dur: 1.3, look: 'camera', keys: [{ t: 0.45, aim: arm('R', [0.2, -0.85, -0.45], [-0.45, -0.5, 0.75]) },
    { t: 0.75, aim: arm('R', [0.2, -0.85, -0.45], [-0.45, -0.45, 0.78]), rot: { head: [-3, 0, 0] } }] },
  // picks up the real mug (studio_live.js moves it with his hand between hold.from and hold.to), sips, puts it back
  sip: { paws: { R: 'fist' }, dur: 3.0, look: 'mug', hold: { piece: 'mug', side: 'R', from: 0.55, to: 2.45 }, keys: [
    { t: 0.55, reach: { side: 'R', target: 'mug' } }, { t: 1.2, reach: { side: 'R', target: 'mouth' }, rot: { head: [-8, 0, 0] } },
    { t: 1.9, reach: { side: 'R', target: 'mouth' }, rot: { head: [-10, 0, 0] } }, { t: 2.45, reach: { side: 'R', target: 'mug' } }] },
  // seated, both hands on the desk's edge: he pushes himself back in the chair (or pulls himself in)
  push_desk: { dur: 1.3, look: 'laptop', keys: [{ t: 0.35, reach: { side: 'R', target: 'desk_r' } }, { t: 0.95, reach: { side: 'R', target: 'desk_r' } }],
    also: { side: 'L', target: 'desk_l' } },
  // his hand on the chair's back as he rolls it away to get up, or pulls it in to sit (studio_live.js moves the chair)
  push_chair: { dur: 1.4, look: 'chair', keys: [{ t: 0.4, reach: { side: 'R', target: 'chair' }, rot: { chest: [0, 25, 0], head: [0, 20, 0] } },
    { t: 1.0, reach: { side: 'R', target: 'chair' }, rot: { chest: [0, 25, 0], head: [0, 20, 0] } }] },
  // closes (or opens) the laptop's lid with one hand on its top edge
  lid: { dur: 1.5, look: 'laptop', keys: [{ t: 0.45, reach: { side: 'R', target: 'lid' }, rot: { head: [10, 0, 0] } },
    { t: 1.05, reach: { side: 'R', target: 'lid' }, rot: { head: [12, 0, 0] } }] },
  // takes his glasses off (the pair moves to his paw), holds them at his chest a moment, puts them back
  glasses_off: { dur: 4.2, off: [0.62, 3.45], keys: [{ t: 0.55, reach: { side: 'R', target: 'nose' } },
    { t: 1.3, reach: { side: 'R', target: 'chest' }, rot: { head: [-4, 0, 3] } }, { t: 2.9, reach: { side: 'R', target: 'chest' }, rot: { head: [-4, 0, 3] } },
    { t: 3.4, reach: { side: 'R', target: 'nose' } }, { t: 3.9, reach: { side: 'R', target: 'nose' } }] },
  // the arm where the sprite pose had it (model.py POSES thumbs_up), so the thumb stands up as in the sprites
  thumbs_up: { dur: 1.6, paws: { R: 'thumb' }, look: 'camera', keys: [{ t: 0.4, aim: arm('R', [0.23, -0.3, -0.2], [-0.08, -0.25, 0.22]) , rot: { handR: [0, -70, 0] } },
    { t: 1.2, aim: arm('R', [0.23, -0.3, -0.2], [-0.08, -0.25, 0.22]), rot: { head: [4, 0, -3], handR: [0, -70, 0] } }] },
  both_up: { paws: { L: 'point', R: 'point' }, dur: 1.4, keys: [{ t: 0.35, aim: both([0.5, -0.1, 0.85], [0.1, -0.1, 1]) }, { t: 1.0, aim: both([0.5, -0.1, 0.85], [0.1, -0.1, 1]) }] },
};

// Blender renders Goli with AgX and the "Punchy" look; three.js has plain AgX only, which made him look faded
// (owner 2026-11-26: "don't change the colour of him, don't make him fade"). This is three's AgX with Blender's
// Punchy look added (power 1.35, saturation 1.4, in AgX's log space before the outset), as CustomToneMapping.
export function punchyAgX() {
  const chunk = THREE.ShaderChunk.tonemapping_pars_fragment;
  if (chunk.includes('PUNCHY_AGX')) return;
  const agx = chunk.slice(chunk.indexOf('vec3 AgXToneMapping'), chunk.indexOf('vec3 NeutralToneMapping'));
  const punchy = agx.replace('vec3 AgXToneMapping', 'vec3 PunchyAgX')
    .replace('color = agxDefaultContrastApprox( color );', `color = agxDefaultContrastApprox( color );
	color = pow( max( color, vec3( 0.0 ) ), vec3( 1.35 ) );
	float pl = dot( color, vec3( 0.2126, 0.7152, 0.0722 ) );
	color = pl + 1.4 * ( color - pl );`);
  THREE.ShaderChunk.tonemapping_pars_fragment = chunk.replace('vec3 CustomToneMapping( vec3 color ) { return color; }',
    '// PUNCHY_AGX\n' + punchy + '\nvec3 CustomToneMapping( vec3 color ) { return PunchyAgX( color ); }');
}

// the sprite library's lights (goli3d/model.py: area key 650 W, fill 160 W, rim 500 W, grey-violet world 0.35),
// matched by eye-free fitting against a Cycles render (tools: /tmp fit, 2026-11-26)
export const LIGHT = { key: 2.0, fill: 0.7, rim: 1.5, env: 0.9, ambient: 0.0, exposure: 0.9 };

export async function mount(canvas, opts = {}) {
  punchyAgX();
  const L = { ...LIGHT, ...(opts.light || {}) };
  const base = opts.base || './goli3d';
  // in the living studio (studio_live.js) he joins its scene, renderer and camera; alone he brings his own
  const renderer = opts.renderer || new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
  if (!opts.renderer) { renderer.setPixelRatio(1); renderer.setSize(canvas.width, canvas.height, false); }
  const S = (opts.place && opts.place.scale) || 1;   // his size in the room (1 = his own model units)
  renderer.toneMapping = THREE.CustomToneMapping;
  renderer.toneMappingExposure = L.exposure;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  const scene = opts.scene || new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = L.env;
  const lights = {};
  for (const [n, c, p] of [['key', 0xfff4e6, [-3.2, -4.2, 4.2]], ['fill', 0xd8e6ff, [4, -3.5, 2.2]], ['rim', 0xfff2d8, [1.5, 3.5, 3.5]]]) {
    const l = new THREE.DirectionalLight(c, L[n]); l.position.copy(V(p)); scene.add(l); lights[n] = l;
  }
  // soft self-shadows from the key (an arm in front of the body, the head over the chest), as Cycles has
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  const ks = lights.key; ks.castShadow = true; ks.shadow.mapSize.set(2048, 2048);
  Object.assign(ks.shadow.camera, { left: -1.8 * S, right: 1.8 * S, top: 2.6 * S, bottom: -0.4 * S, near: 0.1, far: 30 });
  ks.shadow.normalBias = 0.025; ks.shadow.radius = 6; ks.target.position.set(0, 1.1, 0); scene.add(ks.target);
  lights.ambient = new THREE.AmbientLight(0xbfbdcc, L.ambient); scene.add(lights.ambient);
  const setLight = (x) => { Object.assign(L, x); for (const n of ['key', 'fill', 'rim', 'ambient']) lights[n].intensity = L[n];
    scene.environmentIntensity = L.env; renderer.toneMappingExposure = L.exposure; };
  const CAM = { ...CAMERA, ...(opts.camera || {}) };
  const aspect = opts.renderer ? 1 : canvas.width / canvas.height;
  // Blender's AUTO sensor fit: the sensor spans the longer side of the frame
  const half = Math.atan(CAM.sensor / 2 / CAM.lens);
  const vfov = aspect >= 1 ? 2 * Math.atan(Math.tan(half) / aspect) : 2 * half;
  const cam = opts.cameraObj || new THREE.PerspectiveCamera(vfov / D, aspect, 0.1, 100);
  if (!opts.cameraObj) { cam.position.copy(V(CAM.pos)); cam.lookAt(V(CAM.target)); }
  if (opts.floor) {                               // a floor that only shows his shadow (for scenes without the studio)
    const fl = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.ShadowMaterial({ opacity: 0.35 }));
    fl.rotation.x = -Math.PI / 2; fl.receiveShadow = true; scene.add(fl);
  }

  const [gltf, rig] = await Promise.all([new GLTFLoader().loadAsync(`${base}/goli.glb`), fetch(`${base}/goli-rig.json`).then((r) => r.json())]);
  const root = gltf.scene;
  const holder = new THREE.Group(); holder.add(root); holder.scale.setScalar(S); scene.add(holder);
  root.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; o.frustumCulled = false; } });
  if (opts.mirror) root.scale.x = -1;
  const bones = {}; root.traverse((o) => { if (o.isBone) bones[o.name] = o; });
  const rest = {}; for (const k in bones) rest[k] = bones[k].quaternion.clone();
  const swaps = [];
  root.traverse((o) => { const m = o.name.match(/^(mouth|lid|glasses|held|pawL|pawR)_([A-Za-z_]+?)__/); if (m) swaps.push([m[1], m[2], o]); });
  const kit = rig.kits[opts.kit || 'royal'];
  root.traverse((o) => { if (o.material && kit) for (const s of ['body', 'trim', 'sleeve']) if (o.material.name === s && kit[s]) o.material.color = new THREE.Color(kit[s]); });
  const glasses = opts.glasses || 'round_gold';

  const Y = new THREE.Vector3(0, 1, 0);
  const restDir = {};
  root.updateMatrixWorld(true);
  for (const k in bones) {                      // each bone's rest direction in the world (for blending aims)
    const q = new THREE.Quaternion(); bones[k].getWorldQuaternion(q); restDir[k] = Y.clone().applyQuaternion(q);
  }
  function aimTo(name, d, w) {                   // turn a bone toward a world direction, by weight w
    const b = bones[name]; if (!b || w <= 0) return;
    b.parent.updateWorldMatrix(true, false);
    const pq = new THREE.Quaternion(); b.parent.getWorldQuaternion(pq);
    const local = d.clone().normalize().applyQuaternion(pq.invert());
    const cur = Y.clone().applyQuaternion(b.quaternion);
    const turn = new THREE.Quaternion().setFromUnitVectors(cur, local);
    b.quaternion.premultiply(new THREE.Quaternion().slerp(turn, w));
    b.updateWorldMatrix(false, true);
  }
  function turnBone(name, deg, w) {
    const b = bones[name]; if (!b || w <= 0) return;
    b.quaternion.multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(deg[0] * D * w, deg[1] * D * w, deg[2] * D * w)));
  }
  const EYE_MAX = 24 * D;                        // eyes turn at most this far in the head; the head does the rest
  function lookAt(name, pt, w) {
    const b = bones[name]; if (!b) return;
    b.updateWorldMatrix(true, false);
    const p = new THREE.Vector3(); b.getWorldPosition(p);
    const want = V(pt).sub(p).normalize();
    const now = new THREE.Vector3(0, 1, 0).applyQuaternion(b.getWorldQuaternion(new THREE.Quaternion()));
    const ang = now.angleTo(want);
    if (ang > EYE_MAX) want.copy(now.clone().lerp(want, EYE_MAX / ang).normalize());
    aimTo(name, want, w);
  }

  // the plan: {cues: [[t, 'A'..'X']], moves: [{name, at}], looks: [{at, target}], talk: [[t0, t1]], seed}
  const plan = opts.plan || {};
  const seed = plan.seed || 7;
  const blinks = [];                              // seeded blink times
  { const r = rand(seed); let t = 0.8 + r() * 1.5; let n = 0;
    while (t < (plan.duration || 600)) { blinks.push(t); n += 1; if (n % 4 === 0) blinks.push(t + 0.32); t += 2.4 + r() * 2.8; } }
  const glances = [];                             // small eye moves around the current target
  { const r = rand(seed * 3 + 1); let t = 0.6; while (t < (plan.duration || 600)) { glances.push([t, (r() - 0.5) * 0.5, (r() - 0.5) * 0.3]); t += 1.1 + r() * 1.8; } }
  const cues = (plan.cues || []).slice().sort((a, b) => a[0] - b[0]);
  // speech-driven gestures (owner 2026-11-26: "the moves have to be real and smooth, like real talking"). From the
  // spoken words (plan.words = [[start, end, word]]): each sentence opens with a gesture chosen by what it says
  // (a number counts, "you" opens the palms, "this/look/here" points at the screen, a question shrugs, "think"
  // thinks, otherwise explain or open palms, never the same twice running), and stressed words (numbers, long or
  // capitalised words, the word before a comma) get a beat: a small drop of the hand and a nod. Seeded: the same words
  // always give the same performance. Moves written in the plan always win.
  const words = (plan.words || []).map((w) => (Array.isArray(w) ? w : [w.start, w.end, w.word || w.text]));
  const autoMoves = [], beats = [];
  if (plan.auto !== false && words.length) {
    const r = rand(seed * 7 + 3);
    let last = '', busyTill = -1, sentenceStart = true, side = 'R';
    for (let i = 0; i < words.length; i++) {
      const [ws, we, raw] = words[i]; const w = String(raw || '');
      const clean = w.toLowerCase().replace(/[^a-z0-9']/g, '');
      if (sentenceStart && ws >= busyTill) {
        const ahead = words.slice(i, i + 10).map((x) => String(x[2] || '').toLowerCase()).join(' ');
        let pick = /\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|first|second|third)\b/.test(ahead) ? 'count'
          : /\b(this|look|here|see|screen)\b/.test(ahead) ? 'point_screen'
          : /\?/.test(ahead) ? 'shrug'
          : /\b(think|wonder|maybe|imagine)\b/.test(ahead) ? 'think'
          : /\b(you|your)\b/.test(ahead) ? 'open_palms'
          : r() < 0.55 ? 'explain' : 'open_palms';
        if (pick === last) pick = pick === 'explain' ? 'open_palms' : 'explain';
        if (r() < 0.8) { autoMoves.push({ name: pick, at: ws + 0.05, auto: true }); last = pick; busyTill = ws + MOVES[pick].dur + 0.3; }
      }
      sentenceStart = /[.!?]$/.test(w);
      const stressed = /\d/.test(w) || clean.length >= 7 || /^[A-Z]/.test(w) && i > 0 || /,$/.test(w);
      if (stressed && (!beats.length || ws - beats[beats.length - 1][0] > 0.6)) {
        if (r() < 0.35) side = side === 'R' ? 'L' : 'R';
        beats.push([ws + 0.05, 0.6 + 0.4 * r(), side]);
      }
    }
  }
  // how people talk (owner 2026-11-26): a sentence often starts with a short look away while the thought forms, a blink
  // lands on the pause between sentences, and the head settles into a slightly different tilt for each sentence
  const sentences = [];                           // [start, tilt, glance or null]
  { const r = rand(seed * 13 + 5); let start = true;
    for (const [ws, , raw] of words) {
      if (start) sentences.push([ws, (r() - 0.5) * 8, r() < 0.4 ? [r() < 0.5 ? 'up' : (r() < 0.5 ? 'left' : 'right'), 0.35 + r() * 0.4] : null]);
      start = /[.!?]$/.test(String(raw || ''));
    }
    for (const [st] of sentences) if (st > 0.5) blinks.push(st - 0.12);
    blinks.sort((a, b) => a - b); }
  const written = (plan.moves || []).filter((m) => MOVES[m.name]);
  const moves = [...written, ...autoMoves.filter((a) => !written.some((m) => a.at < m.at + MOVES[m.name].dur + 0.2 && m.at < a.at + MOVES[a.name].dur + 0.2))]
    .sort((a, b) => a.at - b.at);
  const looks = (plan.looks || [{ at: 0, target: 'camera' }]).slice().sort((a, b) => a.at - b.at);

  const lidAt = (t) => {
    for (const b of blinks) { const d = t - b; if (d >= 0 && d < 0.2) return d < 0.05 || d >= 0.15 ? 'half' : 'closed'; if (b > t) break; }
    return 'open';
  };
  const mouthAt = (t) => { let s = 'X'; for (const [ct, sh] of cues) { if (ct > t) break; s = sh; } return s; };
  const TG = { ...TARGETS, ...(opts.targets || {}) };   // in the studio: real points of the room
  function targetPoint(name) {                    // a world point (three.js) to reach for
    if (name === 'nose' || name === 'chest') {    // his own face and chest, wherever he is
      const h = new THREE.Vector3(); bones[name === 'nose' ? 'head' : 'chest'].getWorldPosition(h);
      const fwd = new THREE.Vector3(0, 0, 1).applyQuaternion(holder.quaternion);
      return name === 'nose' ? h.add(fwd.multiplyScalar(0.7 * S)).add(new THREE.Vector3(0, 0.42 * S, 0))
        : h.add(fwd.multiplyScalar(0.75 * S)).add(new THREE.Vector3(0.1 * S, 0.05 * S, 0));
    }
    if (name === 'mouth') {
      const h = new THREE.Vector3(); bones.head.getWorldPosition(h);
      const fwd = new THREE.Vector3(0, 0, 1).applyQuaternion(holder.quaternion);
      return h.add(fwd.multiplyScalar(0.62 * S)).add(new THREE.Vector3(0, -0.08 * S, 0));
    }
    return V(pointOf(name));
  }
  const pointOf = (target) => (Array.isArray(target) ? target : TG[target] || TG.camera);
  function gazeAt(t) {                            // where his eyes go, eased between targets (0.25 s)
    let cur = pointOf(looks[0].target), prev = cur, since = 99;
    for (let k = 0; k < looks.length && looks[k].at <= t; k++) { prev = k ? pointOf(looks[k - 1].target) : cur; cur = pointOf(looks[k].target); since = t - looks[k].at; }
    const m = moves.find((mv) => t >= mv.at && t < mv.at + MOVES[mv.name].dur && MOVES[mv.name].look);
    if (m) { prev = cur; cur = pointOf(MOVES[m.name].look); since = t - m.at; }
    const f = ease(since / 0.25);
    const p = [0, 1, 2].map((i) => prev[i] + (cur[i] - prev[i]) * f);
    let g = [0, 0]; for (const [gt, gx, gz] of glances) { if (gt > t) break; g = [gx, gz]; }
    // a look away at the start of a sentence (eased out and back)
    for (const [st, , look] of sentences) {
      if (!look || t < st - 0.1 || t > st + look[1] + 0.25) continue;
      const k = Math.min(ease((t - st + 0.1) / 0.15), ease((st + look[1] + 0.25 - t) / 0.25));
      const q = pointOf(look[0]);
      return [p[0] + (q[0] - p[0]) * k * 0.6, p[1] + (q[1] - p[1]) * k * 0.6, p[2] + (q[2] - p[2]) * k * 0.6];
    }
    return [p[0] + g[0], p[1], p[2] + g[1]];
  }
  function moveAt(t) {                            // the active move's pose and its weight
    for (const m of moves) {
      const M = MOVES[m.name], d = t - m.at;
      if (d < 0 || d >= M.dur) continue;
      const w = Math.min(ease(d / 0.35), ease((M.dur - d) / 0.4));
      let a = M.keys[0], b = M.keys[M.keys.length - 1];
      for (let k = 0; k < M.keys.length - 1; k++) if (d >= M.keys[k].t && d < M.keys[k + 1].t) { a = M.keys[k]; b = M.keys[k + 1]; }
      const f = a === b ? 0 : ease((d - a.t) / (b.t - a.t));
      return { a, b, f, w, name: m.name };
    }
    return null;
  }
  const glassesOff = (t) => moves.some((m) => { const G = MOVES[m.name].off, d = t - m.at; return G && d >= G[0] && d < G[1]; });
  const talking = (t) => (plan.talk || []).some(([a, b]) => t >= a && t < b) || mouthAt(t) !== 'X';

  // where he stands and faces: plan.path = [{at, x, y, face}] (Blender metres on the floor, face in degrees, 0 = the
  // camera, 90 = his left). Between keys he WALKS: the legs step by the distance covered (no sliding feet), the body
  // turns toward where he goes, then to the key's facing when he arrives.
  const path = (plan.path || [{ at: 0, x: 0, y: 0, face: 0 }]).slice().sort((a, b) => a.at - b.at);
  const STRIDE = 0.42;                            // metres per step (one leg)
  const walkLen = [0];                            // distance walked up to each key
  for (let k = 1; k < path.length; k++) walkLen.push(walkLen[k - 1] + Math.hypot(path[k].x - path[k - 1].x, path[k].y - path[k - 1].y));
  const angDiff = (a, b) => ((b - a + 540) % 360) - 180;
  function placeAt(t) {
    let k = 0; while (k < path.length - 1 && path[k + 1].at <= t) k++;
    const a = path[k], b = path[Math.min(k + 1, path.length - 1)];
    if (a === b || t <= a.at) return { x: a.x, y: a.y, face: a.face || 0, walk: 0, dist: walkLen[k], moving: false };
    const span = b.at - a.at, d = Math.hypot(b.x - a.x, b.y - a.y);
    if (b.glide) {                                // carried (he rolls back in his chair): no steps, same facing
      const f = ease((t - a.at) / span);
      return { x: a.x + (b.x - a.x) * f, y: a.y + (b.y - a.y) * f, face: (a.face || 0) + angDiff(a.face || 0, b.face || 0) * f, walk: 0, dist: walkLen[k], moving: false };
    }
    if (d < 0.01) { const f = ease((t - a.at) / Math.min(span, 0.8)); return { x: a.x, y: a.y, face: (a.face || 0) + angDiff(a.face || 0, b.face || 0) * f, walk: 0, dist: walkLen[k], moving: false }; }
    // turn toward the way (0.35 s), walk with an eased start and stop, turn to the new facing (0.35 s)
    const head = Math.atan2(b.x - a.x, -(b.y - a.y)) / D;   // facing angle that walks toward b
    const u = (t - a.at) / span;
    const tw = Math.min(0.35 / span, 0.25);
    const p = u < tw ? 0 : u > 1 - tw ? 1 : (u - tw) / (1 - 2 * tw);
    const pe = p * p * (3 - 2 * p) * 0.15 + p * 0.85;          // mostly steady pace, soft at both ends
    let face = head;
    if (u < tw) face = (a.face || 0) + angDiff(a.face || 0, head) * ease(u / tw);
    else if (u > 1 - tw) face = head + angDiff(head, b.face || 0) * ease((u - (1 - tw)) / tw);
    const walk = u < tw || u > 1 - tw ? 0 : Math.min(1, Math.min(p, 1 - p) * 8);
    return { x: a.x + (b.x - a.x) * pe, y: a.y + (b.y - a.y) * pe, face, walk, dist: walkLen[k] + d * pe, moving: walk > 0 };
  }
  const groundZ = (opts.place && opts.place.floorZ) || 0;
  const seatZ = (opts.place && opts.place.seatZ) || groundZ;
  // seated or standing: plan.sit = [[t, 1|0], ...]; getting up or down takes 0.9 s with a lean forward
  const sits = (plan.sit || []).slice().sort((a, b) => a[0] - b[0]);
  function sitAt(t) {
    let v = sits.length ? sits[0][1] : 0, from = v, since = 99;
    for (let k = 0; k < sits.length && sits[k][0] <= t; k++) { from = k ? sits[k - 1][1] : sits[k][1]; v = sits[k][1]; since = t - sits[k][0]; }
    const f = ease(since / 0.9), w = from + (v - from) * f;
    const lean = since < 0.9 && from !== v ? 22 * Math.sin(Math.PI * since / 0.9) : 0;
    return { w, lean };
  }

  function frame(t) {
    for (const k in bones) bones[k].quaternion.copy(rest[k]);
    const at = placeAt(t);
    const sit = sitAt(t);
    holder.position.set(at.x, groundZ + (seatZ - groundZ) * sit.w, -at.y);
    holder.rotation.y = at.face * D * (opts.mirror ? -1 : 1);   // +90 = he faces (and walks) to screen right
    holder.updateMatrixWorld(true);
    if (sit.w > 0) {                              // seated: thighs forward, shins down, a little lean as he gets up
      for (const n of ['L', 'R']) { turnBone('thigh' + n, [-85, 0, 0], sit.w); turnBone('shin' + n, [80, 0, 0], sit.w); }
      turnBone('spine', [sit.lean, 0, 0], 1);
      holder.updateMatrixWorld(true);
    }
    // the key light's shadow follows him around the room
    lights.key.target.position.set(at.x, 1.1 * S, -at.y); lights.key.position.copy(V([-3.2, -4.2, 4.2])).add(lights.key.target.position).sub(new THREE.Vector3(0, 1.1, 0));
    if (at.walk > 0) {
      // a walk cycle: phase from the distance covered, so feet never slide
      const ph = (at.dist / (STRIDE * S)) * Math.PI, w = at.walk;
      const sL = Math.sin(ph), sR = Math.sin(ph + Math.PI);
      // short legs and a round body walk with a small waddle: a bigger swing, a side sway and a bounce
      turnBone('thighL', [-34 * sL, 0, 0], w); turnBone('thighR', [-34 * sR, 0, 0], w);
      turnBone('shinL', [52 * Math.max(0, Math.cos(ph)), 0, 0], w); turnBone('shinR', [52 * Math.max(0, Math.cos(ph + Math.PI)), 0, 0], w);
      turnBone('footL', [14 * sL, 0, 0], w); turnBone('footR', [14 * sR, 0, 0], w);
      holder.position.y += 0.05 * S * w * Math.abs(Math.cos(ph));
      const side = new THREE.Vector3(Math.cos(holder.rotation.y), 0, -Math.sin(holder.rotation.y));
      holder.position.addScaledVector(side, 0.035 * S * w * Math.sin(ph));
      turnBone('hips', [4, 8 * sL, 6 * Math.sin(ph)], w);
      turnBone('chest', [3, -7 * sL, -3 * Math.sin(ph)], w);
      turnBone('head', [0, 4 * sL, 2 * Math.sin(ph)], w);
      turnBone('upper_armL', [32 * sL, 0, 0], w); turnBone('upper_armR', [32 * sR, 0, 0], w);
      turnBone('forearmL', [-16 - 14 * sL, 0, 0], w); turnBone('forearmR', [-16 - 14 * sR, 0, 0], w);
      holder.updateMatrixWorld(true);
    }
    // idle: breathing (4 s), a slow weight shift, a small nod while he talks
    const br = Math.sin(t * 2 * Math.PI / 4.0);
    turnBone('spine', [1.2 * br, 0, 0.6 * Math.sin(t * 2 * Math.PI / 9)], 1);
    turnBone('chest', [0.8 * br, 0.8 * Math.sin(t * 2 * Math.PI / 11), 0], 1);
    const tk = talking(t) ? 1 : 0;
    { let tilt = 0, prev = 0, since = 9;           // this sentence's head tilt, eased in from the last one
      for (const [st, tl] of sentences) { if (st > t) break; prev = tilt; tilt = tl; since = t - st; }
      turnBone('head', [0, 0, prev + (tilt - prev) * ease(since / 0.6)], 1); }
    turnBone('head', [2.2 * Math.sin(t * 5.1) * tk + 0.8 * Math.sin(t * 0.9), 2.5 * Math.sin(t * 0.7), 1.5 * Math.sin(t * 0.5)], 1);
    // arms at rest: on the desk when seated, loose with a small bend when standing (never stiff by his sides)
    const sitw = sitAt(t).w;
    const restArms = (w0) => {
      for (const n of ['L', 'R']) {
        const sx = n === 'L' ? -1 : 1;
        const upper = sitw > 0.5 ? [0.16 * sx, -0.62, -0.77] : [0.22 * sx, -0.12, -0.97];
        const fore = sitw > 0.5 ? [-0.32 * sx, -0.95, -0.02] : [0.08 * sx, -0.5, -0.86];
        aimTo('upper_arm' + n, V(upper).applyQuaternion(holder.quaternion), w0);
        aimTo('forearm' + n, V(fore).applyQuaternion(holder.quaternion), w0);
      }
    };
    root.updateMatrixWorld(true);
    if (!(at.walk > 0)) {
      restArms(1);
      // resting hands still live: a slow drift of each forearm, out of step with the other
      turnBone('forearmL', [3 * Math.sin(t * 0.9 + 1.3), 0, 2 * Math.sin(t * 0.6)], 1);
      turnBone('forearmR', [3 * Math.sin(t * 0.8 + 0.2), 0, 2 * Math.sin(t * 0.7 + 2)], 1);
    }
    const mv = moveAt(t);
    if (mv) {
      const { a, b, f, w } = mv;
      for (const name of new Set([...Object.keys(a.rot || {}), ...Object.keys(b.rot || {})])) {
        const ra = (a.rot || {})[name] || [0, 0, 0], rb = (b.rot || {})[name] || [0, 0, 0];
        turnBone(name, [0, 1, 2].map((i) => ra[i] + (rb[i] - ra[i]) * f), w);
      }
      root.updateMatrixWorld(true);
      // reaching for a real thing (the screen, the mug, his mouth): a whole-move reach, or one per key, blended
      const RA = a.reach || MOVES[mv.name].reach, RB = b.reach || MOVES[mv.name].reach;
      if (RA || RB) {
        const dirs = (R) => {
          const sh = new THREE.Vector3(); bones['upper_arm' + R.side].getWorldPosition(sh);
          const to = targetPoint(R.target).sub(sh);
          const dist = to.length(), d = to.clone().normalize();
          // a near thing bends the elbow (the upper arm drops, the forearm comes up to it); a far one straightens it
          const bend = Math.max(0, Math.min(1, 1 - dist / (0.75 * S)));
          return { side: R.side, up: d.clone().add(new THREE.Vector3(0, -0.35 - 0.9 * bend, 0)).normalize(),
                   fore: d.clone().add(new THREE.Vector3(0, 0.15 + 0.5 * bend, 0)).normalize() };
        };
        const da = dirs(RA || RB), db = dirs(RB || RA);
        aimTo('upper_arm' + da.side, da.up.clone().lerp(db.up, f).normalize(), w);
        aimTo('forearm' + da.side, da.fore.clone().lerp(db.fore, f).normalize(), w);
        const A2 = MOVES[mv.name].also;
        if (A2) { const d2 = dirs(A2); aimTo('upper_arm' + d2.side, d2.up, w); aimTo('forearm' + d2.side, d2.fore, w); }
      }
      // shoulder to hand, in order, so each child aims from where its parent landed
      for (const name of ['upper_armL', 'forearmL', 'upper_armR', 'forearmR']) {
        const da = (a.aim || {})[name], db = (b.aim || {})[name];
        if (!da && !db) continue;
        const va = V(da || db).normalize(), vb = V(db || da).normalize();
        aimTo(name, va.clone().lerp(vb, f).applyQuaternion(holder.quaternion), w);
      }
    }
    // beats: on a stressed word the leading hand drops and comes back (0.45 s) and the head nods with it
    for (const [bt, amp, side] of beats) {
      const d = t - bt; if (d < -0.1 || d > 0.45) continue;
      const e = Math.sin(Math.PI * Math.min(1, Math.max(0, (d + 0.1) / 0.55)));
      turnBone('forearm' + side, [-14 * amp * e, 0, 0], 1);
      turnBone('upper_arm' + side, [-5 * amp * e, 0, 0], 1);
      turnBone('head', [5 * amp * e, 0, 0], 1);
    }
    const g = gazeAt(t);
    lookAt('eyeL', g, 1); lookAt('eyeR', g, 1);
    const lid = lidAt(t), mouth = mouthAt(t);
    const off = glassesOff(t);                    // the glasses are in his paw, not on his face
    const pawMv = moves.find((m) => MOVES[m.name].paws && t >= m.at + 0.15 && t < m.at + MOVES[m.name].dur - 0.2);
    const paw = { L: (pawMv && MOVES[pawMv.name].paws.L) || 'open', R: (pawMv && MOVES[pawMv.name].paws.R) || 'open' };
    for (const [kind, val, o] of swaps) o.visible = kind === 'mouth' ? val === mouth : kind === 'lid' ? val === lid
      : kind === 'held' ? val === glasses && off : kind === 'pawL' ? val === paw.L : kind === 'pawR' ? val === paw.R
      : val === glasses && !off;
    if (!opts.noRender) renderer.render(scene, cam);
  }
  frame(0);
  frame.setLight = setLight;
  frame.holding = (t) => {                        // {piece, side, w} while a move holds a thing
    for (const m of moves) { const H = MOVES[m.name].hold, d = t - m.at; if (H && d >= H.from && d <= H.to) return H; }
    return null;
  };
  frame.hand = (side) => { const h = bones['hand' + side]; h.updateWorldMatrix(true, false); return h.matrixWorld; };
  return frame;
}
