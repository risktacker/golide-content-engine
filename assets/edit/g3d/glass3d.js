// 3D objects in the video (owner 2026-11-13, looks and moves 2026-11-17): the approved devices (laptop, phone,
// server, chip, battery) or ANY object the storyboard builds from parts, with one gold part the story is about.
// Five looks (Futurepedia 3D atlas, owner's picks): glass (Glass and Light), xray, circuit (Circuit City),
// white (White Model), layers (Layer Stack); one look per video. Moves land on the spoken word: the object's own
// move, explode, assemble, lift, rise (parts build up), spin. Coordinates: x, y, z-up (as vector/motion3d.py);
// three.js is x, y-up, z = -y.
import * as THREE from 'three';
import { RoomEnvironment } from '../examples/jsm/environments/RoomEnvironment.js';
import { RoundedBoxGeometry } from '../examples/jsm/geometries/RoundedBoxGeometry.js';

const ease = (t) => { t = Math.min(1, Math.max(0, t)); return t * t * (3 - 2 * t); };
const B = (cx, cy, cz, sx, sy, sz, gold = false, rx = null, shape = 'box') => ({ c: [cx, cy, cz], s: [sx, sy, sz], gold, rx, shape });

const OBJECTS = {
  laptop(u, o = {}) {
    // owner 2026-11-25: a thin lid with slim bezels, like a MacBook (the lid was 3 times too thick); the keyboard
    // changes from showing to showing: smooth (no keys), real keys, or neon keys
    const a = -108 * Math.PI / 180 * u, hinge = [0, 1.0, 0.145];
    const out = [B(0, 0, 0, 3.0, 2.0, 0.12), B(0, 0.32, 0.12, 2.6, 0.95, o.keys === 'none' || !o.keys ? 0.012 : 0.003),
                 B(0, -0.55, 0.12, 0.95, 0.52, 0.006),
                 B(0, 0, 0.145, 3.0, 2.0, 0.022, false, { a, p: hinge }), B(0, -0.02, 0.139, 2.9, 1.84, 0.005, u > 0.55, { a, p: hinge })];
    if (o.keys === 'keys' || o.keys === 'neon') {
      const cols = 14, rows = 5, w = 2.6 / cols, h = 0.95 / rows, back = 0.32 + 0.475;
      for (let r = 0; r < rows; r++) {
        const y = back - h * (r + 0.5);
        if (r === rows - 1) {          // the front row: a space bar between the side keys
          for (let c = 0; c < cols; c++) {
            if (c >= 4 && c <= 9) { if (c === 4) out.push({ ...B(0 + w * (6.5 - 6.5), y, 0.123, w * 6 - 0.03, h - 0.035, 0.012), key: c / cols }); continue; }
            out.push({ ...B(-1.3 + w * (c + 0.5), y, 0.123, w - 0.03, h - 0.035, 0.012), key: c / cols });
          }
        } else {
          for (let c = 0; c < cols; c++) out.push({ ...B(-1.3 + w * (c + 0.5), y, 0.123, w - 0.03, h - 0.035, 0.012), key: c / cols });
        }
      }
    }
    return out;
  },
  phone(u) {
    const out = []; let z = 0;
    [0.07, 0.11, 0.05, 0.08, 0.05, 0.06].forEach((t, k) => { out.push(B(0, 0, z + u * k * 0.42, 1.25, 2.5, t, k === 4 && u > 0.5)); z += t; });
    return out;
  },
  server(u) {
    const p = [B(-1.05, 0, 0, 0.1, 1.6, 3.0), B(1.05, 0, 0, 0.1, 1.6, 3.0), B(0, 0, 3.0, 2.2, 1.6, 0.08), B(0, 0, -0.08, 2.2, 1.6, 0.08)];
    for (let k = 0; k < 5; k++) p.push(B(0, k === 2 ? -1.4 * u : 0, 0.12 + k * 0.58, 1.98, 1.5, 0.46, k === 2 && u > 0.3));
    return p;
  },
  chip(u) {
    const lift = 1.3 * ease(u / 0.75), tip = 14 * Math.PI / 180 * ease((u - 0.45) / 0.55), piv = [0, 0.95, 0.3 + lift];
    const cap = [B(0, 0, 0.3 + lift, 1.9, 1.9, 0.08), B(-0.9, 0, 0.12 + lift, 0.1, 1.9, 0.18), B(0.9, 0, 0.12 + lift, 0.1, 1.9, 0.18),
                 B(0, -0.9, 0.12 + lift, 1.7, 0.1, 0.18), B(0, 0.9, 0.12 + lift, 1.7, 0.1, 0.18)];
    return [B(0, 0, 0, 2.6, 2.6, 0.12), B(0, 0, 0.12, 1.0, 1.0, 0.1, u > 0.4), ...cap.map((b) => ({ ...b, rx: { a: tip, p: piv } }))];
  },
  battery(u) {
    const p = [B(0, 0, 0, 2.8, 1.8, 0.1), B(-1.35, 0, 0.1, 0.1, 1.8, 0.72), B(1.35, 0, 0.1, 0.1, 1.8, 0.72),
               B(0, -0.85, 0.1, 2.6, 0.1, 0.72), B(0, 0.85, 0.1, 2.6, 0.1, 0.72)];
    for (let i = 0; i < 4; i++) for (let j = 0; j < 2; j++) {
      const k = i * 2 + j, lift = 1.0 * ease((u - k * 0.05) / 0.65);
      p.push(B(-0.96 + i * 0.64, -0.38 + j * 0.76, 0.1 + lift, 0.52, 0.62, 0.62, i === 1 && j === 0 && u > 0.5));
    }
    return p;
  },
};

// what each part is called (in part order), and the parts labelled by default: the gold one first
export const NAMES = {
  laptop: ['Base', 'Keyboard', 'Trackpad', 'Lid', 'Screen'],
  phone: ['Back glass', 'Battery', 'Logic board', 'Midframe', 'Display', 'Cover glass'],
  server: ['Rack', 'Rack', 'Top', 'Bottom', 'Server 1', 'Server 2', 'Server 3', 'Server 4', 'Server 5'],
  chip: ['Substrate', 'Die', 'Heat spreader', 'Wall', 'Wall', 'Wall', 'Wall'],
  battery: ['Case', 'Wall', 'Wall', 'Wall', 'Wall', ...Array.from({ length: 8 }, (_, k) => `Cell ${k + 1}`)],
};
const DEFAULT = { laptop: [4, 1, 2], phone: [4, 1, 2], server: [6, 0], chip: [1, 2, 0], battery: [7, 0] };
export const LOOKS = ['glass', 'xray', 'circuit', 'white', 'layers'];
export const MOVES = ['own', 'explode', 'assemble', 'lift', 'rise', 'spin'];

// ANY object (2026-11-17): parts from the storyboard, [{shape: box|cyl|sphere, x, y, z, w, d, h, gold, mover, name}]
// (z is the part's base). Its own move: "mover" parts slide out to the front.
function custom(parts) {
  return (u) => parts.map((p) => B(+p.x || 0, (+p.y || 0) - (p.mover ? 1.3 * u : 0), +p.z || 0,
    Math.max(0.04, +p.w || 0.5), Math.max(0.04, +p.d || 0.5), Math.max(0.04, +p.h || 0.5), !!p.gold,
    null, ['cyl', 'sphere'].includes(p.shape) ? p.shape : 'box'));
}

// a move on top of the object's own parts. u = 0..1 over the move, landing on the spoken word.
function moved(make, move, goldIndex) {
  const rest = make(0);
  const mid = rest.reduce((a, p) => [a[0] + p.c[0], a[1] + p.c[1], a[2] + p.c[2] + p.s[2] / 2], [0, 0, 0]).map((v) => v / rest.length);
  // a part pushed out sideways from the centre and up by its height in the object (lowest stays down), so
  // stacked things fan into layers and side parts open out, never a gap in the middle
  const rank = rest.map((p, k) => k).sort((a, b) => rest[a].c[2] - rest[b].c[2] || a - b);
  const level = rest.map((_, k) => rank.indexOf(k));
  const away = (p, k, f) => {
    const d = [p.c[0] - mid[0], p.c[1] - mid[1]];
    const n = Math.hypot(...d);
    const side = n > 0.05 ? 0.9 / n : 0;
    return { ...p, c: [p.c[0] + d[0] * side * f, p.c[1] + d[1] * side * f, p.c[2] + level[k] * 0.32 * f] };
  };
  if (move === 'explode') return (u) => make(0).map((p, k) => ({ ...away(p, k, ease(u)), gold: p.gold || (k === goldIndex && u > 0.5) }));
  if (move === 'assemble') return (u) => make(0).map((p, k) => ({ ...away(p, k, 1 - ease(u)), gold: p.gold || (k === goldIndex && u > 0.6) }));
  if (move === 'lift') return (u) => make(0).map((p, k) => (k === goldIndex
    ? { ...p, c: [p.c[0], p.c[1], p.c[2] + 1.2 * ease(u)], gold: u > 0.2 } : p));
  if (move === 'rise') return (u) => make(0).map((p, k, all) => {
    const f = ease((u - k / all.length * 0.6) / 0.4);
    return { ...p, c: [p.c[0], p.c[1], p.c[2] + 2.2 * (1 - f)], fade: f, gold: p.gold || (k === goldIndex && u > 0.85) };
  });
  return make;                    // own (and spin: the object's own move plus a full turn, in render)
}

const shapeGeo = (p) => {
  const [w, d, h] = p.s;
  if (p.shape === 'cyl') { const g = new THREE.CylinderGeometry(0.5, 0.5, 1, 48); g.scale(w, h, d); return g; }
  if (p.shape === 'sphere') { const g = new THREE.SphereGeometry(0.5, 48, 32); g.scale(w, h, d); return g; }
  return new RoundedBoxGeometry(w, h, d, 3, Math.min(0.04, Math.min(...p.s) * 0.45));
};
const edgeGeo = (p) => {
  const [w, d, h] = p.s;
  if (p.shape === 'cyl') { const g = new THREE.EdgesGeometry(new THREE.CylinderGeometry(0.5, 0.5, 1, 32), 30); g.scale(w, h, d); return g; }
  if (p.shape === 'sphere') { const g = new THREE.EdgesGeometry(new THREE.SphereGeometry(0.5, 12, 8), 1); g.scale(w, h, d); return g; }
  return new THREE.EdgesGeometry(new THREE.BoxGeometry(w, h, d));
};

function place(part) {   // centre of the part and its x-rotation, in three.js coordinates
  let [x, y, z] = part.c; z += part.s[2] / 2;
  let a = 0;
  if (part.rx) {
    a = part.rx.a; const [, py, pz] = part.rx.p; const c = Math.cos(a), s = Math.sin(a);
    const qy = y - py, qz = z - pz; y = qy * c - qz * s + py; z = qy * s + qz * c + pz;
  }
  return { pos: new THREE.Vector3(x, z, -y), a };
}

const radial = (rgba0, rgba1) => { const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d');
  const r = g.createRadialGradient(128, 128, 0, 128, 128, 128); r.addColorStop(0, rgba0); r.addColorStop(1, rgba1);
  g.fillStyle = r; g.fillRect(0, 0, 256, 256); return new THREE.CanvasTexture(c); };

// the five looks: body material(s), edge colours, lights, floor
function lookOf(name, n) {
  const gold = new THREE.MeshPhysicalMaterial({ color: 0xe8b84a, metalness: 0.7, roughness: 0.5, clearcoat: 0.15,
    emissive: 0x7a4c00, emissiveIntensity: 0.8, envMapIntensity: 0.45, specularIntensity: 0.4 });
  const goldEdge = new THREE.LineBasicMaterial({ color: 0xffd98a, transparent: true, opacity: 0.9 });
  const line = (color, opacity) => new THREE.LineBasicMaterial({ color, transparent: true, opacity });
  if (name === 'xray') {
    const body = new THREE.MeshBasicMaterial({ color: 0x1f9bff, transparent: true, opacity: 0.07, depthWrite: false,
      blending: THREE.AdditiveBlending, side: THREE.DoubleSide });
    const hot = new THREE.MeshBasicMaterial({ color: 0xffc35a, transparent: true, opacity: 0.85, depthWrite: false,
      blending: THREE.AdditiveBlending });
    return { body: () => body, gold: hot, edge: line(0x6fe8ff, 1), goldEdge: line(0xffe2a0, 1), exposure: 1.0,
      lights: [], floor: radial('rgba(47,184,255,.30)', 'rgba(47,184,255,0)'), scan: true };
  }
  if (name === 'circuit') {
    const body = new THREE.MeshStandardMaterial({ color: 0x0c1c2c, metalness: 0.65, roughness: 0.35, envMapIntensity: 0.6 });
    return { body: () => body, gold, edge: line(0x19f0b4, 0.95), goldEdge, exposure: 1.05,
      lights: [[0x19f0b4, 1.2, [-4, 4, 3]], [0xffffff, 1.0, [5, 8, 2]]],
      floor: radial('rgba(25,240,180,.22)', 'rgba(25,240,180,0)'), grid: 0x19f0b4 };
  }
  if (name === 'white') {
    const body = new THREE.MeshStandardMaterial({ color: 0xf1efe9, metalness: 0, roughness: 0.6, envMapIntensity: 0.9 });
    return { body: () => body, gold, edge: line(0xb9bcc2, 0.35), goldEdge, exposure: 1.0,
      lights: [[0xffffff, 2.2, [5, 9, 4]], [0xdfe8ff, 0.8, [-6, 4, -3]]],
      floor: radial('rgba(0,0,0,.55)', 'rgba(0,0,0,0)'), floorDark: true };
  }
  if (name === 'layers') {
    const tints = [0x3d7bff, 0x5a6cff, 0x7a5cff, 0x9a52ff, 0xb84cf0, 0x4fa8ff];
    const mats = tints.map((c) => new THREE.MeshPhysicalMaterial({ color: c, metalness: 0.1, roughness: 0.25, transmission: 0.35,
      thickness: 0.3, transparent: true, opacity: 0.78, clearcoat: 1, envMapIntensity: 0.8, emissive: c, emissiveIntensity: 0.18 }));
    return { body: (k) => mats[k % mats.length], gold, edge: line(0xe6e9ff, 0.8), goldEdge, exposure: 1.05,
      lights: [[0xffffff, 1.4, [5, 8, 2]], [0xb38cff, 1.6, [-5, 3, -4]]],
      floor: radial('rgba(122,92,255,.28)', 'rgba(122,92,255,0)'), spread: 0.22 };
  }
  const glass = new THREE.MeshPhysicalMaterial({ color: 0xbfe2ff, metalness: 0, roughness: 0.03, transmission: 1,
    thickness: 0.25, ior: 1.5, clearcoat: 1, clearcoatRoughness: 0.02, attenuationColor: new THREE.Color(0x5aa0ff),
    attenuationDistance: 2.2, envMapIntensity: 0.75, transparent: true, opacity: 0.55, depthWrite: false,
    side: THREE.DoubleSide });
  return { body: () => glass, gold, edge: line(0xd8ecff, 0.85), goldEdge, exposure: 1.1,
    lights: [[0xffffff, 1.5, [5, 8, 2]], [0x7fb2ff, 2.0, [-5, 3, -4]]], floor: radial('rgba(232,194,104,.28)', 'rgba(232,194,104,0)') };
}

export function mount(canvas, name, opts = {}) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1);
  renderer.setSize(canvas.width, canvas.height, false);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  const look = lookOf(LOOKS.includes(opts.look) ? opts.look : 'glass');
  renderer.toneMappingExposure = look.exposure;
  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  for (const [c, i, p] of look.lights) { const l = new THREE.DirectionalLight(c, i); l.position.set(...p); scene.add(l); }

  const base = OBJECTS[name] ? ((u) => OBJECTS[name](u, opts))
    : (opts.parts && opts.parts.length ? custom(opts.parts) : OBJECTS.chip);
  const keyMat = (hue) => opts.keys === 'neon'      // neon keys: a lit rainbow across the board
    ? new THREE.MeshStandardMaterial({ color: 0x0b0d14, emissive: new THREE.Color().setHSL(0.5 + 0.45 * hue, 1, 0.38),
      emissiveIntensity: 1.0, roughness: 0.4, toneMapped: false })
    : new THREE.MeshStandardMaterial({ color: 0x1b1e26, metalness: 0.2, roughness: 0.55 });
  const names = NAMES[name] || (opts.parts || []).map((p, k) => p.name || `Part ${k + 1}`);
  const parts0 = base(0);
  let goldIndex = parts0.findIndex((p) => p.gold);
  if (goldIndex < 0) { const own = base(1).findIndex((p) => p.gold); goldIndex = own >= 0 ? own : (DEFAULT[name] || [0])[0]; }
  const move = MOVES.includes(opts.move) ? opts.move : 'own';
  const spread = look.spread || 0;
  const make = ((m) => (u) => m(u).map((p, k) => (spread ? { ...p, c: [p.c[0], p.c[1], p.c[2] + k * spread] } : p)))(moved(base, move, goldIndex));

  // fit: centre and scale over the whole move so the object never leaves its frame
  const box = new THREE.Box3();
  const whole = name === 'phone' && !!opts.screen;    // a phone showing a real screen does not come apart
  for (let i = 0; i <= 10; i++) for (const p of make(whole ? 0 : i / 10)) {
    const { pos } = place(p); const h = new THREE.Vector3(p.s[0] / 2, p.s[2] / 2, p.s[1] / 2);
    box.expandByPoint(pos.clone().sub(h)); box.expandByPoint(pos.clone().add(h));
  }
  const centre = box.getCenter(new THREE.Vector3()), size = box.getSize(new THREE.Vector3()).length();
  const turn = new THREE.Group(); scene.add(turn);          // turns about the object's own centre
  const group = new THREE.Group(); turn.add(group); group.position.set(-centre.x, 0, -centre.z);
  const meshes = parts0.map((p, k) => {
    const m = new THREE.Mesh(shapeGeo(p), look.body(k));
    const e = new THREE.LineSegments(edgeGeo(p), look.edge);
    if (p.key !== undefined) { m.material = keyMat(p.key); m.userData.key = true; e.visible = false; }
    m.add(e); group.add(m); return { m, e, k };
  });
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(size * 0.95, size * 0.95),
    new THREE.MeshBasicMaterial({ map: look.floor, transparent: true, depthWrite: false }));
  floor.rotation.x = -Math.PI / 2; floor.position.y = box.min.y - 0.02; turn.add(floor);
  if (look.grid) {           // Circuit City: the object stands on a lit board of traces
    const grid = new THREE.GridHelper(size * 1.1, 22, look.grid, look.grid);
    grid.material.transparent = true; grid.material.opacity = 0.22; grid.position.y = box.min.y - 0.015; turn.add(grid);
  }
  let scan = null;           // X-Ray: a thin scanner ring sweeps up through the object
  if (look.scan) {
    const sz = box.getSize(new THREE.Vector3()), w = sz.x * 0.62 + 0.15, d = sz.z * 0.62 + 0.15;
    const ring = new THREE.BufferGeometry().setFromPoints([[-w, -d], [w, -d], [w, d], [-w, d], [-w, -d]]
      .map(([x, z]) => new THREE.Vector3(x, 0, z)));
    scan = new THREE.Line(ring, new THREE.LineBasicMaterial({ color: 0x9ff0ff, transparent: true, opacity: 0.9,
      blending: THREE.AdditiveBlending }));
    turn.add(scan);
  }

  const camera = new THREE.PerspectiveCamera(28, canvas.width / canvas.height, 0.1, 100);
  const dist = size * 1.75;
  // owner 2026-11-25 ("same way, same colour, same visual, and the screen is empty"): each showing sits at its own
  // height, and a device with a screen shows the real page or picture of what is being said on it
  const elev = [0.5, 0.28, 0.78, 0.4][(+opts.view || 0) % 4];
  camera.position.set(0, centre.y + size * elev, dist);
  camera.lookAt(0, centre.y, 0);
  const SCREEN = { laptop: { part: 4, w: 2.86, h: 1.8, y: -1 }, phone: { part: 5, w: 1.17, h: 2.38, y: 1 } };
  const glass = SCREEN[name];
  const shot = glass && opts.screen ? document.getElementById(opts.screen) : null;
  let tex = null, shown = false;
  if (shot) {
    tex = new THREE.Texture(shot); tex.colorSpace = THREE.SRGBColorSpace;
    const plane = new THREE.Mesh(new THREE.PlaneGeometry(glass.w, glass.h),
      new THREE.MeshBasicMaterial({ map: tex, toneMapped: false, side: THREE.DoubleSide }));
    const host = meshes[glass.part].m, thick = parts0[glass.part].s[2];
    plane.rotation.x = glass.y < 0 ? Math.PI / 2 : -Math.PI / 2;
    plane.position.y = glass.y * (thick / 2 + 0.004);
    host.add(plane);
  }
  const fit = () => {       // the page's top, cropped to fill the screen (cover), once the picture has loaded
    if (!tex || shown || !shot.complete || !shot.naturalWidth) return;
    const a = (shot.naturalWidth / shot.naturalHeight) / (glass.w / glass.h);
    // a page reads from its left: a tall phone shows the page's left column, a laptop its middle
    if (a > 1) { tex.repeat.set(1 / a, 1); tex.offset.set(name === 'phone' ? 0 : (1 - 1 / a) / 2, 0); }
    else { tex.repeat.set(1, a); tex.offset.set(0, 1 - a); }
    tex.needsUpdate = true; shown = true;
  };

  // callouts: a thin line from the exact spot on a part to a small label beside the object (owner 2026-11-13)
  const overlay = opts.overlay || null;
  const want = opts.callouts && opts.callouts.length ? opts.callouts
    : (DEFAULT[name] || [goldIndex, ...parts0.map((_, k) => k).filter((k) => k !== goldIndex && opts.parts && opts.parts[k] && opts.parts[k].name)]).map((i) => ({ part: i }));
  const callouts = want.filter((c) => c.part >= 0 && c.part < parts0.length).slice(0, 3)
    .map((c, k) => ({ ...c, text: (k === 0 && opts.lead) || c.text || names[c.part] || '', k }))
    .filter((c) => c.text);
  const ns = 'http://www.w3.org/2000/svg';
  const els = overlay ? callouts.map((c) => {
    const g = document.createElementNS(ns, 'g');
    const line = document.createElementNS(ns, 'polyline');
    line.setAttribute('fill', 'none'); line.setAttribute('stroke', c.k === 0 ? '#E8C268' : '#CFE6FF');
    line.setAttribute('stroke-width', '4');
    const dot = document.createElementNS(ns, 'circle'); dot.setAttribute('r', '11');
    dot.setAttribute('fill', c.k === 0 ? '#E8C268' : '#CFE6FF'); dot.setAttribute('stroke', '#07080B'); dot.setAttribute('stroke-width', '3');
    const box = document.createElementNS(ns, 'g');
    const rect = document.createElementNS(ns, 'rect'); rect.setAttribute('rx', '14');
    rect.setAttribute('fill', c.k === 0 ? '#E8C268' : 'rgba(10,12,18,.88)');
    rect.setAttribute('stroke', c.k === 0 ? '#E8C268' : 'rgba(207,230,255,.6)'); rect.setAttribute('stroke-width', '2');
    const txt = document.createElementNS(ns, 'text'); txt.textContent = c.text;
    txt.setAttribute('font-family', 'Poppins'); txt.setAttribute('font-weight', '800'); txt.setAttribute('font-size', '42');
    txt.setAttribute('fill', c.k === 0 ? '#07080B' : '#F4F1EA'); txt.setAttribute('dominant-baseline', 'middle');
    box.append(rect, txt); g.append(line, dot, box); overlay.append(g);
    const w = c.text.length * 42 * 0.6 + 44;
    return { g, line, dot, rect, txt, w };
  }) : [];
  const W = canvas.width, Hh = canvas.height, v = new THREE.Vector3();

  function label(t) {
    // anchor: the top middle of the part, as it is now on screen
    const at = (c, ox = 0, oz = 0) => {
      const { m } = meshes[c.part]; const s = parts0[c.part].s;
      m.updateMatrixWorld(); v.set(ox * s[0], s[2] / 2, oz * s[1]); m.localToWorld(v); v.project(camera);
      return { x: (v.x + 1) / 2 * W, y: (1 - v.y) / 2 * Hh };
    };
    const pts = callouts.map((c) => at(c));
    // two dots on the same spot (a part sitting in the middle of another): the bigger part's moves to its edge
    for (let i = 0; i < pts.length; i++) for (let j = 0; j < i; j++) {
      if (Math.hypot(pts[i].x - pts[j].x, pts[i].y - pts[j].y) < 70) {
        const big = parts0[callouts[i].part].s[0] >= parts0[callouts[j].part].s[0] ? i : j;
        pts[big] = at(callouts[big], 0.36, 0.3);
      }
    }
    // labels in two columns beside the object, kept apart and in the order of their anchors
    const sides = { left: [], right: [] };
    pts.forEach((p, i) => (p.x < W / 2 ? sides.left : sides.right).push(i));
    for (const [side, idx] of Object.entries(sides)) {
      idx.sort((a, b) => pts[a].y - pts[b].y);
      let last = -1e9;
      idx.forEach((i) => {
        const p = pts[i], el = els[i], c = callouts[i];
        const st = opts.safe || [0, 0, 0, 0]; let ly = Math.max(p.y - 70, last + 96, 56, st[2] + 52); ly = Math.min(ly, Hh - 50 - st[3]); last = ly;
        // owner 2026-11-27 ("some blocks had cut edges"): a label never leaves its frame. The left one was kept
        // 20 px in BEFORE its width was taken off, so long labels ran off the left edge ("...dden credits").
        // Its real width is measured, and both sides keep a margin (the phone crop on a Short).
        if (!el.measured && el.txt.getComputedTextLength) { const m = el.txt.getComputedTextLength(); if (m > 0) { el.w = m + 44; el.measured = true; } }
        const sf = opts.safe || [0, 0, 0, 0], ml = Math.max(40, W * 0.05, sf[0] + 16), mr = Math.max(40, W * 0.05, sf[1] + 16);
        const lx = side === 'left' ? Math.max(ml, Math.min(p.x - 160, W * 0.16) - el.w) : Math.max(ml, Math.min(W - mr - el.w, Math.max(p.x + 160, W * 0.84)));
        const edge = side === 'left' ? lx + el.w : lx;
        const knee = side === 'left' ? edge + 30 : edge - 30;
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
    fit();
    // a phone showing a real screen stays whole (its layers would hide the screen); the camera does the moving
    make(whole ? 0 : u).forEach((p, i) => {
      const { pos, a } = place(p); const { m, e, k } = meshes[i];
      m.position.copy(pos); m.rotation.set(a, 0, 0);
      const lit = p.gold && !(tex && glass && i === glass.part);   // a screen showing a picture is not painted gold
      if (!m.userData.key) { m.material = lit ? look.gold : look.body(k); e.material = p.gold ? look.goldEdge : look.edge; }
      const f = p.fade === undefined ? 1 : p.fade;
      m.visible = f > 0.02; m.scale.setScalar(0.6 + 0.4 * f);
    });
    turn.rotation.y = yaw + (move === 'spin' ? Math.PI * 2 * ease(u) : 0);
    if (scan) { const lo = box.min.y, hi = box.max.y; scan.position.y = lo + (hi - lo) * (0.5 - 0.5 * Math.cos(t * 1.6)); }
    renderer.render(scene, camera);
    if (els.length) label(t);
  };
}
