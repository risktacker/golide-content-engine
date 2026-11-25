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
  point_screen: { dur: 2.0, look: 'screen', keys: [
    { t: 0.45, aim: arm('R', [0.85, -0.1, 0.25], [1, -0.05, 0.5]), rot: { head: [0, 22, 0], chest: [0, 6, 0] } },
    { t: 1.6, aim: arm('R', [0.85, -0.12, 0.3], [1, -0.05, 0.55]), rot: { head: [0, 24, 0], chest: [0, 6, 0] } }] },
  point_up: { dur: 1.6, keys: [{ t: 0.4, aim: arm('R', [0.45, -0.2, 0.85], [0.1, -0.15, 1]) }, { t: 1.2, aim: arm('R', [0.45, -0.2, 0.85], [0.1, -0.15, 1]) }] },
  count: { dur: 1.6, keys: [{ t: 0.4, aim: arm('R', [0.3, -0.75, -0.45], [0.05, -0.5, 0.86]) }, { t: 1.2, aim: arm('R', [0.3, -0.75, -0.45], [0.05, -0.5, 0.86]) }] },
  type: { dur: 2.4, look: 'laptop', keys: [
    { t: 0.4, aim: both([0.12, -0.7, -0.7], [-0.3, -1, -0.05]), rot: { head: [12, 0, 0], spine: [5, 0, 0] } },
    { t: 0.7, aim: both([0.12, -0.72, -0.68], [-0.32, -1, -0.12]) },
    { t: 1.0, aim: both([0.12, -0.7, -0.7], [-0.28, -1, -0.02]) },
    { t: 1.3, aim: both([0.12, -0.72, -0.68], [-0.32, -1, -0.12]) },
    { t: 1.6, aim: both([0.12, -0.7, -0.7], [-0.28, -1, -0.02]), rot: { head: [12, 0, 0], spine: [5, 0, 0] } },
    { t: 2.0, aim: both([0.12, -0.7, -0.7], [-0.3, -1, -0.05]) }] },
  think: { dur: 2.2, look: 'up', keys: [{ t: 0.5, aim: arm('R', [0.2, -0.8, -0.55], [-0.5, -0.45, 0.75]), rot: { head: [-6, 8, 6] } },
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
  both_up: { dur: 1.4, keys: [{ t: 0.35, aim: both([0.5, -0.1, 0.85], [0.1, -0.1, 1]) }, { t: 1.0, aim: both([0.5, -0.1, 0.85], [0.1, -0.1, 1]) }] },
};

export async function mount(canvas, opts = {}) {
  const base = opts.base || './goli3d';
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1);
  renderer.setSize(canvas.width, canvas.height, false);
  renderer.toneMapping = THREE.AgXToneMapping;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.35;
  for (const [c, i, p] of [[0xfff4e6, 2.6, [-3.2, -4.2, 4.2]], [0xd8e6ff, 0.7, [4, -3.5, 2.2]], [0xfff2d8, 2.0, [1.5, 3.5, 3.5]]]) {
    const l = new THREE.DirectionalLight(c, i); l.position.copy(V(p)); scene.add(l);
  }
  const aspect = canvas.width / canvas.height;
  // Blender's AUTO sensor fit: the sensor spans the longer side of the frame
  const half = Math.atan(CAMERA.sensor / 2 / CAMERA.lens);
  const vfov = aspect >= 1 ? 2 * Math.atan(Math.tan(half) / aspect) : 2 * half;
  const cam = new THREE.PerspectiveCamera(vfov / D, aspect, 0.1, 100);
  cam.position.copy(V(CAMERA.pos)); cam.lookAt(V(CAMERA.target));

  const [gltf, rig] = await Promise.all([new GLTFLoader().loadAsync(`${base}/goli.glb`), fetch(`${base}/goli-rig.json`).then((r) => r.json())]);
  const root = gltf.scene; scene.add(root);
  if (opts.mirror) root.scale.x = -1;
  const bones = {}; root.traverse((o) => { if (o.isBone) bones[o.name] = o; });
  const rest = {}; for (const k in bones) rest[k] = bones[k].quaternion.clone();
  const swaps = [];
  root.traverse((o) => { const m = o.name.match(/^(mouth|lid|glasses)_([A-Za-z_]+?)__/); if (m) swaps.push([m[1], m[2], o]); });
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
  const moves = (plan.moves || []).filter((m) => MOVES[m.name]).sort((a, b) => a.at - b.at);
  const looks = (plan.looks || [{ at: 0, target: 'camera' }]).slice().sort((a, b) => a.at - b.at);

  const lidAt = (t) => {
    for (const b of blinks) { const d = t - b; if (d >= 0 && d < 0.2) return d < 0.05 || d >= 0.15 ? 'half' : 'closed'; if (b > t) break; }
    return 'open';
  };
  const mouthAt = (t) => { let s = 'X'; for (const [ct, sh] of cues) { if (ct > t) break; s = sh; } return s; };
  const pointOf = (target) => (Array.isArray(target) ? target : TARGETS[target] || TARGETS.camera);
  function gazeAt(t) {                            // where his eyes go, eased between targets (0.25 s)
    let cur = pointOf(looks[0].target), prev = cur, since = 99;
    for (let k = 0; k < looks.length && looks[k].at <= t; k++) { prev = k ? pointOf(looks[k - 1].target) : cur; cur = pointOf(looks[k].target); since = t - looks[k].at; }
    const m = moves.find((mv) => t >= mv.at && t < mv.at + MOVES[mv.name].dur && MOVES[mv.name].look);
    if (m) { prev = cur; cur = pointOf(MOVES[m.name].look); since = t - m.at; }
    const f = ease(since / 0.25);
    const p = [0, 1, 2].map((i) => prev[i] + (cur[i] - prev[i]) * f);
    let g = [0, 0]; for (const [gt, gx, gz] of glances) { if (gt > t) break; g = [gx, gz]; }
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
      return { a, b, f, w };
    }
    return null;
  }
  const talking = (t) => (plan.talk || []).some(([a, b]) => t >= a && t < b) || mouthAt(t) !== 'X';

  function frame(t) {
    for (const k in bones) bones[k].quaternion.copy(rest[k]);
    root.updateMatrixWorld(true);
    // idle: breathing (4 s), a slow weight shift, a small nod while he talks
    const br = Math.sin(t * 2 * Math.PI / 4.0);
    turnBone('spine', [1.2 * br, 0, 0.6 * Math.sin(t * 2 * Math.PI / 9)], 1);
    turnBone('chest', [0.8 * br, 0.8 * Math.sin(t * 2 * Math.PI / 11), 0], 1);
    const tk = talking(t) ? 1 : 0;
    turnBone('head', [2.2 * Math.sin(t * 5.1) * tk + 0.8 * Math.sin(t * 0.9), 2.5 * Math.sin(t * 0.7), 1.5 * Math.sin(t * 0.5)], 1);
    const mv = moveAt(t);
    if (mv) {
      const { a, b, f, w } = mv;
      for (const name of new Set([...Object.keys(a.rot || {}), ...Object.keys(b.rot || {})])) {
        const ra = (a.rot || {})[name] || [0, 0, 0], rb = (b.rot || {})[name] || [0, 0, 0];
        turnBone(name, [0, 1, 2].map((i) => ra[i] + (rb[i] - ra[i]) * f), w);
      }
      root.updateMatrixWorld(true);
      // shoulder to hand, in order, so each child aims from where its parent landed
      for (const name of ['upper_armL', 'forearmL', 'upper_armR', 'forearmR']) {
        const da = (a.aim || {})[name], db = (b.aim || {})[name];
        if (!da && !db) continue;
        const va = V(da || db).normalize(), vb = V(db || da).normalize();
        aimTo(name, va.clone().lerp(vb, f), w);
      }
    }
    const g = gazeAt(t);
    lookAt('eyeL', g, 1); lookAt('eyeR', g, 1);
    const lid = lidAt(t), mouth = mouthAt(t);
    for (const [kind, val, o] of swaps) o.visible = kind === 'mouth' ? val === mouth : kind === 'lid' ? val === lid : val === glasses;
    renderer.render(scene, cam);
  }
  frame(0);
  return frame;
}
