// Hero 3D objects (owner 2026-11-26): real Blender-built models (assets/edit/hero/<name>.glb, goli3d/hero_models.py)
// shown with studio light, Blender's AgX Punchy look, a soft contact shadow and a slow turn; the "accent" parts take
// the colour of the thing the line names (opts.color: a brand's own colour; else house gold), the move lands on the
// spoken word, and up to 3 callouts point at named parts. Same calling shape as glass3d.js: mount(canvas, name, opts)
// returns render(u, yaw, t) where u is the move's progress (0..1).
import * as THREE from 'three';
import { GLTFLoader } from '../examples/jsm/loaders/GLTFLoader.js';
import { RoomEnvironment } from '../examples/jsm/environments/RoomEnvironment.js';
import { punchyAgX } from './goli_live.js';

// what each model's parts are called on screen, and which to label by default (first = gold callout)
export const HERO = {
  robot: { parts: { head: 'Head', visor: 'Vision', chest_light: 'Core', hand: 'Hands', torso: 'Body' }, show: ['visor', 'chest_light', 'hand'], move: 'glow' },
  padlock: { parts: { body: 'Lock', mover_shackle: 'Shackle', keyhole: 'Key' }, show: ['body', 'mover_shackle'], move: 'open' },
  shield: { parts: { shield: 'Protection', mover_check: 'Verified' }, show: ['shield', 'mover_check'], move: 'glow' },
  cloud: { parts: { cloud: 'Cloud', mover_link: 'Sync' }, show: ['cloud', 'mover_link'], move: 'glow' },
  database: { parts: { disc: 'Storage', mover_top: 'Data', seam: 'Index' }, show: ['mover_top', 'disc'], move: 'open' },
  brain: { parts: { left_half: 'Reasoning', right_half: 'Memory', circuits: 'Signals' }, show: ['circuits', 'left_half', 'right_half'], move: 'glow' },
  key: { parts: { bow: 'Access', blade: 'Key', teeth: 'Code' }, show: ['bow', 'teeth'], move: 'spin' },
  globe: { parts: { globe: 'World', places: 'Users', lines: 'Network' }, show: ['places', 'lines'], move: 'spin' },
};
export const HERO_NAMES = Object.keys(HERO);
const ease = (x) => { x = Math.min(1, Math.max(0, x)); return x * x * (3 - 2 * x); };

export async function mount(canvas, name, opts = {}) {
  punchyAgX();
  const W = canvas.width, H = canvas.height;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1); renderer.setSize(W, H, false);
  renderer.toneMapping = THREE.CustomToneMapping; renderer.toneMappingExposure = 1.0;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture; scene.environmentIntensity = 0.9;
  const key = new THREE.DirectionalLight(0xfff1e0, 2.4); key.position.set(-2.5, 4, 3.5); key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024); key.shadow.radius = 8; Object.assign(key.shadow.camera, { left: -2, right: 2, top: 2, bottom: -2 });
  scene.add(key);
  const rim = new THREE.DirectionalLight(0x9db8ff, 2.2); rim.position.set(2.5, 2.5, -3); scene.add(rim);
  const fill = new THREE.DirectionalLight(0xffffff, 0.5); fill.position.set(3, 1, 3); scene.add(fill);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(10, 10), new THREE.ShadowMaterial({ opacity: 0.35 }));
  floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);

  const gltf = await new GLTFLoader().loadAsync(`${opts.base || './hero'}/${name}.glb`);
  const turn = new THREE.Group(); scene.add(turn);
  const model = gltf.scene; turn.add(model);
  const accent = new THREE.Color(opts.color || '#E8C268');
  const movers = [], parts = {};
  model.traverse((o) => {
    if (!o.isMesh) return;
    o.castShadow = true; o.receiveShadow = true;
    const n = o.material && o.material.name;
    if (n === 'accent') { o.material = o.material.clone(); o.material.color.copy(accent); }
    if (n === 'accent_glow') { o.material = o.material.clone(); o.material.emissive.copy(accent).lerp(new THREE.Color('#ffffff'), 0.15); o.material.color.copy(accent); }
    const base = o.name.replace(/\d+$/, '').replace(/_end$/, '');   // three.js drops the dot: eye.001 -> eye001
    (parts[base] = parts[base] || []).push(o);
    if (/^mover/.test(o.name)) movers.push(o);
  });
  // stand it on the floor and fill the frame
  const box = new THREE.Box3().setFromObject(model), size = box.getSize(new THREE.Vector3()), mid = box.getCenter(new THREE.Vector3());
  model.position.set(-mid.x, -box.min.y, -mid.z);
  const hgt = size.y, wid = Math.max(size.x, size.z);
  const cam = new THREE.PerspectiveCamera(28, W / H, 0.05, 50);
  const dist = Math.max(hgt / (2 * Math.tan(14 * Math.PI / 180)), wid * (H / W) / (2 * Math.tan(14 * Math.PI / 180))) * 1.35;
  cam.position.set(0, hgt * 0.62, dist); cam.lookAt(0, hgt * 0.48, 0);
  const home = movers.map((o) => ({ o, p: o.position.clone(), s: o.scale.clone() }));
  const info = HERO[name] || { parts: {}, show: [], move: 'spin' };
  const move = opts.move && opts.move !== 'own' ? opts.move : info.move;
  const glows = []; model.traverse((o) => { if (o.isMesh && o.material && o.material.name === 'accent_glow') glows.push(o.material); });

  // callouts (same look as glass3d.js): a line from the part to a label beside the object
  const overlay = opts.overlay || null, ns = 'http://www.w3.org/2000/svg';
  const want = (opts.callouts && opts.callouts.length ? opts.callouts.map((c) => ({ key: c.key || info.show[c.part] || info.show[0], text: c.text }))
    : info.show.map((k) => ({ key: k }))).filter((c) => parts[c.key]).slice(0, 3)
    .map((c, k) => ({ ...c, k, text: (k === 0 && opts.lead) || c.text || info.parts[c.key] || c.key }));
  const els = overlay ? want.map((c) => {
    const g = document.createElementNS(ns, 'g'), line = document.createElementNS(ns, 'polyline'), dot = document.createElementNS(ns, 'circle');
    const rect = document.createElementNS(ns, 'rect'), txt = document.createElementNS(ns, 'text');
    const gold = c.k === 0;
    line.setAttribute('fill', 'none'); line.setAttribute('stroke', gold ? '#E8C268' : '#CFE6FF'); line.setAttribute('stroke-width', '4');
    dot.setAttribute('r', '11'); dot.setAttribute('fill', gold ? '#E8C268' : '#CFE6FF'); dot.setAttribute('stroke', '#07080B'); dot.setAttribute('stroke-width', '3');
    rect.setAttribute('rx', '14'); rect.setAttribute('fill', gold ? '#E8C268' : 'rgba(10,12,18,.88)');
    rect.setAttribute('stroke', gold ? '#E8C268' : 'rgba(207,230,255,.6)'); rect.setAttribute('stroke-width', '2');
    txt.textContent = c.text; txt.setAttribute('font-family', 'Poppins'); txt.setAttribute('font-weight', '800'); txt.setAttribute('font-size', '42');
    txt.setAttribute('fill', gold ? '#07080B' : '#F4F1EA'); txt.setAttribute('dominant-baseline', 'middle');
    g.append(line, dot, rect, txt); overlay.append(g);
    return { g, line, dot, rect, txt, w: c.text.length * 42 * 0.6 + 44 };
  }) : [];
  const v = new THREE.Vector3();
  function labels(t) {
    const pts = want.map((c) => {
      const b = new THREE.Box3(); parts[c.key].forEach((o) => b.expandByObject(o));
      b.getCenter(v); v.y = b.max.y - (b.max.y - b.min.y) * 0.25; v.project(cam);
      return { x: (v.x + 1) / 2 * W, y: (1 - v.y) / 2 * H };
    });
    const sides = { left: [], right: [] };
    pts.forEach((p, i) => (p.x < W / 2 ? sides.left : sides.right).push(i));
    for (const [side, idx] of Object.entries(sides)) {
      idx.sort((a, b) => pts[a].y - pts[b].y); let last = -1e9;
      idx.forEach((i) => {
        const p = pts[i], el = els[i], c = want[i];
        const st = opts.safe || [0, 0, 0, 0]; let ly = Math.max(p.y - 70, last + 96, 56, st[2] + 52); ly = Math.min(ly, H - 50 - st[3]); last = ly;
        // owner 2026-11-27 ("some blocks had cut edges"): a label never leaves its frame. The left one was kept
        // 20 px in BEFORE its width was taken off, so long labels ran off the left edge ("...dden credits").
        // Its real width is measured, and both sides keep a margin (the phone crop on a Short).
        if (!el.measured && el.txt.getComputedTextLength) { const m = el.txt.getComputedTextLength(); if (m > 0) { el.w = m + 44; el.measured = true; } }
        const sf = opts.safe || [0, 0, 0, 0], ml = Math.max(40, W * 0.05, sf[0] + 16), mr = Math.max(40, W * 0.05, sf[1] + 16);
        const lx = side === 'left' ? Math.max(ml, Math.min(p.x - 160, W * 0.16) - el.w) : Math.max(ml, Math.min(W - mr - el.w, Math.max(p.x + 160, W * 0.84)));
        const edge = side === 'left' ? lx + el.w : lx, knee = side === 'left' ? edge + 30 : edge - 30;
        el.line.setAttribute('points', `${p.x},${p.y} ${knee},${ly} ${edge},${ly}`);
        el.dot.setAttribute('cx', p.x); el.dot.setAttribute('cy', p.y);
        el.rect.setAttribute('x', lx); el.rect.setAttribute('y', ly - 36); el.rect.setAttribute('width', el.w); el.rect.setAttribute('height', 72);
        el.txt.setAttribute('x', lx + 22); el.txt.setAttribute('y', ly + 2);
        const show = Math.min(1, Math.max(0, (t - (opts.at || 1) - 0.7 - c.k * 0.35) / 0.35));
        el.g.setAttribute('opacity', show.toFixed(3));
        el.line.setAttribute('stroke-dasharray', `${(show * 2000).toFixed(0)} 2000`);
      });
    }
  }

  return function render(u, yaw, t = 0) {
    const e = ease(u);
    turn.rotation.y = yaw + (move === 'spin' ? Math.PI * 2 * e : 0);
    // it arrives: rises a little and settles (never pops in)
    const arrive = ease(Math.min(1, t / 0.6));
    turn.position.y = -0.15 * hgt * (1 - arrive); turn.scale.setScalar(0.92 + 0.08 * arrive);
    for (const { o, p, s } of home) {          // the moving parts: open lifts them, glow makes them breathe
      o.position.copy(p); o.scale.copy(s);
      if (move === 'open') o.position.y = p.y + 0.18 * hgt * e;
    }
    for (const m of glows) m.emissiveIntensity = (move === 'glow' ? 1 + 3 * e : 1) * (1 + 0.15 * Math.sin(t * 3));
    renderer.render(scene, cam);
    if (els.length) labels(t);
  };
}
