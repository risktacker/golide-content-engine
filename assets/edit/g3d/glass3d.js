// Glass 3D objects (owner 2026-11-13): the approved devices (laptop, phone, server, chip, battery) as clear glass
// with lit edges and one polished gold part, rendered by three.js inside the video. Same parts and moves as the old
// engine (vector/motion3d.py); coordinates there are x, y, z-up, here x, y-up, z = -y.
import * as THREE from 'three';
import { RoomEnvironment } from '../examples/jsm/environments/RoomEnvironment.js';
import { RoundedBoxGeometry } from '../examples/jsm/geometries/RoundedBoxGeometry.js';

const ease = (t) => { t = Math.min(1, Math.max(0, t)); return t * t * (3 - 2 * t); };
const B = (cx, cy, cz, sx, sy, sz, gold = false, rx = null) => ({ c: [cx, cy, cz], s: [sx, sy, sz], gold, rx });

const OBJECTS = {
  laptop(u) {
    const a = -108 * Math.PI / 180 * u, hinge = [0, 1.0, 0.145];
    return [B(0, 0, 0, 3.0, 2.0, 0.12), B(0, 0.32, 0.12, 2.6, 0.95, 0.012), B(0, -0.55, 0.12, 0.95, 0.52, 0.006),
            B(0, 0, 0.145, 3.0, 2.0, 0.065, false, { a, p: hinge }), B(0, 0.02, 0.137, 2.7, 1.66, 0.008, u > 0.55, { a, p: hinge })];
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

function place(part) {   // centre of the part and its x-rotation, in three.js coordinates
  let [x, y, z] = part.c; z += part.s[2] / 2;
  let a = 0;
  if (part.rx) {
    a = part.rx.a; const [, py, pz] = part.rx.p; const c = Math.cos(a), s = Math.sin(a);
    const qy = y - py, qz = z - pz; y = qy * c - qz * s + py; z = qy * s + qz * c + pz;
  }
  return { pos: new THREE.Vector3(x, z, -y), a };
}

export function mount(canvas, name, opts = {}) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1);
  renderer.setSize(canvas.width, canvas.height, false);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.1;
  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  const key = new THREE.DirectionalLight(0xffffff, 1.5); key.position.set(5, 8, 2); scene.add(key);
  const rim = new THREE.DirectionalLight(0x7fb2ff, 2.0); rim.position.set(-5, 3, -4); scene.add(rim);

  const glass = new THREE.MeshPhysicalMaterial({ color: 0xbfe2ff, metalness: 0, roughness: 0.03, transmission: 1,
    thickness: 0.25, ior: 1.5, clearcoat: 1, clearcoatRoughness: 0.02, attenuationColor: new THREE.Color(0x5aa0ff),
    attenuationDistance: 2.2, envMapIntensity: 0.75, transparent: true, opacity: 0.55, depthWrite: false,
    side: THREE.DoubleSide });
  const gold = new THREE.MeshPhysicalMaterial({ color: 0xe8b84a, metalness: 0.7, roughness: 0.5, clearcoat: 0.15,
    emissive: 0x7a4c00, emissiveIntensity: 0.8, envMapIntensity: 0.45, specularIntensity: 0.4 });
  const edgeMat = new THREE.LineBasicMaterial({ color: 0xd8ecff, transparent: true, opacity: 0.85 });
  const goldEdge = new THREE.LineBasicMaterial({ color: 0xffd98a, transparent: true, opacity: 0.9 });

  const make = OBJECTS[name];
  // fit: centre and scale over the whole move so the object never leaves its frame
  const box = new THREE.Box3();
  for (let i = 0; i <= 10; i++) for (const p of make(i / 10)) {
    const { pos } = place(p); const h = new THREE.Vector3(p.s[0] / 2, p.s[2] / 2, p.s[1] / 2);
    box.expandByPoint(pos.clone().sub(h)); box.expandByPoint(pos.clone().add(h));
  }
  const centre = box.getCenter(new THREE.Vector3()), size = box.getSize(new THREE.Vector3()).length();
  const turn = new THREE.Group(); scene.add(turn);          // turns about the object's own centre
  const group = new THREE.Group(); turn.add(group); group.position.set(-centre.x, 0, -centre.z);
  const meshes = make(0).map((p) => {
    const r = Math.min(0.04, Math.min(...p.s) * 0.45);
    const geo = new RoundedBoxGeometry(p.s[0], p.s[2], p.s[1], 3, r);
    const m = new THREE.Mesh(geo, glass);
    const e = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(p.s[0], p.s[2], p.s[1])), edgeMat);
    m.add(e); group.add(m); return { m, e };
  });
  // a soft glow on the floor under it
  const glowTex = (() => { const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d');
    const r = g.createRadialGradient(128, 128, 0, 128, 128, 128); r.addColorStop(0, 'rgba(232,194,104,.28)'); r.addColorStop(1, 'rgba(232,194,104,0)');
    g.fillStyle = r; g.fillRect(0, 0, 256, 256); return new THREE.CanvasTexture(c); })();
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(size * 0.95, size * 0.95), new THREE.MeshBasicMaterial({ map: glowTex, transparent: true, depthWrite: false }));
  floor.rotation.x = -Math.PI / 2; floor.position.y = box.min.y - 0.02; turn.add(floor);

  const camera = new THREE.PerspectiveCamera(28, canvas.width / canvas.height, 0.1, 100);
  const dist = size * 1.75;
  camera.position.set(0, centre.y + size * 0.5, dist);
  camera.lookAt(0, centre.y, 0);

  return function render(u, yaw) {
    make(u).forEach((p, i) => {
      const { pos, a } = place(p); const { m, e } = meshes[i];
      m.position.copy(pos); m.rotation.set(a, 0, 0);
      m.material = p.gold ? gold : glass; e.material = p.gold ? goldEdge : edgeMat;
    });
    turn.rotation.y = yaw;
    renderer.render(scene, camera);
  };
}
