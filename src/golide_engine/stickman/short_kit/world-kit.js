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
