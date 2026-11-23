// Any GOLIDE 3D Short from a storyboard (owner plan 2026-11-22, step 4): Sol writes board.json ONCE (data, never code);
// this module builds it on the engine's office or home set with the engine's own cast rig, and the director (director.js)
// frames and checks every shot. Loaded as ?golide=board; reads ./golide/board.json and ./golide/board.words.json.
//
// board.json (checked and repaired for free by src/golide_engine/shorts3d/board.py before it gets here):
// { set: "office"|"home",
//   cast:  [{ id, label, place, look: { outfit, color, accent, pattern, hat, glasses } }],
//   tv:    { place: "above:<id>" | "wall-left" | "wall-right" | "none",
//            states: [{ from, kicker, title, chart: "up"|"down"|"none", icon: "chip"|"none", tone: "good"|"bad"|"neutral" }] },
//   beats: [{ from, who, act, face, bubble, look }],     glow: [{ from, place, tone }],
//   shots: [{ from, who: [ids or "tv"], angle, lens, move }] }      `from` = word index in board.words.json
import * as THREE from 'three';

export const PLACES = {
  office: () => { const Z = -20, ZD = Z - 2.9, CHZ = ZD - 0.55, X = [-6.2, -2.1, 2.1, 6.2], p = {};
    X.forEach((x, i) => { const k = i + 1; p[`desk-${k}`] = { x, z: CHZ, ry: 0, desk: x }; p[`desk-${k}-left`] = { x: x - 1.05, z: ZD - 0.1, ry: Math.PI / 2, faceDesk: x };
      p[`desk-${k}-right`] = { x: x + 1.05, z: ZD - 0.1, ry: -Math.PI / 2, faceDesk: x }; });
    [-5, -3, -1, 1, 3, 5].forEach((x, i) => { p[`open-${i + 1}`] = { x, z: Z + 0.6, ry: 0 }; });
    return p; },
  home: () => { const Z = -20, ZB = Z - 6, p = {};
    p['sofa'] = { x: -1.2, z: ZB + 2.1, ry: 0 }; p['table-left'] = { x: 5.05, z: Z - 1.5, ry: Math.PI / 2 }; p['table-right'] = { x: 6.95, z: Z - 1.5, ry: -Math.PI / 2 };
    p['kitchen'] = { x: 5.4, z: ZB + 1.6, ry: 0 }; [-5, -3, -1, 1, 3, 5].forEach((x, i) => { p[`open-${i + 1}`] = { x, z: Z + 0.6, ry: 0 }; });
    return p; },
};
export const ACTS = ['stand', 'type', 'cheer', 'hands-on-head', 'scratch-head', 'point', 'wave', 'laugh', 'shrug', 'nod', 'lean-in', 'arms-crossed'];
const OUTFITS = { suit: { style: 'tunic', civil: true, details: ['tie', 'buttons'] }, vest: { pattern: 'vest', details: ['tie', 'vestBtn', 'hanky'] },
  hoodie: { details: ['hoodie'] }, polo: { details: ['polo'] }, shirt: { style: 'tunic', details: ['buttons', 'collar'] }, bowtie: { style: 'tunic', civil: true, details: ['bow', 'buttons'] } };
const ANGLE = { front: [0, 0.06], low: [0.3, -0.16], high: [-0.2, 0.42], left: [-0.62, 0.08], right: [0.62, 0.08], 'back-left': [Math.PI - 0.5, 0.18], 'back-right': [Math.PI + 0.5, 0.18] };
const LENS = { wide: 46, medium: 36, close: 30 };

export async function build(K, words) {
  const { SR, base, OUTF, ALL, O, FY, Z, V, place, arm, Lw, dirW, face, headC, hips, headTurn, clamp, eio, lerp, scene } = K;
  const B = await (await fetch('./golide/board.json')).json();
  const at = i => { const w = words[Math.max(0, Math.min(words.length - 1, i))]; if (!w) throw new Error(`board: word ${i} has no timing`); return w.start; };
  const DUR = +(words[words.length - 1].end + 0.06).toFixed(2);
  const SET = B.set === 'home' ? 'home' : 'office';
  if ((K.Q.get('set') || 'office') !== SET) throw new Error(`board: the page was opened on the ${K.Q.get('set') || 'office'} set, the storyboard wants ${SET}`);
  const ZD = Z - 2.9, ZB = Z - 6, ZF = Z + 9;
  const P = PLACES[SET]();

  // ---- set dressing: standing desks, laptops turned to their users instead of monitors, the back wall cleared ----
  O.children.filter(o => o.name === 'modern_arm_chair_01').forEach(o => (o.visible = false));
  if (SET === 'office') {
    O.children.filter(o => ['computerScreen', 'computerKeyboard', 'computerMouse'].includes(o.name)).forEach(o => (o.visible = false));
    const lap = O.children.find(o => o.name === 'laptop'); if (!lap) throw new Error('board: the office has no laptop to copy');
    lap.rotation.y = Math.PI; for (const x of [-6.2, 2.1, 6.2]) { const l = lap.clone(true); l.position.x = x + (lap.position.x - -2.1); O.add(l); }
    O.children.filter(o => o.isMesh && o.geometry.type === 'BoxGeometry' && Math.abs(o.position.x - 2.2) < 1.9 && o.position.z < ZB + 0.3 && o.position.y > FY + 1.4 && o.position.y < FY + 3.3).forEach(o => (o.visible = false));
  }
  // ---- cast ----
  const cast = {}, people = [];
  (B.cast || []).forEach((m, i) => { const L = m.look || {}, of = OUTFITS[L.outfit] || OUTFITS.suit, col = L.color || '#2f3542', acc = L.accent || '#c8352f';
    const dark = '#' + new THREE.Color(col).multiplyScalar(0.72).getHexString(), pat = of.pattern === 'vest' ? ['vest', dark] : (L.pattern && L.pattern !== 'none' ? [L.pattern, acc] : undefined);
    const c = SR.build({ ...base, jacket: col, jacket2: dark, style: of.style, civil: of.civil, details: of.details, pattern: pat, tieCol: acc, hankyCol: '#f2cf2c', btn: '#d9d9d9', collarCol: '#ffffff', logoCol: acc,
      hat: L.hat && L.hat !== 'none' ? L.hat : undefined, hatCol: acc, glasses: !!L.glasses });
    c.root.scale.setScalar(0.8); c.phase = 0.4 + i * 0.7; c.root.rotation.order = 'YXZ'; c.tint = c.hm.material.uniforms.base.value.clone(); ALL.push(c);
    const sp = P[m.place]; if (!sp) throw new Error(`board: ${m.id} stands at an unknown place ${m.place}`);
    c.label = m.label || m.id; c.id = m.id; c.spot = { ...sp }; cast[m.id] = c; people.push(c); });
  if (!people.length) throw new Error('board: no cast');
  // the TV on the back wall
  const tvP = (B.tv && B.tv.place) || 'none'; let tv = null; const TVW = 1.2, TVH = 0.675;
  const tvc = document.createElement('canvas'); tvc.width = 1024; tvc.height = 576; const tg = tvc.getContext('2d'); const tvT = new THREE.CanvasTexture(tvc); tvT.colorSpace = THREE.SRGBColorSpace;
  if (tvP !== 'none') { const who = tvP.startsWith('above:') ? cast[tvP.slice(6)] : null;
    // never over a window or anything else on the back wall (2026-11-23: window bars cut through the TV's words)
    const want = who ? who.spot.x : tvP === 'wall-left' ? -3.5 : 3.5;
    const busy = O.children.filter(o => o.visible && o !== tv).map(o => new THREE.Box3().setFromObject(o)).filter(b => {
      const s = b.getSize(new THREE.Vector3()); return b.min.z < ZB + 0.6 && b.max.y > FY + 1.6 && b.min.y < FY + 3.3 && s.x < 6 && s.x > 0.1; });
    const free = xx => busy.every(b => xx + TVW / 2 + 0.15 < b.min.x || xx - TVW / 2 - 0.15 > b.max.x);
    let x = want; for (let d = 0; d <= 8 && !free(x); d += 0.1) { if (free(want + d)) { x = want + d; break; } if (free(want - d)) { x = want - d; break; } }
    tv = new THREE.Group(); tv.name = 'the wall TV';
    const fr = new THREE.Mesh(new THREE.BoxGeometry(TVW + 0.07, TVH + 0.07, 0.06), new THREE.MeshStandardMaterial({ color: '#15171c', roughness: 0.35, metalness: 0.4 })); fr.castShadow = true; tv.add(fr);
    const scr = new THREE.Mesh(new THREE.PlaneGeometry(TVW, TVH), new THREE.MeshBasicMaterial({ map: tvT, toneMapped: false })); scr.position.z = 0.032; tv.add(scr);
    tv.position.set(x, FY + 2.4, ZB + 0.16); O.add(tv); }
  const tvStates = ((B.tv && B.tv.states) || []).map(s => ({ ...s, t: at(s.from) })).sort((a, b) => a.t - b.t);
  const tvState = t => { let s = null; for (const x of tvStates) if (t >= x.t) s = x; return s; };
  const chip = (g, x, y, s, col) => { g.fillStyle = col; for (let i = 0; i < 5; i++) { const o = -s * 0.36 + i * s * 0.18; g.fillRect(x + o - s * 0.03, y - s * 0.62, s * 0.06, s * 0.14); g.fillRect(x + o - s * 0.03, y + s * 0.48, s * 0.06, s * 0.14); g.fillRect(x - s * 0.62, y + o - s * 0.03, s * 0.14, s * 0.06); g.fillRect(x + s * 0.48, y + o - s * 0.03, s * 0.14, s * 0.06); }
    g.fillRect(x - s * 0.5, y - s * 0.5, s, s); g.fillStyle = '#14161c'; g.fillRect(x - s * 0.3, y - s * 0.3, s * 0.6, s * 0.6); };
  const TONE = { good: '#2fd47a', bad: '#ff3b3b', neutral: '#ffffff' };
  const fit = (g, text, max, size) => { let f = size; g.font = `${f}px Anton`; while (g.measureText(text).width > max && f > 40) { f -= 6; g.font = `${f}px Anton`; } return f; };
  function drawTV(t) {
    if (!tv) return; const s = tvState(t), g = tg; g.fillStyle = '#0d1424'; g.fillRect(0, 0, 1024, 576); tv.userData.words = [];
    if (s) { const age = t - s.t, slam = eio(clamp(age / 0.16)), col = TONE[s.tone] || '#ffffff';
      if (s.kicker) { g.fillStyle = s.tone === 'good' ? '#1f9e5a' : '#d7262c'; g.fillRect(0, 0, 1024 * slam, 96); g.fillStyle = '#fff'; g.font = '62px Anton'; if (slam > 0.6) g.fillText(String(s.kicker).toUpperCase().slice(0, 22), 36, 74); tv.userData.words.push([20, 0, 1000, 96]); }
      const icon = s.icon === 'chip'; if (icon) chip(g, 150, 250, 150, '#e8c268');
      const left = icon ? 290 : 40, max = 1024 - left - 40, title = String(s.title || '').toUpperCase().slice(0, 24);
      g.save(); const f = fit(g, title, max, 190), cx = left + max / 2; g.translate(cx, 250); const k = lerp(0.6, 1, slam); /* grows in: never wider than its final, measured size */ g.scale(k, k); g.fillStyle = col; g.textAlign = 'center'; g.fillText(title, 0, f * 0.36); g.restore();
      tv.userData.words.push([left, 250 - f * 0.55, left + max, 250 + f * 0.45]);
      const k2 = clamp(age / 1.2);
      if (s.chart === 'up' || s.chart === 'down') { g.strokeStyle = s.chart === 'up' ? '#2fd47a' : '#ff3b3b'; g.lineWidth = 12; g.beginPath();
        for (let i = 0; i <= 9 * k2; i++) { const x = 60 + i * 100, y = s.chart === 'up' ? 540 - i * 16 - (i % 2) * 24 : 400 + i * 14 + (i % 2) * 24; i ? g.lineTo(x, y) : g.moveTo(x, y); } g.stroke(); } }
    tvT.needsUpdate = true;
  }
  const tvBox = (x0, y0, x1, y1) => { tv.updateMatrixWorld(true); const a = V((x0 / 1024 - 0.5) * TVW, (0.5 - y1 / 576) * TVH, 0.03), b = V((x1 / 1024 - 0.5) * TVW, (0.5 - y0 / 576) * TVH, 0.04);
    return new THREE.Box3().setFromPoints([tv.localToWorld(a), tv.localToWorld(b)]); };
  const setWords = t => !tv ? [] : [{ box: new THREE.Box3().setFromObject(tv), label: 'the wall TV', noCrop: true, subjectOnly: tv },
    ...(drawTV(t), tv.userData.words || []).map((r, i) => ({ box: tvBox(...r), label: `the TV words (${i + 1})` }))];

  // bubbles and screen glows
  const BUB = {}; for (const ch of ['?', '!', '$']) { const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d'); g.fillStyle = '#fff'; g.beginPath(); g.arc(64, 60, 50, 0, 7); g.fill(); g.lineWidth = 6; g.strokeStyle = '#2a1612'; g.stroke(); g.fillStyle = ch === '$' ? '#1f9e5a' : '#e8442a'; g.font = '80px Anton'; g.textAlign = 'center'; g.fillText(ch, 64, 90); BUB[ch] = new THREE.CanvasTexture(c); BUB[ch].colorSpace = THREE.SRGBColorSpace; }
  const bub = new Map(people.map(c => { const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: BUB['?'], transparent: true, depthTest: false })); s.visible = false; scene.add(s); return [c, s]; }));
  const glows = (B.glow || []).map(gl => { const sp = P[gl.place]; const l = new THREE.PointLight(TONE[gl.tone] || '#ffffff', 0, 1.6, 2); l.position.set(sp ? (sp.desk ?? sp.faceDesk ?? sp.x) : 0, FY + 0.95, ZD); scene.add(l); return { ...gl, t: at(gl.from), l }; });

  // beats: what each person is doing from a word on, held until their next beat
  const beats = new Map(people.map(c => [c, []]));
  (B.beats || []).forEach(b => { const c = cast[b.who]; if (c) beats.get(c).push({ ...b, t: at(b.from) }); });
  beats.forEach(l => l.sort((a, b) => a.t - b.t));
  const beatOf = (c, t) => { let cur = null, prev = null; for (const b of beats.get(c)) if (t >= b.t) { prev = cur; cur = b; } return [cur, prev]; };
  const restArms = c => { if (c.spot.desk !== undefined || c.spot.faceDesk !== undefined) { arm(c, 'Left', Lw(c, 0.18, 0.95, 0.5)); arm(c, 'Right', Lw(c, -0.18, 0.95, 0.5)); } };
  const ACT = {
    stand: c => restArms(c),
    type: (c, t) => { const a = 0.03 * Math.sin(t * 28 + c.phase), b = 0.03 * Math.sin(t * 31 + 1 + c.phase); arm(c, 'Left', Lw(c, 0.16, 0.97 + a, 0.52)); arm(c, 'Right', Lw(c, -0.16, 0.97 + b, 0.52)); },
    cheer: (c, t, k) => { const s = Math.sin(t * 9) * 0.05; arm(c, 'Left', Lw(c, lerp(0.18, 0.42, k), lerp(0.95, 1.95, k) + s, lerp(0.5, 0.12, k)), dirW(c, 1, 0.2, -0.5)); arm(c, 'Right', Lw(c, lerp(-0.18, -0.42, k), lerp(0.95, 1.95, k) - s, lerp(0.5, 0.12, k)), dirW(c, -1, 0.2, -0.5)); },
    'hands-on-head': (c, t, k) => { const h = headC(c), r = 0.27; arm(c, 'Left', Lw(c, 0.18, 0.95, 0.5).lerp(h.clone().add(dirW(c, 1, 0, 0).multiplyScalar(r)).add(V(0, 0.08, 0)), k), dirW(c, 1, -0.3, -0.4)); arm(c, 'Right', Lw(c, -0.18, 0.95, 0.5).lerp(h.clone().add(dirW(c, -1, 0, 0).multiplyScalar(r)).add(V(0, 0.08, 0)), k), dirW(c, -1, -0.3, -0.4)); },
    'scratch-head': (c, t, k) => { restArms(c); const h = headC(c); arm(c, 'Right', Lw(c, -0.18, 0.95, 0.5).lerp(h.clone().add(dirW(c, -1, 0, 0).multiplyScalar(0.25)).add(V(0, 0.12 + 0.03 * Math.sin(t * 14), 0)), k), dirW(c, -1, -0.3, -0.4)); },
    point: (c, t, k, b) => { restArms(c); const tg2 = b.look && cast[b.look] ? headC(cast[b.look]) : b.look === 'tv' && tv ? tv.position.clone() : headC(c).add(dirW(c, 0, 0, 1).multiplyScalar(2)); const sh = K.SR.wp(c.bone('RightArm')); arm(c, 'Right', sh.clone().lerp(sh.clone().add(tg2.sub(sh).normalize().multiplyScalar(0.62)), k), dirW(c, -1, -0.3, 0)); },
    wave: (c, t, k) => { restArms(c); const s = Math.sin(t * 8); arm(c, 'Right', Lw(c, lerp(-0.18, -0.45 + 0.12 * s, k), lerp(0.95, 1.85, k), lerp(0.5, 0.1, k)), dirW(c, -1, -0.2, -0.3)); },
    laugh: (c, t, k) => { const s = Math.abs(Math.sin((t + c.phase) * 11)) * k; hips(c, -0.02 * s); arm(c, 'Left', Lw(c, 0.1, 1.02, 0.22), dirW(c, 1, 0, -0.2)); arm(c, 'Right', Lw(c, -0.08, 1.0 + 0.03 * s, 0.24), dirW(c, -1, 0, -0.2)); },
    shrug: (c, t, k) => { arm(c, 'Left', Lw(c, lerp(0.18, 0.42, k), lerp(0.95, 1.1, k), lerp(0.5, 0.3, k)), dirW(c, 1, -0.6, 0)); arm(c, 'Right', Lw(c, lerp(-0.18, -0.42, k), lerp(0.95, 1.1, k), lerp(0.5, 0.3, k)), dirW(c, -1, -0.6, 0)); },
    nod: (c, t) => { restArms(c); headTurn(c, 0, 0.18 * Math.max(0, Math.sin(t * 9))); },
    'lean-in': (c, t, k) => { restArms(c); hips(c, 0, 0.06 * k); },
    'arms-crossed': (c, t, k) => { const ch = Lw(c, 0, 1.12, 0.26); arm(c, 'Left', Lw(c, 0.18, 0.95, 0.5).lerp(ch.clone().add(dirW(c, -1, 0, 0).multiplyScalar(0.12)), k), dirW(c, 1, -0.6, 0)); arm(c, 'Right', Lw(c, -0.18, 0.95, 0.5).lerp(ch.clone().add(dirW(c, 1, 0, 0).multiplyScalar(0.12)).add(V(0, -0.04, 0)), k), dirW(c, -1, -0.6, 0)); },
  };
  function pose(t) {
    K.resetScene(); drawTV(t);
    for (const c of people) {
      const [b] = beatOf(c, t); place(c, c.spot.x, c.spot.z, c.spot.ry, FY); SR.clipAt(c, 'idle', 0.4 + c.phase);
      const act = b && ACT[b.act] ? b.act : (c.spot.desk !== undefined ? 'type' : 'stand'), k = b ? eio(clamp((t - b.t) / 0.3)) : 1;
      if (!(c.spot.desk !== undefined || c.spot.faceDesk !== undefined) && (act === 'stand' || act === 'nod')) K.idle(c, t);
      ACT[act](c, t, k, b || {});
      if (b && b.look && b.look !== 'front') { const tgt = b.look === 'tv' && tv ? tv.position : cast[b.look] ? cast[b.look].root.position : null;
        if (tgt) { const want = Math.atan2(tgt.x - c.root.position.x, tgt.z - c.root.position.z), turn = THREE.MathUtils.clamp(((want - c.spot.ry + 3 * Math.PI) % (2 * Math.PI)) - Math.PI, -0.9, 0.9); headTurn(c, turn * k, 0); } }
      face(c, (b && b.face) || 'calm');
      const s = bub.get(c), on = b && b.bubble && b.bubble !== 'none' && BUB[b.bubble]; s.visible = !!on;
      if (on) { s.material.map = BUB[b.bubble]; const h = headC(c), kk = Math.min(1, (t - b.t) * 6); s.position.set(h.x + 0.24, h.y + 0.42 + 0.03 * Math.sin(t * 8), h.z); s.scale.setScalar(0.36 * kk); }
    }
    for (const g of glows) { g.l.intensity = t >= g.t ? 1.0 * clamp((t - g.t) / 0.4) : 0; /* a glow on the faces, not a green desk */ }
    ALL.forEach(c => SR.updateLimbs(c));
  }
  const bubbleBoxes = (ids, t) => ids.map(c => bub.get(c)).filter(s => s && s.visible).map(s => ({ box: new THREE.Box3().setFromCenterAndSize(s.position, V(0.4, 0.4, 0.4)), label: 'a bubble', onTop: true }));
  function light(t, cam, sh) {
    K.setLook('day'); K.hemi.intensity = 0.32; K.hemi.color.set('#9fb4e0'); K.sun.intensity = 2.6; K.sun.color.set('#ffd29a'); K.SUNDIR.set(0.35, 0.5, -0.75).normalize();
    K.U.uSat.value = 1.2; K.U.uCon.value = 1.22; K.U.uWarm.value = 0.07; K.renderer.toneMappingExposure = 0.42; K.U.uVig.value = 0.55;
    const f = sh.box.getCenter(V(0, 0, 0)); K.sun.target.position.copy(f); K.sun.position.copy(f).addScaledVector(K.SUNDIR, 60); const sc = K.sun.shadow.camera; sc.left = sc.bottom = -10; sc.right = sc.top = 10; sc.near = 1; sc.far = 140; sc.updateProjectionMatrix();
  }
  // shots
  const raw = (B.shots || []).map(s => ({ ...s, t0: at(s.from) })).sort((a, b) => a.t0 - b.t0);
  if (!raw.length) throw new Error('board: no shots');
  raw[0].t0 = 0;
  const shots = raw.map((s, i) => {
    const who = (s.who || []).map(id => id === 'tv' ? tv : cast[id]).filter(Boolean); if (!who.length) throw new Error(`board: shot ${i + 1} has nobody in it`);
    const [yaw, pitch] = ANGLE[s.angle] || ANGLE.front, fov = LENS[s.lens] || LENS.medium, mv = s.move || 'push';
    const view = u => { const e = eio(u), v = { yaw, pitch, fov, k: 1, roll: 0 };
      if (mv === 'push') v.k = lerp(1.14, 1.0, e); else if (mv === 'pull') v.k = lerp(1.0, 1.14, e);
      else if (mv === 'crane-down') { v.pitch = pitch + lerp(0.25, 0, e); v.k = lerp(1.1, 1.0, e); } else if (mv === 'crane-up') { v.pitch = pitch + lerp(0, 0.25, e); }
      else if (mv === 'orbit-left') v.yaw = yaw + lerp(0.12, -0.12, e); else if (mv === 'orbit-right') v.yaw = yaw + lerp(-0.12, 0.12, e);
      else if (mv === 'dolly-zoom') { v.fov = lerp(fov + 10, fov - 8, e); v.roll = -0.07 * e; } else v.k = lerp(1.03, 1.0, e);   // hold: a breath of movement
      return v; };
    const hidden = who.filter(c => c && c.spot && c.spot.desk !== undefined).map(c => ({ who: c, below: FY + 0.66, frontZ: ZD + 0.4 }));
    return { name: `${i + 1} ${s.angle || 'front'} ${s.lens || 'medium'} ${mv}: ${who.map(w => w.label || w.name).join(', ')}`, t0: s.t0, t1: i + 1 < raw.length ? raw[i + 1].t0 : DUR,
      who, hidden, dof: s.lens === 'close' ? 0.01 : 0, extras: t => bubbleBoxes(who.filter(w => w && w.root), t), view };
  });
  const props = [];
  O.children.forEach(o => { if (!o.visible) return; if (o === tv) { props.push({ obj: o, label: 'the wall TV' }); return; }
    if (o.name) { props.push({ obj: o, label: o.name.replace(/_/g, ' ').replace(/\d+$/, '').trim(), floor: /rug/i.test(o.name) }); return; }
    if (o.isMesh && o.geometry.type === 'BoxGeometry') { const s = new THREE.Box3().setFromObject(o).getSize(V(0, 0, 0)); if (Math.max(s.x, s.y, s.z) < 6 && s.y > 0.2) props.push({ obj: o, label: 'a set piece' }); } });
  const room = { min: V(-8.85, FY + 0.03, ZB + 0.12), max: V(8.85, FY + 4.15, ZF - 0.1) };
  return { dur: DUR, people, props, room, pose, light, shots, words: setWords };
}
