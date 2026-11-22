// First proof (owner plan 2026-11-22, step 2): the 9 s opening of golide-short-2026-11-22-trial rebuilt in the 3D engine.
// "Imagine you're running the chipmaker, and a huge AI IPO lands, but instead of reassuring investors,
//  it makes them question the AI buildout."
// One place (the engine's office), four people: you (the chipmaker's boss, vest and red tie) at your desk, and three
// investors gathered round one laptop at the next desk. The wall TV behind you carries the story: the chipmaker's orders, then BREAKING: AI IPO, then the red turn.
// Cuts land on the real word timings; every shot moves; the director frames and checks each one.
import * as THREE from 'three';

export async function build(K, words) {
  const { SR, base, OUTF, ALL, O, FY, Z, V, place, arm, Lw, dirW, face, headC, hips, clamp, eio, lerp, scene } = K;
  const norm = s => s.toLowerCase().replace(/[^a-z0-9$.]/g, '');
  const W = (w, n = 0) => { const m = words.filter(x => norm(x.word).replace(/\.$/, '') === w); if (!m[n]) throw new Error(`chipmaker-open: the word "${w}" is not in the timings`); return m[n]; };
  const T = { chip: W('chipmaker').start, and: W('and').start, huge: W('huge').start, ipo: W('ipo').start, lands: W('lands').start,
    but: W('but').start, reassure: W('reassuring').start, investors: W('investors').start, it: W('it').start, makes: W('makes').start,
    question: W('question').start, build: W('buildout').start };
  const DUR = +(W('buildout').end + 0.06).toFixed(2);

  const ZD = Z - 2.9, CHZ = ZD - 0.55, ZB = Z - 6, ZF = Z + 9, ME = 2.1;
  // ---- set: chairs away (standing desks, as the engine's skit); laptops instead of desktop monitors, so screens never
  // stand between the camera and a face; each laptop turned to the person using it ----
  O.children.filter(o => o.name === 'modern_arm_chair_01').forEach(o => (o.visible = false));
  const at = (o, x) => Math.abs(o.position.x - x) < 0.7 && Math.abs(o.position.z - ZD) < 0.4;
  O.children.filter(o => ['computerScreen', 'computerKeyboard', 'computerMouse'].includes(o.name)).forEach(o => (o.visible = false));
  const lapI = O.children.find(o => o.name === 'laptop'); if (!lapI) throw new Error('chipmaker-open: the engine office has no laptop to copy');
  lapI.rotation.y = Math.PI; const lapY = lapI.clone(true); lapY.position.x = ME + (lapI.position.x - -2.1); O.add(lapY);
  // the back wall's whiteboard makes way for a wall TV behind you
  O.children.filter(o => o.isMesh && o.geometry.type === 'BoxGeometry' && Math.abs(o.position.x - 2.2) < 1.9 && o.position.z < ZB + 0.3 && o.position.y > FY + 1.4 && o.position.y < FY + 3.3).forEach(o => (o.visible = false));
  const TVW = 1.6, TVH = 0.9, TVY = FY + 2.2;
  const tvc = document.createElement('canvas'); tvc.width = 1024; tvc.height = 576; const tg = tvc.getContext('2d');
  const tvT = new THREE.CanvasTexture(tvc); tvT.colorSpace = THREE.SRGBColorSpace;
  const tv = new THREE.Group(); tv.name = 'the wall TV'; tv.userData.label = 'the wall TV';
  { const frameM = new THREE.Mesh(new THREE.BoxGeometry(TVW + 0.08, TVH + 0.08, 0.06), new THREE.MeshStandardMaterial({ color: '#15171c', roughness: 0.35, metalness: 0.4 })); frameM.castShadow = true; tv.add(frameM);
    const scr = new THREE.Mesh(new THREE.PlaneGeometry(TVW, TVH), new THREE.MeshBasicMaterial({ map: tvT, toneMapped: false })); scr.position.z = 0.032; tv.add(scr);
    tv.position.set(ME, TVY, ZB + 0.16); O.add(tv); }
  const chipIcon = (g, x, y, s, col = '#e8c268') => { g.fillStyle = col; for (let i = 0; i < 5; i++) { const o = -s * 0.36 + i * s * 0.18; g.fillRect(x + o - s * 0.03, y - s * 0.62, s * 0.06, s * 0.14); g.fillRect(x + o - s * 0.03, y + s * 0.48, s * 0.06, s * 0.14); g.fillRect(x - s * 0.62, y + o - s * 0.03, s * 0.14, s * 0.06); g.fillRect(x + s * 0.48, y + o - s * 0.03, s * 0.14, s * 0.06); }
    g.fillRect(x - s * 0.5, y - s * 0.5, s, s); g.fillStyle = '#14161c'; g.fillRect(x - s * 0.3, y - s * 0.3, s * 0.6, s * 0.6); g.strokeStyle = col; g.lineWidth = s * 0.05; g.strokeRect(x - s * 0.2, y - s * 0.2, s * 0.4, s * 0.4); };
  function drawTV(t) {
    const g = tg; g.fillStyle = '#0d1424'; g.fillRect(0, 0, 1024, 576);
    if (t < T.lands) {                                         // the chipmaker's orders, climbing
      chipIcon(g, 170, 200, 170); g.fillStyle = '#ffffff'; g.font = '110px Anton'; g.fillText('CHIPMAKER', 320, 250);
      g.fillStyle = '#8fa3c8'; g.font = '40px InterB'; g.fillText('ORDERS', 330, 320);
      const k = clamp(t / 1.6);
      for (let i = 0; i < 8; i++) { const h = (60 + i * 26) * eio(clamp(k * 1.4 - i * 0.06)); g.fillStyle = '#2fd47a'; g.fillRect(330 + i * 78, 520 - h, 54, h); }
    } else {                                                   // BREAKING: AI IPO, then the turn to red
      const slam = eio(clamp((t - T.lands) / 0.16)), red = clamp((t - T.makes) / 0.5);
      g.fillStyle = '#d7262c'; g.fillRect(0, 0, 1024 * slam, 96); g.fillStyle = '#ffffff'; g.font = '62px Anton'; if (slam > 0.6) g.fillText('BREAKING', 36, 74);
      // the headline sits in the TV's top half: in the last shot your head covers its lower half
      const turn = t >= T.build; g.save(); g.translate(512, turn ? 230 : 300); const s = lerp(1.6, 1, slam); g.scale(s, s); g.fillStyle = turn ? '#ff3b3b' : '#ffffff'; g.font = turn ? '150px Anton' : '210px Anton'; g.textAlign = 'center'; g.fillText(turn ? 'AI BUILDOUT?' : 'AI IPO', 0, 70); g.restore();
      if (red <= 0) { g.fillStyle = '#2fd47a'; g.beginPath(); g.moveTo(870, 470); g.lineTo(930, 400); g.lineTo(990, 470); g.fill(); g.fillRect(912, 470, 36, 70); }
      else { g.strokeStyle = '#ff3b3b'; g.lineWidth = 12; g.beginPath(); const n = 9; for (let i = 0; i <= n * red; i++) { const x = 60 + i * 100, y = 410 + i * 14 + (i % 2) * 26; i ? g.lineTo(x, y) : g.moveTo(x, y); } g.stroke();
      }
    }
    tvT.needsUpdate = true;
  }
  // screen glow on the investors' faces: green while the IPO is good news, red once they start asking
  const glows = [new THREE.PointLight('#2fd47a', 0, 2.4, 2)]; glows[0].position.set(-2.1, FY + 0.95, ZD); scene.add(glows[0]);

  // ---- cast (built with the engine's own rig and look) ----
  const mk = (o, label, phase) => { const c = SR.build({ ...base, ...o }); c.root.scale.setScalar(0.8); c.phase = phase; c.root.rotation.order = 'YXZ'; c.tint = c.hm.material.uniforms.base.value.clone(); ALL.push(c); c.label = label; return c; };
  const you = OUTF[1]; you.label = 'you (the chipmaker\'s boss)';
  const A = mk({ jacket: '#2c3e6b', jacket2: '#1f2d50', style: 'tunic', civil: true, pattern: ['pinstripe', '#5b6f9e'], details: ['tie', 'buttons'], tieCol: '#3d7be0', btn: '#d9d9d9' }, 'investor 1', 0.4);
  const B = mk({ jacket: '#3a3f4a', jacket2: '#2a2e36', pattern: ['vest', '#2f333c'], details: ['tie', 'vestBtn'], tieCol: '#e8b730' }, 'investor 2', 1.1);
  const C = mk({ jacket: '#7a5134', jacket2: '#5a3a24', style: 'tunic', civil: true, pattern: ['plaid', '#8f6444'], details: ['bow', 'buttons'], tieCol: '#c8352f', btn: '#e8d3a8' }, 'investor 3', 1.9);
  // investors round the laptop at desk 2 (x -2.1): one behind it, one at each end, turned to the laptop
  you.spot = { x: ME, z: CHZ, ry: 0 }; B.spot = { x: -2.1, z: CHZ, ry: 0 }; A.spot = { x: -3.05, z: ZD - 0.1, ry: Math.PI / 2 }; C.spot = { x: -1.15, z: ZD - 0.1, ry: -Math.PI / 2 };
  const people = [you, A, B, C], investors = [A, B, C];

  // "?" over the investors when they start asking
  const qT = (() => { const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d'); g.fillStyle = '#fff'; g.beginPath(); g.arc(64, 60, 50, 0, 7); g.fill(); g.lineWidth = 6; g.strokeStyle = '#2a1612'; g.stroke(); g.fillStyle = '#e8442a'; g.font = '80px Anton'; g.textAlign = 'center'; g.fillText('?', 64, 90); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t; })();
  const bub = investors.map(() => { const b = new THREE.Sprite(new THREE.SpriteMaterial({ map: qT, transparent: true, depthTest: false })); b.visible = false; b.userData.noBlock = true; scene.add(b); return b; });
  const bubAt = i => T.question + i * 0.14;

  // ---- acting ----
  const stand = (c, dy = 0) => { place(c, c.spot.x, c.spot.z, c.spot.ry, FY - dy); SR.clipAt(c, 'idle', 0.4); if (dy > 0.01) hips(c, 0); arm(c, 'Left', Lw(c, 0.18, 0.95, 0.5)); arm(c, 'Right', Lw(c, -0.18, 0.95, 0.5)); };
  const type = (c, t) => { const a = 0.03 * Math.sin(t * 28 + c.phase), b = 0.03 * Math.sin(t * 31 + 1 + c.phase); arm(c, 'Left', Lw(c, 0.16, 0.97 + a, 0.52)); arm(c, 'Right', Lw(c, -0.16, 0.97 + b, 0.52)); };
  const cheer = (c, t, k) => { const s = Math.sin(t * 9) * 0.05; arm(c, 'Left', Lw(c, lerp(0.18, 0.42, k), lerp(0.95, 1.95, k) + s, lerp(0.5, 0.12, k)), dirW(c, 1, 0.2, -0.5)); arm(c, 'Right', Lw(c, lerp(-0.18, -0.42, k), lerp(0.95, 1.95, k) - s, lerp(0.5, 0.12, k)), dirW(c, -1, 0.2, -0.5)); };
  const handsToHead = (c, k, one = false) => { const h = headC(c), r = 0.27; const L = h.clone().add(dirW(c, 1, 0, 0).multiplyScalar(r)).add(V(0, 0.08, 0)), R = h.clone().add(dirW(c, -1, 0, 0).multiplyScalar(r)).add(V(0, 0.08, 0));
    if (!one) arm(c, 'Left', Lw(c, 0.18, 0.95, 0.5).lerp(L, k), dirW(c, 1, -0.3, -0.4)); arm(c, 'Right', Lw(c, -0.18, 0.95, 0.5).lerp(R, k), dirW(c, -1, -0.3, -0.4)); };
  function pose(t) {
    K.resetScene(); drawTV(t);
    // you
    const sink = eio(clamp((t - T.build) / 0.8)) * 0.18; stand(you, sink);
    const up = clamp((t - T.huge) / 0.25) * (1 - clamp((t - T.but) / 0.3));
    if (t < T.huge) type(you, t); else if (up > 0) cheer(you, t, eio(up));
    face(you, t < T.huge ? 'smug' : t < T.but ? 'grin' : t < T.build ? 'calm' : 'pale');
    // investors
    investors.forEach((c, i) => { stand(c); const q = eio(clamp((t - bubAt(i)) / 0.3));
      if (t < T.investors) { if (c === B) type(c, t); } else if (q > 0) { if (i === 0) handsToHead(c, q, true); if (i === 1) handsToHead(c, q); }
      face(c, t < T.reassure ? 'calm' : t < T.makes ? 'grin' : (i === 1 ? 'pale' : i === 0 ? 'wide' : 'squint'));
      const b = bub[i], on = t >= bubAt(i); b.visible = on; if (on) { const h = headC(c), k = Math.min(1, (t - bubAt(i)) * 6); b.position.set(h.x + 0.24, h.y + 0.42 + 0.03 * Math.sin(t * 8 + i), h.z); b.scale.setScalar(0.36 * k); } });
    const g = clamp((t - T.but) / 0.4), r = clamp((t - T.makes) / 0.4);
    glows.forEach(l => { l.color.set(r > 0 ? '#ff3b3b' : '#2fd47a'); l.intensity = r > 0 ? 3.0 * r : 2.0 * g; });
    ALL.forEach(c => SR.updateLimbs(c));
  }
  const bubbleBoxes = t => investors.map((c, i) => t >= bubAt(i) ? { box: new THREE.Box3().setFromCenterAndSize(bub[i].position, V(0.4, 0.4, 0.4)), label: `${c.label}'s "?"` } : null).filter(Boolean);
  function light(t, cam, sh) {   // the engine's dim office look (its skit's numbers), sun shadow around the shot
    K.setLook('day'); K.hemi.intensity = 0.32; K.hemi.color.set('#9fb4e0'); K.sun.intensity = 2.6; K.sun.color.set('#ffd29a'); K.SUNDIR.set(0.35, 0.5, -0.75).normalize();
    K.U.uSat.value = 1.2; K.U.uCon.value = 1.22; K.U.uWarm.value = 0.07; K.renderer.toneMappingExposure = 0.42; K.U.uVig.value = 0.55;
    const f = sh.box.getCenter(V(0, 0, 0)); K.sun.target.position.copy(f); K.sun.position.copy(f).addScaledVector(K.SUNDIR, 60); const sc = K.sun.shadow.camera; sc.left = sc.bottom = -10; sc.right = sc.top = 10; sc.near = 1; sc.far = 140; sc.updateProjectionMatrix();
  }
  // ---- shots (director's plan: establish → low hero push → the news lands → reactions → the turn → dolly-zoom) ----
  const shots = [
    { name: '1 establish: you and your company', t0: 0, t1: T.and, who: [you, tv], dof: 0, view: u => ({ yaw: lerp(-0.55, -0.32, eio(u)), pitch: lerp(0.32, 0.12, eio(u)), fov: 46, k: lerp(1.14, 1.0, eio(u)) }) },
    { name: '2 low push: a huge AI IPO', t0: T.and, t1: T.ipo, who: [you], dof: 0.01, view: u => ({ yaw: 0.38, pitch: -0.16, fov: 36, k: lerp(1.16, 1.0, eio(u)) }) },
    { name: '3 the news lands on the TV', t0: T.ipo, t1: T.but, who: [you, tv], dof: 0, view: (u, t) => ({ yaw: 0.16, pitch: -0.04, fov: 46, k: t < T.lands ? lerp(1.3, 1.22, clamp((t - T.ipo) / (T.lands - T.ipo))) : lerp(1.22, 1.0, eio(clamp((t - T.lands) / 0.14))) }) },
    { name: '4 the investors, hopeful', t0: T.but, t1: T.it, who: [A, B, C], dof: 0, view: u => ({ yaw: lerp(0.3, 0.18, u), pitch: 0.06, fov: 30, k: lerp(1.12, 1.0, eio(u)) }) },
    { name: '5 they start asking', t0: T.it, t1: T.build, who: [A, B, C], extras: bubbleBoxes, dof: 0, view: u => ({ yaw: lerp(-0.95, -0.85, u), pitch: 0.12, fov: 34, k: lerp(1.1, 1.0, eio(u)) }) },
    { name: '6 dolly-zoom: the buildout', t0: T.build, t1: DUR, who: [you], dof: 0.012, view: u => ({ yaw: 0.0, pitch: 0.06, fov: lerp(44, 24, eio(u)), k: 1.0, roll: -0.08 * eio(u) }) },
  ];
  // what the director may not put the camera in or people through: furniture, the TV (walls are the room bounds)
  const props = [];
  O.children.forEach(o => { if (!o.visible) return; if (o === tv) { props.push({ obj: o, label: 'the wall TV' }); return; }
    if (o.name) { const floor = /rug/i.test(o.name); props.push({ obj: o, label: o.name.replace(/_/g, ' ').replace(/\d+$/, '').trim(), floor }); return; }
    if (o.isMesh && o.geometry.type === 'BoxGeometry') { const s = new THREE.Box3().setFromObject(o).getSize(V(0, 0, 0)); if (Math.max(s.x, s.y, s.z) < 6 && s.y > 0.2) props.push({ obj: o, label: 'a set piece' }); } });
  const room = { min: V(-8.85, FY + 0.03, ZB + 0.12), max: V(8.85, FY + 4.15, ZF - 0.1) };
  return { dur: DUR, people, props, room, pose, light, shots };
}
