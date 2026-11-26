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
      // solid from every side (owner 2026-11-26: the chair "phasing" into the wall when the camera rose): some pieces
      // were built with their faces turned inward, so drawn one-sided they vanished from other angles
      if (m.map) m.map.format = THREE.RGBAFormat;
      o.material = new THREE.MeshBasicMaterial({ map: m.map || null, color: m.map ? 0xffffff : m.color, toneMapped: false,
        side: THREE.DoubleSide, transparent: false, opacity: 1, alphaTest: 0, depthWrite: true });
    }
    o.receiveShadow = true; o.frustumCulled = false;
    const part = (o.name.match(/^(chair|mug|laptop|mic)__/) || [])[1] || (o.name === 'laptop_screen' ? 'laptop' : null);
    if (part) pieces[part].attach(o);
  }
  // the laptop's lid on its hinge: the parts standing up from the base (lid, screen, our mark) turn about the hinge line
  {
    const lap = pieces.laptop, kids = [...lap.children];
    const box = new THREE.Box3().setFromObject(lap), baseTop = box.min.y + 0.02;
    const lid = new THREE.Group();
    const upright = kids.filter((o) => { const b = new THREE.Box3().setFromObject(o); return b.max.y - b.min.y > 0.08; });
    if (upright.length) {
      const lb = new THREE.Box3(); upright.forEach((o) => lb.expandByObject(o));
      // the hinge: along the lid's bottom edge, at the base's top
      const hinge = new THREE.Vector3((lb.min.x + lb.max.x) / 2, baseTop, (lb.min.z + lb.max.z) / 2);
      lid.position.copy(hinge); scene.add(lid); upright.forEach((o) => lid.attach(o)); lap.attach(lid);
      pieces.lid = lid;
    }
  }
  for (const [name, g] of Object.entries(pieces)) {    // each piece turns and slides about its own base
    if (name === 'lid') continue;
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
    mug: centre(pieces.mug), chair: (() => { const b = new THREE.Box3().setFromObject(pieces.chair); return [(b.min.x + b.max.x) / 2, -b.max.z + 0.05, b.max.y - 0.25]; })(),
    mic: (() => { const b = new THREE.Box3().setFromObject(pieces.mic); return [(b.min.x + b.max.x) / 2 + 0.05, -(b.min.z + b.max.z) / 2, b.max.y - 0.12]; })(),
    lid: pieces.lid ? (() => { const b = new THREE.Box3().setFromObject(pieces.lid); return [(b.min.x + b.max.x) / 2, -(b.min.z + b.max.z) / 2, b.max.y]; })() : c.pos,
    desk_r: [SEAT.x + 0.28, set.desk.front_y + 0.9, set.desk.top_z + 0.02], desk_l: [SEAT.x - 0.28, set.desk.front_y + 0.9, set.desk.top_z + 0.02],
    up: [SEAT.x + 0.4, -3, 3.2], down: [SEAT.x, -2.2, 0.6], left: [-3, -2, 1.6], right: [2, -2, 1.6] };

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
  // the TV's picture over time (plan.tv = [[t, url | null]]): the scene's own picture is ON the 3D screen, so it stays
  // right when the camera moves (the page's overlay only matches the main shot)
  const tvAt = [];
  const blank = screens.tv ? screens.tv.material : null;
  for (const [t, url] of (plan.tv || [])) {
    if (!screens.tv) break;
    if (!url) { tvAt.push([t, blank]); continue; }
    const tex = await loader.loadAsync(url); tex.colorSpace = THREE.SRGBColorSpace;
    // cover the screen like the overlay does (object-fit: cover, top aligned)
    const sb = new THREE.Box3().setFromObject(screens.tv), sw = sb.max.x - sb.min.x, sh = sb.max.y - sb.min.y;
    const ia = tex.image.width / tex.image.height, sa = sw / sh;
    if (ia > sa) { tex.repeat.set(sa / ia, 1); tex.offset.set((1 - sa / ia) / 2, 0); } else { tex.repeat.set(1, ia / sa); tex.offset.set(0, 1 - ia / sa); }
    tvAt.push([t, new THREE.MeshBasicMaterial({ map: tex, toneMapped: false })]);
  }
  tvAt.sort((a, b) => a[0] - b[0]);

  // camera shots (plan.camera = [{at, shot: 'main'|'wide'|'close'|'screen'|{pos, target, lens}, dur}]): 'main' is the
  // plates' own shot; the others are real camera positions in the room; the camera travels between them (eased)
  const SHOTS = {
    main: { pos: c.pos, target: [c.pos[0], c.pos[1] + 1, c.pos[2]], lens: c.lens, shift: c.shift_y },
    wide: { pos: [0.35, -8.6, 2.75], target: [0.1, -1.2, 0.75], lens: 30, shift: 0 },
    close: { pos: [SEAT.x + 0.35, -3.9, 1.62], target: [SEAT.x, -1.0, 1.38], lens: 55, shift: 0 },
    screen: { pos: [-1.6, -5.6, 2.4], target: [1.3, 0, 1.55], lens: 30, shift: 0 },   // over his shoulder when he stands at the screen
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

  // speed (owner 2026-11-26): the room's fixed pieces are drawn ONCE per camera position into a picture with its depth,
  // and every frame only lays that picture down (one draw, depth included so the desk still hides Goli's legs) and
  // draws what moves on top: Goli, the moving pieces, the shadows. When the camera moves, the picture is redrawn.
  const rt = new THREE.WebGLRenderTarget(W, H, { depthTexture: new THREE.DepthTexture(W, H), samples: 4 });
  rt.texture.colorSpace = THREE.SRGBColorSpace;
  const quadScene = new THREE.Scene(), quadCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial({
    uniforms: { tColor: { value: rt.texture }, tDepth: { value: rt.depthTexture } },
    vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: 'uniform sampler2D tColor; uniform sampler2D tDepth; varying vec2 vUv; void main(){ gl_FragColor = texture2D(tColor, vUv); gl_FragDepth = texture2D(tDepth, vUv).x;\n#include <colorspace_fragment>\n}',
    depthTest: true, depthWrite: true }));
  quad.frustumCulled = false; quadScene.add(quad);
  let cacheKey = '';
  function draw() {
    cam.updateMatrixWorld();
    const key = cam.matrixWorld.elements.join(',') + '|' + cam.projectionMatrix.elements.join(',');
    if (key !== cacheKey) {                       // the camera moved: draw the fixed room again
      const shown = scene.children.map((c) => c.visible);
      scene.children.forEach((c) => { c.visible = c === room; });
      renderer.setRenderTarget(rt); renderer.render(scene, cam); renderer.setRenderTarget(null);
      scene.children.forEach((c, i) => { c.visible = shown[i]; });
      cacheKey = key;
    }
    room.visible = false;
    renderer.autoClear = true; renderer.render(quadScene, quadCam);
    renderer.autoClear = false; renderer.render(scene, cam); renderer.autoClear = true;
    room.visible = true;
  }

  const props = (plan.props || []).slice().sort((a, b) => a.at - b.at);
  const home = {}; for (const [k, g] of Object.entries(pieces)) home[k] = { p: g.position.clone(), r: g.rotation.y, x: g.rotation.x };
  function frame(t) {
    for (const [k, g] of Object.entries(pieces)) { g.position.copy(home[k].p); g.rotation.y = home[k].r; g.rotation.x = home[k].x; }
    for (const pr of props) {
      const g = pieces[pr.piece]; if (!g || t < pr.at) continue;
      const f = ease((t - pr.at) / (pr.dur || 0.8));
      g.position.x += (pr.dx || 0) * f; g.position.z -= (pr.dy || 0) * f; g.rotation.y -= (pr.turn || 0) * Math.PI / 180 * f;
      g.rotation.x -= (pr.tilt || 0) * Math.PI / 180 * f;     // the lid: tilt 102 closes it onto the keys, -102 opens it
    }
    placeCamera(t);
    if (tvAt.length) { let m = blank; for (const [tt, mm] of tvAt) { if (tt > t) break; m = mm; } screens.tv.material = m; }
    goli(t);
    const hold = goli.holding(t);
    if (hold && pieces[hold.piece]) {             // the thing travels in his paw (its base in the palm)
      const g = pieces[hold.piece], m = goli.hand(hold.side);
      const palm = new THREE.Vector3(0, 0.12, 0).applyMatrix4(m);   // hand space (his scale is in the matrix)
      g.position.copy(palm).add(new THREE.Vector3(0, -0.05, 0)); g.rotation.set(0, home[hold.piece].r, 0);
    }
    draw();
  }
  frame(0);
  frame.mainShot = (t) => { let k = camKeys[0]; for (const c2 of camKeys) { if (c2.at > t) break; k = c2; }
    return k.shot === 'main' && (k === camKeys[0] || t - k.at >= (k.dur || 1.4)); };
  frame.camera = cam; frame.pieces = pieces; frame.renderer = renderer; frame.scene = scene;
  return frame;
}
