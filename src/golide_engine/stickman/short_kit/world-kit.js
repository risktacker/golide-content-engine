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
const city = (x0, x1, zNear = -18, seed = 21) => { const r = P.rng(seed);
  for (let x = x0; x < x1; x += 6 + r() * 5) tower(x, zNear - r() * 30, 5 + r() * 7, 5 + r() * 6, 12 + r() * 38);
  for (let i = 0; i < 50; i++) { const a = r() * Math.PI * 2, d = 160 + r() * 200; tower(Math.cos(a) * d, Math.sin(a) * d, 12 + r() * 16, 12 + r() * 16, 30 + r() * 90); } };
const street = (x0, x1, z = 10) => { const g = add(new THREE.PlaneGeometry(2400, 2400), KM.road, 0, DECK, 0, scene, { cast: false }); g.rotation.x = -Math.PI / 2;
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
  add(new THREE.BoxGeometry(0.9, 0.45, 0.04), screenTex('reels', reels), 0, 1.35, 0.46, g);
  add(new THREE.BoxGeometry(1.05, 0.5, 0.5), screenTex('jackpot', top), 0, 2.25, 0.1, g);
  add(new THREE.BoxGeometry(1.0, 0.1, 0.35), KM.dark, 0, 0.95, 0.55, g);
  const arm = add(new THREE.CylinderGeometry(0.04, 0.04, 0.8, 8), KM.steel, 0.62, 1.4, 0, g); add(new THREE.SphereGeometry(0.1, 12, 8), KM.red, 0.62, 1.82, 0, g); g.arm = arm;
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

