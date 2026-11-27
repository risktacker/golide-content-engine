// Metaphors in 3D (owner 2026-11-26: "rebuild in 3D and make them colour match to a said thing"): the nine ideas of
// edit/metaphors.py (scales, unlock, magnify, funnel, stack, gauge, transform, iceberg, cycle) as real 3D scenes in
// studio light, each thing in the colour of what the line names (opts.colors, worked out by the composer from the
// words: a brand's own colour, a colour word, else gold/blue), its move landing on the spoken word, its words on
// clean labels pinned to the 3D parts. render(t) takes seconds from the scene's start. Deterministic.
import * as THREE from 'three';
import { RoundedBoxGeometry } from '../examples/jsm/geometries/RoundedBoxGeometry.js';
import { RoomEnvironment } from '../examples/jsm/environments/RoomEnvironment.js';
import { GLTFLoader } from '../examples/jsm/loaders/GLTFLoader.js';
import { punchyAgX } from './goli_live.js';

const ease = (x) => { x = Math.min(1, Math.max(0, x)); return x * x * (3 - 2 * x); };
const back = (x) => { x = Math.min(1, Math.max(0, x)); const c = 1.70158; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2; };
const elastic = (x) => (x <= 0 ? 0 : x >= 1 ? 1 : 2 ** (-10 * x) * Math.sin((x * 10 - 0.75) * (2 * Math.PI) / 3) + 1);

export async function mount(canvas, kind, args = {}, opts = {}) {
  punchyAgX();
  const W = canvas.width, H = canvas.height;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1); renderer.setSize(W, H, false);
  renderer.toneMapping = THREE.CustomToneMapping; renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  const scene = new THREE.Scene();
  scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(), 0.04).texture; scene.environmentIntensity = 0.85;
  const key = new THREE.DirectionalLight(0xfff1e0, 2.3); key.position.set(-3, 6, 5); key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024); key.shadow.radius = 8; Object.assign(key.shadow.camera, { left: -6, right: 6, top: 6, bottom: -6, far: 30 });
  scene.add(key);
  const rim = new THREE.DirectionalLight(0x9db8ff, 2.0); rim.position.set(4, 3, -4); scene.add(rim);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.ShadowMaterial({ opacity: 0.32 }));
  floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);

  const C = opts.colors || {};
  const col = (k, d) => new THREE.Color(C[k] || d);
  const M = {
    gold: new THREE.MeshPhysicalMaterial({ color: '#E8C268', metalness: 1, roughness: 0.22 }),
    chrome: new THREE.MeshPhysicalMaterial({ color: '#D8DCE2', metalness: 1, roughness: 0.14 }),
    dark: new THREE.MeshPhysicalMaterial({ color: '#1C1F26', metalness: 0.5, roughness: 0.35 }),
    white: new THREE.MeshPhysicalMaterial({ color: '#F2F3F5', roughness: 0.25, clearcoat: 0.8 }),
    // no refraction pass (owner 2026-11-26: a software-WebGL frame with refracting glass hung the filming)
    glass: new THREE.MeshPhysicalMaterial({ color: '#DCE6FF', roughness: 0.05, metalness: 0.1, clearcoat: 1, transparent: true, opacity: 0.32, depthWrite: false }),
    ice: new THREE.MeshPhysicalMaterial({ color: '#D7F0FF', roughness: 0.12, clearcoat: 1, transparent: true, opacity: 0.9 }),
    water: new THREE.MeshPhysicalMaterial({ color: '#0E2A5A', roughness: 0.08, transparent: true, opacity: 0.62, metalness: 0.1 }),
  };
  const paint = (c, glow = 0) => new THREE.MeshPhysicalMaterial({ color: c, roughness: 0.28, clearcoat: 0.6, metalness: 0.15, emissive: c, emissiveIntensity: glow });
  const add = (geo, mat, pos = [0, 0, 0], parent = scene) => {
    const m = new THREE.Mesh(geo, mat); m.position.set(...pos); m.castShadow = true; m.receiveShadow = true; parent.add(m); return m;
  };
  const rbox = (w, h, d, r = 0.08) => new RoundedBoxGeometry(w, h, d, 4, Math.min(r, w / 2, h / 2, d / 2));

  // owner 2026-11-26: the things are SHOWN, not written: a real app or model gets its real logo in its own colour, a
  // kind of thing (data, docs, people...) a matching icon (data looks like a chat), a prompt is the written prompt
  // itself (the word "prompt" never appears). opts.pictures: {left|right|label|itemN: {kind, svg, color}}
  const PICS = opts.pictures || {};
  const svgOf = (pic, fg) => (pic.kind === 'logo'
    ? pic.svg.replace('<svg', `<svg fill="${fg}"`) : pic.svg.replace(/currentColor/g, fg));
  async function picImage(pic, fg) {
    const img = new Image(); img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgOf(pic, fg));
    try { await img.decode(); } catch (e) { return null; }
    return img;
  }
  const tileColor = (pic) => (pic.kind === 'logo' ? pic.color : '#1B1F2A');
  async function tile3d(pic, size = 0.9) {        // a glossy app tile: the logo (white on its colour) or the icon (gold)
    const g = new THREE.Group();
    const body = add(rbox(size, size, size * 0.22, size * 0.2), paint(new THREE.Color(tileColor(pic)), pic.kind === 'logo' ? 0.12 : 0), [0, 0, 0], g);
    const cv = document.createElement('canvas'); cv.width = cv.height = 256;
    const img = await picImage(pic, pic.kind === 'logo' ? '#FFFFFF' : '#E8C268');
    if (img) cv.getContext('2d').drawImage(img, 40, 40, 176, 176);
    const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
    const face = new THREE.Mesh(new THREE.PlaneGeometry(size * 0.92, size * 0.92), new THREE.MeshBasicMaterial({ map: tex, transparent: true, toneMapped: false }));
    face.position.z = size * 0.111 + 0.002; g.add(face);
    if (pic.kind !== 'logo') body.material.color.set('#1B1F2A');
    return g;
  }
  const picFor = (key, text) => PICS[key] || null;
  const showWord = (key, text) => (PICS[key] && PICS[key].kind === 'prompt' ? '' : text);

  // labels: chips pinned to 3D points (the anchor is projected every frame), the thing's picture on the left
  const overlay = opts.overlay || null, ns = 'http://www.w3.org/2000/svg', labels = [];
  function label(text, anchor, { gold = false, at = 0, size = 44, dy = 0, key = null } = {}) {
    const pic = key ? PICS[key] : null;
    if (pic && pic.kind === 'prompt') return promptCard(anchor, { at, dy });
    if (!overlay || !text) return;
    const g = document.createElementNS(ns, 'g'), rect = document.createElementNS(ns, 'rect'), txt = document.createElementNS(ns, 'text');
    const iw = pic ? size * 1.35 : 0;
    const w = String(text).length * size * 0.6 + 48 + iw;
    rect.setAttribute('rx', '18'); rect.setAttribute('height', size * 1.6); rect.setAttribute('width', w);
    rect.setAttribute('fill', gold ? '#E8C268' : 'rgba(10,12,18,.9)'); rect.setAttribute('stroke', gold ? '#E8C268' : 'rgba(232,194,104,.6)');
    rect.setAttribute('stroke-width', '2.5');
    txt.textContent = text; txt.setAttribute('font-family', 'Poppins'); txt.setAttribute('font-weight', '800'); txt.setAttribute('font-size', size);
    txt.setAttribute('fill', gold ? '#07080B' : '#F4F1EA'); txt.setAttribute('text-anchor', 'middle'); txt.setAttribute('dominant-baseline', 'middle');
    g.append(rect, txt);
    let icon = null;
    if (pic) {                                    // the logo / icon in its own little tile inside the chip
      icon = document.createElementNS(ns, 'svg'); icon.setAttribute('viewBox', '-3 -3 30 30');
      icon.setAttribute('width', size * 1.25); icon.setAttribute('height', size * 1.25);
      const inner = pic.svg.replace(/<svg[^>]*>/, '').replace('</svg>', '');
      icon.innerHTML = `<rect x="-3" y="-3" width="30" height="30" rx="7" fill="${pic.kind === 'logo' ? pic.color : '#1B1F2A'}" stroke="rgba(232,194,104,.7)" stroke-width="${pic.kind === 'logo' ? 0 : 1}"/>` +
        (pic.kind === 'logo' ? `<g fill="#FFFFFF">${inner}</g>`
          : `<g fill="none" stroke="#E8C268" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round">${inner}</g>`);
      g.append(icon);
    }
    overlay.append(g);
    labels.push({ g, rect, txt, w, h: size * 1.6, anchor, at, dy, icon, iw, size });
  }
  // a prompt is shown as the prompt: a small dark card with the words typed in (opts.prompt), never the word "prompt"
  function promptCard(anchor, { at = 0, dy = 0 } = {}) {
    if (!overlay) return;
    const words = String(opts.prompt || '').split(/\s+/).filter(Boolean).slice(0, 14);
    const text = words.join(' '), size = 26, per = 22;
    const lines = []; let cur = '';
    for (const w of words) { if ((cur + ' ' + w).trim().length > per) { lines.push(cur.trim()); cur = w; } else cur += ' ' + w; }
    if (cur.trim()) lines.push(cur.trim());
    if (!lines.length) lines.push('');
    const g = document.createElementNS(ns, 'g'), rect = document.createElementNS(ns, 'rect');
    const w = Math.max(260, per * size * 0.6 + 70), h = lines.length * size * 1.35 + 40;
    rect.setAttribute('rx', '16'); rect.setAttribute('width', w); rect.setAttribute('height', h);
    rect.setAttribute('fill', 'rgba(10,12,18,.94)'); rect.setAttribute('stroke', '#E8C268'); rect.setAttribute('stroke-width', '2.5');
    g.append(rect);
    const tx = lines.map((ln, i) => { const e = document.createElementNS(ns, 'text');
      e.setAttribute('font-family', 'JetBrains Mono, monospace'); e.setAttribute('font-size', size); e.setAttribute('fill', '#F4F1EA');
      g.append(e); return { e, ln, i }; });
    const caret = document.createElementNS(ns, 'text'); caret.textContent = '>'; caret.setAttribute('font-family', 'JetBrains Mono, monospace');
    caret.setAttribute('font-size', size); caret.setAttribute('font-weight', '800'); caret.setAttribute('fill', '#E8C268'); g.append(caret);
    overlay.append(g);
    labels.push({ g, rect, w, h, anchor, at, dy, prompt: { tx, caret, total: text.length, size } });
  }
  const v = new THREE.Vector3();
  function drawLabels(t) {
    for (const L of labels) {
      if (typeof L.anchor === 'function') v.copy(L.anchor()).project(cam); else { L.anchor.getWorldPosition(v); v.project(cam); }
      // owner 2026-11-27 ("cut edges"): a chip stays whole inside the safe frame, however the object turns
      const sf = opts.safe || [0, 0, 0, 0], ml = Math.max(24, sf[0] + 12), mr = Math.max(24, sf[1] + 12);
      const mt = Math.max(24, sf[2] + 12), mb = Math.max(24, sf[3] + 12);
      const x = Math.min(W - mr - L.w / 2, Math.max(ml + L.w / 2, (v.x + 1) / 2 * W));
      const y = Math.min(H - mb - L.h / 2, Math.max(mt + L.h / 2, (1 - v.y) / 2 * H + L.dy));
      L.rect.setAttribute('x', x - L.w / 2); L.rect.setAttribute('y', y - L.h / 2);
      if (L.prompt) {                             // typed in, a letter at a time, from the moment it shows
        const P = L.prompt, n = Math.max(0, Math.floor((t - L.at) * 28)); let used = 0;
        P.caret.setAttribute('x', x - L.w / 2 + 18); P.caret.setAttribute('y', y - L.h / 2 + 20 + P.size);
        for (const { e, ln, i } of P.tx) {
          e.textContent = ln.slice(0, Math.max(0, n - used)); used += ln.length + 1;
          e.setAttribute('x', x - L.w / 2 + 18 + P.size * 0.9); e.setAttribute('y', y - L.h / 2 + 20 + P.size + i * P.size * 1.35);
        }
      } else {
        const ix = L.icon ? L.iw / 2 : 0;
        L.txt.setAttribute('x', x + ix); L.txt.setAttribute('y', y + 2);
        if (L.icon) { L.icon.setAttribute('x', x - L.w / 2 + 10); L.icon.setAttribute('y', y - L.size * 0.625); }
      }
      const show = ease((t - L.at) / 0.35);
      L.g.setAttribute('opacity', show.toFixed(3));
      L.g.setAttribute('transform', `translate(0 ${(12 * (1 - show)).toFixed(1)})`);
    }
  }
  const at = opts.at || 1.0;
  const items = (args.items || []).slice(0, 5);
  const times = args.times || [];
  const itemAt = (i) => (times[i] !== undefined ? Math.max(0.2, times[i]) : at + i * 0.45);
  let cam = new THREE.PerspectiveCamera(32, W / H, 0.05, 80);
  let update = () => {};
  const look = (pos, target) => { cam.position.set(...pos); cam.lookAt(...target); };

  if (kind === 'scales') {
    // a real balance: base, pillar, beam on a pivot, two pans on chains; the winner's pan drops on the word
    const winL = (args.winner || 'left') === 'left';
    add(new THREE.CylinderGeometry(0.9, 1.0, 0.18, 64), M.dark, [0, 0.09, 0]);
    add(new THREE.CylinderGeometry(0.09, 0.12, 2.6, 32), M.gold, [0, 1.4, 0]);
    const pivot = new THREE.Group(); pivot.position.set(0, 2.75, 0); scene.add(pivot);
    add(new THREE.SphereGeometry(0.16, 32, 16), M.gold, [0, 0, 0], pivot);
    add(rbox(4.4, 0.12, 0.16, 0.05), M.gold, [0, 0, 0], pivot);
    const pans = await Promise.all([-1, 1].map(async (s) => {
      const hang = new THREE.Group(); hang.position.set(s * 2.05, 0, 0); pivot.add(hang);
      const pan = new THREE.Group(); scene.add(pan);
      const c = col(s < 0 ? 'left' : 'right', s < 0 ? '#E8C268' : '#4C7DFF');
      add(new THREE.SphereGeometry(0.7, 48, 16, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2.6), paint(c), [0, 0.32, 0], pan).material.side = THREE.DoubleSide;
      for (const a of [0.5, 2.6, 4.7]) {
        const from = new THREE.Vector3(Math.cos(a) * 0.66, 0.34, Math.sin(a) * 0.66), to = new THREE.Vector3(0, 1.6, 0);
        const dir = to.clone().sub(from), ch = add(new THREE.CylinderGeometry(0.014, 0.014, dir.length(), 8), M.chrome, [0, 0, 0], pan);
        ch.position.copy(from).addScaledVector(dir, 0.5); ch.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
      }
      const anchor = new THREE.Object3D(); anchor.position.set(0, -0.15, 0); pan.add(anchor);
      const key = s < 0 ? 'left' : 'right';
      label(s < 0 ? args.left : args.right, anchor, { gold: (s < 0) === winL, at: at + 0.3, dy: 70, key });
      if (PICS[key] && PICS[key].kind !== 'prompt') {           // the thing itself sits in its pan
        const tl_ = await tile3d(PICS[key], 0.62); tl_.position.set(0, 0.55, 0); tl_.rotation.x = -0.15; pan.add(tl_);
      }
      return { hang, pan, s };
    }));
    look([0, 2.2, 9.0], [0, 1.5, 0]);
    update = (t) => {
      const k = elastic(Math.min(1, Math.max(0, (t - at) / 1.1)));
      pivot.rotation.z = (winL ? 1 : -1) * 0.2 * k;
      for (const p of pans) { p.hang.getWorldPosition(v); p.pan.position.set(v.x, v.y - 1.6, v.z); }
    };
  } else if (kind === 'unlock') {
    const gltf = await new GLTFLoader().loadAsync(`${opts.base || './hero'}/padlock.glb`);
    const lock = gltf.scene; lock.scale.setScalar(3.2); scene.add(lock);
    const movers = []; lock.traverse((o) => { if (o.isMesh) { o.castShadow = true; if (o.material.name === 'accent') { o.material = o.material.clone(); o.material.color.copy(col('label', '#E8C268')); } if (/^mover/.test(o.name)) movers.push([o, o.position.y]); } });
    const glow = new THREE.PointLight(col('label', '#E8C268'), 0, 8); glow.position.set(0, 2, 1.5); scene.add(glow);
    const anchor = new THREE.Object3D(); anchor.position.set(0, 0, 0.6); scene.add(anchor);
    label(args.label, anchor, { gold: true, at: at + 0.4, size: 52, dy: 50, key: 'label' });
    const box = new THREE.Box3().setFromObject(lock), mid = box.getCenter(new THREE.Vector3());
    look([1.4, mid.y + 0.4, mid.y + 8.5], [0, mid.y, 0]);
    update = (t) => { const k = back(Math.min(1, Math.max(0, (t - at) / 0.7))); for (const [o, y] of movers) o.position.y = y + 0.12 * k; glow.intensity = 6 * ease((t - at) / 0.5); lock.rotation.y = -0.3 + 0.08 * Math.sin(t * 0.6); };
  } else if (kind === 'stack') {
    // layers built one on another, each on its spoken word, each in its own colour
    const n = Math.max(1, items.length), layers = [];
    for (let i = 0; i < n; i++) {
      const c = col(`item${i}`, ['#E8C268', '#4C7DFF', '#38BDF8', '#9B5CFF', '#34C759'][i % 5]);
      const m = add(rbox(3.4 - i * 0.25, 0.42, 2.2 - i * 0.12, 0.1), paint(c, 0.05), [0, 0.21 + i * 0.5, 0]);
      const anchor = new THREE.Object3D(); anchor.position.set(1.9 - i * 0.12, 0, 0); m.add(anchor);
      label(items[i], anchor, { gold: i === n - 1, at: itemAt(i) + 0.25, size: 40, key: `item${i}` });
      layers.push({ m, y: 0.21 + i * 0.5, at: itemAt(i) });
    }
    look([3.2, 2.6 + n * 0.25, 7.5], [0.3, 0.3 + n * 0.25, 0]);
    update = (t) => { for (const L of layers) { const k = back(Math.min(1, Math.max(0, (t - L.at) / 0.5))); L.m.position.y = L.y + 2.5 * (1 - k); L.m.visible = t >= L.at - 0.05; L.m.material.opacity = 1; } };
  } else if (kind === 'funnel') {
    // many things pour in at the top, one comes out at the bottom (the label), glowing
    const pts = []; for (let i = 0; i <= 20; i++) { const y = i / 20; pts.push(new THREE.Vector2(y < 0.35 ? 0.22 : 0.22 + (y - 0.35) * 2.6, y * 2.4)); }
    const f = add(new THREE.LatheGeometry(pts, 64), M.glass, [0, 0.9, 0]); f.material.side = THREE.DoubleSide;
    add(new THREE.TorusGeometry(1.92, 0.04, 12, 96), M.gold, [0, 3.3, 0]).rotation.x = Math.PI / 2;
    const n = Math.max(1, items.length), balls = [];
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2, c = col(`item${i}`, ['#4C7DFF', '#38BDF8', '#9B5CFF', '#34C759', '#E8C268'][i % 5]);
      const pic = PICS[`item${i}`];
      const b = pic && pic.kind !== 'prompt' ? await tile3d(pic, 0.5) : add(new THREE.SphereGeometry(0.26, 32, 16), paint(c, 0.15), [0, 0, 0]);
      if (b.parent !== scene) scene.add(b);
      const anchor = new THREE.Object3D(); b.add(anchor); anchor.position.set(0, 0.45, 0);
      label(items[i], anchor, { at: itemAt(i) - 0.6, size: 36, key: `item${i}` });
      balls.push({ b, a, at: itemAt(i) });
    }
    // owner 2026-11-27 ("the ball rolled outside the funnel"): each thing drops INTO the mouth, rolls down the inside of
    // the cone in a spiral (on its wall, never through it), then falls through the spout
    const R = (h) => { const y = h / 2.4; return y < 0.35 ? 0.22 : 0.22 + (y - 0.35) * 2.6; };   // the cone's radius at height h
    const path = (B, k) => {
      const rb = 0.26;
      if (k < 0.25) {                                  // falls straight down into the mouth, inside the rim
        const e = ease(k / 0.25), r = 1.35;
        return { p: [Math.cos(B.a) * r, 5.2 - (5.2 - 3.15) * e, Math.sin(B.a) * r], s: 1 };
      }
      if (k < 0.85) {                                  // rolls round and down the cone's inside wall
        const e = (k - 0.25) / 0.6, h = 2.25 - (2.25 - 0.9) * (e * e * 0.4 + e * 0.6);   // speeds up as it drops
        const ang = B.a + e * Math.PI * 3.2, r = Math.max(0, R(h) - rb * 1.15);
        return { p: [Math.cos(ang) * r, 0.9 + h + rb * 0.4, Math.sin(ang) * r], s: 1 };
      }
      const e = (k - 0.85) / 0.15;                     // through the spout and out
      return { p: [0, 0.9 + 0.9 + rb * 0.4 - 1.9 * e, 0], s: 1 - 0.5 * e };
    };
    const out = add(new THREE.SphereGeometry(0.34, 32, 16), paint(col('label', '#E8C268'), 0.4), [0, 0.35, 0]);
    const oa = new THREE.Object3D(); oa.position.set(0, -0.6, 0); out.add(oa);
    label(args.label, oa, { gold: true, at: at + 1.0, size: 46, key: 'label' });
    look([0, 3.2, 8.0], [0, 1.7, 0]);
    update = (t) => {
      for (const B of balls) {
        const k = Math.min(1, Math.max(0, (t - B.at + 0.6) / 2.2));
        B.b.visible = k < 1 && t > B.at - 0.6;
        const q = path(B, k); B.b.position.set(q.p[0], q.p[1], q.p[2]); B.b.scale.setScalar(q.s);
      }
      const k = back(Math.min(1, Math.max(0, (t - at - 0.8) / 0.5))); out.scale.setScalar(Math.max(0.001, k));
    };
  } else if (kind === 'gauge') {
    // a dial that swings to the level the words name
    const val = Math.max(0, Math.min(100, Number(args.value ?? 80)));
    add(new THREE.CircleGeometry(2.25, 96, 0, Math.PI), M.dark, [0, 0.1, 0]);
    add(new THREE.TorusGeometry(2.25, 0.05, 12, 96, Math.PI), M.gold, [0, 0.1, 0.02]);
    const segs = 24;
    for (let i = 0; i < segs; i++) {
      const a = Math.PI * (1 - (i + 0.5) / segs), c = new THREE.Color('#34C759').lerp(new THREE.Color(col('label', '#E53935')), i / segs);
      add(rbox(0.32, 0.12, 0.08, 0.03), paint(c, 0.25), [Math.cos(a) * 1.85, 0.1 + Math.sin(a) * 1.85, 0.14]).rotation.z = a - Math.PI / 2;
    }
    const needle = new THREE.Group(); needle.position.set(0, 0.1, 0.25); scene.add(needle);
    add(rbox(0.1, 1.6, 0.06, 0.03), M.gold, [0, 0.8, 0], needle);
    add(new THREE.CylinderGeometry(0.16, 0.16, 0.12, 32), M.gold, [0, 0, 0], needle).rotation.x = Math.PI / 2;
    const anchor = new THREE.Object3D(); anchor.position.set(0, -0.55, 0.3); scene.add(anchor);
    label((args.label ? args.label + ' ' : '') + `${Math.round(val)}%`, anchor, { gold: true, at: at + 0.4, size: 50, key: PICS.label && PICS.label.kind === 'prompt' ? null : 'label' });
    look([0, 1.1, 6.5], [0, 1.0, 0]);
    update = (t) => { const k = elastic(Math.min(1, Math.max(0, (t - at) / 1.2))); needle.rotation.z = Math.PI / 2 - Math.PI * (val / 100) * k; };
  } else if (kind === 'transform') {
    // one thing (left) breaks into pieces that fly over and rebuild as the other (right)
    const cA = col('left', '#4C7DFF'), cB = col('right', '#E8C268'), cubes = [];
    for (let i = 0; i < 27; i++) {
      const x = (i % 3) - 1, y = Math.floor(i / 3) % 3, z = Math.floor(i / 9) - 1;
      const m = add(rbox(0.42, 0.42, 0.42, 0.06), paint(cA, 0.05), [0, 0, 0]);
      cubes.push({ m, a: new THREE.Vector3(-2.0 + x * 0.46, 0.25 + y * 0.46, z * 0.46), b: new THREE.Vector3(2.4 + x * 0.46, 0.25 + y * 0.46, z * 0.46), d: i * 0.025 });
    }
    const aL = new THREE.Object3D(); aL.position.set(-2.0, -0.15, 0.8); scene.add(aL);
    const bL = new THREE.Object3D(); bL.position.set(2.4, -0.15, 0.8); scene.add(bL);
    label(args.left, aL, { at: 0.3, size: 42, key: 'left' }); label(args.right, bL, { gold: true, at: at + 1.2, size: 42, key: 'right' });
    look([0, 1.8, 8.4], [0, 0.7, 0]);
    update = (t) => {
      for (const c of cubes) {
        const k = ease(Math.min(1, Math.max(0, (t - at - c.d) / 0.9)));
        c.m.position.lerpVectors(c.a, c.b, k); c.m.position.y += Math.sin(Math.PI * k) * 1.4;
        c.m.rotation.set(k * Math.PI, k * Math.PI * 0.5, 0); c.m.material.color.copy(cA).lerp(cB, k); c.m.material.emissive.copy(c.m.material.color);
      }
    };
  } else if (kind === 'iceberg') {
    // what everyone sees above the water, and the much bigger part below it
    const ice = new THREE.Group(); scene.add(ice);
    const tip = add(new THREE.ConeGeometry(0.7, 1.2, 7), M.ice, [0, 2.55, 0], ice);
    const bulk = add(new THREE.IcosahedronGeometry(1.7, 1), M.ice, [0, 0.4, 0], ice); bulk.scale.set(1.25, 1.0, 1);
    const water = add(new THREE.BoxGeometry(60, 0.02, 40), M.water, [0, 2.0, 0]); water.receiveShadow = false;
    const ta = new THREE.Object3D(); ta.position.set(0, 3.6, 0); ice.add(ta);
    label(args.label, ta, { gold: true, at: 0.4, size: 44, key: 'label' });
    items.slice(0, 4).forEach((it, i) => {
      const a = new THREE.Object3D(); a.position.set(i % 2 ? 1.9 : -1.9, 1.2 - Math.floor(i / 2) * 1.0, 1.2); ice.add(a);
      label(it, a, { at: itemAt(i), size: 36, key: `item${i}` });
    });
    look([0, 4.6, 9.5], [0, 1.3, 0]);
    update = (t) => { ice.position.y = 0.05 * Math.sin(t * 0.8); ice.rotation.y = 0.15 * Math.sin(t * 0.3); };
  } else if (kind === 'magnify') {
    // owner 2026-11-26: the glass lens SCANS across a frosted card (rows of blurred content); on the word it finds the
    // hidden thing, which lifts out of the card above it into a spotlight, its real logo or icon on a glossy tile
    const card = add(rbox(5.2, 0.12, 2.8, 0.12), M.white, [0, 0.06, 0]);
    for (let r = 0; r < 4; r++) for (let k = 0; k < 3; k++)
      add(rbox(1.1 + ((r + k) % 3) * 0.25, 0.03, 0.14, 0.03), M.dark, [-1.75 + k * 1.75, 0.13, -0.95 + r * 0.62]);
    add(rbox(5.0, 0.03, 2.6, 0.1), new THREE.MeshPhysicalMaterial({ color: '#DCE6FF', roughness: 0.65, transparent: true, opacity: 0.8 }), [0, 0.16, 0]);
    const pic = PICS.label && PICS.label.kind !== 'prompt' ? PICS.label : (PICS.item0 && PICS.item0.kind !== 'prompt' ? PICS.item0 : null);
    const found = pic ? await tile3d(pic, 0.95) : add(rbox(0.95, 0.95, 0.2, 0.18), paint(col('label', '#E8C268'), 0.35), [0, 0, 0]);
    if (found.parent !== scene) scene.add(found);
    const spot = new THREE.SpotLight(0xfff1d6, 0, 12, 0.38, 0.6); spot.position.set(0, 5.5, 1.2); spot.target = found; scene.add(spot);
    const halo = add(new THREE.RingGeometry(0.55, 0.85, 64), new THREE.MeshBasicMaterial({ color: col('label', '#E8C268'), transparent: true, opacity: 0, side: THREE.DoubleSide }), [0, 0.2, 0]);
    halo.rotation.x = -Math.PI / 2; halo.castShadow = false;
    const mag = new THREE.Group(); scene.add(mag);
    add(new THREE.TorusGeometry(0.75, 0.08, 16, 64), M.gold, [0, 0, 0], mag).rotation.x = Math.PI / 2;
    add(new THREE.CylinderGeometry(0.72, 0.72, 0.04, 64), M.glass, [0, 0, 0], mag);
    add(rbox(0.16, 0.16, 1.5, 0.06), M.dark, [1.05, 0, 1.05], mag).rotation.y = Math.PI / 4;
    const anchor = new THREE.Object3D(); anchor.position.set(0, 0.85, 0); found.add(anchor);
    label(args.label || items[0], anchor, { gold: true, at: at + 0.45, size: 46, key: PICS.label ? 'label' : 'item0' });
    look([0, 3.6, 6.2], [0, 0.7, 0]);
    update = (t) => {
      // the scan: two passes over the card, slowing to the middle where the thing is, landing on the word
      const s = Math.min(1, Math.max(0, (t - 0.2) / Math.max(0.6, at - 0.2)));
      const x = s < 1 ? Math.sin(s * Math.PI * 1.5) * 2.1 * (1 - s) : 0, z = s < 1 ? Math.cos(s * Math.PI * 3) * 0.55 * (1 - s) : 0;
      const after = ease((t - at - 0.8) / 0.6);
      mag.position.set(x + 2.0 * after, 0.75 + 0.06 * Math.sin(t * 2.2), z + 0.6 * after);
      const k = back(Math.min(1, Math.max(0, (t - at) / 0.75)));
      found.position.set(0, 0.1 + 1.25 * k, 0); found.rotation.set(-0.35 * (1 - k) - 0.1, 0.25 * Math.sin(t * 0.8) * k, 0);
      found.visible = t >= at - 0.05;
      spot.intensity = 60 * ease((t - at) / 0.5); halo.material.opacity = 0.5 * ease((t - at) / 0.5);
    };
  } else {
    // cycle: a loop of steps on a ring; a light runs round, each step lights on its word
    const n = Math.max(2, items.length), R = 2.4, nodes = [];
    add(new THREE.TorusGeometry(R, 0.05, 16, 128), M.gold, [0, 0.12, 0]).rotation.x = Math.PI / 2;
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2 - Math.PI / 2, c = col(`item${i}`, ['#4C7DFF', '#38BDF8', '#9B5CFF', '#34C759', '#E8C268'][i % 5]);
      const m = add(new THREE.CylinderGeometry(0.42, 0.42, 0.3, 48), paint(c, 0.1), [Math.cos(a) * R, 0.15, Math.sin(a) * R]);
      const anchor = new THREE.Object3D(); anchor.position.set(0, 0.55, 0); m.add(anchor);
      label(items[i], anchor, { at: itemAt(i), size: 36, key: `item${i}` });
      nodes.push({ m, at: itemAt(i) });
    }
    const runner = add(new THREE.SphereGeometry(0.14, 24, 12), paint(new THREE.Color('#ffffff'), 2), [0, 0.2, 0]);
    look([0, 6.0, 7.4], [0, -0.2, 0]);
    update = (t) => {
      const a = (t * 0.9) % (Math.PI * 2) - Math.PI / 2; runner.position.set(Math.cos(a) * R, 0.2, Math.sin(a) * R);
      for (const N of nodes) { const k = back(Math.min(1, Math.max(0, (t - N.at) / 0.4))); N.m.scale.set(1, 0.3 + 0.7 * k, 1); N.m.material.emissiveIntensity = 0.1 + 0.5 * ease((t - N.at) / 0.4); }
    };
  }
  cam.aspect = W / H; cam.updateProjectionMatrix();
  return function render(t) {
    update(t);
    renderer.render(scene, cam);
    drawLabels(t);
  };
}
