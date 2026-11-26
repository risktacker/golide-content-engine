// The living studio (owner 2026-11-26): Goli's office as ONE 3D set (assets/goli3d/live/studio.glb, built once by
// tools/goli3d_studio_live.py with the room's Cycles light baked into every piece) and the live Goli in it
// (goli_live.js). The camera is the plates' own camera, so the default shot looks like today's studio; the pieces
// move (the chair rolls and turns, the mug lifts) and he can get up, walk, turn and sit down again.
//
// plan: everything goli_live.js reads, plus
//   props: [{at, piece: 'chair'|'mug'|'laptop'|'mic', dx, dy, turn, dur}]   (metres, degrees; each move adds on)
//   screens: {tv: url, laptop: url}                                         (the video's pictures on the screens)
import * as THREE from 'three';
import { GLTFLoader } from '../examples/jsm/loaders/GLTFLoader.js';
import { mount as mountGoli } from './goli_live.js';

const V = (b) => new THREE.Vector3(b[0], b[2], -b[1]);
const ease = (t) => { t = Math.min(1, Math.max(0, t)); return t * t * (3 - 2 * t); };
// where Goli sits so the default shot matches the sprite studio (solved against the plates, 2026-11-26)
export const SEAT = { x: -0.574, y: -0.95, scale: 0.55, seatZ: 0.606, floorZ: 0.135 };

export async function mountStudio(canvas, opts = {}) {
  const base = opts.base || './goli3d';
  const W = canvas.width, H = canvas.height;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1); renderer.setSize(W, H, false);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  const scene = new THREE.Scene();
  const [set, gltf] = await Promise.all([fetch(`${base}/studio-set.json`).then((r) => r.json()), new GLTFLoader().loadAsync(`${base}/studio.glb`)]);

  // the camera of the plates: lens, sensor on the wide side, lens shift
  const c = set.camera, big = c.sensor / 2 / c.lens;
  const vfov = W >= H ? 2 * Math.atan(big * H / W) : 2 * Math.atan(big);   // Blender's AUTO sensor fit
  const cam = new THREE.PerspectiveCamera(vfov * 180 / Math.PI, W / H, 0.05, 100);
  cam.position.copy(V(c.pos)); cam.lookAt(V([c.pos[0], c.pos[1] + 1, c.pos[2]]));
  cam.setViewOffset(W, H, 0, -c.shift_y * Math.max(W, H), W, H);

  // the room: baked pictures drawn as they are (no light, no tone mapping: they ARE the Cycles render)
  const pieces = { chair: new THREE.Group(), mug: new THREE.Group(), laptop: new THREE.Group(), mic: new THREE.Group() };
  const room = gltf.scene; scene.add(room);
  const screens = {};
  const meshes = []; room.traverse((o) => { if (o.isMesh) meshes.push(o); });
  for (const o of meshes) {
    const m = o.material;
    if (o.name === 'tv_screen' || o.name === 'laptop_screen') {
      o.material = new THREE.MeshBasicMaterial({ color: 0x05060a, toneMapped: false });
      screens[o.name === 'tv_screen' ? 'tv' : 'laptop'] = o;
    } else {
      o.material = new THREE.MeshBasicMaterial({ map: m.map || null, color: m.map ? 0xffffff : m.color, toneMapped: false });
    }
    o.receiveShadow = true;
    const part = (o.name.match(/^(chair|mug|laptop|mic)__/) || [])[1] || (o.name === 'laptop_screen' ? 'laptop' : null);
    if (part) pieces[part].attach(o);
  }
  for (const [name, g] of Object.entries(pieces)) {    // each piece turns and slides about its own base
    const pv = set.pieces[name]; if (!pv) continue;
    const pivot = new THREE.Group(); pivot.position.copy(V(pv.base)); scene.add(pivot);
    pivot.attach(g); pieces[name] = pivot;
  }
  // Goli's shadow on the room (desk top, floor, chair): a shadow-only layer over the baked pictures
  const catcher = new THREE.Mesh(new THREE.PlaneGeometry(12, 8), new THREE.ShadowMaterial({ opacity: 0.28 }));
  catcher.rotation.x = -Math.PI / 2; catcher.position.y = SEAT.floorZ + 0.002; catcher.receiveShadow = true; scene.add(catcher);
  const deskTop = new THREE.Mesh(new THREE.PlaneGeometry(set.desk.x[1] - set.desk.x[0], 0.95), new THREE.ShadowMaterial({ opacity: 0.22 }));
  deskTop.rotation.x = -Math.PI / 2; deskTop.position.set((set.desk.x[0] + set.desk.x[1]) / 2, set.desk.top_z + 0.003, -(set.desk.front_y + 0.475));
  deskTop.receiveShadow = true; scene.add(deskTop);

  const centre = (o) => { const b = new THREE.Box3().setFromObject(o); const v = b.getCenter(new THREE.Vector3()); return [v.x, -v.z, v.y]; };
  const targets = { camera: c.pos, screen: screens.tv ? centre(screens.tv) : [1.2, 0, 2.2], laptop: screens.laptop ? centre(screens.laptop) : [SEAT.x, -1.5, 1.2],
    mug: centre(pieces.mug), up: [SEAT.x + 0.4, -3, 3.2], down: [SEAT.x, -2.2, 0.6], left: [-3, -2, 1.6], right: [2, -2, 1.6] };

  const plan = opts.plan || {};
  plan.path = plan.path || [{ at: 0, x: SEAT.x, y: SEAT.y, face: 0 }];
  if (!plan.sit) plan.sit = [[0, 1]];
  const goli = await mountGoli(canvas, { ...opts, renderer, scene, cameraObj: cam, noRender: true, targets,
    place: { scale: SEAT.scale, floorZ: SEAT.floorZ, seatZ: SEAT.seatZ } });

  // pictures on the screens (the real page or picture the line names)
  const loader = new THREE.TextureLoader();
  for (const [k, url] of Object.entries(plan.screens || {})) {
    if (!screens[k] || !url) continue;
    const tex = await loader.loadAsync(url); tex.colorSpace = THREE.SRGBColorSpace;
    screens[k].material = new THREE.MeshBasicMaterial({ map: tex, toneMapped: false });
  }

  // camera shots (plan.camera = [{at, shot: 'main'|'wide'|'close'|'screen'|{pos, target, lens}, dur}]): 'main' is the
  // plates' own shot; the others are real camera positions in the room; the camera travels between them (eased)
  const SHOTS = {
    main: { pos: c.pos, target: [c.pos[0], c.pos[1] + 1, c.pos[2]], lens: c.lens, shift: c.shift_y },
    wide: { pos: [0.35, -8.6, 2.75], target: [0.1, -1.2, 0.75], lens: 30, shift: 0 },
    close: { pos: [SEAT.x + 0.35, -3.9, 1.62], target: [SEAT.x, -1.0, 1.38], lens: 55, shift: 0 },
    screen: { pos: [-0.2, -5.6, 2.1], target: [1.3, 0, 1.75], lens: 36, shift: 0 },
  };
  const shotOf = (s) => (typeof s === 'string' ? SHOTS[s] || SHOTS.main : { shift: 0, ...s });
  const camKeys = (plan.camera || [{ at: 0, shot: 'main' }]).slice().sort((a, b) => a.at - b.at);
  const dir = (sh) => V(sh.target).sub(V(sh.pos)).normalize();
  function placeCamera(t) {
    let a = shotOf(camKeys[0].shot), b = a, f = 1;
    for (let k = 0; k < camKeys.length && camKeys[k].at <= t; k++) {
      a = k ? shotOf(camKeys[k - 1].shot) : shotOf(camKeys[k].shot); b = shotOf(camKeys[k].shot);
      f = ease((t - camKeys[k].at) / (camKeys[k].dur || 1.4));
    }
    const pos = V(a.pos).lerp(V(b.pos), f), d = dir(a).lerp(dir(b), f).normalize();
    const lens = a.lens + (b.lens - a.lens) * f, shift = a.shift + (b.shift - a.shift) * f;
    const bg = c.sensor / 2 / lens;
    cam.fov = (W >= H ? 2 * Math.atan(bg * H / W) : 2 * Math.atan(bg)) * 180 / Math.PI;
    cam.position.copy(pos); cam.lookAt(pos.clone().add(d));
    cam.setViewOffset(W, H, 0, -shift * Math.max(W, H), W, H);
    cam.updateProjectionMatrix();
  }

  const props = (plan.props || []).slice().sort((a, b) => a.at - b.at);
  const home = {}; for (const [k, g] of Object.entries(pieces)) home[k] = { p: g.position.clone(), r: g.rotation.y };
  function frame(t) {
    for (const [k, g] of Object.entries(pieces)) { g.position.copy(home[k].p); g.rotation.y = home[k].r; }
    for (const pr of props) {
      const g = pieces[pr.piece]; if (!g || t < pr.at) continue;
      const f = ease((t - pr.at) / (pr.dur || 0.8));
      g.position.x += (pr.dx || 0) * f; g.position.z -= (pr.dy || 0) * f; g.rotation.y -= (pr.turn || 0) * Math.PI / 180 * f;
    }
    placeCamera(t);
    goli(t);
    const hold = goli.holding(t);
    if (hold && pieces[hold.piece]) {             // the thing travels in his paw (its base in the palm)
      const g = pieces[hold.piece], m = goli.hand(hold.side);
      const palm = new THREE.Vector3(0, 0.12, 0).applyMatrix4(m);   // hand space (his scale is in the matrix)
      g.position.copy(palm).add(new THREE.Vector3(0, -0.05, 0)); g.rotation.set(0, home[hold.piece].r, 0);
    }
    renderer.render(scene, cam);
  }
  frame(0);
  frame.camera = cam; frame.pieces = pieces;
  return frame;
}
