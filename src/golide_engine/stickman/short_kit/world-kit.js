// ===== GOLIDE world kit (2026-11-18, from the owner's fast-cut Elon test): ready pieces for tech / city stories. =====
// Everything is built from the engine's own helpers (add, tbox, toon, P.tex), so it is inked and lit like the rest.
// LOGO (set by the engine above this kit) holds the real logos of the brands the script names: { slug: { d, hex, title } }.
const KC = (c) => toon({ color: c });
const KM = { concrete: KC('#c9c3b6'), white: KC('#f1efe8'), dark: KC('#2b2d34'), steel: KC('#8e959e'), gold: KC('#e9b43a'),
  glass: KC('#3d5d7a'), road: KC('#8b8f96'), lane: KC('#f4efe4'), red: KC('#c7322e'), screen: KC('#10141c') };
const kTex = (c) => { const t = P.tex(c); t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping; return t; };
const kCanvas = (w, h) => { const c = document.createElement('canvas'); c.width = w; c.height = h; return [c, c.getContext('2d')]; };
// a brand's real logo as a canvas drawing (simple-icons 24x24 path), or nothing when the brand is not known
const drawLogo = (g, slug, x, y, size, colour) => { const L = (typeof LOGO !== 'undefined') && LOGO[slug]; if (!L) return false;
  g.save(); g.translate(x, y); g.scale(size / 24, size / 24); g.fillStyle = colour || ('#' + (L.hex || '111111')); g.fill(new Path2D(L.d)); g.restore(); return true; };
// SETS: build each place at least 600 m from the others (x = 0, 600, 1200, ...): far pieces (the city ring, a starfield,
// the sea) are big and must never show up in another place's shot.
// a sign: optional logo + words, fitted to the board; front face material for a box (face 4 = +z)
const signMat = (text, opts = {}) => { const { slug = null, bg = '#ffffff', fg = '#111114', w = 1024, h = 320, border = true } = opts;
  const [c, g] = kCanvas(w, h); g.fillStyle = bg; g.fillRect(0, 0, w, h);
  if (border) { g.strokeStyle = '#1b1a20'; g.lineWidth = 16; g.strokeRect(8, 8, w - 16, h - 16); }
  let x0 = h * 0.2; if (slug && drawLogo(g, slug, x0, h * 0.19, h * 0.62)) x0 += h * 0.78; else x0 = null;
  let fs = Math.round(h * 0.42); g.font = `800 ${fs}px sans-serif`; g.fillStyle = fg; g.textBaseline = 'middle';
  const room = x0 === null ? w * 0.88 : w - x0 - h * 0.14; while (g.measureText(text).width > room && fs > 18) { fs -= 4; g.font = `800 ${fs}px sans-serif`; }
  if (x0 === null) { g.textAlign = 'center'; g.fillText(text, w / 2, h / 2 + 4); } else { g.textAlign = 'left'; g.fillText(text, x0, h / 2 + 4); }
  return toon({ map: kTex(c) }); };
// a board standing in the world, words (and logo) on its front; ry turns it
const signBoard = (text, x, y, z, w, h, opts = {}, parent = scene) => { const m = signMat(text, opts), d = KM.dark;
  const b = add(new THREE.BoxGeometry(w, h, 0.25), [d, d, d, d, m, d], x, y, z, parent); b.rotation.y = opts.ry || 0; return b; };
// a signpost on a pole whose arrow board can flip (set post.board.rotation.y over time)
const signPost = (text, x, z, opts = {}) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g);
  add(new THREE.CylinderGeometry(0.09, 0.11, 3.2, 10), KM.steel, 0, 1.6, 0, g);
  const pv = new THREE.Group(); pv.position.set(0, 2.8, 0); g.add(pv);
  const sh = new THREE.Shape(); sh.moveTo(-0.9, -0.28); sh.lineTo(0.7, -0.28); sh.lineTo(1.05, 0); sh.lineTo(0.7, 0.28); sh.lineTo(-0.9, 0.28); sh.closePath();
  const geo = new THREE.ExtrudeGeometry(sh, { depth: 0.08, bevelEnabled: false }); geo.translate(0, 0, -0.04);
  const m = signMat(text, { ...opts, w: 768, h: 192 }); const tex = m.map; tex.repeat.set(1 / 1.95, 1 / 0.56); tex.offset.set(0.9 / 1.95, 0.28 / 0.56);
  add(geo, [m, opts.side ? KC(opts.side) : KM.white], 0, 0, 0, pv); g.board = pv; return g; };
// a screen / monitor with words or a logo on it (a phone, a laptop lid, a billboard screen)
const screenBox = (text, x, y, z, w, h, opts = {}, parent = scene) => signBoard(text, x, y, z, w, h, { bg: '#10141c', fg: '#e9f2ff', ...opts }, parent);
// the city: towers of glass and concrete with lit windows (near rows behind the action, far ring all around)
const winTex = (() => { const [c, g] = kCanvas(128, 256); g.fillStyle = '#5f6f82'; g.fillRect(0, 0, 128, 256);
  for (let y = 10; y < 256; y += 32) for (let x = 10; x < 128; x += 30) { g.fillStyle = (x * 7 + y * 3) % 5 ? '#9ec3e6' : '#f1d38a'; g.fillRect(x, y, 18, 20); } return c; })();
const tower = (x, z, w, d, h, parent = scene) => { const m = toon({ map: P.tex(winTex, Math.max(1, w / 4), Math.max(1, h / 8)) });
  return add(new THREE.BoxGeometry(w, h, d), [m, m, KM.steel, KM.steel, m, m], x, DECK + h / 2, z, parent); };
// 2026-11-22: the far ring circles the street's own middle (it used to circle 0,0 and stood inside other sets)
const city = (x0, x1, zNear = -18, seed = 21) => { const r = P.rng(seed), mx = (x0 + x1) / 2;
  for (let x = x0; x < x1; x += 6 + r() * 5) tower(x, zNear - r() * 30, 5 + r() * 7, 5 + r() * 6, 12 + r() * 38);
  for (let i = 0; i < 50; i++) { const a = Math.PI * (1.05 + r() * 0.9), d = 160 + r() * 200; tower(mx + Math.cos(a) * d, zNear + Math.sin(a) * d, 12 + r() * 16, 12 + r() * 16, 30 + r() * 90); } };
// the road covers its own stretch only (a 2400 m plane at 0,0 used to pave over every other set)
const street = (x0, x1, z = 10) => { const g = add(new THREE.PlaneGeometry(x1 - x0 + 200, 260), KM.road, (x0 + x1) / 2, DECK, z - 60, scene, { cast: false }); g.rotation.x = -Math.PI / 2;
  for (let x = x0; x < x1; x += 6) add(new THREE.BoxGeometry(3, 0.03, 0.25), KM.lane, x, DECK + 0.01, z, scene, { cast: false }); return g; };
// money that reads as money: $100 bills, bundles with a paper band, a block of bundles to stand on
const billCanvas = (() => { const [c, g] = kCanvas(512, 220); g.fillStyle = '#cfdcc4'; g.fillRect(0, 0, 512, 220); g.strokeStyle = '#3f6a4a'; g.lineWidth = 10; g.strokeRect(12, 12, 488, 196);
  g.fillStyle = '#9fbf98'; g.beginPath(); g.ellipse(256, 110, 62, 78, 0, 0, 7); g.fill(); g.strokeStyle = '#3f6a4a'; g.lineWidth = 5; g.stroke();
  g.fillStyle = '#2f5a3c'; g.font = '900 64px sans-serif'; g.textBaseline = 'middle'; g.fillText('100', 34, 64); g.fillText('100', 370, 160); return c; })();
const billM = toon({ map: P.tex(billCanvas) }), bandM = KC('#e8d7a6'), billSide = KC('#b9cdb0');
const cashBundle = (x, y, z, ry = 0, parent = scene) => { const g = new THREE.Group(); g.position.set(x, y, z); g.rotation.y = ry; parent.add(g);
  add(new THREE.BoxGeometry(1.56, 0.36, 0.68), [billSide, billSide, billM, billSide, billSide, billSide], 0, 0.18, 0, g); add(new THREE.BoxGeometry(0.22, 0.38, 0.7), bandM, 0, 0.18, 0, g); return g; };
const cashBlock = (x, z, levels = 9, cols = 2, rows = 5) => { for (let lv = 0; lv < levels; lv++) for (let i = 0; i < cols; i++) for (let j = 0; j < rows; j++)
  cashBundle(x - (cols - 1) * 0.8 + i * 1.6, DECK + lv * 0.38, z - (rows - 1) * 0.35 + j * 0.7); return DECK + levels * 0.38; };   // returns the top height
// a kart (mini ride) with the brand on its side; move it with .position over time
const kart = (col, slug = null, name = '') => { const g = new THREE.Group(); scene.add(g); const b = KC(col);
  add(new THREE.BoxGeometry(2.4, 0.5, 1.3), b, 0, 0.45, 0, g); add(new THREE.BoxGeometry(0.7, 0.35, 1.1), b, 1.35, 0.4, 0, g); add(new THREE.BoxGeometry(0.25, 0.8, 1.0), KM.dark, -0.55, 0.9, 0, g);
  for (const [x, z] of [[0.85, 0.72], [0.85, -0.72], [-0.85, 0.72], [-0.85, -0.72]]) { const w = add(new THREE.CylinderGeometry(0.34, 0.34, 0.3, 16), KM.dark, x, 0.34, z, g); w.rotation.x = Math.PI / 2; }
  if (name || slug) { const m = signMat(name, { slug }); add(new THREE.BoxGeometry(1.7, 0.48, 0.02), m, 0.1, 0.48, 0.66, g); } return g; };
// the Earth (painted oceans and land) and satellites to orbit it: spin earth.rotation.y, place satellites with orbitAt
const earthCanvas = (() => { const [c, g] = kCanvas(1024, 512); g.fillStyle = '#2f78c4'; g.fillRect(0, 0, 1024, 512); const r = P.rng(5);
  for (let i = 0; i < 26; i++) { const x = r() * 1024, y = 90 + r() * 330, s = 30 + r() * 90; g.fillStyle = i % 4 ? '#5fae4e' : '#c9b06a'; g.beginPath();
    for (let k = 0; k < 12; k++) { const a = k / 12 * Math.PI * 2, rr = s * (0.6 + 0.5 * r()); g.lineTo(x + Math.cos(a) * rr, y + Math.sin(a) * rr * 0.7); } g.fill(); }
  g.fillStyle = '#f4f6fa'; g.fillRect(0, 0, 1024, 34); g.fillRect(0, 478, 1024, 34); return c; })();
const earth = (x, y, z, r = 6) => add(new THREE.SphereGeometry(r, 48, 32), toon({ map: P.tex(earthCanvas) }), x, y, z, scene, { cast: false });
const satellite = (slug = null) => { const g = new THREE.Group(); scene.add(g); add(new THREE.BoxGeometry(0.7, 0.7, 0.9), KM.gold, 0, 0, 0, g);
  for (const s of [-1, 1]) add(new THREE.BoxGeometry(1.6, 0.05, 0.6), KC('#2f4f8f'), s * 1.2, 0, 0, g);
  add(new THREE.ConeGeometry(0.25, 0.4, 12), KM.white, 0, 0.5, 0, g); if (slug) add(new THREE.BoxGeometry(0.5, 0.5, 0.02), signMat('', { slug, border: false, w: 256, h: 256 }), 0, 0, 0.46, g); return g; };
const orbitAt = (obj, centre, radius, angle, tilt = 0.35) => obj.position.set(centre[0] + Math.cos(angle) * radius, centre[1] + Math.sin(angle) * radius * Math.sin(tilt), centre[2] + Math.sin(angle) * radius * Math.cos(tilt));
// ===== end of the GOLIDE world kit =====
// ===== GOLIDE indoor kit (2026-11-22, from the owner's Shorts models: Afterhour Theory, Ricks Clips): ready rooms =====
// room(x, z, w, d, h, opts) builds an open-front box room (floor, back wall, side walls, ceiling with light panels) and
// returns { group, floorY, back, left, right }; opts: floor 'tiles' | 'wood' | 'carpet' | 'checker' | 'concrete',
// wall colour, ceiling true, lights n. Furniture: deskSet, officeRows, slotMachine, slotRow, roulette, coinPile,
// cellBars, bunkBed, wallClock, wallScreen, pottedPlant, counter. All stand on DECK unless given y.
const floorTex = (kind) => { const [c, g] = kCanvas(256, 256);
  if (kind === 'checker') { for (let y = 0; y < 4; y++) for (let x = 0; x < 4; x++) { g.fillStyle = (x + y) % 2 ? '#3d4a42' : '#cfd6cc'; g.fillRect(x * 64, y * 64, 64, 64); } }
  else if (kind === 'carpet') { g.fillStyle = '#8e1f2a'; g.fillRect(0, 0, 256, 256); g.strokeStyle = '#e2b23c'; g.lineWidth = 5;
    for (let y = 32; y < 256; y += 64) for (let x = 32; x < 256; x += 64) { g.beginPath(); g.arc(x, y, 18, 0, 7); g.stroke(); g.fillStyle = '#6f1520'; g.fillRect(x - 4, y - 4, 8, 8); } }
  else if (kind === 'wood') { const r = P.rng(7); for (let y = 0; y < 256; y += 32) { g.fillStyle = ['#b98a5a', '#a87a4c', '#c39668'][Math.floor(r() * 3)]; g.fillRect(0, y, 256, 31); g.fillStyle = '#7a5434'; g.fillRect(0, y + 31, 256, 1); } }
  else if (kind === 'concrete') { g.fillStyle = '#b9b6ad'; g.fillRect(0, 0, 256, 256); const r = P.rng(3); for (let i = 0; i < 400; i++) { g.fillStyle = r() > .5 ? '#a9a69e' : '#c6c3ba'; g.fillRect(r() * 256, r() * 256, 3, 3); } }
  else { g.fillStyle = '#d9dcd6'; g.fillRect(0, 0, 256, 256); g.strokeStyle = '#b8bcb5'; g.lineWidth = 3; for (let k = 0; k <= 256; k += 64) { g.beginPath(); g.moveTo(k, 0); g.lineTo(k, 256); g.moveTo(0, k); g.lineTo(256, k); g.stroke(); } }
  return c; };
const room = (x, z, w, d, h, opts = {}) => { const { floor = 'tiles', wall = '#e9e4da', ceiling = true, lights = 3, trim = '#c9c2b3' } = opts;
  const grp = new THREE.Group(); grp.position.set(x, DECK, z); scene.add(grp); const wm = KC(wall);
  const fl = add(new THREE.PlaneGeometry(w, d), toon({ map: P.tex(floorTex(floor), w / 3, d / 3) }), 0, 0.01, 0, grp, { cast: false }); fl.rotation.x = -Math.PI / 2;
  add(new THREE.BoxGeometry(w, h, 0.3), wm, 0, h / 2, -d / 2, grp);
  add(new THREE.BoxGeometry(0.3, h, d), wm, -w / 2, h / 2, 0, grp); add(new THREE.BoxGeometry(0.3, h, d), wm, w / 2, h / 2, 0, grp);
  add(new THREE.BoxGeometry(w, 0.35, 0.34), KC(trim), 0, 0.17, -d / 2 + 0.02, grp);                       // skirting
  if (ceiling) { add(new THREE.BoxGeometry(w, 0.3, d), KC('#f3f1ec'), 0, h, 0, grp, { cast: false });
    for (let i = 0; i < lights; i++) for (const zz of [-d / 4, d / 6]) add(new THREE.BoxGeometry(2.2, 0.06, 0.7), toon({ color: '#ffffff', emissive: '#fff8e8', emissiveIntensity: 0.9 }), -w / 2 + (i + 0.5) * w / lights, h - 0.18, zz, grp, { cast: false }); }
  return { group: grp, floorY: DECK, back: -d / 2 + 0.16, left: -w / 2 + 0.16, right: w / 2 - 0.16 }; };
const screenTex = (kind = 'code', text = '') => { const [c, g] = kCanvas(512, 320); g.fillStyle = '#0f1a2a'; g.fillRect(0, 0, 512, 320);
  if (kind === 'code') { const r = P.rng(text.length + 4); for (let y = 24; y < 300; y += 22) { let x = 24 + (r() * 3 | 0) * 22; while (x < 470 && r() > 0.12) { const len = 20 + r() * 70; g.fillStyle = ['#7ee0a1', '#8fc4ff', '#ffd27a', '#e8eef7'][r() * 4 | 0]; g.fillRect(x, y, len, 9); x += len + 12; } } }
  else if (kind === 'chart') { g.strokeStyle = '#3fe08a'; g.lineWidth = 10; g.beginPath(); [[30, 260], [130, 210], [220, 230], [320, 140], [400, 160], [480, 50]].forEach(([a, b], i) => i ? g.lineTo(a, b) : g.moveTo(a, b)); g.stroke(); }
  else if (kind === 'down') { g.strokeStyle = '#ff4d4d'; g.lineWidth = 10; g.beginPath(); [[30, 60], [130, 110], [220, 90], [320, 200], [400, 180], [480, 280]].forEach(([a, b], i) => i ? g.lineTo(a, b) : g.moveTo(a, b)); g.stroke(); }
  if (text) { let fs = 64; g.font = `900 ${fs}px sans-serif`; while (g.measureText(text).width > 460 && fs > 20) { fs -= 4; g.font = `900 ${fs}px sans-serif`; }
    const ty = kind === 'code' ? 250 : 160, tw = g.measureText(text).width;
    if (kind === 'code') { g.fillStyle = '#0f1a2aee'; g.fillRect(256 - tw / 2 - 20, ty - fs * 0.7, tw + 40, fs * 1.4); }   // a plate: words never sit on code lines
    g.fillStyle = kind === 'jackpot' ? '#ffd23f' : '#ffffff'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(text, 256, ty); }
  return toon({ map: kTex(c), emissive: '#ffffff', emissiveMap: kTex(c), emissiveIntensity: 0.55 }); };
const pottedPlant = (x, z, s = 1, parent = scene, y = DECK) => { const g = new THREE.Group(); g.position.set(x, y, z); g.scale.setScalar(s); parent.add(g);
  add(new THREE.CylinderGeometry(0.22, 0.17, 0.4, 12), KC('#c86f3d'), 0, 0.2, 0, g); for (let i = 0; i < 6; i++) { const l = add(new THREE.SphereGeometry(0.18, 8, 6), KC(i % 2 ? '#4f9a46' : '#6cbf55'), Math.cos(i) * 0.14, 0.55 + (i % 3) * 0.12, Math.sin(i) * 0.14, g); l.scale.set(1, 1.6, 0.6); l.rotation.z = Math.cos(i * 2) * 0.6; } return g; };
const deskSet = (x, z, ry = 0, opts = {}) => { const { screen = 'code', text = '', plant = true, chair = true, colour = '#e9e3d6' } = opts;
  const g = new THREE.Group(); g.position.set(x, DECK, z); g.rotation.y = ry; scene.add(g); const top = KC(colour), leg = KM.steel;
  add(new THREE.BoxGeometry(2.4, 0.1, 1.1), top, 0, 1.05, 0, g); for (const [a, b] of [[-1.1, -0.45], [1.1, -0.45], [-1.1, 0.45], [1.1, 0.45]]) add(new THREE.BoxGeometry(0.08, 1.0, 0.08), leg, a, 0.5, b, g);
  add(new THREE.BoxGeometry(1.3, 0.8, 0.06), KM.dark, 0, 1.6, -0.3, g); add(new THREE.BoxGeometry(1.2, 0.7, 0.02), screenTex(screen, text), 0, 1.6, -0.265, g);
  add(new THREE.BoxGeometry(0.12, 0.35, 0.12), KM.dark, 0, 1.25, -0.32, g); add(new THREE.BoxGeometry(0.8, 0.04, 0.28), KM.dark, 0, 1.12, 0.15, g);
  if (plant) pottedPlant(0.95, -0.25, 0.7, g, 1.1);
  if (chair) { const ch = new THREE.Group(); ch.position.set(0, 0, 0.95); g.add(ch); add(new THREE.BoxGeometry(0.8, 0.12, 0.75), KC('#3b5b8f'), 0, 0.75, 0, ch); add(new THREE.BoxGeometry(0.8, 0.9, 0.1), KC('#3b5b8f'), 0, 1.25, 0.33, ch); add(new THREE.CylinderGeometry(0.05, 0.05, 0.7, 8), leg, 0, 0.38, 0, ch); }
  return g; };
const officeRows = (x0, z0, cols = 3, rows = 2, gap = [3.2, 3.0], opts = {}) => { const out = []; for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++)
  out.push(deskSet(x0 + c * gap[0], z0 - r * gap[1], 0, { screen: ['code', 'chart', 'code'][(r + c) % 3], plant: (r + c) % 2 === 0, ...opts })); return out; };
const wallClock = (x, y, z, r = 0.45, parent = scene) => { const g = new THREE.Group(); g.position.set(x, y, z); parent.add(g);
  const face = add(new THREE.CylinderGeometry(r, r, 0.08, 32), KM.white, 0, 0, 0, g); face.rotation.x = Math.PI / 2;
  const rim = add(new THREE.TorusGeometry(r, 0.05, 8, 32), KM.dark, 0, 0, 0.04, g);
  g.hand = add(new THREE.BoxGeometry(0.04, r * 0.75, 0.02), KM.dark, 0, r * 0.3, 0.06, g); g.hand.geometry.translate(0, r * 0.08, 0); return g; };
const wallScreen = (text, x, y, z, w = 4, h = 2.3, kind = 'chart', parent = scene) => { const b = add(new THREE.BoxGeometry(w, h, 0.12), [KM.dark, KM.dark, KM.dark, KM.dark, screenTex(kind, text), KM.dark], x, y, z, parent); return b; };
const counter = (x, z, w = 4, ry = 0, colour = '#6b4b8f') => { const g = new THREE.Group(); g.position.set(x, DECK, z); g.rotation.y = ry; scene.add(g);
  add(new THREE.BoxGeometry(w, 1.1, 0.9), KC(colour), 0, 0.55, 0, g); add(new THREE.BoxGeometry(w + 0.2, 0.1, 1.1), KM.gold, 0, 1.15, 0, g); return g; };
// casino: slot machines with a reel window and a lit JACKPOT topper, a roulette wheel, red-and-gold carpet (room floor 'carpet')
const slotMachine = (x, z, ry = 0, opts = {}) => { const { colour = '#d23b4a', top = 'JACKPOT', reels = '7 7 7' } = opts;
  const g = new THREE.Group(); g.position.set(x, DECK, z); g.rotation.y = ry; scene.add(g); const body = KC(colour);
  add(new THREE.BoxGeometry(1.1, 1.9, 0.9), body, 0, 0.95, 0, g); add(new THREE.BoxGeometry(1.15, 0.12, 0.95), KM.gold, 0, 1.92, 0, g);
  const reelMats = [reels, '7 BAR 7', 'BAR 7 BAR', '$ $ 7', '7 $ BAR'].map((t) => screenTex('reels', t));
  const reelWin = add(new THREE.BoxGeometry(0.9, 0.45, 0.04), reelMats[0], 0, 1.35, 0.46, g);
  g.spin = (f, stopAt = 1e9) => { reelWin.material = f >= stopAt ? reelMats[0] : reelMats[1 + (Math.floor(f / 2) % 4)]; };   // reels roll, then land on `reels`
  g.pull = (k) => { arm.rotation.x = -0.9 * k; };                                                                         // lever 0..1
  add(new THREE.BoxGeometry(1.05, 0.5, 0.5), screenTex('jackpot', top), 0, 2.25, 0.1, g);
  add(new THREE.BoxGeometry(1.0, 0.1, 0.35), KM.dark, 0, 0.95, 0.55, g);
  const armG = new THREE.Group(); armG.position.set(0.62, 1.05, 0); g.add(armG); add(new THREE.CylinderGeometry(0.04, 0.04, 0.8, 8), KM.steel, 0, 0.4, 0, armG); add(new THREE.SphereGeometry(0.1, 12, 8), KM.red, 0, 0.8, 0, armG); const arm = armG; g.arm = armG;
  const stool = add(new THREE.CylinderGeometry(0.32, 0.32, 0.12, 16), KC('#c7322e'), 0, 0.75, 1.0, g); add(new THREE.CylinderGeometry(0.05, 0.05, 0.75, 8), KM.steel, 0, 0.37, 1.0, g);
  return g; };
const slotRow = (x0, z, n = 5, gap = 1.25, ry = 0) => { const c = ['#d23b4a', '#3b6fd2', '#e2a52c', '#8a3bd2', '#2cae6e']; const out = [];
  for (let i = 0; i < n; i++) out.push(slotMachine(x0 + i * gap, z, ry, { colour: c[i % c.length] })); return out; };
const roulette = (x, z, r = 1.6) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g);
  add(new THREE.CylinderGeometry(r * 1.25, r * 1.3, 1.0, 40), KC('#6b3a1f'), 0, 0.5, 0, g);
  const [c, gg] = kCanvas(512, 512); gg.translate(256, 256); for (let i = 0; i < 37; i++) { gg.fillStyle = i === 0 ? '#1f8a3c' : i % 2 ? '#c7322e' : '#17161b'; gg.beginPath(); gg.moveTo(0, 0); gg.arc(0, 0, 250, i / 37 * 6.283, (i + 1) / 37 * 6.283); gg.fill(); }
  gg.fillStyle = '#e9b43a'; gg.beginPath(); gg.arc(0, 0, 120, 0, 7); gg.fill(); gg.fillStyle = '#b07d22'; gg.beginPath(); gg.arc(0, 0, 60, 0, 7); gg.fill();
  const wheel = add(new THREE.CylinderGeometry(r, r, 0.12, 48), [KM.gold, toon({ map: kTex(c) }), KM.gold], 0, 1.06, 0, g); g.wheel = wheel;
  const spindle = add(new THREE.CylinderGeometry(0.08, 0.12, 0.6, 12), KM.gold, 0, 1.35, 0, g); for (let k = 0; k < 4; k++) { const b = add(new THREE.CylinderGeometry(0.05, 0.05, 0.9, 8), KM.gold, 0, 1.55, 0, g); b.rotation.z = Math.PI / 2; b.rotation.y = k * Math.PI / 2; }
  g.ball = add(new THREE.SphereGeometry(0.09, 12, 8), KM.white, r * 0.8, 1.16, 0, g); return g; };
// a pile of gold coins (heaped discs), for treasure, a dragon's hoard or a rich man's swim
const coinM = toon({ color: '#e9b43a' }), coinEdge = toon({ color: '#c78f24' });
const coinPile = (x, z, r = 4, h = 1.6, seed = 9) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); const rr = P.rng(seed);
  const mound = add(new THREE.SphereGeometry(r, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2), coinM, 0, 0, 0, g); mound.scale.y = h / r;
  for (let i = 0; i < 220; i++) { const a = rr() * 6.283, d = Math.sqrt(rr()) * r * 0.98, yy = h * Math.sqrt(Math.max(0, 1 - (d / r) ** 2));
    const c = add(new THREE.CylinderGeometry(0.22, 0.22, 0.05, 14), [coinEdge, coinM, coinM], Math.cos(a) * d, yy + 0.02, Math.sin(a) * d, g, { cast: false }); c.rotation.set((rr() - 0.5) * 1.2, rr() * 6, (rr() - 0.5) * 1.2); }
  return g; };
// prison: a cell front of bars (door can slide: .door.position.x), a bunk bed, a toilet block
const cellBars = (x, z, w = 4, h = 3.2, ry = 0, colour = '#62c7c0') => { const g = new THREE.Group(); g.position.set(x, DECK, z); g.rotation.y = ry; scene.add(g); const m = KC(colour);
  add(new THREE.BoxGeometry(w, 0.14, 0.14), m, 0, h, 0, g); add(new THREE.BoxGeometry(w, 0.14, 0.14), m, 0, 0.07, 0, g);
  for (let i = 0; i <= Math.round(w / 0.34); i++) if (i % 7 !== 3) add(new THREE.CylinderGeometry(0.045, 0.045, h, 8), m, -w / 2 + i * 0.34, h / 2, 0, g);
  const door = new THREE.Group(); g.add(door); for (let k = 0; k < 4; k++) add(new THREE.CylinderGeometry(0.045, 0.045, h, 8), m, 0.85 + k * 0.3, h / 2, 0.12, door);
  add(new THREE.BoxGeometry(1.1, 0.12, 0.08), m, 1.3, h * 0.5, 0.12, door); g.door = door; return g; };
const bunkBed = (x, z, ry = 0) => { const g = new THREE.Group(); g.position.set(x, DECK, z); g.rotation.y = ry; scene.add(g); const f = KC('#5e6d7a');
  for (const [a, b] of [[-1.05, -0.45], [1.05, -0.45], [-1.05, 0.45], [1.05, 0.45]]) add(new THREE.BoxGeometry(0.08, 2.4, 0.08), f, a, 1.2, b, g);
  for (const y of [0.5, 1.7]) { add(new THREE.BoxGeometry(2.2, 0.08, 1.0), f, 0, y, 0, g); add(new THREE.BoxGeometry(2.0, 0.2, 0.9), KC('#e8e4da'), 0, y + 0.14, 0, g);
    add(new THREE.BoxGeometry(2.0, 0.1, 0.9), KC(y < 1 ? '#c7322e' : '#3b5b8f'), 0.2, y + 0.27, 0, g); } return g; };
// ===== end of the GOLIDE indoor kit =====
// ===== GOLIDE indoor kit, batch 2 (2026-11-22): spaceship, ship deck, tent, street traffic, banners =====
// spaceCabin(x, z, w, d, h): a dark cabin with panel walls, lit consoles, two seats and a big window onto stars (and the
// Earth, opts.earth). shipDeck(x, z, name, opts): a liner's deck and hull with its NAME on the bow, funnels, railings,
// lifeboats; ship.group.position/rotation can tilt it (sinking). tentRoom(x, z, w, d): canvas walls and a rug.
// car(colour) / bus(colour, name) / busStop(x, z) / trafficLight(x, z): move cars and buses with .position over time.
// banners(x, z, n, colour, emblem): a row of tall flags (armies, rallies, a company's campus).
const starTex = (() => { const [c, g] = kCanvas(1024, 512); g.fillStyle = '#05070f'; g.fillRect(0, 0, 1024, 512); const r = P.rng(12);
  for (let i = 0; i < 500; i++) { g.fillStyle = r() > 0.85 ? '#ffe9b0' : '#ffffff'; const s = r() * 2.4; g.fillRect(r() * 1024, r() * 512, s, s); } return c; })();
const spaceCabin = (x, z, w = 12, d = 9, h = 4.2, opts = {}) => { const grp = new THREE.Group(); grp.position.set(x, DECK, z); scene.add(grp);
  const panel = (() => { const [c, g] = kCanvas(256, 256); g.fillStyle = '#d9dde3'; g.fillRect(0, 0, 256, 256); g.strokeStyle = '#9aa2ad'; g.lineWidth = 6; g.strokeRect(8, 8, 240, 240);
    g.fillStyle = '#b8bfc9'; for (let k = 0; k < 4; k++) g.fillRect(30 + k * 52, 200, 30, 12); return toon({ map: P.tex(c, w / 3, h / 3) }); })();
  const fl = add(new THREE.PlaneGeometry(w, d), KC('#4a4f5a'), 0, 0.01, 0, grp, { cast: false }); fl.rotation.x = -Math.PI / 2;
  add(new THREE.BoxGeometry(0.3, h, d), panel, -w / 2, h / 2, 0, grp); add(new THREE.BoxGeometry(0.3, h, d), panel, w / 2, h / 2, 0, grp);
  add(new THREE.BoxGeometry(w, 0.3, d), panel, 0, h, 0, grp, { cast: false });
  const wall = new THREE.Group(); wall.position.set(0, 0, -d / 2); grp.add(wall);              // the back wall around a big window
  add(new THREE.BoxGeometry(w, 0.9, 0.3), panel, 0, 0.45, 0, wall); add(new THREE.BoxGeometry(w, 0.7, 0.3), panel, 0, h - 0.35, 0, wall);
  add(new THREE.BoxGeometry(1.2, h, 0.3), panel, -w / 2 + 0.6, h / 2, 0, wall); add(new THREE.BoxGeometry(1.2, h, 0.3), panel, w / 2 - 0.6, h / 2, 0, wall);
  const sky = add(new THREE.PlaneGeometry(300, 160), new THREE.MeshBasicMaterial({ map: kTex(starTex) }), 0, h / 2, -60, grp, { cast: false }); sky.userData.ndSkip = true;
  if (opts.earth !== false) earth(x - 8, DECK + 2, z - d / 2 - 40, 14);
  for (const s of [-1, 1]) { add(new THREE.BoxGeometry(2.6, 1.0, 1.0), KC('#2b2d34'), s * 2.2, 0.5, -d / 2 + 1.0, grp);
    add(new THREE.BoxGeometry(2.4, 0.06, 0.8), screenTex(s < 0 ? 'chart' : 'code', ''), s * 2.2, 1.03, -d / 2 + 1.0, grp);
    for (let k = 0; k < 5; k++) add(new THREE.BoxGeometry(0.16, 0.08, 0.16), toon({ color: ['#ff4d4d', '#3fe08a', '#ffd23f'][k % 3], emissive: ['#ff4d4d', '#3fe08a', '#ffd23f'][k % 3], emissiveIntensity: 0.8 }), s * 2.2 - 0.8 + k * 0.4, 1.05, -d / 2 + 1.42, grp);
    const seat = new THREE.Group(); seat.position.set(s * 2.2, 0, -d / 2 + 2.6); grp.add(seat); add(new THREE.BoxGeometry(1.0, 0.2, 0.9), KC('#e2a52c'), 0, 0.8, 0, seat); add(new THREE.BoxGeometry(1.0, 1.4, 0.2), KC('#e2a52c'), 0, 1.5, 0.45, seat); add(new THREE.CylinderGeometry(0.12, 0.12, 0.8, 8), KM.steel, 0, 0.4, 0, seat); }
  return { group: grp, back: -d / 2 + 0.2 }; };
const shipDeck = (x, z, name = 'TITANIC', opts = {}) => { const { hull = '#1b1c22', deck = '#b08a5a', funnels = 4 } = opts; const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g);
  const L = 60, Wd = 10; add(new THREE.BoxGeometry(L, 6, Wd), KC(hull), 0, -3, 0, g); add(new THREE.BoxGeometry(L, 0.6, Wd), KC('#c7322e'), 0, -6.0, 0, g);
  const nm = signMat(name, { bg: hull, fg: '#e9b43a', border: false, w: 1024, h: 256 }); add(new THREE.BoxGeometry(8, 2, 0.05), nm, L / 2 - 7, -1.6, Wd / 2 + 0.03, g);
  for (let i = 0; i < 18; i++) add(new THREE.CylinderGeometry(0.22, 0.22, 0.06, 12), KC('#e8e4da'), -L / 2 + 4 + i * 3, -1.6, Wd / 2 + 0.02, g).rotation.x = Math.PI / 2;
  const dk = add(new THREE.PlaneGeometry(L, Wd), toon({ map: P.tex(floorTex('wood'), L / 3, Wd / 3) }), 0, 0.01, 0, g, { cast: false }); dk.rotation.x = -Math.PI / 2;
  add(new THREE.BoxGeometry(L * 0.55, 3, Wd * 0.6), KC('#f1efe8'), -4, 1.5, -1, g);
  for (let i = 0; i < funnels; i++) { add(new THREE.CylinderGeometry(1.1, 1.2, 6, 20), KC('#e9b43a'), -16 + i * 7, 6, -1, g); add(new THREE.CylinderGeometry(1.15, 1.15, 1.4, 20), KC('#17161b'), -16 + i * 7, 8.4, -1, g); }
  for (const s of [-1, 1]) for (let i = 0; i < 30; i++) add(new THREE.BoxGeometry(0.06, 1.0, 0.06), KM.white, -L / 2 + 1 + i * 2, 0.5, s * (Wd / 2 - 0.1), g);
  for (const s of [-1, 1]) add(new THREE.BoxGeometry(L, 0.08, 0.08), KM.white, 0, 1.0, s * (Wd / 2 - 0.1), g);
  for (let i = 0; i < 4; i++) { const b = add(new THREE.CapsuleGeometry(0.6, 2.4, 4, 10), KM.white, -14 + i * 6, 3.6, Wd * 0.3 + 0.9, g); b.rotation.z = Math.PI / 2; }
  return { group: g, deckY: DECK, front: Wd / 2 }; };
const tentRoom = (x, z, w = 10, d = 8, h = 4.5) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); const cv = KC('#d8c9a3'), cvD = KC('#b9a77e');
  const fl = add(new THREE.PlaneGeometry(w, d), toon({ map: P.tex(floorTex('carpet'), 2, 2) }), 0, 0.02, 0, g, { cast: false }); fl.rotation.x = -Math.PI / 2;
  const roofL = add(new THREE.PlaneGeometry(d, Math.hypot(w / 2, h * 0.45)), cv, -w / 4, h * 0.78, 0, g); roofL.rotation.set(0, Math.PI / 2, 0); roofL.rotation.x = 0;
  for (const s of [-1, 1]) { const r = add(new THREE.BoxGeometry(w / 2 + 0.4, 0.1, d), s < 0 ? cv : cvD, s * w / 4, h * 0.8, 0, g); r.rotation.z = -s * 0.42; }
  add(new THREE.BoxGeometry(w, h * 0.62, 0.15), cvD, 0, h * 0.31, -d / 2, g); for (const s of [-1, 1]) add(new THREE.BoxGeometry(0.15, h * 0.62, d), cv, s * w / 2, h * 0.31, 0, g);
  add(new THREE.CylinderGeometry(0.1, 0.1, h * 1.02, 8), KC('#6b4a2a'), 0, h * 0.51, -d / 2 + 0.4, g); return g; };
const car = (col = '#2f78c4') => { const g = new THREE.Group(); scene.add(g); const b = KC(col);
  add(new THREE.BoxGeometry(3.8, 0.8, 1.7), b, 0, 0.7, 0, g); add(new THREE.BoxGeometry(2.0, 0.7, 1.5), b, -0.2, 1.4, 0, g); add(new THREE.BoxGeometry(1.9, 0.5, 1.52), KM.glass, -0.2, 1.45, 0, g);
  for (const [a, c] of [[1.2, 0.85], [1.2, -0.85], [-1.2, 0.85], [-1.2, -0.85]]) { const w = add(new THREE.CylinderGeometry(0.38, 0.38, 0.3, 16), KM.dark, a, 0.38, c, g); w.rotation.x = Math.PI / 2; } return g; };
const bus = (col = '#f2c230', name = 'CITY') => { const g = new THREE.Group(); scene.add(g); const b = KC(col);
  add(new THREE.BoxGeometry(10, 2.8, 2.5), b, 0, 1.9, 0, g); add(new THREE.BoxGeometry(9.6, 0.9, 2.52), KM.glass, 0, 2.5, 0, g); add(new THREE.BoxGeometry(10.02, 0.3, 2.52), KC('#c7322e'), 0, 1.2, 0, g);
  add(new THREE.BoxGeometry(3, 0.5, 0.02), signMat(name, { bg: '#17161b', fg: '#ffd23f', border: false, w: 768, h: 128 }), 3.2, 3.05, 1.27, g);
  for (const [a, c] of [[3.4, 1.15], [3.4, -1.15], [-3.4, 1.15], [-3.4, -1.15]]) { const w = add(new THREE.CylinderGeometry(0.5, 0.5, 0.35, 16), KM.dark, a, 0.5, c, g); w.rotation.x = Math.PI / 2; } return g; };
const busStop = (x, z, ry = 0) => { const g = new THREE.Group(); g.position.set(x, DECK, z); g.rotation.y = ry; scene.add(g);
  add(new THREE.CylinderGeometry(0.07, 0.07, 3, 8), KM.steel, 0, 1.5, 0, g); add(new THREE.BoxGeometry(1.2, 0.5, 0.08), signMat('BUS STOP', { bg: '#2f5fb8', fg: '#ffffff', w: 768, h: 256 }), 0, 2.8, 0.05, g);
  add(new THREE.BoxGeometry(2.6, 0.1, 0.6), KM.dark, 1.6, 0.6, -0.4, g); return g; };
const trafficLight = (x, z, on = 'red') => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); add(new THREE.CylinderGeometry(0.08, 0.08, 3.2, 8), KM.dark, 0, 1.6, 0, g);
  add(new THREE.BoxGeometry(0.5, 1.3, 0.4), KM.dark, 0, 3.5, 0, g); g.lamps = {};
  for (const [k, c, y] of [['red', '#ff3b30', 3.9], ['amber', '#ffb020', 3.5], ['green', '#3fe08a', 3.1]]) g.lamps[k] = add(new THREE.SphereGeometry(0.14, 12, 8), toon({ color: c, emissive: c, emissiveIntensity: k === on ? 1.2 : 0.05 }), 0, y, 0.21, g);
  return g; };
const banners = (x, z, n = 6, colour = '#f2c230', emblem = '') => { const out = []; for (let i = 0; i < n; i++) { const g = new THREE.Group(); g.position.set(x + i * 1.6, DECK, z - (i % 2) * 0.8); scene.add(g);
  add(new THREE.CylinderGeometry(0.05, 0.05, 5, 8), KC('#6b4a2a'), 0, 2.5, 0, g); add(new THREE.ConeGeometry(0.12, 0.3, 8), KM.steel, 0, 5.1, 0, g);
  add(new THREE.BoxGeometry(1.1, 1.6, 0.04), signMat(emblem, { bg: colour, fg: '#17161b', w: 256, h: 384 }), 0.6, 4.1, 0, g); out.push(g); } return out; };
// ===== end of batch 2 =====
// ===== GOLIDE indoor kit, batch 3 (2026-11-22): courtroom, hospital ward, data centre, classroom, news desk, stage =====
// courtroom(x, z): judge's raised bench with a gavel, witness box, two counsel tables, flags. hospitalWard(x, z, beds):
// beds with pillows and blankets, drip stands, curtains, a heart monitor. dataCentre(x, z, rows, len): aisles of server
// racks with blinking lights (call .blink(f) every frame). classroom(x, z): blackboard with words, rows of school desks.
// newsDesk(x, z, title): a curved anchor desk with a big screen behind. stage(x, z, slug, title): a raised stage, a podium
// with the brand's logo, spotlights and a giant screen. Each returns { group } (and extras named below).
const courtroom = (x, z) => { const r = room(x, z, 16, 12, 5.5, { floor: 'wood', wall: '#8a5a33', lights: 3, trim: '#5a3a24' }); const g = r.group, wd = KC('#6b3f22'), wd2 = KC('#8a5a33');
  // the judge stands on a dais behind a chest-high bench: place the judge card at y = DECK + 1.0, z = -5.3
  add(new THREE.BoxGeometry(6, 1.0, 2.0), wd2, 0, 0.5, -5.2, g);
  add(new THREE.BoxGeometry(6, 1.55, 1.2), wd, 0, 0.78, -4.0, g); add(new THREE.BoxGeometry(6.4, 0.15, 1.5), wd2, 0, 1.6, -4.0, g);
  add(new THREE.BoxGeometry(1.4, 0.7, 0.06), signMat('COURT', { bg: '#e9b43a', fg: '#5a3a24', border: false, w: 512, h: 256 }), 0, 3.6, -5.8, g);
  const gavel = add(new THREE.CylinderGeometry(0.12, 0.12, 0.5, 12), wd2, 1.4, 1.8, -3.8, g); gavel.rotation.z = Math.PI / 2;
  add(new THREE.BoxGeometry(2.2, 1.3, 1.6), wd, 4.6, 0.65, -2.6, g);
  for (const s_ of [-1, 1]) { add(new THREE.BoxGeometry(3.4, 0.12, 1.4), wd2, s_ * 3.6, 1.05, 1.6, g); for (const a of [-1.5, 1.5]) add(new THREE.BoxGeometry(0.12, 1.0, 1.2), wd, s_ * 3.6 + a, 0.5, 1.6, g); }
  for (const [s_, c] of [[-1, '#2f5fb8'], [1, '#c7322e']]) { add(new THREE.CylinderGeometry(0.05, 0.05, 3.6, 8), KM.gold, s_ * 6.6, 1.8, -5.2, g); add(new THREE.BoxGeometry(1.0, 1.4, 0.04), KC(c), s_ * 6.6 + 0.55, 2.9, -5.2, g); }
  return { group: g, gavel }; };
const hospitalWard = (x, z, beds = 3) => { const r = room(x, z, 16, 11, 4.2, { floor: 'tiles', wall: '#dfeee9', lights: 3, trim: '#9fc9bd' }); const g = r.group;
  for (let i = 0; i < beds; i++) { const bx = -5 + i * 5; add(new THREE.BoxGeometry(2.0, 0.6, 3.6), KC('#e8e8e8'), bx, 0.9, -2.4, g); add(new THREE.BoxGeometry(2.0, 0.25, 3.0), KC('#9fc3e6'), bx, 1.3, -2.1, g);
    add(new THREE.BoxGeometry(1.4, 0.3, 0.6), KM.white, bx, 1.35, -3.8, g); add(new THREE.BoxGeometry(2.1, 1.2, 0.1), KM.steel, bx, 1.2, -4.25, g);
    for (const [a, b] of [[-0.9, -4.1], [0.9, -4.1], [-0.9, -0.7], [0.9, -0.7]]) add(new THREE.CylinderGeometry(0.05, 0.05, 0.6, 8), KM.steel, bx + a, 0.3, b, g);
    add(new THREE.CylinderGeometry(0.03, 0.03, 2.4, 8), KM.steel, bx + 1.4, 1.2, -3.4, g); add(new THREE.BoxGeometry(0.3, 0.45, 0.1), KC('#bfe3ff'), bx + 1.4, 2.3, -3.4, g);
    if (i < beds - 1) add(new THREE.BoxGeometry(0.08, 2.6, 3.4), KC('#9fc9bd'), bx + 2.5, 1.5, -2.4, g); }
  const mon = add(new THREE.BoxGeometry(1.0, 0.7, 0.1), screenTex('chart', ''), -6.8, 2.4, -4.6, g); return { group: g, monitor: mon }; };
const dataCentre = (x, z, rows = 2, len = 6) => { const r = room(x, z, 14, 18, 4.5, { floor: 'checker', wall: '#d9dde3', lights: 4 }); const g = r.group, lights = [];
  for (let rw = 0; rw < rows; rw++) for (let i = 0; i < len; i++) for (const s_ of [-1, 1]) { const rx = s_ * (1.8 + rw * 3.6), rz = 5 - i * 1.4;
    add(new THREE.BoxGeometry(1.0, 3.2, 1.2), KC('#1d2027'), rx, 1.6, rz, g);
    for (let k = 0; k < 8; k++) { const m = toon({ color: '#3fe08a', emissive: '#3fe08a', emissiveIntensity: 1 }); lights.push(m); add(new THREE.BoxGeometry(0.06, 0.06, 0.06), m, rx - s_ * 0.52, 0.5 + k * 0.33, rz + ((k * 7) % 5 - 2) * 0.18, g); } }
  return { group: g, blink: (f) => lights.forEach((m, k) => { m.emissiveIntensity = ((f + k * 7) % 23) < 3 ? 0.05 : 1; m.color.set(((f + k * 11) % 97) < 2 ? '#ff4d4d' : '#3fe08a'); m.emissive.copy(m.color); }) }; };
const classroom = (x, z, words = '') => { const r = room(x, z, 16, 12, 4.4, { floor: 'wood', wall: '#efe4c8', lights: 3 }); const g = r.group;
  add(new THREE.BoxGeometry(7, 2.6, 0.1), KC('#7a5434'), 0, 2.5, -5.75, g);
  add(new THREE.BoxGeometry(6.6, 2.2, 0.06), signMat(words, { bg: '#2f5a44', fg: '#f4f1ea', border: false, w: 1024, h: 340 }), 0, 2.5, -5.68, g);
  for (let rw = 0; rw < 3; rw++) for (let c = 0; c < 4; c++) { const dx = -4.5 + c * 3, dz = -2 + rw * 2.2; add(new THREE.BoxGeometry(1.6, 0.08, 0.9), KC('#c39668'), dx, 1.0, dz, g);
    for (const [a, b] of [[-0.7, -0.35], [0.7, -0.35], [-0.7, 0.35], [0.7, 0.35]]) add(new THREE.BoxGeometry(0.06, 1.0, 0.06), KM.steel, dx + a, 0.5, dz + b, g); }
  add(new THREE.BoxGeometry(2.4, 1.1, 1.0), KC('#8a5a33'), -5.6, 0.55, -4.2, g); return { group: g }; };
const newsDesk = (x, z, title = 'BREAKING NEWS') => { const r = room(x, z, 14, 10, 5, { floor: 'concrete', wall: '#1d2a44', lights: 3, trim: '#c7322e' }); const g = r.group;
  const desk = add(new THREE.CylinderGeometry(3.2, 3.2, 1.2, 40, 1, false, Math.PI * 0.75, Math.PI * 0.5), KC('#2f78c4'), 0, 0.6, 1.2, g); desk.rotation.y = Math.PI;
  add(new THREE.BoxGeometry(9, 4, 0.1), screenTex('chart', title), 0, 2.8, -4.7, g);
  add(new THREE.BoxGeometry(14, 0.6, 0.06), signMat(title, { bg: '#c7322e', fg: '#ffffff', border: false, w: 1536, h: 128 }), 0, 0.35, -4.6, g); return { group: g }; };
const stage = (x, z, slug = null, title = '') => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g);
  const fl = add(new THREE.PlaneGeometry(40, 30), KC('#17161b'), 0, 0.01, 0, g, { cast: false }); fl.rotation.x = -Math.PI / 2;
  add(new THREE.BoxGeometry(14, 1.0, 7), KC('#2b2d34'), 0, 0.5, -3, g);
  add(new THREE.BoxGeometry(12, 6, 0.2), signMat(title, { slug, bg: '#0f1a2a', fg: '#ffffff', border: false, w: 1024, h: 512 }), 0, 4.6, -6.4, g);
  const pod = add(new THREE.BoxGeometry(1.2, 1.4, 0.8), KC('#e9e3d6'), 2.8, 1.7, -2, g); add(new THREE.BoxGeometry(1.0, 0.6, 0.02), signMat('', { slug, bg: '#ffffff', border: false, w: 256, h: 160 }), 2.8, 1.9, -1.59, g);
  // spotlights: lamps on a truss and bright pools on the stage (light cones drew as grey wedges through the ink pass)
  add(new THREE.BoxGeometry(14, 0.25, 0.25), KM.steel, 0, 8.2, -1, g);
  const spots = []; for (const s_ of [-1, 0, 1]) { add(new THREE.CylinderGeometry(0.3, 0.42, 0.7, 14), KM.dark, s_ * 4, 7.8, -1, g);
    const pool = add(new THREE.CircleGeometry(1.8, 32), new THREE.MeshBasicMaterial({ color: '#fff1c8', transparent: true, opacity: 0.35, depthWrite: false }), s_ * 4, 1.02, -2.6, g, { cast: false });
    pool.rotation.x = -Math.PI / 2; pool.userData.ndSkip = true; spots.push(pool); }
  return { group: g, top: DECK + 1.0, spots }; };
// ===== end of batch 3 =====
// ===== GOLIDE reactions, batch 4 (2026-11-22): set pieces that move on the story's words =====
// door(x, z, w, h, colour): a door that swings open with door.open(k) (0..1). breakTo(obj, k): shatter a box object into
// falling chunks (k 0..1). burst(x, y, z, kind): a 3D burst of coins | bills | confetti | sparks with .at(t). dominoes(x, z, n):
// a domino line that falls with .fall(t). balloon(x, y, z, colour): .pop(k). bigButton(x, z, label): a pressable red button
// .press(k). The engine calls worldProps(W, f) every frame: drive these from W there.
const door = (x, z, w = 1.4, h = 2.6, colour = '#7a5434', ry = 0) => { const g = new THREE.Group(); g.position.set(x, DECK, z); g.rotation.y = ry; scene.add(g);
  add(new THREE.BoxGeometry(w + 0.3, h + 0.2, 0.2), KM.white, 0, (h + 0.2) / 2, -0.12, g); const hinge = new THREE.Group(); hinge.position.set(-w / 2, 0, 0); g.add(hinge);
  add(new THREE.BoxGeometry(w, h, 0.1), KC(colour), w / 2, h / 2, 0.02, hinge); add(new THREE.SphereGeometry(0.07, 10, 8), KM.gold, w - 0.18, h * 0.48, 0.1, hinge);
  g.open = (k) => { hinge.rotation.y = -1.6 * k; }; return g; };
const burst = (x, y, z, kind = 'coins', n = 40, seed = 3) => { const g = new THREE.Group(); g.position.set(x, y, z); scene.add(g); const r = P.rng(seed), parts = [];
  const mat = { coins: coinM, bills: billM, confetti: null, sparks: toon({ color: '#ffd23f', emissive: '#ffd23f', emissiveIntensity: 1 }) }[kind];
  for (let i = 0; i < n; i++) { const m = kind === 'confetti' ? KC(['#c7322e', '#2f78c4', '#3fa36b', '#e9b43a', '#e86a92'][i % 5]) : mat;
    const geo = kind === 'coins' ? new THREE.CylinderGeometry(0.16, 0.16, 0.04, 12) : kind === 'bills' ? new THREE.BoxGeometry(0.6, 0.01, 0.26) : new THREE.BoxGeometry(0.12, 0.12, 0.02);
    const o = add(geo, m, 0, 0, 0, g, { cast: false }); const v = [(r() - 0.5) * 6, 3 + r() * 5, (r() - 0.5) * 4]; parts.push([o, v, r() * 6]); }
  g.at = (t) => { g.visible = t > 0; for (const [o, v, s] of parts) { const tt = Math.max(0, t) * 1.6; o.position.set(v[0] * tt, v[1] * tt - 4.9 * tt * tt, v[2] * tt); o.rotation.set(s + tt * 6, s * 2 + tt * 4, s); } };
  g.at(0); return g; };
const breakTo = (obj, k) => { if (!obj.userData.chunks) { obj.userData.chunks = []; obj.traverse((m) => { if (m.isMesh) obj.userData.chunks.push([m, m.position.clone(), m.rotation.clone(), Math.random() * 2 - 1]); }); }
  for (const [m, p0, r0, s] of obj.userData.chunks) { m.position.set(p0.x + s * k * 1.5, Math.max(-p0.y, p0.y - 4.9 * k * k * 0.6), p0.z + s * k); m.rotation.set(r0.x + k * 2 * s, r0.y, r0.z + k * 2.5 * s); } };
const dominoes = (x, z, n = 12, gap = 0.55, colour = '#f1efe8') => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); const out = [];
  for (let i = 0; i < n; i++) { const piv = new THREE.Group(); piv.position.set(i * gap, 0, 0); g.add(piv); add(new THREE.BoxGeometry(0.12, 1.0, 0.5), KC(colour), 0.06, 0.5, 0, piv);
    for (const y of [0.3, 0.7]) p_dot(piv, 0.125, y); out.push(piv); }
  function p_dot(pv, x_, y_) { add(new THREE.SphereGeometry(0.04, 8, 6), KM.dark, x_, y_, 0, pv); }
  g.fall = (t) => out.forEach((pv, i) => { const k = Math.max(0, Math.min(1, t * n - i)); pv.rotation.z = -1.25 * k; }); return g; };
const balloon = (x, y, z, colour = '#e8445a') => { const g = new THREE.Group(); g.position.set(x, y, z); scene.add(g); const b = add(new THREE.SphereGeometry(0.6, 20, 14), KC(colour), 0, 0, 0, g); b.scale.y = 1.2;
  add(new THREE.CylinderGeometry(0.01, 0.01, 1.6, 4), KM.dark, 0, -1.4, 0, g); g.pop = (k) => { b.visible = k < 0.5; b.scale.setScalar(1 + k * 0.6); b.scale.y = (1 + k * 0.6) * 1.2; }; return g; };
const bigButton = (x, z, label = '') => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); add(new THREE.CylinderGeometry(0.5, 0.6, 1.0, 20), KM.dark, 0, 0.5, 0, g);
  const cap = add(new THREE.CylinderGeometry(0.36, 0.36, 0.18, 20), toon({ color: '#e23b3b', emissive: '#e23b3b', emissiveIntensity: 0.3 }), 0, 1.08, 0, g);
  if (label) add(new THREE.BoxGeometry(0.9, 0.25, 0.02), signMat(label, { bg: '#ffd23f', fg: '#17161b', border: false, w: 512, h: 128 }), 0, 0.6, 0.6, g);
  g.press = (k) => { cap.position.y = 1.08 - 0.1 * k; }; return g; };
// ===== end of batch 4 =====
// ===== GOLIDE places, batch 5 (2026-11-22): everyday life and work, outdoors =====
// livingRoom, kitchen, bedroom, restaurant, gym, factory (assembly line with .run(f)), planeCabin, bankHall (counter, vault
// door .open(k)), lab, supermarket, constructionSite, policeDesk / interrogation, rooftop, farm, forest, beach, snowPeak,
// desert. Each takes (x, z) and returns { group, ... }. Outdoor places paint their own ground; build each 600 m apart.
const furn = (g, w, h, d, c, x, y, z) => add(new THREE.BoxGeometry(w, h, d), KC(c), x, y, z, g);
const sofa = (g, x, z, c = '#3b5b8f', ry = 0) => { const s_ = new THREE.Group(); s_.position.set(x, 0, z); s_.rotation.y = ry; g.add(s_);
  furn(s_, 3.2, 0.5, 1.1, c, 0, 0.45, 0); furn(s_, 3.2, 0.9, 0.3, c, 0, 0.95, -0.42); for (const a of [-1.5, 1.5]) furn(s_, 0.3, 0.75, 1.1, c, a, 0.6, 0); return s_; };
const livingRoom = (x, z) => { const r = room(x, z, 16, 11, 4.2, { floor: 'wood', wall: '#e8d9c0', lights: 2 }); const g = r.group;
  sofa(g, 0, -3.2); furn(g, 2.2, 0.4, 1.0, '#7a5434', 0, 0.3, -1.4); const tv = add(new THREE.BoxGeometry(3.6, 2.0, 0.1), screenTex('chart', ''), 0, 2.4, -5.3, g);
  furn(g, 4.2, 0.6, 0.5, '#5a3a24', 0, 0.3, -5.2); pottedPlant(5.5, -4.5, 1.6, g, 0); furn(g, 3.0, 2.0, 0.1, '#bfe3ff', -5, 2.6, -5.4);
  const lamp = add(new THREE.CylinderGeometry(0.4, 0.6, 0.6, 16), toon({ color: '#ffe8a8', emissive: '#ffe8a8', emissiveIntensity: 0.6 }), 4.6, 1.9, -3.6, g); add(new THREE.CylinderGeometry(0.04, 0.04, 1.6, 8), KM.dark, 4.6, 0.8, -3.6, g);
  return { group: g, tv }; };
const kitchen = (x, z) => { const r = room(x, z, 14, 10, 4.2, { floor: 'checker', wall: '#f2efe6', lights: 2 }); const g = r.group;
  furn(g, 10, 1.0, 1.0, '#e9e3d6', 0, 0.5, -4.4); furn(g, 10.2, 0.1, 1.1, '#5f6f82', 0, 1.05, -4.4); furn(g, 1.6, 2.6, 1.0, '#d9dde3', 5.2, 1.3, -4.4);
  for (let i = 0; i < 4; i++) furn(g, 1.8, 0.9, 0.5, '#e9e3d6', -4 + i * 2.2, 2.9, -4.7); const stove = furn(g, 1.6, 0.06, 0.9, '#17161b', -1.5, 1.12, -4.4);
  for (const [a, b] of [[-1.9, -4.6], [-1.1, -4.6], [-1.9, -4.2], [-1.1, -4.2]]) add(new THREE.TorusGeometry(0.16, 0.03, 6, 16), KM.dark, a, 1.16, b, g).rotation.x = Math.PI / 2;
  furn(g, 3, 0.1, 1.6, '#c39668', 0, 1.0, -0.5); for (const a of [-1.2, 1.2]) furn(g, 0.1, 1.0, 1.4, '#7a5434', a, 0.5, -0.5); return { group: g }; };
const bedroom = (x, z) => { const r = room(x, z, 14, 10, 4.0, { floor: 'wood', wall: '#cfd8e8', lights: 1 }); const g = r.group;
  furn(g, 3, 0.6, 4, '#e8e4da', 0, 0.5, -2.6); furn(g, 3, 0.25, 3.0, '#5a7fc0', 0, 0.9, -2.2); furn(g, 1.2, 0.25, 0.6, '#ffffff', -0.7, 0.95, -4.2); furn(g, 1.2, 0.25, 0.6, '#ffffff', 0.7, 0.95, -4.2);
  furn(g, 3.2, 1.4, 0.2, '#7a5434', 0, 1.0, -4.7); furn(g, 0.8, 0.8, 0.8, '#7a5434', 2.2, 0.4, -4.2); add(new THREE.SphereGeometry(0.25, 12, 8), toon({ color: '#ffe8a8', emissive: '#ffe8a8', emissiveIntensity: 0.7 }), 2.2, 1.1, -4.2, g);
  furn(g, 2.2, 1.6, 0.1, '#0b1430', -4.5, 2.4, -4.9); return { group: g }; };
const restaurant = (x, z) => { const r = room(x, z, 18, 12, 4.4, { floor: 'checker', wall: '#7a2f2a', lights: 4, trim: '#e9b43a' }); const g = r.group;
  for (let i = 0; i < 3; i++) for (let j = 0; j < 2; j++) { const tx = -5 + i * 5, tz = -3.5 + j * 4; add(new THREE.CylinderGeometry(0.9, 0.9, 0.08, 24), KM.white, tx, 1.0, tz, g); add(new THREE.CylinderGeometry(0.08, 0.08, 1.0, 8), KM.dark, tx, 0.5, tz, g);
    for (const a of [-1.2, 1.2]) { furn(g, 0.6, 0.08, 0.6, '#5a3a24', tx + a, 0.6, tz); furn(g, 0.6, 0.8, 0.08, '#5a3a24', tx + a * 1.25, 1.0, tz); } add(new THREE.CylinderGeometry(0.3, 0.3, 0.04, 16), KM.white, tx, 1.06, tz, g); }
  signBoard('OPEN', 7, 3, -5.8, 2.2, 0.8, { bg: '#17161b', fg: '#ff5a5a' }, g); return { group: g }; };
const gym = (x, z) => { const r = room(x, z, 18, 12, 5, { floor: 'concrete', wall: '#2b2d34', lights: 4, trim: '#e9b43a' }); const g = r.group;
  for (let i = 0; i < 3; i++) { const tx = -6 + i * 3; furn(g, 1.0, 1.2, 2.4, '#3b3d44', tx, 0.6, -4); furn(g, 0.9, 0.05, 2.0, '#17161b', tx, 1.22, -4); furn(g, 0.9, 0.8, 0.1, '#5aa8ff', tx, 2.0, -5.1); }
  const bar = add(new THREE.CylinderGeometry(0.05, 0.05, 3, 8), KM.steel, 4, 1.0, -2, g); bar.rotation.z = Math.PI / 2; for (const a of [-1.3, 1.3]) { const w = add(new THREE.CylinderGeometry(0.5, 0.5, 0.2, 20), KM.dark, 4 + a, 1.0, -2, g); w.rotation.z = Math.PI / 2; }
  furn(g, 6, 3, 0.1, '#bfe3ff', 4, 2.4, -5.9); return { group: g, bar }; };
const factory = (x, z, item = '#e9b43a') => { const r = room(x, z, 24, 14, 7, { floor: 'concrete', wall: '#9aa3ad', lights: 5 }); const g = r.group, boxes = [];
  furn(g, 20, 0.9, 1.6, '#3b3d44', 0, 0.45, -2); for (let i = 0; i < 20; i++) add(new THREE.CylinderGeometry(0.2, 0.2, 1.6, 10), KM.steel, -9.5 + i, 0.95, -2, g).rotation.x = Math.PI / 2;
  for (let i = 0; i < 9; i++) boxes.push(add(new THREE.BoxGeometry(0.9, 0.7, 0.9), KC(item), -9 + i * 2.2, 1.5, -2, g));
  for (const a of [-5, 3]) { furn(g, 1.2, 4, 1.2, '#e2a52c', a, 2, -4.4); const armR = furn(g, 0.3, 0.3, 2.8, '#e2a52c', a, 3.9, -3.2); }
  furn(g, 4, 2.4, 2.4, '#5f6f82', 8, 1.2, -5.4); return { group: g, run: (f) => boxes.forEach((b, i) => { b.position.x = -10 + ((i * 2.2 + f * 0.05) % 20); }) }; };
const planeCabin = (x, z, rows = 8) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); const w = 5.6, L = rows * 1.3 + 4, wall = KC('#eef0f3');
  const fl = add(new THREE.PlaneGeometry(w, L), KC('#6a6f7a'), 0, 0.01, -L / 2 + 2, g, { cast: false }); fl.rotation.x = -Math.PI / 2;
  const tube = add(new THREE.CylinderGeometry(3.0, 3.0, L, 32, 1, true, Math.PI * 0.62, Math.PI * 1.76), wall, 0, 1.2, -L / 2 + 2, g); tube.rotation.x = Math.PI / 2; tube.material.side = THREE.DoubleSide;
  furn(g, 0.7, 0.03, L, '#8e1f2a', 0, 0.02, -L / 2 + 2);
  for (let i = 0; i < rows; i++) for (const s_ of [-1, 1]) for (const k of [0, 1]) { const sx = s_ * (1.1 + k * 0.7), sz = 0.5 - i * 1.3; furn(g, 0.62, 0.15, 0.6, '#2f4f8f', sx, 0.6, sz); furn(g, 0.62, 1.0, 0.14, '#2f4f8f', sx, 1.15, sz + 0.3); furn(g, 0.5, 0.1, 0.08, '#e8e4da', sx, 1.7, sz + 0.3); }
  for (let i = 0; i < rows; i++) for (const s_ of [-1, 1]) add(new THREE.BoxGeometry(0.06, 0.5, 0.36), KC('#bfe3ff'), s_ * 2.62, 1.8, 0.4 - i * 1.3, g);
  for (const s_ of [-1, 1]) furn(g, 1.6, 0.5, L, '#e1e4e9', s_ * 1.8, 2.75, -L / 2 + 2); return { group: g, aisleZ: (i) => 0.5 - i * 1.3 }; };
const bankHall = (x, z) => { const r = room(x, z, 18, 12, 5.5, { floor: 'checker', wall: '#e8e1cf', lights: 4, trim: '#e9b43a' }); const g = r.group;
  furn(g, 12, 1.3, 1.0, '#7a5434', 0, 0.65, -1.5); for (let i = 0; i < 4; i++) furn(g, 0.08, 1.0, 0.9, '#e9b43a', -4.5 + i * 3, 1.8, -1.5);
  const vg = new THREE.Group(); vg.position.set(5.5, 2.2, -5.7); g.add(vg); const vd = add(new THREE.CylinderGeometry(1.8, 1.8, 0.4, 36), KM.steel, 0, 0, 0, vg); vd.rotation.x = Math.PI / 2;
  for (let k = 0; k < 6; k++) { const sp = add(new THREE.CylinderGeometry(0.06, 0.06, 1.6, 8), KM.gold, 0, 0, 0.3, vg); sp.rotation.z = k * Math.PI / 6; }
  signBoard('BANK', -5, 4.2, -5.8, 3, 1, { bg: '#1f2a44', fg: '#e9b43a' }, g); return { group: g, vault: { open: (k) => { vg.rotation.y = -1.4 * k; vg.position.x = 5.5 - 1.6 * k; } } }; };
const lab = (x, z) => { const r = room(x, z, 16, 11, 4.4, { floor: 'tiles', wall: '#eef3f6', lights: 4 }); const g = r.group; const glass = toon({ color: '#bfe3ff', transparent: true, opacity: 0.75 });
  furn(g, 10, 1.0, 1.4, '#e9e3d6', 0, 0.5, -3.6); furn(g, 10.2, 0.08, 1.5, '#2b2d34', 0, 1.04, -3.6);
  for (let i = 0; i < 7; i++) { const lx = -4 + i * 1.3, c = ['#3fe08a', '#5aa8ff', '#e8445a', '#ffd23f'][i % 4]; add(new THREE.CylinderGeometry(0.18, 0.28, 0.5, 14), glass, lx, 1.35, -3.6, g); add(new THREE.CylinderGeometry(0.24, 0.27, 0.22, 14), toon({ color: c, emissive: c, emissiveIntensity: 0.4 }), lx, 1.22, -3.6, g); }
  const mic = furn(g, 0.5, 0.9, 0.5, '#d9dde3', 4.5, 1.5, -3.6); furn(g, 3, 2, 0.1, '#2b2d34', -4, 2.8, -5.3); return { group: g }; };
const supermarket = (x, z) => { const r = room(x, z, 20, 14, 5, { floor: 'tiles', wall: '#f2efe6', lights: 5, trim: '#3fa36b' }); const g = r.group;
  for (let a = 0; a < 3; a++) for (let lv = 0; lv < 4; lv++) { const sx = -6 + a * 6; furn(g, 4.4, 0.08, 1.0, '#9aa3ad', sx, 0.4 + lv * 0.6, -3); const r_ = P.rng(a * 10 + lv);
    for (let k = 0; k < 9; k++) furn(g, 0.36, 0.45, 0.4, ['#e8445a', '#ffd23f', '#3fa36b', '#5aa8ff', '#e2a52c'][Math.floor(r_() * 5)], sx - 2 + k * 0.5, 0.66 + lv * 0.6, -3); }
  const cart = new THREE.Group(); cart.position.set(2, 0, 1.5); g.add(cart); furn(cart, 1.2, 0.7, 0.8, '#9aa3ad', 0, 0.9, 0); for (const [a, b] of [[-0.5, -0.3], [0.5, -0.3], [-0.5, 0.3], [0.5, 0.3]]) add(new THREE.CylinderGeometry(0.1, 0.1, 0.06, 10), KM.dark, a, 0.1, b, cart).rotation.x = Math.PI / 2;
  signBoard('SALE -50%', 0, 4.2, -6.8, 4, 1.1, { bg: '#e8445a', fg: '#ffffff' }, g); return { group: g, cart }; };
const constructionSite = (x, z) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g);
  const gr = add(new THREE.PlaneGeometry(200, 200), toon({ map: P.tex(floorTex('concrete'), 20, 20), color: '#d8c49a' }), 0, 0.01, 0, g, { cast: false }); gr.rotation.x = -Math.PI / 2;
  for (let lv = 0; lv < 5; lv++) { furn(g, 10, 0.3, 8, '#b9b6ad', 0, lv * 3 + 0.15, -10); for (const [a, b] of [[-4.6, -6.4], [4.6, -6.4], [-4.6, -13.6], [4.6, -13.6]]) furn(g, 0.4, 3, 0.4, '#9aa3ad', a, lv * 3 + 1.5, b); }
  furn(g, 0.6, 22, 0.6, '#f2c230', 9, 11, -8); const jib = furn(g, 16, 0.5, 0.5, '#f2c230', 4, 22, -8); add(new THREE.CylinderGeometry(0.02, 0.02, 10, 4), KM.dark, -2, 17, -8, g);
  for (let i = 0; i < 6; i++) add(new THREE.ConeGeometry(0.25, 0.7, 12), KC('#ff7a1a'), -6 + i * 2.4, 0.35, 2, g); return { group: g, jib }; };
const policeDesk = (x, z) => { const r = room(x, z, 14, 10, 4.2, { floor: 'tiles', wall: '#c9d3df', lights: 2, trim: '#1f2a44' }); const g = r.group;
  furn(g, 4, 1.0, 1.6, '#5a6d7a', 0, 0.5, -1); furn(g, 4.2, 0.08, 1.8, '#2b2d34', 0, 1.04, -1); add(new THREE.CylinderGeometry(0.5, 0.6, 0.12, 20), toon({ color: '#fff3c8', emissive: '#fff3c8', emissiveIntensity: 0.6 }), 0, 3.6, -1, g);
  furn(g, 0.9, 0.08, 0.9, '#3b3d44', 0, 0.7, 0.8); furn(g, 0.9, 0.08, 0.9, '#3b3d44', 0, 0.7, -2.8); furn(g, 4, 2.4, 0.08, '#2a2f38', -4.5, 2.2, -4.9);
  signBoard('POLICE', 3.5, 3.4, -4.85, 3, 0.9, { bg: '#1f2a44', fg: '#ffffff' }, g); return { group: g }; };
// outdoor ground: a disc that ends before the next set (sets stand 600 m apart), its edge hidden behind a ring of low
// hills in the ground's own colour (a bare edge drew a black ink band at the horizon; a bigger plane covered other sets)
const groundPaint = (g, colour, tex = null, size = 540) => { size = Math.min(size, 540);
  const m = tex ? toon({ map: P.tex(tex, size / 8, size / 8), color: colour }) : KC(colour);
  const pl = add(new THREE.CircleGeometry(size / 2, 64), m, 0, 0.005, 0, g, { cast: false }); pl.rotation.x = -Math.PI / 2; pl.userData.ndSkip = true;   // no ink from the ground's far edge
  const hill = KC(new THREE.Color(colour).multiplyScalar(0.86).getStyle()), r_ = P.rng(size);
  // small grounds (a rooftop) have no hills: they would stand on the set
  if (size >= 300) for (let i = 0; i < 46; i++) { const a = i / 46 * Math.PI * 2, d = size / 2 - 24 - r_() * 10; const h = add(new THREE.SphereGeometry(26 + r_() * 14, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2), hill, Math.cos(a) * d, 0, Math.sin(a) * d, g, { cast: false }); h.scale.y = 0.28 + r_() * 0.2; h.userData.ndSkip = true; }
  return pl; };
const tree = (g, x, z, h = 6, c = '#4f9a46') => { furn(g, 0.5, h * 0.45, 0.5, '#6b4a2a', x, h * 0.22, z); const t = add(new THREE.ConeGeometry(h * 0.3, h * 0.7, 10), KC(c), x, h * 0.75, z, g); return t; };
const rooftop = (x, z) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); groundPaint(g, '#8b8f96', floorTex('concrete'), 120);
  for (const s_ of [-1, 1]) furn(g, 0.3, 1.1, 30, '#9aa3ad', s_ * 15, 0.55, 0); furn(g, 30, 1.1, 0.3, '#9aa3ad', 0, 0.55, -15);
  furn(g, 3, 2.5, 3, '#5f6f82', -8, 1.25, -9); furn(g, 2, 1.2, 2, '#9aa3ad', 6, 0.6, -8); const city_ = new THREE.Group(); g.add(city_);
  const r_ = P.rng(4); for (let i = 0; i < 40; i++) { const a = Math.PI * (1.08 + r_() * 0.84), d = 70 + r_() * 150; tower(x + Math.cos(a) * d, z + Math.sin(a) * d, 8 + r_() * 10, 8 + r_() * 10, 12 + r_() * 80); } return { group: g }; };
const farm = (x, z) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); groundPaint(g, '#7aa64c', null, 400);
  const barn = new THREE.Group(); barn.position.set(-8, 0, -14); g.add(barn); furn(barn, 8, 5, 7, '#b8282b', 0, 2.5, 0); const rf = add(new THREE.ConeGeometry(6, 3, 4), KC('#5a2a22'), 0, 6.5, 0, barn); rf.rotation.y = Math.PI / 4; rf.scale.set(1, 1, 0.9);
  furn(barn, 2.6, 3.2, 0.1, '#f1efe8', 0, 1.6, 3.55); for (let i = 0; i < 14; i++) furn(g, 0.12, 1.1, 0.12, '#c39668', -14 + i * 2, 0.55, -2); furn(g, 28, 0.1, 0.1, '#c39668', -1, 0.9, -2);
  for (let r_ = 0; r_ < 6; r_++) for (let c = 0; c < 10; c++) add(new THREE.SphereGeometry(0.35, 8, 6), KC('#5f9a3a'), 4 + c * 1.2, 0.3, -8 - r_ * 1.4, g);
  for (let i = 0; i < 8; i++) tree(g, -25 + i * 7, -30 - (i % 3) * 4, 7); return { group: g }; };
const forest = (x, z, n = 60) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); groundPaint(g, '#5f8a3e', null, 300); const r_ = P.rng(8);
  for (let i = 0; i < n; i++) { const a = r_() * Math.PI * 2, d = 5 + r_() * 60; if (Math.abs(Math.sin(a) * d) < 3 && Math.cos(a) * d > -4) continue; tree(g, Math.cos(a) * d, Math.sin(a) * d - 6, 5 + r_() * 6, ['#3f6b36', '#4f8a3e', '#5c8a3c'][i % 3]); }
  furn(g, 2.2, 0.1, 80, '#9b7d55', 0, 0.02, 0); return { group: g }; };
const beach = (x, z) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); groundPaint(g, '#ecd9a6', null, 300);
  const sea = add(new THREE.PlaneGeometry(520, 230), KC('#2f8fc4'), 0, 0.02, -125, g, { cast: false }); sea.userData.ndSkip = true; sea.rotation.x = -Math.PI / 2;
  for (let i = 0; i < 3; i++) { const px = -8 + i * 9, trunk = add(new THREE.CylinderGeometry(0.22, 0.32, 6, 8), KC('#8a6a3a'), px, 3, -4 - i * 2, g); trunk.rotation.z = 0.15;
    for (let k = 0; k < 6; k++) { const lf = add(new THREE.BoxGeometry(3, 0.08, 0.7), KC('#3f8a3e'), px + 0.4 + Math.cos(k) * 1.2, 6.1, -4 - i * 2 + Math.sin(k) * 1.2, g); lf.rotation.y = k; lf.rotation.z = -0.4; } }
  add(new THREE.ConeGeometry(1.8, 0.6, 16), KC('#e8445a'), 3, 2.6, 2, g); add(new THREE.CylinderGeometry(0.05, 0.05, 2.6, 6), KM.white, 3, 1.3, 2, g); furn(g, 0.9, 0.2, 2.0, '#ffd23f', 4.5, 0.3, 2.2); return { group: g }; };
const snowPeak = (x, z) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); groundPaint(g, '#f4f6fa', null, 400); const r_ = P.rng(11);
  for (let i = 0; i < 9; i++) { const m = add(new THREE.ConeGeometry(18 + r_() * 20, 30 + r_() * 40, 7), KC('#8fa7b8'), -80 + i * 22, 15, -90 - r_() * 40, g); add(new THREE.ConeGeometry(8, 12, 7), KC('#f4f6fa'), m.position.x, m.position.y + 18 + r_() * 6, m.position.z, g); }
  for (let i = 0; i < 10; i++) tree(g, -20 + i * 4.5, -14 - (i % 2) * 4, 5, '#2f5a3a'); return { group: g }; };
const desert = (x, z) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); groundPaint(g, '#e2b877', null, 400); const r_ = P.rng(13);
  for (let i = 0; i < 12; i++) { const d = add(new THREE.SphereGeometry(10 + r_() * 14, 18, 10, 0, Math.PI * 2, 0, Math.PI / 2), KC(i % 2 ? '#d9a865' : '#e8c48a'), -90 + i * 16, 0, -50 - r_() * 50, g); d.scale.y = 0.3; }
  for (let i = 0; i < 4; i++) { const cx_ = -6 + i * 5; furn(g, 0.5, 3, 0.5, '#4f8a3e', cx_, 1.5, -6 - i); furn(g, 0.35, 1.2, 0.35, '#4f8a3e', cx_ + 0.5, 2.0, -6 - i); }
  const pyr = add(new THREE.ConeGeometry(16, 14, 4), KC('#d6a35c'), 30, 7, -70, g); pyr.rotation.y = Math.PI / 4; return { group: g }; };
// ===== end of batch 5 =====
// ===== GOLIDE tech and money, batch 7 (2026-11-22) =====
// giantPhone(x, z, h, app, opts) a phone as tall as a building with an app screen (opts.lines, opts.slug); giantLaptop(x, z, w,
// text, slug); giantChip(x, z, size, label, slug) a processor with gold pins on a board; gpuRack(x, z, n) GPU boards with fans
// (.spin(f)); launchPad(x, z, label) a rocket on its pad (.lift(k)) with a gantry; satelliteDish(x, z); tradingFloor(x, z) desks
// with screens and a big ticker wall (.tick(f)); stockBoard(x, y, z, rows) a red/green price board; warRoom(x, z) a world map
// table and wall screens; powerPlant(x, z) cooling towers with steam; evCharger(x, z, slug) and evCar(colour); drone(slug)
// (.fly(f)); vrHeadset (drawn over a face: O.vr in the cast kit is not needed, use the item); likesWall(x, y, z) a wall of
// floating social reactions (.pop(f)); cryptoRig(x, z) a mining shelf; robotArm(x, z) an assembly arm (.swing(k)).
const appTex = (title = 'APP', lines = [], accent = '#2f78c4', slug = null) => { const [c, g] = kCanvas(512, 1024); g.fillStyle = '#ffffff'; g.fillRect(0, 0, 512, 1024);
  g.fillStyle = accent; g.fillRect(0, 0, 512, 150); if (slug && drawLogo(g, slug, 24, 30, 90, '#ffffff')) {} g.fillStyle = '#ffffff'; g.font = '900 54px sans-serif'; g.textBaseline = 'middle'; g.fillText(title, slug ? 130 : 30, 78);
  const L = lines.length ? lines : ['', '', '', '']; L.forEach((t, i) => { const y = 200 + i * 190; g.fillStyle = '#f1f3f6'; g.fillRect(24, y, 464, 160); g.fillStyle = ['#e8445a', '#3fa36b', '#e9b43a', '#8a3bd2', '#2f78c4'][i % 5]; g.beginPath(); g.arc(84, y + 80, 44, 0, 7); g.fill();
    g.fillStyle = '#17161b'; g.font = '800 40px sans-serif'; g.fillText(String(t).slice(0, 16), 150, y + 60); g.fillStyle = '#b9bfc9'; g.fillRect(150, y + 100, 280, 18); }); return toon({ map: kTex(c), emissive: '#ffffff', emissiveMap: kTex(c), emissiveIntensity: 0.25 }); };
const giantPhone = (x, z, h = 12, app = 'APP', opts = {}) => { const g = new THREE.Group(); g.position.set(x, DECK, z); g.rotation.y = opts.ry || 0; scene.add(g); const w = h * 0.48;
  add(new THREE.BoxGeometry(w, h, 0.8), KC(opts.colour || '#17161b'), 0, h / 2, 0, g); add(new THREE.BoxGeometry(w * 0.9, h * 0.92, 0.05), appTex(app, opts.lines || [], opts.accent, opts.slug), 0, h / 2, 0.42, g);
  add(new THREE.BoxGeometry(w * 0.25, h * 0.02, 0.05), KM.dark, 0, h * 0.975, 0.43, g); return g; };
const giantLaptop = (x, z, w = 10, text = '', slug = null) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g);
  add(new THREE.BoxGeometry(w, 0.4, w * 0.66), KC('#c9ccd2'), 0, 0.2, 0, g); add(new THREE.BoxGeometry(w * 0.8, 0.02, w * 0.3), KM.dark, 0, 0.41, -0.05 * w, g);
  const lid = new THREE.Group(); lid.position.set(0, 0.4, -w * 0.33); g.add(lid); add(new THREE.BoxGeometry(w, w * 0.64, 0.3), KC('#c9ccd2'), 0, w * 0.32, 0, lid);
  add(new THREE.BoxGeometry(w * 0.92, w * 0.56, 0.02), slug || text ? signMat(text, { slug, bg: '#10141c', fg: '#e9f2ff', border: false }) : screenTex('code', ''), 0, w * 0.33, 0.16, lid); lid.rotation.x = -0.18; g.lid = lid; return g; };
const giantChip = (x, z, size = 6, label = 'AI', slug = null) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g);
  add(new THREE.BoxGeometry(size * 2.2, 0.3, size * 2.2), KC('#2f6b3a'), 0, 0.15, 0, g); for (let i = 0; i < 16; i++) for (const s_ of [-1, 1]) { furnL(g, size * 0.06, 0.08, size * 0.5, s_ * size * 0.75, 0.35, -size * 0.6 + i * size * 0.08); furnL(g, size * 0.5, 0.08, size * 0.06, -size * 0.6 + i * size * 0.08, 0.35, s_ * size * 0.75); }
  add(new THREE.BoxGeometry(size, size * 0.18, size), KC('#2b2d34'), 0, 0.42, 0, g); add(new THREE.BoxGeometry(size * 0.8, 0.02, size * 0.8), signMat(label, { slug, bg: '#c9ccd2', fg: '#17161b', w: 512, h: 512 }), 0, 0.52 + size * 0.0, 0, g).rotation.x = 0; return g; };
const furnL = (g, w, h, d, x, y, z) => add(new THREE.BoxGeometry(w, h, d), KM.gold, x, y, z, g, { cast: false });
const gpuRack = (x, z, n = 6) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); const fans = [];
  add(new THREE.BoxGeometry(5, 0.2, 2), KM.steel, 0, 0.1, 0, g); for (let i = 0; i < n; i++) { const y = 0.4 + i * 0.55; add(new THREE.BoxGeometry(4.4, 0.4, 1.6), KC('#1d2027'), 0, y, 0, g); add(new THREE.BoxGeometry(4.4, 0.06, 1.62), KC('#76b900'), 0, y + 0.18, 0, g);
    for (const a of [-1.2, 0, 1.2]) { const f = add(new THREE.CylinderGeometry(0.28, 0.28, 0.04, 6), KM.dark, a, y, 0.82, g); f.rotation.x = Math.PI / 2; fans.push(f); } }
  for (const a of [-2.3, 2.3]) add(new THREE.BoxGeometry(0.12, n * 0.55 + 0.5, 1.8), KM.steel, a, (n * 0.55 + 0.5) / 2, 0, g); return { group: g, spin: (f) => fans.forEach((m, i) => { m.rotation.y = f * 0.5 + i; }) }; };
const launchPad = (x, z, label = '') => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); add(new THREE.CylinderGeometry(9, 10, 1.4, 32), KC('#9aa3ad'), 0, 0.7, 0, g);
  const rocket = new THREE.Group(); rocket.position.set(0, 1.4, 0); g.add(rocket); add(new THREE.CylinderGeometry(1.4, 1.4, 22, 24), KM.white, 0, 11, 0, rocket); add(new THREE.ConeGeometry(1.4, 4, 24), KC('#2b2d34'), 0, 24, 0, rocket);
  for (let k = 0; k < 4; k++) { const fin = add(new THREE.BoxGeometry(0.15, 3, 2.2), KC('#2b2d34'), Math.cos(k * Math.PI / 2) * 1.5, 1.5, Math.sin(k * Math.PI / 2) * 1.5, rocket); fin.rotation.y = -k * Math.PI / 2; }
  if (label) add(new THREE.BoxGeometry(0.02, 8, 1.6), signMat(label, { bg: '#ffffff', fg: '#17161b', border: false, w: 256, h: 1024 }), 1.42, 13, 0, rocket);
  const flame = add(new THREE.ConeGeometry(1.2, 6, 16), toon({ color: '#ffb020', emissive: '#ff7a1a', emissiveIntensity: 1 }), 0, -3, 0, rocket); flame.rotation.x = Math.PI; flame.visible = false;
  for (let lv = 0; lv < 8; lv++) add(new THREE.BoxGeometry(2.4, 0.2, 2.4), KC('#c7322e'), -5, 1.4 + lv * 3, 0, g); for (const [a, b] of [[-6, -1], [-4, -1], [-6, 1], [-4, 1]]) add(new THREE.BoxGeometry(0.2, 24, 0.2), KC('#c7322e'), a, 13, b, g);
  return { group: g, rocket, lift: (k) => { rocket.position.y = 1.4 + 60 * k * k; flame.visible = k > 0; flame.scale.y = 1 + 2 * k; } }; };
const satelliteDish = (x, z, s = 1) => { const g = new THREE.Group(); g.position.set(x, DECK, z); g.scale.setScalar(s); scene.add(g); add(new THREE.CylinderGeometry(0.4, 0.6, 4, 12), KM.steel, 0, 2, 0, g);
  const d = add(new THREE.SphereGeometry(4, 24, 12, 0, Math.PI * 2, 0, Math.PI / 3.2), KM.white, 0, 5, 0, g); d.rotation.x = -1.0; d.material.side = THREE.DoubleSide; add(new THREE.CylinderGeometry(0.05, 0.05, 3, 6), KM.steel, 0, 6.2, 1.2, g).rotation.x = -0.6; return g; };
const stockBoard = (x, y, z, rows = 6, w = 8, parent = scene) => { const [c, g] = kCanvas(1024, 128 * rows); g.fillStyle = '#0b0d16'; g.fillRect(0, 0, 1024, 128 * rows); const r = P.rng(rows * 7);
  const names = ['NVDA', 'AAPL', 'TSLA', 'MSFT', 'GOOG', 'AMZN', 'META', 'BTC', 'AMD', 'OPENAI'];
  for (let i = 0; i < rows; i++) { const up = r() > 0.45, ch = (r() * 9).toFixed(2); g.font = '900 72px monospace'; g.fillStyle = '#e8eef7'; g.textBaseline = 'middle'; g.fillText(names[i % names.length], 40, i * 128 + 64);
    g.fillStyle = up ? '#3fe08a' : '#ff4d4d'; g.fillText((up ? '▲ +' : '▼ -') + ch + '%', 560, i * 128 + 64); }
  return add(new THREE.BoxGeometry(w, w * rows / 8, 0.12), [KM.dark, KM.dark, KM.dark, KM.dark, toon({ map: kTex(c), emissive: '#ffffff', emissiveMap: kTex(c), emissiveIntensity: 0.6 }), KM.dark], x, y, z, parent); };
const tradingFloor = (x, z) => { const r = room(x, z, 20, 12, 6, { floor: 'carpet', wall: '#1d2a44', lights: 4, trim: '#2f78c4' }); const g = r.group;
  for (let i = 0; i < 4; i++) for (let j = 0; j < 2; j++) { const d = deskSet(x - 6 + i * 4, z - 1 + j * 3.2, 0, { screen: (i + j) % 2 ? 'chart' : 'down', plant: false }); }
  stockBoard(x, 3.8, z - 5.7, 5, 9); const tape = new THREE.Group(); tape.position.set(x, 5.4, z - 5.6); scene.add(tape); const tk = signMat('NVDA +4.2%  TSLA -1.8%  BTC +6.1%  AAPL +0.9%', { bg: '#0b0d16', fg: '#ffd23f', border: false, w: 2048, h: 96 });
  const strip = add(new THREE.BoxGeometry(24, 0.5, 0.05), tk, 0, 0, 0, tape); return { group: g, tick: (f) => { strip.position.x = 6 - (f * 0.08) % 12; } }; };
const warRoom = (x, z) => { const r = room(x, z, 18, 12, 5, { floor: 'concrete', wall: '#1b2230', lights: 2, trim: '#c7322e' }); const g = r.group;
  const table = add(new THREE.BoxGeometry(8, 0.2, 4.5), toon({ map: P.tex(earthCanvas) }), 0, 1.05, -1, g); add(new THREE.BoxGeometry(8.2, 1.0, 4.7), KC('#2b2d34'), 0, 0.5, -1, g);
  for (const [a, w_] of [[-5.5, 'down'], [0, 'chart'], [5.5, 'code']]) add(new THREE.BoxGeometry(4.6, 2.6, 0.1), screenTex(w_, ''), a, 3.2, -5.8, g);
  for (let k = 0; k < 6; k++) add(new THREE.SphereGeometry(0.12, 10, 8), toon({ color: '#ff4d4d', emissive: '#ff4d4d', emissiveIntensity: 1 }), -3 + k * 1.2, 1.2, -1 + Math.sin(k) * 1.2, g); return { group: g }; };
const powerPlant = (x, z) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); groundPaint(g, '#8fa070', null, 540); const puffs = [];
  for (const a of [-12, 0, 12]) { const t = add(new THREE.CylinderGeometry(4.2, 6.5, 18, 28, 1, true), KC('#d9dde3'), a, 9, -30, g); t.material.side = THREE.DoubleSide;
    for (let k = 0; k < 5; k++) { const p_ = add(new THREE.SphereGeometry(3 + k * 0.6, 12, 8), KM.white, a, 20 + k * 3, -30, g, { cast: false }); puffs.push([p_, k]); } }
  furn(g, 14, 6, 8, '#9aa3ad', 0, 3, -14); for (let i = 0; i < 6; i++) furn(g, 0.3, 14, 0.3, '#5f6f82', -20 + i * 8, 7, -6); return { group: g, steam: (f) => puffs.forEach(([m, k]) => { m.position.y = 20 + ((k * 3 + f * 0.06) % 15); m.scale.setScalar(1 + ((k * 3 + f * 0.06) % 15) / 10); }) }; };
const evCar = (col = '#e8e8e8') => { const g = car(col); add(new THREE.BoxGeometry(0.5, 0.25, 0.02), KC('#3fe08a'), 1.6, 0.9, 0.86, g); return g; };
const evCharger = (x, z, slug = null) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); add(new THREE.BoxGeometry(0.8, 2.0, 0.5), KM.white, 0, 1.0, 0, g);
  add(new THREE.BoxGeometry(0.6, 0.6, 0.02), signMat('', { slug, bg: '#3fe08a', border: false, w: 256, h: 256 }), 0, 1.5, 0.26, g); add(new THREE.TorusGeometry(0.3, 0.04, 6, 16, Math.PI), KM.dark, 0.35, 0.8, 0.3, g); return g; };
const drone = (slug = null) => { const g = new THREE.Group(); scene.add(g); add(new THREE.BoxGeometry(0.8, 0.25, 0.8), KC('#2b2d34'), 0, 0, 0, g); const props = [];
  for (const [a, b] of [[0.7, 0.7], [-0.7, 0.7], [0.7, -0.7], [-0.7, -0.7]]) { add(new THREE.BoxGeometry(0.9, 0.06, 0.08), KM.dark, a / 2, 0, b / 2, g).rotation.y = Math.atan2(b, a); props.push(add(new THREE.BoxGeometry(0.7, 0.02, 0.08), KM.steel, a, 0.12, b, g)); }
  if (slug) add(new THREE.BoxGeometry(0.4, 0.4, 0.02), signMat('', { slug, border: false, w: 256, h: 256 }), 0, 0, 0.41, g); g.fly = (f) => props.forEach((p_) => { p_.rotation.y = f * 1.5; }); return g; };
const likesWall = (x, y, z, n = 14) => { const g = new THREE.Group(); g.position.set(x, y, z); scene.add(g); const items = [];
  const icon = (kind) => { const [c, gg] = kCanvas(128, 128); gg.fillStyle = { like: '#2f78c4', heart: '#e8445a', fire: '#ff7a1a', star: '#e9b43a' }[kind]; gg.beginPath(); gg.arc(64, 64, 60, 0, 7); gg.fill();
    gg.fillStyle = '#ffffff'; gg.font = '900 64px sans-serif'; gg.textAlign = 'center'; gg.textBaseline = 'middle'; gg.fillText({ like: '+1', heart: '♥', fire: '!', star: '★' }[kind], 64, 70); return new THREE.MeshBasicMaterial({ map: kTex(c), transparent: true }); };
  const mats = ['like', 'heart', 'fire', 'star'].map(icon); const r = P.rng(n);
  for (let i = 0; i < n; i++) { const m = add(new THREE.PlaneGeometry(0.9, 0.9), mats[i % 4], (r() - 0.5) * 6, 0, (r() - 0.5) * 1, g, { cast: false }); m.userData.ndSkip = true; items.push([m, r() * 60]); }
  return { group: g, pop: (f) => items.forEach(([m, d]) => { const t = ((f + d) % 60) / 60; m.position.y = t * 5; m.material.opacity = 1 - t; m.scale.setScalar(0.6 + t * 0.6); }) }; };
const cryptoRig = (x, z) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); for (let lv = 0; lv < 4; lv++) { furn(g, 5, 0.08, 1.2, '#7a7f88', 0, 0.6 + lv * 0.8, 0);
  for (let i = 0; i < 5; i++) { furn(g, 0.8, 0.5, 0.9, '#1d2027', -2 + i, 0.9 + lv * 0.8, 0); add(new THREE.BoxGeometry(0.06, 0.06, 0.06), toon({ color: '#3fe08a', emissive: '#3fe08a', emissiveIntensity: 1 }), -1.7 + i, 0.95 + lv * 0.8, 0.46, g); } }
  add(new THREE.BoxGeometry(1.4, 1.4, 0.05), signMat('₿', { bg: '#f7931a', fg: '#ffffff', border: false, w: 256, h: 256 }), 3.4, 2.6, 0.3, g); return g; };
const robotArm = (x, z, colour = '#e2a52c') => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); add(new THREE.CylinderGeometry(0.7, 0.9, 0.6, 16), KC('#3b3d44'), 0, 0.3, 0, g);
  const j1 = new THREE.Group(); j1.position.set(0, 0.6, 0); g.add(j1); add(new THREE.BoxGeometry(0.5, 2.6, 0.5), KC(colour), 0, 1.3, 0, j1); const j2 = new THREE.Group(); j2.position.set(0, 2.6, 0); j1.add(j2);
  add(new THREE.BoxGeometry(0.4, 2.2, 0.4), KC(colour), 0, 1.1, 0, j2); add(new THREE.BoxGeometry(0.7, 0.3, 0.7), KM.dark, 0, 2.3, 0, j2); j2.rotation.z = 1.2;
  return { group: g, swing: (k) => { j1.rotation.z = -0.4 + 0.8 * k; j1.rotation.y = 1.2 * k; } }; };
// ===== end of batch 7 =====
// ===== GOLIDE places, batch 8 (2026-11-22): travel, city life, history and adventure =====
// airportGate(x, z) windows onto a parked plane, seats, a departures board; trainCar(x, z) a metro carriage with poles and
// seats (.shake(f)); highway(x, z) lanes with moving traffic (.run(f)); gasStation(x, z, slug); port(x, z) container stacks,
// a crane and a cargo ship; hotelLobby(x, z, name); castle(x, z) walls, towers and a gate; pyramidTomb(x, z) a torch-lit
// stone chamber with a sarcophagus (.open(k)); colosseum(x, z); pirateShip(x, z, name) sails and a skull flag; treasureCave(x, z)
// rocks, a chest (.open(k)) and gold; jungle(x, z); volcano(x, z) (.erupt(k)); underwater(x, z) seabed, fish, a wreck;
// moonSurface(x, z) / marsSurface(x, z) craters, a lander and a flag.
const seatsRow = (g, x, z, n = 4, c = '#2f5fb8') => { for (let i = 0; i < n; i++) { furn(g, 0.8, 0.12, 0.7, c, x + i * 0.9, 0.55, z); furn(g, 0.8, 0.8, 0.1, c, x + i * 0.9, 0.95, z - 0.32); } };
const airportGate = (x, z) => { const r = room(x, z, 22, 12, 6, { floor: 'tiles', wall: '#dfe6ee', lights: 5 }); const g = r.group;
  furn(g, 20, 4, 0.1, '#9fd0f2', 0, 3, -5.84); for (let i = 0; i < 6; i++) furn(g, 0.2, 4.2, 0.2, '#5f6f82', -10 + i * 4, 3, -5.8);
  const pl = new THREE.Group(); pl.position.set(2, 0, -26); g.add(pl); const body = add(new THREE.CapsuleGeometry(2.2, 22, 6, 20), KM.white, 0, 4, 0, pl); body.rotation.z = Math.PI / 2;
  const wing = add(new THREE.BoxGeometry(5, 0.3, 26), KM.white, 1, 3.4, 0, pl); add(new THREE.BoxGeometry(3.5, 4, 0.3), KC('#c7322e'), -11, 7, 0, pl);
  for (let i = 0; i < 12; i++) add(new THREE.CircleGeometry(0.28, 12), KM.glass, -9 + i * 1.6, 4.6, 2.2, pl);
  seatsRow(g, -8, 0, 5); seatsRow(g, 2, 0, 5); stockBoard(6.5, 4.4, -5.6, 4, 5, g); return { group: g }; };
const trainCar = (x, z) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); const w = 3.4, L = 20;
  const fl = add(new THREE.PlaneGeometry(w, L), KC('#7a7f88'), 0, 0.01, -L / 2 + 3, g, { cast: false }); fl.rotation.x = -Math.PI / 2;
  for (const s_ of [-1, 1]) { furn(g, 0.1, 2.8, L, '#dfe6ee', s_ * w / 2, 1.4, -L / 2 + 3); for (let i = 0; i < 6; i++) furn(g, 0.08, 1.0, 1.8, '#9fd0f2', s_ * (w / 2 - 0.06), 1.8, 1.5 - i * 3.2);
    furn(g, 0.6, 0.12, L - 2, '#2f78c4', s_ * (w / 2 - 0.4), 0.55, -L / 2 + 3); } furn(g, w, 0.1, L, '#f1efe8', 0, 2.8, -L / 2 + 3);
  for (let i = 0; i < 6; i++) add(new THREE.CylinderGeometry(0.04, 0.04, 2.8, 8), KM.steel, 0, 1.4, 1 - i * 3, g);
  return { group: g, shake: (f) => { g.position.y = DECK + 0.02 * Math.sin(f * 1.7); g.rotation.z = 0.004 * Math.sin(f * 0.9); } }; };
const highway = (x, z, lanes = 4) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); groundPaint(g, '#7aa64c', null, 540);
  furn(g, 400, 0.05, lanes * 3.6, '#5a5e66', 0, 0.02, 0); for (let l = 1; l < lanes; l++) for (let k = -60; k < 60; k++) furn(g, 2, 0.06, 0.15, '#f4efe4', k * 6, 0.04, -lanes * 1.8 + l * 3.6);
  const cars = []; for (let i = 0; i < 10; i++) { const c = car(['#c7322e', '#2f78c4', '#e9b43a', '#f1efe8', '#2b2d34'][i % 5]); c.userData.lane = i % lanes; c.userData.off = i * 23; cars.push(c); }
  return { group: g, run: (f) => cars.forEach((c) => { const dir = c.userData.lane < lanes / 2 ? 1 : -1; c.position.set(x + ((c.userData.off + f * 0.35 * dir) % 120) - 60 * dir, DECK, z - lanes * 1.8 + 1.8 + c.userData.lane * 3.6); c.rotation.y = dir > 0 ? 0 : Math.PI; }) }; };
const gasStation = (x, z, slug = null, name = 'FUEL') => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); groundPaint(g, '#8b8f96', floorTex('concrete'), 200);
  furn(g, 14, 0.5, 8, '#f1efe8', 0, 5, -2); furn(g, 14.2, 0.6, 0.2, '#c7322e', 0, 4.7, 2); for (const a of [-5, 5]) furn(g, 0.4, 5, 0.4, '#9aa3ad', a, 2.5, -2);
  for (const a of [-2.5, 2.5]) { furn(g, 0.9, 1.8, 0.6, '#c7322e', a, 0.9, -2); furn(g, 0.7, 0.5, 0.02, '#10141c', a, 1.4, -1.69); }
  signBoard(name, 9, 5.5, -2, 3, 2.2, { slug, bg: '#ffffff', fg: '#c7322e' }, g); furn(g, 8, 3.5, 5, '#e8e1cf', 0, 1.75, -12); return { group: g }; };
const port = (x, z) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); groundPaint(g, '#8b8f96', floorTex('concrete'), 300);
  const sea = add(new THREE.PlaneGeometry(300, 120), KC('#2f6f9f'), 0, -0.4, -80, g, { cast: false }); sea.rotation.x = -Math.PI / 2; sea.userData.ndSkip = true;
  const cc = ['#c7322e', '#2f78c4', '#e9b43a', '#3fa36b', '#e8e8e8', '#8a3bd2']; const r_ = P.rng(6);
  for (let i = 0; i < 8; i++) for (let j = 0; j < 3; j++) for (let lv = 0; lv < 1 + Math.floor(r_() * 4); lv++) furn(g, 6, 2.5, 2.4, cc[Math.floor(r_() * 6)], -24 + i * 6.4, 1.25 + lv * 2.5, -6 - j * 2.6);
  furn(g, 1.2, 20, 1.2, '#2f78c4', 18, 10, -14); furn(g, 1.2, 20, 1.2, '#2f78c4', 24, 10, -14); furn(g, 2, 1.2, 30, '#2f78c4', 21, 20, -22);
  const ship = new THREE.Group(); ship.position.set(0, 0, -30); g.add(ship); furn(ship, 70, 5, 12, '#1b1c22', 0, -1, 0); for (let i = 0; i < 10; i++) for (let lv = 0; lv < 3; lv++) furn(ship, 6, 2.5, 10, cc[(i + lv) % 6], -28 + i * 6.2, 2.75 + lv * 2.5, 0);
  return { group: g }; };
const hotelLobby = (x, z, name = 'GRAND HOTEL') => { const r = room(x, z, 20, 13, 7, { floor: 'checker', wall: '#efe4c8', lights: 4, trim: '#e9b43a' }); const g = r.group;
  furn(g, 7, 1.2, 1.2, '#5a3a24', 0, 0.6, -4); furn(g, 7.2, 0.1, 1.4, '#e9b43a', 0, 1.25, -4); signBoard(name, 0, 4.4, -6.3, 7, 1.2, { bg: '#5a3a24', fg: '#e9b43a', border: false }, g);
  for (const a of [-8, 8]) { add(new THREE.CylinderGeometry(0.5, 0.5, 7, 20), KM.white, a, 3.5, -3, g); pottedPlant(a, 0.5, 1.6, g, 0); }
  add(new THREE.SphereGeometry(1, 16, 10), toon({ color: '#ffe8a8', emissive: '#ffe8a8', emissiveIntensity: 0.8 }), 0, 5.6, -1, g); sofa(g, -5, 2, '#8e1f2a', 0); sofa(g, 5, 2, '#8e1f2a', 0); return { group: g }; };
const stoneM = () => toon({ map: P.tex(P.stone(4), 2, 2) });
const castle = (x, z) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); groundPaint(g, '#7aa64c', null, 540); const st = stoneM();
  add(new THREE.BoxGeometry(30, 9, 2), st, 0, 4.5, -16, g); for (const a of [-15, 15]) { add(new THREE.CylinderGeometry(3, 3.4, 14, 16), st, a, 7, -16, g); add(new THREE.ConeGeometry(3.6, 5, 16), KC('#2f4f8f'), a, 16.5, -16, g); }
  for (let i = 0; i < 12; i++) add(new THREE.BoxGeometry(1.2, 1.2, 2.2), st, -13.5 + i * 2.5, 9.6, -16, g); add(new THREE.BoxGeometry(5, 6, 2.4), KC('#3a2414'), 0, 3, -15.5, g);
  add(new THREE.BoxGeometry(0.06, 2, 1.2), KC('#c7322e'), 15, 20, -16, g); add(new THREE.CylinderGeometry(0.05, 0.05, 4, 6), KM.dark, 15, 20, -16.7, g); return { group: g }; };
const pyramidTomb = (x, z) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); const st = toon({ map: P.tex(P.stone(7), 3, 3), color: '#d9b77a' });
  const fl = add(new THREE.PlaneGeometry(16, 14), st, 0, 0.01, 0, g, { cast: false }); fl.rotation.x = -Math.PI / 2;
  for (const s_ of [-1, 1]) add(new THREE.BoxGeometry(0.4, 6, 14), st, s_ * 8, 3, 0, g); add(new THREE.BoxGeometry(16, 6, 0.4), st, 0, 3, -7, g); add(new THREE.BoxGeometry(16, 0.4, 14), st, 0, 6, 0, g);
  const sarc = furn(g, 3, 1.2, 1.4, '#c9a04a', 0, 0.6, -3.5); const lid = new THREE.Group(); lid.position.set(0, 1.2, -3.5); g.add(lid); furn(lid, 3.1, 0.25, 1.5, '#e9b43a', 0, 0.12, 0);
  for (const a of [-6, 6]) { furn(g, 0.2, 0.8, 0.2, '#5a3a24', a, 3.4, -6.7); add(new THREE.ConeGeometry(0.25, 0.6, 10), toon({ color: '#ffb020', emissive: '#ff7a1a', emissiveIntensity: 1 }), a, 4.1, -6.6, g); }
  return { group: g, open: (k) => { lid.position.x = 2.6 * k; lid.rotation.z = -0.3 * k; } }; };
const colosseum = (x, z) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); groundPaint(g, '#d9c08a', null, 540); const st = toon({ map: P.tex(P.stone(9), 6, 2), color: '#e8d6b0' });
  const ring = add(new THREE.CylinderGeometry(40, 40, 16, 64, 1, true, Math.PI * 0.15, Math.PI * 1.7), st, 0, 8, -10, g); ring.material.side = THREE.DoubleSide;
  for (let i = 0; i < 40; i++) { const a = Math.PI * 0.15 + i / 40 * Math.PI * 1.7; for (let lv = 0; lv < 3; lv++) add(new THREE.BoxGeometry(2, 2.6, 0.3), KC('#5a4a3a'), Math.sin(a) * 39.6, 2.5 + lv * 4.8, -10 + Math.cos(a) * 39.6, g).rotation.y = a; }
  return { group: g }; };
const pirateShip = (x, z, name = 'BLACK PEARL') => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); const sea = add(new THREE.PlaneGeometry(500, 500), KC('#2f6f9f'), 0, -1.6, 0, g, { cast: false }); sea.rotation.x = -Math.PI / 2; sea.userData.ndSkip = true;
  const hull = KC('#5a3a24'); add(new THREE.BoxGeometry(24, 4, 8), hull, 0, -0.4, 0, g); add(new THREE.BoxGeometry(6, 3, 8), hull, -10, 3, 0, g);
  const dk = add(new THREE.PlaneGeometry(24, 8), toon({ map: P.tex(floorTex('wood'), 8, 3) }), 0, 1.62, 0, g, { cast: false }); dk.rotation.x = -Math.PI / 2;
  for (const [a, h] of [[-3, 18], [5, 15]]) { add(new THREE.CylinderGeometry(0.3, 0.35, h, 10), KC('#3a2414'), a, h / 2, 0, g); const sl = add(new THREE.BoxGeometry(0.1, h * 0.5, 7), KC('#f1ead8'), a + 0.4, h * 0.6, 0, g); sl.rotation.y = 0.1; }
  add(new THREE.BoxGeometry(0.05, 1.6, 2.4), signMat('☠', { bg: '#17161b', fg: '#ffffff', border: false, w: 256, h: 256 }), -3, 19, 0, g);
  add(new THREE.BoxGeometry(8, 1.2, 0.05), signMat(name, { bg: '#5a3a24', fg: '#e9b43a', border: false, w: 1024, h: 160 }), 4, 0.6, 4.03, g); return { group: g }; };
const rock = (g, x, z, s = 1, c = '#7a6e62') => { const m = add(new THREE.DodecahedronGeometry(s, 0), KC(c), x, s * 0.6, z, g); m.rotation.set(x, z, s); return m; };
const treasureCave = (x, z) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); const fl = add(new THREE.PlaneGeometry(30, 30), KC('#5a4a3a'), 0, 0.01, 0, g, { cast: false }); fl.rotation.x = -Math.PI / 2;
  const dome = add(new THREE.SphereGeometry(14, 24, 16, 0, Math.PI * 2, 0, Math.PI / 2), KC('#4a3e34'), 0, 0, -2, g); dome.material.side = THREE.BackSide; dome.scale.y = 0.6;
  for (let i = 0; i < 14; i++) rock(g, -10 + (i * 7) % 20, -10 + (i * 5) % 8, 0.6 + (i % 4) * 0.5);
  coinPileAt(g, 3, -5); const ch = new THREE.Group(); ch.position.set(-2, 0, -4); g.add(ch); furn(ch, 2, 1.1, 1.2, '#7a5434', 0, 0.55, 0); furn(ch, 2.1, 0.12, 1.3, '#e9b43a', 0, 0.6, 0);
  const lid = new THREE.Group(); lid.position.set(0, 1.1, -0.6); ch.add(lid); furn(lid, 2, 0.4, 1.2, '#7a5434', 0, 0.2, 0.6);
  return { group: g, open: (k) => { lid.rotation.x = -1.6 * k; } }; };
function coinPileAt(g, x, z) { const m = add(new THREE.SphereGeometry(2.4, 20, 10, 0, Math.PI * 2, 0, Math.PI / 2), coinM, x, 0, z, g); m.scale.y = 0.4; const r_ = P.rng(3);
  for (let i = 0; i < 60; i++) { const a = r_() * 6.28, d = Math.sqrt(r_()) * 2.3; add(new THREE.CylinderGeometry(0.16, 0.16, 0.04, 10), [coinEdge, coinM, coinM], x + Math.cos(a) * d, 0.96 * Math.sqrt(Math.max(0, 1 - (d / 2.4) ** 2)) + 0.02, z + Math.sin(a) * d, g, { cast: false }).rotation.set(r_(), r_() * 6, r_()); } }
const jungle = (x, z, n = 50) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); groundPaint(g, '#4f7a2e', null, 540); const r_ = P.rng(15);
  for (let i = 0; i < n; i++) { const a = r_() * 6.28, d = 6 + r_() * 50; if (Math.abs(Math.sin(a) * d) < 4 && Math.cos(a) * d > 0) continue; const tx = Math.cos(a) * d, tz = Math.sin(a) * d - 8;
    furn(g, 0.6, 9, 0.6, '#6b4a2a', tx, 4.5, tz); for (let k = 0; k < 5; k++) { const lf = add(new THREE.SphereGeometry(2.2, 10, 6), KC(['#2f6b2e', '#3f8a3e', '#4f9a46'][k % 3]), tx + Math.cos(k) * 1.6, 9 + (k % 2), tz + Math.sin(k) * 1.6, g); lf.scale.y = 0.5; } }
  for (let i = 0; i < 20; i++) { const b = add(new THREE.SphereGeometry(0.9, 8, 6), KC('#3f8a3e'), -12 + (i * 5) % 24, 0.5, -3 - (i % 4) * 2, g); b.scale.y = 0.6; } return { group: g }; };
const volcano = (x, z) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); groundPaint(g, '#5a4a3a', null, 540);
  const v = add(new THREE.CylinderGeometry(8, 40, 40, 24, 1, true), KC('#4a3e34'), 0, 20, -80, g); v.material.side = THREE.DoubleSide; add(new THREE.CircleGeometry(8, 24), toon({ color: '#ff5a1a', emissive: '#ff5a1a', emissiveIntensity: 1 }), 0, 39.8, -80, g).rotation.x = -Math.PI / 2;
  const lava = []; for (let i = 0; i < 24; i++) lava.push(add(new THREE.SphereGeometry(1.2, 8, 6), toon({ color: '#ffb020', emissive: '#ff5a1a', emissiveIntensity: 1 }), 0, 40, -80, g, { cast: false }));
  const smoke = add(new THREE.SphereGeometry(10, 14, 10), KC('#5f5a58'), 0, 52, -80, g, { cast: false }); return { group: g, erupt: (k) => { smoke.scale.setScalar(0.6 + k * 1.4);
    lava.forEach((m, i) => { const a = i / 24 * 6.28, t = (k * 2 + i / 24) % 1; m.position.set(Math.cos(a) * t * 30, 40 + 30 * t - 40 * t * t, -80 + Math.sin(a) * t * 30); m.visible = k > 0; }); } }; };
const underwater = (x, z) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); groundPaint(g, '#d8c493', null, 540); const fish = [];
  for (let i = 0; i < 16; i++) rock(g, -20 + (i * 9) % 40, -6 - (i * 7) % 20, 0.8 + (i % 3), '#6f7f78');
  for (let i = 0; i < 12; i++) { const sw = furn(g, 0.12, 2 + (i % 4), 0.12, '#3f8a5e', -10 + i * 1.8, 1 + (i % 4) / 2, -4 - (i % 3)); }
  const wreck = new THREE.Group(); wreck.position.set(8, 0, -14); wreck.rotation.z = 0.25; g.add(wreck); furn(wreck, 14, 3, 4, '#5a3a24', 0, 1.2, 0); add(new THREE.CylinderGeometry(0.2, 0.2, 8, 8), KC('#3a2414'), 0, 5, 0, wreck);
  for (let i = 0; i < 9; i++) { const f = new THREE.Group(); scene.add(f); add(new THREE.SphereGeometry(0.35, 10, 6), KC(['#ff8a1a', '#ffd23f', '#2f78c4'][i % 3]), 0, 0, 0, f).scale.set(1.6, 1, 0.6); add(new THREE.ConeGeometry(0.3, 0.5, 4), KC('#ff8a1a'), -0.7, 0, 0, f).rotation.z = Math.PI / 2; fish.push([f, i]); }
  return { group: g, swim: (f_) => fish.forEach(([f, i]) => f.position.set(x - 10 + ((i * 7 + f_ * 0.05) % 20), 2 + (i % 4) + 0.3 * Math.sin(f_ * 0.1 + i), z - 4 - (i % 3) * 2)) }; };
const moonSurface = (x, z, mars = false) => { const g = new THREE.Group(); g.position.set(x, DECK, z); scene.add(g); groundPaint(g, mars ? '#c4643a' : '#b9b6ad', null, 540);
  const r_ = P.rng(mars ? 9 : 19); for (let i = 0; i < 18; i++) { const c = add(new THREE.TorusGeometry(1.5 + r_() * 3, 0.35, 6, 20), KC(mars ? '#a8522e' : '#9a978e'), -30 + r_() * 60, 0.1, -6 - r_() * 40, g); c.rotation.x = Math.PI / 2; }
  const lander = new THREE.Group(); lander.position.set(6, 0, -8); g.add(lander); furn(lander, 3, 2, 3, '#e9b43a', 0, 2.6, 0); for (const [a, b] of [[-1.8, -1.8], [1.8, -1.8], [-1.8, 1.8], [1.8, 1.8]]) add(new THREE.CylinderGeometry(0.08, 0.08, 2.6, 6), KM.steel, a, 1.1, b, lander).rotation.z = a * 0.12;
  add(new THREE.CylinderGeometry(0.04, 0.04, 3, 6), KM.white, -3, 1.5, -4, g); add(new THREE.BoxGeometry(1.4, 0.9, 0.02), signMat('', { bg: '#ffffff', border: false, w: 256, h: 160 }), -2.3, 2.6, -4, g);
  if (!mars) earth(x - 40, 60, z - 200, 14); return { group: g }; };
const marsSurface = (x, z) => moonSurface(x, z, true);
// ===== end of batch 8 =====







