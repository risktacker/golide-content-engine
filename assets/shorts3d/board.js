// Any GOLIDE 3D Short from an open storyboard (owner 2026-11-23: "you don't know what's coming with another script, but
// you are prepared to make whatever will come"). Nothing here is a set or a prop list: the place is built from the
// storyboard's ground, sky and walls; every thing it names is a CC0 library model found by name or built from its own
// 3D parts (things.json, resolved by src/golide_engine/shorts3d/things.py); the engine's own cast rig acts the beats
// (walk, run, hold, give, throw, kick, ride, sit, fall ...) and the things act their events (move, spin, bend, break ...).
// The director (director.js) frames and checks every shot. Loaded as ?golide=board&set=track (no office is built).
//
// board.json: see src/golide_engine/shorts3d/board.py (schema + repair). things.json: [{ id, model, parts }].
import * as THREE from 'three';

const OUTFITS = { suit: { style: 'tunic', civil: true, details: ['tie', 'buttons'] }, vest: { pattern: 'vest', details: ['tie', 'vestBtn', 'hanky'] },
  hoodie: { details: ['hoodie'] }, polo: { details: ['polo'] }, shirt: { style: 'tunic', details: ['buttons', 'collar'] }, bowtie: { style: 'tunic', civil: true, details: ['bow', 'buttons'] },
  uniform: { style: 'tunic', details: ['buttons', 'belt', 'collar'] }, overalls: { pattern: 'vest', details: ['buttons'] }, coat: { style: 'tunic', civil: true, details: ['buttons', 'belt'] },
  dress: { style: 'tunic', civil: true, details: [] }, jersey: { details: ['polo'] }, apron: { pattern: 'vest', details: [] } };
const HATS = { cap: 'cap', beret: 'beret', boonie: 'boonie', pith: 'pith', helmet: 'm1', police: 'cap79', hardhat: 'pith', chef: 'beret', cowboy: 'boonie', beanie: 'beret' };
const ANGLE = { front: [0, 0.06], low: [0.3, -0.16], high: [-0.2, 0.42], left: [-0.62, 0.08], right: [0.62, 0.08], 'over-shoulder': [Math.PI - 0.45, 0.12], top: [0, 1.15] };
const LENS = { wide: 46, medium: 36, close: 30, 'extreme-close': 24, face: 28 };
const SKY = { day: ['#9cc8ee', '#e6f0f6'], dusk: ['#5b4a7a', '#ffb07a'], night: ['#0d1630', '#2a3a5e'], overcast: ['#aab3bb', '#d8dcdf'] };
const SPEED = { walk: 1.3, run: 3.4, sneak: 0.7 };
const HAND_DO = new Set(['hold', 'pick-up', 'use', 'give', 'throw', 'kick', 'put-down']);

export async function build(K, words) {
  const { SR, base, ALL, V, place, arm, leg, Lw, dirW, face, headC, hips, headTurn, clamp, eio, lerp, scene } = K;
  const B = await (await fetch('./golide/board.json')).json();
  const LIB = await (await fetch('./golide/things.json')).json();
  const at = i => { const w = words[Math.max(0, Math.min(words.length - 1, i))]; if (!w) throw new Error(`board: word ${i} has no timing`); return w.start; };
  const DUR = +(words[words.length - 1].end + 0.06).toFixed(2);
  const W = B.world || {}, [SW, SD] = W.size || [30, 30], IN = !!W.indoor, WH = 4.2;

  // ---- the place: everything the engine built is hidden; ground, sky and walls from the storyboard ----
  const keep = new Set([K.hemi, K.sun, K.sun.target]); ALL.forEach(c => keep.add(c.root));
  scene.children.forEach(o => { if (!keep.has(o)) o.visible = false; });
  const G = new THREE.Group(); G.name = 'golide-world'; scene.add(G);
  const tex = (col, kind) => { const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d'); g.fillStyle = col; g.fillRect(0, 0, 256, 256);
    const base2 = new THREE.Color(col); for (let i = 0; i < 2600; i++) { const k = (Math.random() - 0.5) * 0.16, cc = base2.clone().offsetHSL(0, 0, k); g.fillStyle = `#${cc.getHexString()}`; const s = kind === 'fine' ? 1 : 1 + Math.random() * 3; g.fillRect(Math.random() * 256, Math.random() * 256, s, s); }
    const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t; };
  const gcol = W.ground_color || (IN ? '#b9b2a4' : '#8fae6b');
  const gt = tex(gcol); gt.repeat.set(SW / 3, SD / 3);
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(SW, SD), new THREE.MeshStandardMaterial({ map: gt, roughness: 0.92, metalness: 0 }));
  ground.rotation.x = -Math.PI / 2; ground.receiveShadow = true; G.add(ground);
  let room;
  if (IN) {
    const wm = new THREE.MeshStandardMaterial({ map: tex(W.walls_color || '#d9d2c3', 'fine'), roughness: 0.85 });
    const wall = (w, h, d, x, y, z) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), wm); m.position.set(x, y, z); m.receiveShadow = true; G.add(m); return m; };
    wall(SW, WH, 0.2, 0, WH / 2, -SD / 2); wall(SW, WH, 0.2, 0, WH / 2, SD / 2); wall(0.2, WH, SD, -SW / 2, WH / 2, 0); wall(0.2, WH, SD, SW / 2, WH / 2, 0);
    const ceil = new THREE.Mesh(new THREE.BoxGeometry(SW, 0.1, SD), new THREE.MeshStandardMaterial({ color: '#f6f2ea', roughness: 0.9 })); ceil.position.y = WH + 0.05; G.add(ceil);
    for (let x = -SW / 2 + 3; x < SW / 2; x += 5) for (let z = -SD / 2 + 3; z < SD / 2; z += 5) { const l = new THREE.PointLight('#ffe2b8', 5, 9, 1.6); l.position.set(x, WH - 0.4, z); G.add(l); }
    scene.background = new THREE.Color('#f3e9d6'); scene.fog.near = 400; scene.fog.far = 4000;
    room = { min: V(-SW / 2 + 0.12, 0.03, -SD / 2 + 0.12), max: V(SW / 2 - 0.12, WH - 0.05, SD / 2 - 0.12) };
  } else {
    const [top, hor] = SKY[W.sky] || SKY.day;
    const far = new THREE.Mesh(new THREE.PlaneGeometry(4000, 4000), new THREE.MeshStandardMaterial({ map: (() => { const t = tex(gcol); t.repeat.set(1300, 1300); return t; })(), roughness: 1 }));
    far.rotation.x = -Math.PI / 2; far.position.y = -0.02; far.receiveShadow = true; G.add(far);
    const sc = document.createElement('canvas'); sc.width = 4; sc.height = 512; { const g = sc.getContext('2d'), gr = g.createLinearGradient(0, 0, 0, 512); gr.addColorStop(0, top); gr.addColorStop(0.55, hor); gr.addColorStop(1, hor); g.fillStyle = gr; g.fillRect(0, 0, 4, 512); }
    const st = new THREE.CanvasTexture(sc); st.colorSpace = THREE.SRGBColorSpace;
    const sky = new THREE.Mesh(new THREE.SphereGeometry(1800, 32, 16), new THREE.MeshBasicMaterial({ map: st, side: THREE.BackSide, fog: false, depthWrite: false })); G.add(sky);
    scene.background = new THREE.Color(hor); scene.fog.color.set(hor); scene.fog.near = Math.max(SW, SD) * 4; scene.fog.far = Math.max(SW, SD) * 4 + 1400;   // wide views from far off stay clear
    room = { min: V(-SW / 2 - 300, 0.03, -SD / 2 - 300), max: V(SW / 2 + 300, 200, SD / 2 + 300) };   // outdoors the camera may stand far off for a wide view
  }
  { const { RoomEnvironment } = await import('three/addons/environments/RoomEnvironment.js'); const pm = new THREE.PMREMGenerator(K.renderer); scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture; scene.environmentIntensity = IN ? 0.55 : 0.4; }

  // ---- things: a library model found by name, or the thing's own parts; scaled to its real height ----
  const { GLTFLoader } = await import('three/addons/loaders/GLTFLoader.js'); const GL = new GLTFLoader();
  const SHAPE = { box: () => new THREE.BoxGeometry(1, 1, 1), cyl: () => new THREE.CylinderGeometry(0.5, 0.5, 1, 28), sphere: () => new THREE.SphereGeometry(0.5, 28, 16), cone: () => new THREE.ConeGeometry(0.5, 1, 28) };
  const things = {}, list = [];
  const label = (text, w) => { const c = document.createElement('canvas'); c.width = 1024; c.height = 256; const g = c.getContext('2d'); g.fillStyle = '#fbf7ef'; g.fillRect(0, 0, 1024, 256);
    g.fillStyle = '#17141a'; let f = 170; g.font = `${f}px Anton`; while (g.measureText(text).width > 960 && f > 40) { f -= 8; g.font = `${f}px Anton`; } g.textAlign = 'center'; g.fillText(text, 512, 128 + f * 0.36);
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; const m = new THREE.Mesh(new THREE.PlaneGeometry(w, w / 4), new THREE.MeshBasicMaterial({ map: t, toneMapped: false })); m.userData.draw = (s) => { g.fillStyle = '#fbf7ef'; g.fillRect(0, 0, 1024, 256); g.fillStyle = '#17141a'; let ff = 170; g.font = `${ff}px Anton`; while (g.measureText(s).width > 960 && ff > 40) { ff -= 8; g.font = `${ff}px Anton`; } g.fillText(s, 512, 128 + ff * 0.36); t.needsUpdate = true; }; return m; };
  for (const T of B.things || []) {
    const L = LIB.find(x => x.id === T.id) || {}; let obj = null;
    if (L.model) { try { const g = await GL.loadAsync(L.model); obj = g.scene.clone(true); obj.traverse(m => { if (m.isMesh) { m.castShadow = m.receiveShadow = true; } }); } catch (e) { console.warn('board: model failed', T.id, e); obj = null; } }
    if (!obj && (L.parts || []).length) { obj = new THREE.Group();
      for (const p of L.parts) { const mat = new THREE.MeshStandardMaterial({ color: p.gold ? '#d8a63a' : (p.color || T.color || '#9aa0a6'), roughness: p.gold ? 0.3 : 0.7, metalness: p.gold ? 0.8 : 0.05 });
        const m = new THREE.Mesh((SHAPE[p.shape] || SHAPE.box)(), mat); m.scale.set(...p.s); m.position.set(...p.c); m.rotation.set(...p.r); m.castShadow = m.receiveShadow = true; m.name = p.name; obj.add(m); } }
    if (!obj) { obj = new THREE.Group(); const m = new THREE.Mesh(SHAPE.box(), new THREE.MeshStandardMaterial({ color: T.color || '#9aa0a6', roughness: 0.7 })); m.position.y = 0.5; obj.add(m); { const lb = label(T.name, 1.2); lb.position.set(0, 0.5, 0.51); obj.add(lb); } }
    if (T.color && L.model) obj.traverse(m => { if (m.isMesh && m.material) { m.material = m.material.clone(); m.material.color?.lerp(new THREE.Color(T.color), 0.5); } });
    const holder = new THREE.Group(); holder.name = T.name; holder.add(obj);
    obj.updateMatrixWorld(true); let bb = new THREE.Box3().setFromObject(obj); const sz = bb.getSize(V(0, 0, 0));
    const k = (T.height_m || 1) / Math.max(sz.y, 1e-4); obj.scale.multiplyScalar(k); obj.updateMatrixWorld(true);
    bb = new THREE.Box3().setFromObject(obj); const cc = bb.getCenter(V(0, 0, 0)); obj.position.x -= cc.x; obj.position.z -= cc.z; obj.position.y -= bb.min.y;
    const s2 = bb.getSize(V(0, 0, 0)); holder.userData.longX = s2.x >= s2.z; holder.userData.size = s2;
    if (T.text) { const lb = label(T.text, Math.max(0.3, Math.min(s2.x, 3) * 0.8)); lb.position.set(0, s2.y * 0.6, s2.z / 2 + 0.02); holder.add(lb); holder.userData.sign = lb; }
    holder.rotation.y = THREE.MathUtils.degToRad(T.turn_deg || 0); G.add(holder);
    const th = { id: T.id, T, obj: holder, inner: obj, base: V(T.at[0], 0, T.at[1]), yaw0: holder.rotation.y, size: s2, parts: obj.children.slice(), hero: !!T.hero };
    things[T.id] = th; list.push(th); }
  for (const th of list) if (th.T.on && things[th.T.on]) { const o = things[th.T.on]; th.base.y = o.size.y; }   // standing on another thing

  // ---- cast ----
  const cast = {}, people = [];
  (B.cast || []).forEach((m, i) => { const L = m.look || {}, of = OUTFITS[L.outfit] || OUTFITS.shirt, col = L.color || '#2f3542', acc = L.accent || '#c8352f';
    const dark = '#' + new THREE.Color(col).multiplyScalar(0.72).getHexString(), pat = of.pattern === 'vest' ? ['vest', dark] : (L.pattern && L.pattern !== 'none' ? [L.pattern, acc] : undefined);
    const c = SR.build({ ...base, jacket: col, jacket2: dark, style: of.style, civil: of.civil, details: of.details, pattern: pat, tieCol: acc, hankyCol: '#f2cf2c', btn: '#d9d9d9', collarCol: '#ffffff', logoCol: acc,
      hat: HATS[L.hat], hatCol: L.hat === 'chef' ? '#ffffff' : L.hat === 'hardhat' ? '#f2c12c' : acc, glasses: !!L.glasses });
    c.root.scale.setScalar(0.8); c.phase = 0.4 + i * 0.7; c.root.rotation.order = 'YXZ'; c.tint = c.hm.material.uniforms.base.value.clone(); ALL.push(c);
    c.label = m.label || m.id; c.id = m.id; c.start = V(m.at[0], 0, m.at[1]); c.spot = c.start; c.yaw0 = THREE.MathUtils.degToRad(m.turn_deg || 0); cast[m.id] = c; people.push(c); });
  const byId = id => cast[id] || (things[id] && things[id].obj) || null;

  // ---- beats: what each person does, on the real word timings ----
  const beats = new Map(people.map(c => [c, []]));
  (B.beats || []).forEach(b => { const c = cast[b.who]; if (c) beats.get(c).push({ ...b, t: at(b.from), t1: Math.max(at(b.until ?? b.from), at(b.from)) }); });
  beats.forEach(l => l.sort((a, b) => a.t - b.t));
  const beatAt = (c, t) => { let cur = null; for (const b of beats.get(c)) if (t >= b.t) cur = b; return cur; };
  // where a thing or person stands at time t without posing anyone (spots for walking, throwing, giving)
  const spotOf = (id, t) => cast[id] ? pathAt(cast[id], t).p : things[id] ? thingPos(things[id], t) : null;
  // walking routes: each walk / run / sneak goes from where they are to its spot (or just short of its target)
  // routes are rebuilt whenever the director moves a start spot (people stepped clear of things)
  const routes = new Map(), routeKey = new Map();
  function buildRoute(c) { const r = []; let p = c.start.clone(), tEnd = 0;
    for (const b of beats.get(c)) { if (!SPEED[b.do]) continue; const t0 = Math.max(b.t, tEnd);
      let dest = b.to && b.to.length === 2 ? V(b.to[0], 0, b.to[1]) : null;
      if (!dest && b.target) { const tp = (cast[b.target] ? cast[b.target].start : things[b.target] ? things[b.target].base : null); if (tp) { const d = tp.clone().setY(0).sub(p); const reach = cast[b.target] ? 0.8 : 0.45 + Math.max(things[b.target].size.x, things[b.target].size.z) / 2; dest = d.length() > reach ? p.clone().add(d.setLength(d.length() - reach)) : p.clone(); } }
      if (!dest) continue; const dist = dest.distanceTo(p); if (dist < 0.05) continue;
      const dur = dist / SPEED[b.do]; r.push({ t0, t1: t0 + dur, a: p.clone(), b: dest.clone(), kind: b.do }); p = dest; tEnd = t0 + dur; }
    return r; }
  const routeOf = c => { const k = `${c.start.x.toFixed(3)},${c.start.z.toFixed(3)}`; if (routeKey.get(c) !== k) { routes.set(c, buildRoute(c)); routeKey.set(c, k); } return routes.get(c); };
  function pathAt(c, t) { let p = c.start.clone(), yaw = c.yaw0, moving = null;
    for (const s of routeOf(c)) { if (t >= s.t1) { p = s.b.clone(); yaw = Math.atan2(s.b.x - s.a.x, s.b.z - s.a.z); }
      else if (t >= s.t0) { const u = (t - s.t0) / (s.t1 - s.t0); p = s.a.clone().lerp(s.b, u); yaw = Math.atan2(s.b.x - s.a.x, s.b.z - s.a.z); moving = s; break; } else break; }
    return { p, yaw, moving }; }

  // ---- what things do: their own events, plus being carried, thrown, kicked, given or ridden ----
  const events = new Map(list.map(th => [th, []]));
  (B.events || []).forEach(e => { const th = things[e.thing]; if (th) events.get(th).push({ ...e, t: at(e.from), t1: Math.max(at(e.until ?? e.from), at(e.from)) }); });
  const moveOf = (th, t) => { let p = th.base.clone(), yaw = th.yaw0;
    for (const e of events.get(th)) { if (e.do !== 'move' || t < e.t) continue; const pts = [p.clone(), ...(e.path.length ? e.path : [e.to]).map(q => V(q[0], th.base.y, q[1]))];
      let len = 0; const seg = []; for (let i = 1; i < pts.length; i++) { const d = pts[i].distanceTo(pts[i - 1]); seg.push(d); len += d; }
      const dur = Math.max(e.t1 - e.t, Math.min(6, len / 6), 0.6), u = clamp((t - e.t) / dur) * len; let acc = 0;
      for (let i = 0; i < seg.length; i++) { if (u <= acc + seg[i] || i === seg.length - 1) { const k = seg[i] ? clamp((u - acc) / seg[i]) : 1; p = pts[i].clone().lerp(pts[i + 1], k);
        const d = pts[i + 1].clone().sub(pts[i]); if (d.lengthSq() > 1e-6) yaw = Math.atan2(d.x, d.z) - (th.obj.userData.longX ? Math.PI / 2 : 0); break; } acc += seg[i]; } }
    return { p, yaw }; };
  const handOf = new Map();                                             // a thing's hand interactions in time order
  for (const c of people) for (const b of beats.get(c)) if (HAND_DO.has(b.do) && b.with && things[b.with]) { const th = things[b.with]; if (!handOf.has(th)) handOf.set(th, []); handOf.get(th).push({ ...b, c }); }
  handOf.forEach(l => l.sort((a, b) => a.t - b.t));
  const handPos = (c, t) => { const s = pathAt(c, t); return s.p.clone().add(V(Math.sin(s.yaw) * 0.32, 0.95, Math.cos(s.yaw) * 0.32)); };
  const destOf = (b, t) => b.to && b.to.length === 2 ? V(b.to[0], 0, b.to[1]) : b.target ? (spotOf(b.target, t) || V(0, 0, 0)) : pathAt(b.c, t).p.clone().add(V(Math.sin(pathAt(b.c, t).yaw) * 6, 0, Math.cos(pathAt(b.c, t).yaw) * 6));
  // holder at time t: { c } (in hand), or a free position, or a flight
  function carry(th, t) {
    let st = { free: true }, from = null;
    for (const b of handOf.get(th) || []) { if (t < b.t) break;
      if (b.do === 'hold' || b.do === 'pick-up' || b.do === 'use') st = { c: b.c, since: b.t, from: st.free ? null : st };
      else if (b.do === 'give') { const to = cast[b.target]; st = to ? { c: to, since: b.t + 0.5, giver: b.c, t0: b.t } : st; }
      else if (b.do === 'put-down') { const s = pathAt(b.c, b.t); st = { free: true, at: s.p.clone().add(V(Math.sin(s.yaw) * 0.5, 0, Math.cos(s.yaw) * 0.5)) }; }
      else if (b.do === 'throw' || b.do === 'kick') { const a = b.do === 'kick' ? pathAt(b.c, b.t).p.clone().add(V(Math.sin(pathAt(b.c, b.t).yaw) * 0.3, 0.1, Math.cos(pathAt(b.c, b.t).yaw) * 0.3)) : handPos(b.c, b.t);
        const d = destOf(b, b.t + 0.3); st = { fly: true, a, b: d, t0: b.t + (b.do === 'kick' ? 0.18 : 0.3), dur: clamp(a.distanceTo(d) / 9, 0.45, 1.6), h: 0.6 + a.distanceTo(d) * 0.12 }; } }
    return st;
  }
  function thingPos(th, t) { const st = carry(th, t), m = moveOf(th, t);
    if (st.fly) { const u = clamp((t - st.t0) / st.dur); if (t < st.t0) return st.a.clone(); const p = st.a.clone().lerp(st.b, u); p.y = lerp(st.a.y, 0, u) + Math.sin(u * Math.PI) * st.h; return p; }
    if (st.c) return handPos(st.c, t); if (st.at) return st.at.clone(); return m.p; }
  // riding: a person rides a thing from a beat on; they sit on top of it and move with it
  const rideOf = (c, t) => { const b = beatAt(c, t); return b && b.do === 'ride' && things[b.target] ? things[b.target] : null; };

  // ---- small effects: bubbles, smoke, fire, glow ----
  const BUB = {}; for (const ch of ['?', '!', '$', '...']) { const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d'); g.fillStyle = '#fff'; g.beginPath(); g.arc(64, 60, 50, 0, 7); g.fill(); g.lineWidth = 6; g.strokeStyle = '#2a1612'; g.stroke(); g.fillStyle = ch === '$' ? '#1f9e5a' : '#e8442a'; g.font = `${ch.length > 1 ? 60 : 80}px Anton`; g.textAlign = 'center'; g.fillText(ch, 64, ch.length > 1 ? 80 : 90); BUB[ch] = new THREE.CanvasTexture(c); BUB[ch].colorSpace = THREE.SRGBColorSpace; }
  const bub = new Map(people.map(c => { const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: BUB['?'], transparent: true, depthTest: false })); s.visible = false; scene.add(s); return [c, s]; }));
  const puff = (col) => { const c = document.createElement('canvas'); c.width = c.height = 64; const g = c.getContext('2d'), gr = g.createRadialGradient(32, 32, 2, 32, 32, 32); gr.addColorStop(0, col); gr.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = gr; g.fillRect(0, 0, 64, 64); const t = new THREE.CanvasTexture(c); return t; };
  const SMOKE = puff('rgba(200,200,200,0.85)'), FIRE = puff('rgba(255,150,40,0.95)');
  const fx = list.map(th => { const ps = []; for (let i = 0; i < 14; i++) { const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: SMOKE, transparent: true, depthWrite: false })); s.visible = false; scene.add(s); ps.push(s); }
    const l = new THREE.PointLight('#ffd27a', 0, Math.max(3, th.size.y * 3), 2); scene.add(l); return { th, ps, l }; });

  // ---- one moment of the film ----
  function poseThing(th, t) {
    const o = th.obj, ev = events.get(th); let p = thingPos(th, t), yaw = moveOf(th, t).yaw, show = true, sc = 1, tilt = 0, roll = 0, shake = 0;
    const st = carry(th, t); if (st.c) { yaw = pathAt(st.c, t).yaw; }
    th.parts.forEach(m => { if (m.userData.p0 === undefined) m.userData.p0 = m.position.clone(); m.position.copy(m.userData.p0); });
    for (const e of ev) { const on = t >= e.t, u = clamp((t - e.t) / Math.max(0.6, e.t1 - e.t));
      if (e.do === 'appear') show = on; if (e.do === 'vanish' && on) show = false;
      if (!on) continue;
      if (e.do === 'spin') yaw += THREE.MathUtils.degToRad(e.amount || 360) * u;
      if (e.do === 'shake') shake = Math.max(shake, (1 - u * 0.5) * 0.05 * (e.amount || 1));
      if (e.do === 'tilt') roll += THREE.MathUtils.degToRad(e.amount || 20) * eio(u);
      if (e.do === 'fall') tilt = Math.PI / 2 * eio(clamp((t - e.t) / 0.7));
      if (e.do === 'grow') sc *= lerp(1, Math.max(1.05, e.amount || 1.5), eio(u)); if (e.do === 'shrink') sc *= lerp(1, Math.min(0.95, e.amount && e.amount < 1 ? e.amount : 0.5), eio(u));
      if (e.do === 'bend') { const ax = th.obj.userData.longX ? 'x' : 'z', half = (ax === 'x' ? th.size.x : th.size.z) / 2 || 1, side = ax === 'x' ? 'z' : 'x', amp = (e.amount && Math.abs(e.amount) < 50 ? e.amount : 1.2) * eio(u);
        th.parts.forEach(m => { const q = clamp((m.userData.p0[ax] * th.inner.scale.x + half) / (2 * half)); m.position[side] = m.userData.p0[side] + Math.sin(q * Math.PI) * amp / th.inner.scale.x * Math.sin(q * Math.PI * 2 + 0.6); }); }
      if (e.do === 'break') th.parts.forEach((m, i) => { const d = m.userData.p0.clone().setY(0); if (d.lengthSq() < 1e-6) d.set(Math.sin(i * 2.4), 0, Math.cos(i * 2.4)); d.normalize(); const k = eio(clamp((t - e.t) / 0.8)) * 0.5 / th.inner.scale.x; m.position.addScaledVector(d, k * (1 + (i % 3))); m.position.y = m.userData.p0.y * (1 - 0.6 * eio(clamp((t - e.t) / 0.8))); });
      if (e.do === 'text' && th.obj.userData.sign && th.obj.userData.shown !== e.text) { th.obj.userData.sign.userData.draw(e.text); th.obj.userData.shown = e.text; } }
    if (th.T.text && th.obj.userData.sign && !ev.some(e => e.do === 'text' && t >= e.t) && th.obj.userData.shown !== th.T.text) { th.obj.userData.sign.userData.draw(th.T.text); th.obj.userData.shown = th.T.text; }
    o.visible = show; o.position.copy(p); if (shake) o.position.add(V(Math.sin(t * 61) * shake, Math.abs(Math.sin(t * 47)) * shake * 0.5, Math.cos(t * 53) * shake));
    o.rotation.set(tilt, yaw, roll, 'YXZ'); o.scale.setScalar(sc); if (st.c) { const s = th.size; o.position.y -= s.y * 0.5; }
    o.updateMatrixWorld(true);
  }
  function posePerson(c, t) {
    const b = beatAt(c, t), k = b ? eio(clamp((t - b.t) / 0.3)) : 1, s = pathAt(c, t), ride = rideOf(c, t);
    let p = s.p, yaw = s.yaw, y = 0;
    if (ride) { p = ride.obj.position.clone(); y = ride.obj.position.y + ride.size.y * 0.55; yaw = ride.obj.rotation.y + (ride.obj.userData.longX ? Math.PI / 2 : 0); }
    else if (b && b.target && !SPEED[b.do] && !s.moving) { const tp = spotOf(b.target, t); if (tp) { const want = Math.atan2(tp.x - p.x, tp.z - p.z); let d = ((want - yaw + 3 * Math.PI) % (2 * Math.PI)) - Math.PI; yaw += d * eio(clamp((t - b.t) / 0.35)); } }
    if (b && b.do === 'sit' && b.target && things[b.target]) y = things[b.target].size.y * 0.55;
    place(c, p.x, p.z, yaw, y);
    if (s.moving && !ride) SR.clipAt(c, s.moving.kind === 'run' ? 'run' : 'walk', t * (s.moving.kind === 'sneak' ? 0.6 : 1) + c.phase);
    else if (b && b.do === 'sneak') SR.clipAt(c, 'sneak_pose', 0.3);
    else SR.clipAt(c, 'idle', 0.4 + c.phase);
    const rest = () => { if (!s.moving) K.idle(c, t); };
    const handTo = (side, P2, hint) => arm(c, side, P2, hint);
    const tgt = () => b && b.target ? (byId(b.target) && cast[b.target] ? headC(cast[b.target]) : spotOf(b.target, t)?.clone().add(V(0, Math.min(1.2, (things[b.target]?.size.y || 1) * 0.6), 0))) : null;
    const d = b ? b.do : 'stand';
    if (d === 'stand' || d === 'walk' || d === 'run' || d === 'look' || d === 'turn') { rest(); if (d === 'look' && tgt()) { const tp = tgt(); headTurn(c, 0, clamp((tp.y - headC(c).y) * -0.3, -0.4, 0.4)); } }
    else if (d === 'hold' || d === 'pick-up' || d === 'use' || d === 'give' || d === 'put-down') { rest();
      const st = b.with && things[b.with] ? carry(things[b.with], t) : {}; const mine = st.c === c;
      if (d === 'pick-up' && t - b.t < 0.5) hips(c, -0.25 * Math.sin(clamp((t - b.t) / 0.5) * Math.PI), 0.1);
      if (mine || (d === 'give' && t - b.t < 0.6)) { const h = Lw(c, 0, d === 'use' ? 1.0 : 0.95, d === 'give' ? lerp(0.35, 0.55, k) : 0.36); handTo('Left', h.clone().add(dirW(c, 0.09, 0, 0)), dirW(c, 1, -0.4, -0.3)); handTo('Right', h.clone().add(dirW(c, -0.09, 0, 0)), dirW(c, -1, -0.4, -0.3)); } }
    else if (d === 'throw') { rest(); const u = clamp((t - b.t) / 0.45); const back = Lw(c, -0.22, 1.5, -0.25), fwd = Lw(c, -0.2, 1.25, 0.6); handTo('Right', u < 0.5 ? Lw(c, -0.2, 1.0, 0.35).lerp(back, u * 2) : back.lerp(fwd, (u - 0.5) * 2), dirW(c, -1, -0.3, -0.3)); }
    else if (d === 'kick') { rest(); const u = clamp((t - b.t) / 0.4); const a = Lw(c, -0.1, 0.25, -0.35), f = Lw(c, -0.1, 0.45, 0.5); leg(c, 'Right', u < 0.45 ? Lw(c, -0.1, 0.08, 0).lerp(a, u / 0.45) : a.lerp(f, (u - 0.45) / 0.55)); }
    else if (d === 'push' || d === 'pull') { const tp = tgt() || Lw(c, 0, 1.05, 0.55); SR.pose(c, d === 'push' ? 'shoulder_push' : 'rope_pull', t, d === 'push' ? { target: tp } : { lean: 30 }); }
    else if (d === 'sit') { rest(); hips(c, -0.32 * k, -0.08 * k); leg(c, 'Left', Lw(c, 0.1, 0.12, 0.42)); leg(c, 'Right', Lw(c, -0.1, 0.12, 0.42)); }
    else if (d === 'lie' || d === 'fall') { rest(); const u = d === 'fall' ? eio(clamp((t - b.t) / 0.55)) : 1; c.root.rotation.x = -Math.PI / 2 * u; c.root.position.y += 0.18 * u; c.root.updateMatrixWorld(true); }
    else if (d === 'jump') { rest(); const u = clamp((t - b.t) / 0.6); c.root.position.y += Math.sin(u * Math.PI) * 0.45; c.root.updateMatrixWorld(true); }
    else if (d === 'ride') { rest(); hips(c, -0.2, 0); }
    else if (d === 'hide') { SR.clipAt(c, 'sneak_pose', 0.3); hips(c, -0.25 * k, 0); }
    else if (d === 'sneak') { /* clip above */ }
    else if (d === 'point') { rest(); const tp = tgt() || headC(c).add(dirW(c, 0, 0, 1).multiplyScalar(2)); const sh = SR.wp(c.bone('RightArm')); handTo('Right', sh.clone().lerp(sh.clone().add(tp.clone().sub(sh).normalize().multiplyScalar(0.62)), k), dirW(c, -1, -0.3, 0)); }
    else if (d === 'wave') { rest(); const w2 = Math.sin(t * 8); handTo('Right', Lw(c, lerp(-0.18, -0.45 + 0.12 * w2, k), lerp(0.95, 1.85, k), lerp(0.5, 0.1, k)), dirW(c, -1, -0.2, -0.3)); }
    else if (d === 'cheer') { const w2 = Math.sin(t * 9) * 0.05; handTo('Left', Lw(c, lerp(0.18, 0.42, k), lerp(0.95, 1.95, k) + w2, lerp(0.5, 0.12, k)), dirW(c, 1, 0.2, -0.5)); handTo('Right', Lw(c, lerp(-0.18, -0.42, k), lerp(0.95, 1.95, k) - w2, lerp(0.5, 0.12, k)), dirW(c, -1, 0.2, -0.5)); }
    else if (d === 'hands-on-head') { const h = headC(c), r = 0.27; handTo('Left', Lw(c, 0.18, 0.95, 0.5).lerp(h.clone().add(dirW(c, 1, 0, 0).multiplyScalar(r)).add(V(0, 0.08, 0)), k), dirW(c, 1, -0.3, -0.4)); handTo('Right', Lw(c, -0.18, 0.95, 0.5).lerp(h.clone().add(dirW(c, -1, 0, 0).multiplyScalar(r)).add(V(0, 0.08, 0)), k), dirW(c, -1, -0.3, -0.4)); }
    else if (d === 'scratch-head') { rest(); const h = headC(c); handTo('Right', Lw(c, -0.18, 0.95, 0.5).lerp(h.clone().add(dirW(c, -1, 0, 0).multiplyScalar(0.25)).add(V(0, 0.12 + 0.03 * Math.sin(t * 14), 0)), k), dirW(c, -1, -0.3, -0.4)); }
    else if (d === 'shrug') { handTo('Left', Lw(c, lerp(0.18, 0.42, k), lerp(0.95, 1.1, k), lerp(0.5, 0.3, k)), dirW(c, 1, -0.6, 0)); handTo('Right', Lw(c, lerp(-0.18, -0.42, k), lerp(0.95, 1.1, k), lerp(0.5, 0.3, k)), dirW(c, -1, -0.6, 0)); }
    else if (d === 'nod') { rest(); headTurn(c, 0, 0.18 * Math.max(0, Math.sin(t * 9))); }
    else if (d === 'shake-head') { rest(); headTurn(c, 0.3 * Math.sin(t * 10), 0); }
    else if (d === 'lean-in') { rest(); hips(c, 0, 0.06 * k); }
    else if (d === 'arms-crossed') { const ch = Lw(c, 0, 1.12, 0.26); handTo('Left', Lw(c, 0.18, 0.95, 0.5).lerp(ch.clone().add(dirW(c, -1, 0, 0).multiplyScalar(0.12)), k), dirW(c, 1, -0.6, 0)); handTo('Right', Lw(c, -0.18, 0.95, 0.5).lerp(ch.clone().add(dirW(c, 1, 0, 0).multiplyScalar(0.12)).add(V(0, -0.04, 0)), k), dirW(c, -1, -0.6, 0)); }
    else rest();
    face(c, (b && b.face) || 'calm');
    const sp = bub.get(c), on = b && b.bubble && b.bubble !== 'none' && BUB[b.bubble]; sp.visible = !!on;
    if (on) { sp.material.map = BUB[b.bubble]; const h = headC(c), kk = Math.min(1, (t - b.t) * 6); sp.position.set(h.x + 0.24, h.y + 0.42 + 0.03 * Math.sin(t * 8), h.z); sp.scale.setScalar(0.36 * kk); }
  }
  function pose(t) {
    K.resetScene();
    for (const th of list) poseThing(th, t);
    for (const c of people) posePerson(c, t);
    for (const th of list) { const st = carry(th, t); if (st.c) { const h = SR.wp(st.c.bone('RightHand')).lerp(SR.wp(st.c.bone('LeftHand')), 0.5), big = th.size.y > 0.25;
      /* carried in front: small things in the hands, big things held from below at the belly, never over the face */ th.obj.position.copy(h).add(dirW(st.c, 0, 0, 1).multiplyScalar(big ? th.size.z / 2 + 0.05 : 0)).add(V(0, big ? -Math.min(th.size.y * 0.75, 0.55) : -th.size.y * 0.5, 0)); th.obj.updateMatrixWorld(true); } }
    for (const f of fx) { const ev = events.get(f.th).filter(e => (e.do === 'smoke' || e.do === 'fire' || e.do === 'glow') && t >= e.t); const top = new THREE.Box3().setFromObject(f.th.obj);
      const smoke = ev.some(e => e.do === 'smoke'), fire = ev.some(e => e.do === 'fire'), glow = ev.some(e => e.do === 'glow') || fire;
      f.ps.forEach((s, i) => { s.visible = (smoke || fire) && f.th.obj.visible; if (!s.visible) return; s.material.map = fire && i % 2 ? FIRE : SMOKE; const ph = ((t * 0.7 + i / f.ps.length) % 1); const c2 = top.getCenter(V(0, 0, 0));
        const r = Math.max(0.08, f.th.size.x * 0.25); s.position.set(c2.x + Math.sin(i * 2.1) * r * ph, top.max.y + ph * Math.max(0.4, f.th.size.y), c2.z + Math.cos(i * 1.7) * r * ph); s.scale.setScalar(Math.max(0.12, f.th.size.x * 0.4) * (0.5 + ph)); s.material.opacity = 1 - ph; });
      f.l.intensity = glow ? 3 : 0; f.l.position.copy(top.getCenter(V(0, 0, 0))).setY(top.max.y + 0.3); }
    ALL.forEach(c => SR.updateLimbs(c)); poseCallouts(t);
  }
  // callouts: a label that pops up over a thing or a person on a word (a number, an amount, a status)
  const CT = { good: ['#1f9e5a', '#ffffff'], bad: ['#d7262c', '#ffffff'], neutral: ['#14161c', '#f2cf2c'] };
  const callouts = (B.callouts || []).map(cl => { const c = document.createElement('canvas'); c.width = 768; c.height = 192; const g = c.getContext('2d'), [bg, fg] = CT[cl.tone] || CT.neutral;
    g.font = '120px Anton'; const text = String(cl.text).toUpperCase(); let f = 120; while (g.measureText(text).width > 680 && f > 40) { f -= 6; g.font = `${f}px Anton`; } const w = Math.min(760, g.measureText(text).width + 80);
    g.fillStyle = bg; g.beginPath(); g.roundRect((768 - w) / 2, 16, w, 160, 80); g.fill(); g.lineWidth = 10; g.strokeStyle = '#ffffff'; g.stroke(); g.fillStyle = fg; g.textAlign = 'center'; g.fillText(text, 384, 96 + f * 0.36);
    const t2 = new THREE.CanvasTexture(c); t2.colorSpace = THREE.SRGBColorSpace; const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: t2, transparent: true, depthTest: false, toneMapped: false })); sp.visible = false; sp.renderOrder = 10; scene.add(sp);
    return { ...cl, t: at(cl.from), t1: Math.max(at(cl.until ?? cl.from) + 0.6, at(cl.from) + 1.2), sp, aspect: w / 160 }; });
  function poseCallouts(t) { for (const cl of callouts) { const on = t >= cl.t && t < cl.t1, o = byId(cl.on); cl.sp.visible = on && !!o; if (!cl.sp.visible) continue;
    const b = cast[cl.on] ? new THREE.Box3().setFromObject(cast[cl.on].head) : new THREE.Box3().setFromObject(o), c2 = b.getCenter(V(0, 0, 0)), size = cast[cl.on] ? 0.32 : Math.max(0.3, Math.min(1.6, b.getSize(V(0, 0, 0)).y * 0.3));
    const k = eio(clamp((t - cl.t) / 0.18)) * (1 + 0.12 * Math.sin(clamp((t - cl.t) / 0.3) * Math.PI)); cl.sp.position.set(c2.x, b.max.y + size * 0.8, c2.z); cl.sp.scale.set(size * cl.aspect * k, size * k, 1); } }
  const calloutBoxes = (objs, t) => callouts.filter(cl => cl.sp.visible && objs.includes(byId(cl.on))).map(cl => ({ box: new THREE.Box3().setFromCenterAndSize(cl.sp.position, V(cl.sp.scale.x, cl.sp.scale.y, 0.05)), label: `the label ${cl.text}`, onTop: true }));
  const bubbleBoxes = (ids) => ids.map(c => bub.get(c)).filter(s => s && s.visible).map(s => ({ box: new THREE.Box3().setFromCenterAndSize(s.position, V(0.4, 0.4, 0.4)), label: 'a bubble', onTop: true }));
  const labelBoxes = (objs) => objs.filter(o => o && o.userData && o.userData.sign && o.visible).map(o => ({ box: new THREE.Box3().setFromObject(o.userData.sign), label: `the words on ${o.name}` }));
  const LIGHT = { day: { hemi: 1.1, sun: 3.0, sunC: '#fff2dc', hemiC: '#cfe4ff', exp: 0.85, dir: [-0.45, 0.8, 0.45] }, dusk: { hemi: 0.8, sun: 2.4, sunC: '#ffaf80', hemiC: '#a08fc0', exp: 0.8, dir: [-0.72, 0.25, 0.62] },
    night: { hemi: 0.35, sun: 0.8, sunC: '#9fb4ff', hemiC: '#3a4a7a', exp: 0.7, dir: [0.3, 0.7, 0.5] }, overcast: { hemi: 1.3, sun: 1.2, sunC: '#f0f0f0', hemiC: '#d0d6dc', exp: 0.8, dir: [-0.3, 0.9, 0.3] } };
  function light(t, cam, sh) {
    K.setLook('day'); scene.fog.color.set(IN ? '#f3e9d6' : (SKY[W.sky] || SKY.day)[1]);
    if (IN) { K.hemi.intensity = 0.32; K.hemi.color.set('#9fb4e0'); K.sun.intensity = 2.6; K.sun.color.set('#ffd29a'); K.SUNDIR.set(0.35, 0.5, -0.75).normalize(); K.renderer.toneMappingExposure = 0.42; K.U.uVig.value = 0.55; K.U.uCon.value = 1.22; }
    else { const l = LIGHT[W.sky] || LIGHT.day; K.hemi.intensity = l.hemi; K.hemi.color.set(l.hemiC); K.sun.intensity = l.sun; K.sun.color.set(l.sunC); K.SUNDIR.set(...l.dir).normalize(); K.renderer.toneMappingExposure = l.exp; K.U.uVig.value = 0.6; K.U.uCon.value = 1.12; }
    K.U.uSat.value = 1.15; K.U.uWarm.value = W.light === 'cool' ? -0.02 : W.light === 'neutral' ? 0.02 : 0.07;
    const f = sh.box.getCenter(V(0, 0, 0)), r = Math.max(10, sh.box.getSize(V(0, 0, 0)).length()); K.sun.target.position.copy(f); K.sun.position.copy(f).addScaledVector(K.SUNDIR, 60 + r); const sc = K.sun.shadow.camera; sc.left = sc.bottom = -r; sc.right = sc.top = r; sc.near = 1; sc.far = 200 + r * 2; sc.updateProjectionMatrix();
  }
  // shots
  const raw = (B.shots || []).map(s => ({ ...s, t0: at(s.from) })).sort((a, b) => a.t0 - b.t0);
  if (!raw.length) throw new Error('board: no shots');
  raw[0].t0 = 0;
  const shots = raw.map((s, i) => {
    const who = (s.frame || s.who || []).map(byId).filter(Boolean); if (!who.length) throw new Error(`board: shot ${i + 1} frames nothing`);
    const [yaw, pitch] = ANGLE[s.angle] || ANGLE.front, fov = LENS[s.lens] || LENS.medium, mv = s.move || 'push';
    const view = u => { const e = eio(u), v = { yaw, pitch, fov, k: 1, roll: 0 };
      if (mv === 'push') v.k = lerp(1.14, 1.0, e); else if (mv === 'pull') v.k = lerp(1.0, 1.14, e);
      else if (mv === 'crane-down') { v.pitch = pitch + lerp(0.3, 0, e); v.k = lerp(1.12, 1.0, e); } else if (mv === 'crane-up') { v.pitch = pitch + lerp(0, 0.25, e); }
      else if (mv === 'orbit-left') v.yaw = yaw + lerp(0.14, -0.14, e); else if (mv === 'orbit-right') v.yaw = yaw + lerp(-0.14, 0.14, e);
      else if (mv === 'pan' || mv === 'track') v.yaw = yaw + lerp(-0.08, 0.08, e);
      else if (mv === 'whip') { const w2 = clamp((u - 0.45) / 0.12); v.yaw = yaw + lerp(-0.35, 0, eio(w2)); v.roll = 0.04 * Math.sin(w2 * Math.PI); }
      else if (mv === 'snap-zoom') { v.k = u < 0.35 ? 1.18 : lerp(1.18, 0.95, eio(clamp((u - 0.35) / 0.1))); }
      else if (mv === 'dolly-zoom') { v.fov = lerp(fov + 10, fov - 8, e); v.roll = -0.07 * e; } else v.k = lerp(1.03, 1.0, e);
      return v; };
    return { name: `${i + 1} ${s.angle || 'front'} ${s.lens || 'medium'} ${mv}: ${who.map(w => w.label || w.name).join(', ')}`, t0: s.t0, t1: i + 1 < raw.length ? raw[i + 1].t0 : DUR,
      who, hidden: [], dof: s.lens === 'close' || s.lens === 'extreme-close' || s.lens === 'face' ? 0.01 : 0, extras: t => [...bubbleBoxes(who.filter(w => w && w.root)), ...labelBoxes(who.filter(w => !w.root)), ...calloutBoxes(who, t)], view,
      faces: s.lens === 'face' ? who.filter(w => w.root) : [] };
  });
  // things people hold, ride, sit on or kick, and flat things, are not obstacles; everything else is
  const touched = new Set(); for (const c of people) for (const b of beats.get(c)) { if (b.with) touched.add(b.with); if (['ride', 'sit', 'push', 'pull', 'hide', 'lie'].includes(b.do) && b.target) touched.add(b.target); }
  const props = list.filter(th => !touched.has(th.id)).map(th => ({ obj: th.obj, label: th.T.name, floor: th.size.y < 0.15 }));
  return { dur: DUR, people, props, room, pose, light, shots, group: G, walls: IN, maxDist: IN ? 120 : 420 };
}
