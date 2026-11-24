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
const SKY = { day: ['#5b96d3', '#9fb6e6'],   /* Rick's day sky, measured: upper #5b96d3, horizon #9fb6e6 */ dusk: ['#5b4a7a', '#ffb07a'], night: ['#0d1630', '#2a3a5e'], overcast: ['#aab3bb', '#d8dcdf'] };
const SPEED = { walk: 1.3, run: 3.4, sneak: 0.7 };
const HAND_DO = new Set(['hold', 'pick-up', 'use', 'give', 'throw', 'kick', 'put-down', 'work', 'carry', 'kneel']);

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
    const day = !/sunset|dusk|night|dawn|storm/.test(W.sky || 'day');   // Ricks Clips is a bright cartoon day unless the script says otherwise
    const sky = day ? new THREE.Mesh(new THREE.SphereGeometry(1800, 32, 16), new THREE.ShaderMaterial({ side: THREE.BackSide, depthWrite: false, fog: false,
        vertexShader: 'varying vec3 vp; void main(){ vp = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
        fragmentShader: `varying vec3 vp; void main(){ float h = vp.y; vec3 c = mix(vec3(0.86,0.94,1.0), vec3(0.52,0.78,1.0), smoothstep(0.0, 0.12, h));
          c = mix(c, vec3(0.27,0.6,0.98), smoothstep(0.1, 0.4, h)); c = mix(c, vec3(0.16,0.45,0.92), smoothstep(0.4, 0.9, h)); c = mix(c, vec3(0.7,0.82,0.9), smoothstep(0.0, -0.05, h)); gl_FragColor = vec4(c, 1.0); }` }))
      : new THREE.Mesh(new THREE.SphereGeometry(1800, 32, 16), new THREE.MeshBasicMaterial({ map: st, side: THREE.BackSide, fog: false, depthWrite: false }));
    sky.renderOrder = -1; G.add(sky);
    if (day) {   // flat cartoon clouds in three rings (the engine's own clouds)
      let sd = 11; const R = () => (sd = (sd * 9301 + 49297) % 233280) / 233280;
      const cloudM = (fade) => new THREE.ShaderMaterial({ fog: false, uniforms: { fade: { value: fade } },
        vertexShader: 'varying vec3 vN; void main(){ vN = normalize(mat3(modelMatrix) * normal); gl_Position = projectionMatrix * viewMatrix * modelMatrix * vec4(position, 1.0); }',
        fragmentShader: `uniform float fade; varying vec3 vN; void main(){ float l = dot(normalize(vN), normalize(vec3(-0.7, 0.15, 0.6)));
          vec3 top = vec3(1.0), mid = vec3(0.95, 0.97, 1.0), bot = vec3(0.74, 0.82, 0.94); vec3 c = l > 0.35 ? top : (l > -0.1 ? mid : bot); c = mix(c, vec3(0.86, 0.92, 1.0), fade); gl_FragColor = vec4(c, 1.0); }` });
      for (const [n, d0, d1, sz, fade] of [[10, 420, 700, 0.8, 0.0], [14, 800, 1200, 1.2, 0.25], [16, 1300, 1700, 1.6, 0.5]]) { const m = cloudM(fade);
        for (let i = 0; i < n; i++) { const g2 = new THREE.Group(), a = R() * Math.PI * 2, dist = d0 + R() * (d1 - d0); g2.position.set(Math.sin(a) * dist, 90 + R() * 130 * sz, Math.cos(a) * dist);
          const w = (50 + R() * 60) * sz, puffs = 9 + Math.floor(R() * 8);
          for (let k = 0; k < puffs; k++) { const u = R() * 2 - 1, r = w * (0.22 + R() * 0.2) * (1 - Math.abs(u) * 0.45); const s2 = new THREE.Mesh(new THREE.IcosahedronGeometry(1, 3), m); s2.scale.set(r * 1.15, r, r);
            s2.position.set(u * w, Math.max(0, r * 0.55 - Math.abs(u) * w * 0.12) + R() * r * 0.4, (R() - 0.5) * w * 0.35); g2.add(s2); }
          g2.lookAt(0, g2.position.y, 0); G.add(g2); } } }
    scene.background = new THREE.Color(hor); scene.fog.color.set(hor); scene.fog.near = Math.max(SW, SD) * 4; scene.fog.far = Math.max(SW, SD) * 4 + 1400;   // wide views from far off stay clear
    room = { min: V(-SW / 2 - 300, 0.03, -SD / 2 - 300), max: V(SW / 2 + 300, 200, SD / 2 + 300) };   // outdoors the camera may stand far off for a wide view
  }
  { const { RoomEnvironment } = await import('three/addons/environments/RoomEnvironment.js'); const pm = new THREE.PMREMGenerator(K.renderer); scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture; scene.environmentIntensity = IN ? 0.55 : 0.4; }

  // ---- Rick's look (owner 2026-11-24, his pirates Short): toon shading with painted surfaces and a constant ~3 px ink
  // line drawn as an inverted hull around every set piece (the engine's own way for its puppets); the screen-space ink
  // pass of 2026-11-23 is gone: it flickered on the puppets' thin limbs ----
  const { mergeVertices } = await import('three/addons/utils/BufferGeometryUtils.js');
  const GKIND = (() => { const g = `${W.ground || ''} ${W.place || ''}`.toLowerCase(); return /sea|ocean|water|lake|river|harbou?r|bay/.test(g) ? 'water' : /deck|plank|wooden floor|boards/.test(g) ? 'planks'
    : /cobble|paving|paved|stone|flagstone|plaza|courtyard|fort/.test(g) ? 'stone' : /sand|beach|desert|dune/.test(g) ? 'sand' : /brick/.test(g) ? 'brick' : /rock|canyon|cliff|mountain/.test(g) ? 'rock' : IN ? null : 'grass'; })();
  const INK_PX = 2.6, inkRes = new THREE.Vector2(1080, 1920);
  const inkMat = new THREE.ShaderMaterial({ side: THREE.BackSide, uniforms: { res: { value: inkRes }, px: { value: INK_PX } },
    vertexShader: `uniform vec2 res; uniform float px; varying float vD; void main() { vec4 mv = modelViewMatrix * vec4(position, 1.0); vD = -mv.z; vec4 c = projectionMatrix * mv;
      vec3 n = normalize(normalMatrix * normal); vec2 d = (projectionMatrix * vec4(n, 0.0)).xy; float l = length(d); if (l > 1e-5) c.xy += d / l * px * 2.0 / res * c.w; gl_Position = c; }`,
    fragmentShader: 'varying float vD; void main() { if (vD < 1.5) discard; gl_FragColor = vec4(0.086, 0.067, 0.059, 1.0); }' });   /* no ink sheet when the lens is right at a thing */
  const inked = (mesh) => { const g = mesh.geometry.clone(); for (const k of Object.keys(g.attributes)) if (k !== 'position') g.deleteAttribute(k);
    const h = new THREE.Mesh(mergeVertices(g, 1e-4), inkMat); h.geometry.computeVertexNormals(); h.castShadow = false; h.receiveShadow = false; h.userData.ink = true; h.raycast = () => {}; mesh.add(h); return mesh; };
  // painted surfaces: neutral detail tinted by the part's own colour (toon map), tiled by real metres (box projection)
  const PAINT = {}, TILE = { planks: 1.2, wood: 0.9, brick: 1.0, stone: 1.6, rock: 3, metal: 1.2, iron: 1.2, rope: 0.25, cloth: 1.6, water: 7, sand: 2.5, grass: 2.5, leather: 0.8 };
  const paint = (kind) => { if (PAINT[kind] !== undefined) return PAINT[kind]; if (!TILE[kind]) return (PAINT[kind] = null);
    const N = 256, c = document.createElement('canvas'); c.width = c.height = N; const g = c.getContext('2d'); let sd = 7 + kind.length * 13; const R = () => (sd = (sd * 9301 + 49297) % 233280) / 233280;
    const sh = (v) => `rgb(${v},${v},${v})`; g.fillStyle = '#fff'; g.fillRect(0, 0, N, N);
    if (kind === 'planks' || kind === 'wood') { const rows = kind === 'planks' ? 4 : 1;
      for (let r = 0; r < rows; r++) { const y0 = r * N / rows, hh = N / rows; g.fillStyle = sh(232 + Math.floor(R() * 23)); g.fillRect(0, y0, N, hh);
        for (let k = 0; k < 7; k++) { g.strokeStyle = `rgba(90,55,30,${0.12 + R() * 0.12})`; g.lineWidth = 1 + R() * 2; g.beginPath(); const yy = y0 + R() * hh; g.moveTo(0, yy); for (let x = 0; x <= N; x += 32) g.lineTo(x, yy + Math.sin(x / 40 + R() * 3) * 3); g.stroke(); }
        if (rows > 1) { g.fillStyle = 'rgba(60,35,20,0.55)'; g.fillRect(0, y0, N, 3); const jx = R() * N; g.fillRect(jx, y0, 3, hh); g.fillStyle = 'rgba(60,35,20,0.5)'; g.beginPath(); g.arc(jx + 10, y0 + hh / 2, 2, 0, 7); g.arc(jx - 8, y0 + hh / 2, 2, 0, 7); g.fill(); } } }
    else if (kind === 'brick') { g.fillStyle = sh(238); g.fillRect(0, 0, N, N); const rows = 8, cols = 4, bh = N / rows, bw = N / cols;
      for (let r = 0; r < rows; r++) for (let k = -1; k <= cols; k++) { const x = k * bw + (r % 2 ? bw / 2 : 0); g.fillStyle = `rgb(${200 + Math.floor(R() * 40)},${150 + Math.floor(R() * 30)},${140 + Math.floor(R() * 25)})`; g.fillRect(x + 3, r * bh + 3, bw - 6, bh - 6); } }
    else if (kind === 'stone' || kind === 'rock') { const n = kind === 'stone' ? 4 : 3, cs = N / n; g.fillStyle = sh(150); g.fillRect(0, 0, N, N);
      for (let a = 0; a < n; a++) for (let b = 0; b < n; b++) { g.fillStyle = sh(205 + Math.floor(R() * 45)); const j = () => (R() - 0.5) * cs * 0.12; g.beginPath(); g.moveTo(a * cs + 4 + j(), b * cs + 4 + j()); g.lineTo((a + 1) * cs - 4 + j(), b * cs + 4 + j()); g.lineTo((a + 1) * cs - 4 + j(), (b + 1) * cs - 4 + j()); g.lineTo(a * cs + 4 + j(), (b + 1) * cs - 4 + j()); g.closePath(); g.fill(); } }
    else if (kind === 'metal' || kind === 'iron') { const gr = g.createLinearGradient(0, 0, N, 0); gr.addColorStop(0, sh(220)); gr.addColorStop(0.45, sh(255)); gr.addColorStop(0.55, sh(240)); gr.addColorStop(1, sh(215)); g.fillStyle = gr; g.fillRect(0, 0, N, N); }
    else if (kind === 'rope') { for (let k = -N; k < N * 2; k += 24) { g.strokeStyle = sh(200); g.lineWidth = 9; g.beginPath(); g.moveTo(k, 0); g.lineTo(k + N, N); g.stroke(); } }
    else if (kind === 'cloth') { for (let k = 0; k < N; k += 4) { g.fillStyle = 'rgba(0,0,0,0.035)'; g.fillRect(k, 0, 1, N); g.fillRect(0, k, N, 1); } g.fillStyle = 'rgba(0,0,0,0.12)'; g.fillRect(0, N / 2, N, 2); }
    else if (kind === 'water') { g.fillStyle = sh(235); g.fillRect(0, 0, N, N); for (let k = 0; k < 34; k++) { g.strokeStyle = `rgba(255,255,255,${0.5 + R() * 0.5})`; g.lineWidth = 2 + R() * 2; const x = R() * N, y = R() * N, w = 14 + R() * 30; g.beginPath(); g.moveTo(x, y); g.quadraticCurveTo(x + w / 2, y - 5, x + w, y); g.stroke(); } }
    else { for (let k = 0; k < 2200; k++) { g.fillStyle = `rgba(0,0,0,${R() * 0.08})`; g.fillRect(R() * N, R() * N, 1 + R() * 2, 1 + R() * 2); } }
    const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return (PAINT[kind] = t); };
  const MATWORD = [[/plank|deck|floor ?board|hull|bulwark|rail|gunwale|quarterdeck/, 'planks'], [/brick|chimney|furnace|oven|kiln/, 'brick'], [/stone|paving|cobble|wall of rock|pier|quay|battery wall/, 'stone'], [/rock|cliff|boulder|pillar of rock/, 'rock'],
    [/barrel(?!.*gun)|crate|chest|hull|rail|mast|bowsprit|yard|oar|cart|wheel|carriage|table|chair|bench|stool|door|frame|post|pole|beam|log|wood|staff|handle|keg|box|shelf|ladder|hut|fence|boat/, 'wood'],
    [/cannon|barrel of the gun|muzzle|gun|anchor|chain|iron|steel|metal|blade|sword|pipe|tongs|shovel|hoop|band|rivet|plate|pot|kettle|engine|tank|machine/, 'metal'],
    [/sail|flag|cloth|banner|curtain|tent|blanket|sack|bag|shirt|coat/, 'cloth'], [/rope|rigging|line|net/, 'rope'], [/water|sea|wave|river|lake|ocean/, 'water'], [/sand|beach|dune/, 'sand'], [/grass|lawn|hedge|bush|leaf|leaves|palm top|tree top/, 'grass']];
  const matOf = (p) => p.gold ? 'gold' : (p.mat || (MATWORD.find(([re]) => re.test(p.name || '')) || [0, null])[1]);
  const boxUV = (geo, k, tile) => { const P = geo.attributes.position, Nn = geo.attributes.normal, uv = new Float32Array(P.count * 2);
    for (let i = 0; i < P.count; i++) { const nx = Math.abs(Nn.getX(i)), ny = Math.abs(Nn.getY(i)), nz = Math.abs(Nn.getZ(i)), x = P.getX(i) * k / tile, y = P.getY(i) * k / tile, z = P.getZ(i) * k / tile;
      if (ny >= nx && ny >= nz) { uv[i * 2] = x; uv[i * 2 + 1] = z; } else if (nx >= nz) { uv[i * 2] = z; uv[i * 2 + 1] = y; } else { uv[i * 2] = x; uv[i * 2 + 1] = y; } }
    geo.setAttribute('uv', new THREE.BufferAttribute(uv, 2)); };
  const toonOf = (col, kind) => { if (kind === 'gold') return SR.toon('#e0b040', { rim: 0.9 }); if (kind === 'glass') { const m = SR.toon(col); m.transparent = true; m.opacity = 0.45; return m; }
    if (kind === 'fire') { return new THREE.MeshBasicMaterial({ color: col || '#ff8a2a', toneMapped: false }); }
    const t = paint(kind), m = SR.toon(col, { rim: 0, kick: 0, flat2: true, ...(t ? { map: t } : {}) }); m.emissive = new THREE.Color(col).multiplyScalar(0.32); if (t) m.emissiveMap = t; return m; };   /* shade stays warm and coloured (Ricks: no black sides) */   /* two bright bands like Ricks: a side in shade is never near-black */   /* no rim light on set pieces: it bleached big flat decks white */
  if (GKIND) for (const pl of [ground, G.children.find(o => o.isMesh && o !== ground && o.geometry?.parameters?.width === 4000)].filter(Boolean)) {   // the ground painted like the place
    pl.material = toonOf(GKIND === 'water' ? (W.ground_color || '#2fb3c9') : gcol, GKIND); boxUV(pl.geometry, 1, TILE[GKIND] || 2); pl.receiveShadow = true; }

  // ---- things: a library model found by name, or the thing's own parts; scaled to its real height ----
  const { GLTFLoader } = await import('three/addons/loaders/GLTFLoader.js'); const GL = new GLTFLoader();
  const { RoundedBoxGeometry } = await import('three/addons/geometries/RoundedBoxGeometry.js');
  const lathe = (prof) => { const n = prof.length, pts = [V(0, -0.5, 0)], cv = new THREE.CatmullRomCurve3(prof.map((r, i) => V(Math.max(0.001, r * 0.5), -0.5 + i / (n - 1), 0)));
    for (const q of cv.getPoints(Math.max(8, n * 5))) pts.push(new THREE.Vector2(q.x, q.y)); pts.push(new THREE.Vector2(0, 0.5)); pts[0] = new THREE.Vector2(0, -0.5); return new THREE.LatheGeometry(pts, 36); };
  const loft = (top, bot) => { const g = new THREE.BufferGeometry(), v = [], n = top.length, tri = (a, b, c) => v.push(...a, ...b, ...c);
    const T3 = top.map(([x, z]) => [x, 0.5, z]), B3 = bot.map(([x, z]) => [x, -0.5, z]);
    for (let i = 0; i < n; i++) { const a = T3[i], b = T3[(i + 1) % n], c = B3[(i + 1) % n], d = B3[i]; tri(a, d, c); tri(a, c, b); }
    for (let i = 1; i < n - 1; i++) { tri(T3[0], T3[i + 1], T3[i]); tri(B3[0], B3[i], B3[i + 1]); }
    let vol = 0; for (let i = 0; i < v.length; i += 9) vol += v[i] * (v[i + 4] * v[i + 8] - v[i + 5] * v[i + 7]) - v[i + 1] * (v[i + 3] * v[i + 8] - v[i + 5] * v[i + 6]) + v[i + 2] * (v[i + 3] * v[i + 7] - v[i + 4] * v[i + 6]);
    if (vol < 0) for (let i = 0; i < v.length; i += 9) for (let k = 0; k < 3; k++) { const t = v[i + 3 + k]; v[i + 3 + k] = v[i + 6 + k]; v[i + 6 + k] = t; }   /* faces point outward */
    g.setAttribute('position', new THREE.Float32BufferAttribute(v, 3)); g.computeVertexNormals(); return g; };
  const SHAPE = { box: (p) => p.round ? new RoundedBoxGeometry(1, 1, 1, 3, 0.12) : new THREE.BoxGeometry(1, 1, 1), cyl: () => new THREE.CylinderGeometry(0.5, 0.5, 1, 32),
    taper: (p) => new THREE.CylinderGeometry(0.5 * (p.taper ?? 0.6), 0.5, 1, 32), turned: (p) => lathe(p.profile || [0.8, 1, 0.8]),
    sphere: () => new THREE.SphereGeometry(0.5, 32, 18), cone: () => new THREE.ConeGeometry(0.5, 1, 32), ring: () => new THREE.TorusGeometry(0.4, 0.1, 12, 40).rotateX(Math.PI / 2).scale(1, 5, 1),
    wedge: () => loft([[-0.5, -0.5], [0.5, -0.5], [0.5, -0.49], [-0.5, -0.49]], [[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]]),
    prow: () => loft([[-0.5, -0.5], [0.22, -0.5], [0.5, 0], [0.22, 0.5], [-0.5, 0.5]], [[-0.44, -0.3], [0.16, -0.3], [0.42, 0], [0.16, 0.3], [-0.44, 0.3]]) };
  const things = {}, list = [];
  const label = (text, w) => { const c = document.createElement('canvas'); c.width = 1024; c.height = 256; const g = c.getContext('2d'); g.fillStyle = '#fbf7ef'; g.fillRect(0, 0, 1024, 256);
    g.fillStyle = '#17141a'; let f = 170; g.font = `${f}px Anton`; while (g.measureText(text).width > 960 && f > 40) { f -= 8; g.font = `${f}px Anton`; } g.textAlign = 'center'; g.fillText(text, 512, 128 + f * 0.36);
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; const m = new THREE.Mesh(new THREE.PlaneGeometry(w, w / 4), new THREE.MeshBasicMaterial({ map: t, toneMapped: false })); m.userData.draw = (s) => { g.fillStyle = '#fbf7ef'; g.fillRect(0, 0, 1024, 256); g.fillStyle = '#17141a'; let ff = 170; g.font = `${ff}px Anton`; while (g.measureText(s).width > 960 && ff > 40) { ff -= 8; g.font = `${ff}px Anton`; } g.fillText(s, 512, 128 + ff * 0.36); t.needsUpdate = true; }; return m; };
  for (const T of B.things || []) {
    const L = LIB.find(x => x.id === T.id) || {}; let obj = null;
    if (L.model) { try { const g = await GL.loadAsync(L.model); obj = g.scene.clone(true); obj.traverse(m => { if (m.isMesh) { m.castShadow = m.receiveShadow = true; } }); } catch (e) { console.warn('board: model failed', T.id, e); obj = null; } }
    if (!obj && (L.parts || []).length) { obj = new THREE.Group();
      for (const p of L.parts) { const kind = matOf(p), geo = (SHAPE[p.shape] || SHAPE.box)(p).scale(...p.s); if (!geo.attributes.normal) geo.computeVertexNormals();
        const m = new THREE.Mesh(geo, toonOf(p.color || T.color || '#9aa0a6', kind)); m.position.set(...p.c); m.rotation.set(...p.r); m.castShadow = m.receiveShadow = true; m.name = p.name; m.userData.kind = kind; inked(m); obj.add(m); } }
    if (!obj) { obj = new THREE.Group(); const m = new THREE.Mesh(SHAPE.box(), new THREE.MeshStandardMaterial({ color: T.color || '#9aa0a6', roughness: 0.7 })); m.position.y = 0.5; obj.add(m); { const lb = label(T.name, 1.2); lb.position.set(0, 0.5, 0.51); obj.add(lb); } }
    if (T.color && L.model) obj.traverse(m => { if (m.isMesh && m.material) { m.material = m.material.clone(); m.material.color?.lerp(new THREE.Color(T.color), 0.5); } });
    if (L.model) { const ms = []; obj.traverse(m => { if (m.isMesh && !m.userData.ink) ms.push(m); }); ms.forEach(inked); }
    const holder = new THREE.Group(); holder.name = T.name; holder.userData.thing = T.id; holder.add(obj);
    obj.updateMatrixWorld(true); let bb = new THREE.Box3().setFromObject(obj); const sz = bb.getSize(V(0, 0, 0));
    const k = (T.height_m || 1) / Math.max(sz.y, 1e-4); obj.scale.multiplyScalar(k); obj.updateMatrixWorld(true);
    obj.traverse(m => { if (m.isMesh && m.userData.kind && TILE[m.userData.kind]) boxUV(m.geometry, k, TILE[m.userData.kind]); });
    bb = new THREE.Box3().setFromObject(obj); const cc = bb.getCenter(V(0, 0, 0)); obj.position.x -= cc.x; obj.position.z -= cc.z; obj.position.y -= bb.min.y;
    const s2 = bb.getSize(V(0, 0, 0)); holder.userData.longX = s2.x >= s2.z; holder.userData.size = s2;
    if (T.text) {   // the words go on the thing's biggest flat face (a banner's cloth, a sign's board, a screen), sized to it
      let face = null; const signy = obj.children.filter(m => /sign|label|plate|board|banner|screen|plaque|name/.test(m.name || ''));
      if (!L.model) for (const m of (signy.length ? signy : obj.children)) { const b = new THREE.Box3().setFromObject(m), z = b.getSize(V(0, 0, 0)); if (!face || z.x * z.y > face.a) face = { a: z.x * z.y, b }; }
      const fb = face ? face.b : new THREE.Box3(V(-s2.x / 2, s2.y * 0.35, -s2.z / 2), V(s2.x / 2, s2.y * 0.85, s2.z / 2)), fs = fb.getSize(V(0, 0, 0)), fc = fb.getCenter(V(0, 0, 0));
      const w = Math.max(0.3, Math.min(fs.x * 0.92, fs.y * 0.92 * 4, 1.8)); const lb = label(T.text, w);   /* a real sign's size, never a billboard */ lb.position.set(fc.x, fc.y, fb.max.z + 0.02); holder.add(lb); holder.userData.sign = lb; }
    holder.rotation.y = THREE.MathUtils.degToRad(T.turn_deg || 0); G.add(holder);
    const th = { id: T.id, T, obj: holder, inner: obj, base: V(T.at[0], T.at.length > 2 ? T.at[2] : 0, T.at[1]), yaw0: holder.rotation.y, size: s2, parts: obj.children.slice(), hero: !!T.hero };
    things[T.id] = th; list.push(th); }
  // ---- surfaces: a deck, a roof, a stage, a table top. People and things stand on the real top of what is under them
  // (a ray down through the thing's own meshes, sails and walls skipped by their slope), never on its bounding box ----
  const RC = new THREE.Raycaster(), DOWN = V(0, -1, 0), NM = new THREE.Matrix3(), surf = new Map();
  const footprint = (th, shrink = 0) => { th.obj.updateMatrixWorld(true); const b = new THREE.Box3().setFromObject(th.inner); b.min.x += shrink; b.min.z += shrink; b.max.x -= shrink; b.max.z -= shrink; return b; };
  const inside = (b, p) => p.x >= b.min.x && p.x <= b.max.x && p.z >= b.min.z && p.z <= b.max.z;
  function surfaceAt(th, x, z, room = 1.8) {   // height of the lowest upward top of th at world (x, z) with `room` free above it (a deck under the sails, a table top), or null
    const loc = th.obj.worldToLocal(V(x, 0, z)), key = `${th.id}:${loc.x.toFixed(1)},${loc.z.toFixed(1)}:${room.toFixed(1)}`;
    if (surf.has(key)) { const h = surf.get(key); return h === null ? null : th.obj.position.y + h; }
    const top = footprint(th).max.y + 2; RC.set(V(x, top, z), DOWN); RC.far = top + 1; let h = null;
    const hits = RC.intersectObject(th.inner, true).filter(q => !q.object.userData.proxy && q.face), y0 = th.obj.position.y;
    const ups = hits.filter(q => q.face.normal.clone().applyMatrix3(NM.getNormalMatrix(q.object.matrixWorld)).normalize().y > 0.5)   /* the normal matrix: parts are scaled unevenly */.map(q => q.point.y).sort((a2, b2) => a2 - b2);
    for (const u of ups) { if (u - y0 < 0.05) continue; if (!hits.some(q => q.point.y > u + 0.02 && q.point.y < u + room)) { h = u - y0; break; } }
    surf.set(key, h); return h === null ? null : y0 + h; }
  for (const th of list) { th.obj.position.copy(th.base); th.obj.rotation.y = th.yaw0; th.obj.updateMatrixWorld(true); }
  for (const th of list) if (th.T.on && things[th.T.on]) { const o = things[th.T.on]; th.base.y = surfaceAt(o, th.base.x, th.base.z, Math.max(0.05, th.size.y * 0.9)) ?? o.size.y; }   // standing on another thing's real top
  // clusters: one entry stands for count copies scattered within spread metres, each turned and sized a little differently
  const rnd = (seed => () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; });
  const copies = [];
  for (const th of list) { const n = Math.max(1, th.T.count || 1) - 1; if (!n) continue; const r = rnd([...th.id].reduce((a, ch) => a * 31 + ch.charCodeAt(0), 7) % 2147483646 + 1), sp = Math.max(0.5, th.T.spread || 2);
    const ar = th.T.arrange || 'scatter', sz = th.size;
    for (let i = 0; i < n; i++) { const a = r() * Math.PI * 2, o = th.inner.clone(true), h = new THREE.Group(); h.add(o); h.name = th.T.name; h.userData.thing = th.id; let x = 0, y = 0, z = 0;
      if (ar === 'heap') { const d = sp * Math.sqrt(r()); x = Math.cos(a) * d; z = Math.sin(a) * d; y = Math.max(0, (1 - d / sp) * sp * 0.75 - sz.y * 0.5 * r()); }   // a mound, highest in the middle
      else if (ar === 'stack') { y = (i + 1) * sz.y * 0.98; x = (r() - 0.5) * sz.x * 0.08; z = (r() - 0.5) * sz.z * 0.08; }
      else if (ar === 'row') { x = (i + 1) * Math.max(sz.x, 0.1) * 1.1; }
      else { const d = sp * Math.sqrt(r()); x = Math.cos(a) * d; z = Math.sin(a) * d; }
      h.position.set(th.base.x + x, th.base.y + y, th.base.z + z); h.rotation.y = ar === 'stack' || ar === 'row' ? th.yaw0 + (r() - 0.5) * 0.15 : r() * Math.PI * 2; h.scale.setScalar(ar === 'scatter' || ar === 'heap' ? 0.8 + 0.4 * r() : 1); G.add(h); h.updateMatrixWorld(true);
      copies.push({ th, obj: h, phase: r() * 6.28, y0: h.position.y, ry0: h.rotation.y }); } }

  // ---- cast ----
  const cast = {}, people = [];
  (B.cast || []).forEach((m, i) => { const L = m.look || {}, of = OUTFITS[L.outfit] || OUTFITS.shirt, col = L.color || '#2f3542', acc = L.accent || '#c8352f';
    const dark = '#' + new THREE.Color(col).multiplyScalar(0.72).getHexString(), pat = of.pattern === 'vest' ? ['vest', dark] : (L.pattern && L.pattern !== 'none' ? [L.pattern, acc] : undefined);
    const c = SR.build({ ...base, jacket: col, jacket2: dark, style: of.style, civil: of.civil, details: of.details, pattern: pat, tieCol: acc, hankyCol: '#f2cf2c', btn: '#d9d9d9', collarCol: '#ffffff', logoCol: acc,
      hat: HATS[L.hat], hatCol: L.hat === 'chef' ? '#ffffff' : L.hat === 'hardhat' ? '#f2c12c' : acc, glasses: !!L.glasses });
    c.root.scale.setScalar(0.8); c.phase = 0.4 + i * 0.7; c.root.rotation.order = 'YXZ'; c.tint = c.hm.material.uniforms.base.value.clone(); ALL.push(c);
    c.label = m.label || m.id; c.id = m.id; c.start = V(m.at[0], 0, m.at[1]); c.spot = c.start; c.yaw0 = THREE.MathUtils.degToRad(m.turn_deg || 0); cast[m.id] = c; people.push(c); });
  const byId = id => cast[id] || (things[id] && things[id].obj) || null;
  // things people stand on: any thing above 0.3 m whose footprint holds a person's start or a walk spot
  const standOn = list.filter(th => th.size.y > 0.3 && (th.T.count || 1) <= 1);
  const stoodOn = new Set();
  for (const c of people) { for (const th of standOn) { const b = footprint(th, 0.05); const spots = [c.start, ...(B.beats || []).filter(b2 => b2.who === c.id && b2.to && b2.to.length === 2).map(b2 => V(b2.to[0], 0, b2.to[1]))];
      if (spots.some(q => inside(b, q) && (surfaceAt(th, q.x, q.z) ?? 0) > 0.3)) stoodOn.add(th); }
    let best = null; for (const th of stoodOn) { const y = inside(footprint(th, 0.05), c.start) ? surfaceAt(th, c.start.x, c.start.z) : null; if (y !== null && y > 0.3 && (!best || y > best.y)) best = { th, y }; }
    c.platform = best ? best.th : null; }   // they move with it when it moves (a ship sails, a cart rolls)
  console.log('GOLIDE stood on: ' + [...stoodOn].map(th => th.id).join(', ') + ' | ' + people.map(c => `${c.id}@${c.platform ? c.platform.id + ':' + surfaceAt(c.platform, c.start.x, c.start.z)?.toFixed(2) : '-'}`).join(' '));

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
    for (const e of events.get(th)) { if (e.do !== 'move' || t < e.t) continue; const pts = [p.clone(), ...(e.path.length ? e.path : [e.to]).map(q => V(q[0], q.length > 2 ? q[2] : th.base.y, q[1]))];
      let len = 0; const seg = []; for (let i = 1; i < pts.length; i++) { const d = pts[i].distanceTo(pts[i - 1]); seg.push(d); len += d; }
      const dur = e.t1 > e.t + 0.05 ? Math.max(0.3, e.t1 - e.t) : Math.max(Math.min(6, len / 6), 0.6),   /* a written until is kept: a shot ball flies fast */ u = clamp((t - e.t) / dur) * len; let acc = 0;
      for (let i = 0; i < seg.length; i++) { if (u <= acc + seg[i] || i === seg.length - 1) { const k = seg[i] ? clamp((u - acc) / seg[i]) : 1; p = pts[i].clone().lerp(pts[i + 1], k);
        const d = pts[i + 1].clone().sub(pts[i]); if (d.lengthSq() > 1e-6) yaw = Math.atan2(d.x, d.z) - (th.obj.userData.longX ? Math.PI / 2 : 0); break; } acc += seg[i]; } }
    return { p, yaw }; };
  const handOf = new Map();                                             // a thing's hand interactions in time order
  for (const c of people) for (const b of beats.get(c)) if ((HAND_DO.has(b.do) || SPEED[b.do]) && b.with && things[b.with]) { const th = things[b.with]; if (!handOf.has(th)) handOf.set(th, []); handOf.get(th).push({ ...b, c }); }
  handOf.forEach(l => l.sort((a, b) => a.t - b.t));
  const handPos = (c, t) => { const s = pathAt(c, t); return s.p.clone().add(V(Math.sin(s.yaw) * 0.32, 0.95, Math.cos(s.yaw) * 0.32)); };
  const destOf = (b, t) => b.to && b.to.length === 2 ? V(b.to[0], 0, b.to[1]) : b.target ? (spotOf(b.target, t) || V(0, 0, 0)) : pathAt(b.c, t).p.clone().add(V(Math.sin(pathAt(b.c, t).yaw) * 6, 0, Math.cos(pathAt(b.c, t).yaw) * 6));
  // holder at time t: { c } (in hand), or a free position, or a flight
  function carry(th, t) {
    let st = { free: true }, from = null;
    for (const b of handOf.get(th) || []) { if (t < b.t) break;
      if (b.do === 'hold' || b.do === 'pick-up' || b.do === 'use' || b.do === 'work' || b.do === 'carry' || b.do === 'kneel' || SPEED[b.do]) st = { c: b.c, since: b.t, from: st.free ? null : st };
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
  // riding lasts until the person gets off (walks, runs, jumps, falls or rides something else), not until the next gesture
  const rideOf = (c, t) => { let on = null; for (const b of beats.get(c)) { if (b.t > t) break; if (b.do === 'ride') on = things[b.target] || null; else if (['walk', 'run', 'sneak', 'jump', 'fall', 'lie', 'sit'].includes(b.do)) on = null; } return on; };

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
    if (ride) { p = ride.obj.position.clone(); y = ride.obj.position.y + (ride.size.y < 1.6 ? ride.size.y : ride.size.y * 0.55);   /* on a low deck or seat: on top; a tall vehicle: in its seat */ yaw = ride.obj.rotation.y + (ride.obj.userData.longX ? Math.PI / 2 : 0); }
    else if (b && b.target && !SPEED[b.do] && !s.moving && !['sit', 'lie', 'ride'].includes(b.do)) { const tp = spotOf(b.target, t); if (tp) { const want = Math.atan2(tp.x - p.x, tp.z - p.z); let d = ((want - yaw + 3 * Math.PI) % (2 * Math.PI)) - Math.PI; yaw += d * eio(clamp((t - b.t) / 0.35)); } }
    if (!ride && c.platform) { const pf = c.platform, d = thingPos(pf, t).sub(pf.base); p = p.clone().add(d.setY(0)); }
    if (!ride && stoodOn.size) { for (const th of stoodOn) { if (!inside(footprint(th, 0.02), p)) continue; const h = surfaceAt(th, p.x, p.z); if (h !== null && h > y) y = h; } }
    if (b && b.do === 'sit' && b.target && things[b.target]) y = Math.max(y, (surfaceAt(things[b.target], p.x, p.z) ?? things[b.target].size.y * 0.55));
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
    else if (d === 'hands-on-hips') { const hp = Lw(c, 0, 0.78, 0.02); handTo('Left', Lw(c, 0.18, 0.95, 0.5).lerp(hp.clone().add(dirW(c, 0.3, 0, 0)), k), dirW(c, 1, 0.2, -0.6)); handTo('Right', Lw(c, -0.18, 0.95, 0.5).lerp(hp.clone().add(dirW(c, -0.3, 0, 0)), k), dirW(c, -1, 0.2, -0.6)); hips(c, 0, -0.03 * k); }
    else if (d === 'kneel') { rest(); const fl = Lw(c, 0.12, 0, 0.32), bk = Lw(c, -0.12, 0, -0.3); c.root.position.y -= 0.28 * k; c.root.updateMatrixWorld(true); hips(c, -0.08 * k, 0.06 * k);
      leg(c, 'Left', fl.setY(0.04)); leg(c, 'Right', bk.setY(0.06)); const tp = tgt(); if (tp && !(b.with && things[b.with])) handTo('Right', tp.clone().lerp(Lw(c, -0.2, 0.6, 0.4), 0.3), dirW(c, -1, -0.4, 0)); }
    else if (d === 'cry') { const h = headC(c), s2 = Math.sin(t * 14) * 0.015; hips(c, -0.04, 0.05); handTo('Left', Lw(c, 0.18, 0.95, 0.5).lerp(h.clone().add(dirW(c, 0.1, -0.1, 0.18)).add(V(0, s2, 0)), k), dirW(c, 1, -0.5, -0.2)); handTo('Right', Lw(c, -0.18, 0.95, 0.5).lerp(h.clone().add(dirW(c, -0.1, -0.1, 0.18)).add(V(0, -s2, 0)), k), dirW(c, -1, -0.5, -0.2)); }
    else if (d === 'facepalm') { rest(); const h = headC(c); handTo('Right', Lw(c, -0.18, 0.95, 0.5).lerp(h.clone().add(dirW(c, 0, 0, 0.22)), k), dirW(c, -1, -0.5, -0.2)); headTurn(c, 0, 0.15 * k); }
    else if (d === 'lean-back') { rest(); hips(c, 0, -0.07 * k); headTurn(c, 0, -0.12 * k); }
    else if (d === 'work' || d === 'carry') { rest(); const st = b.with && things[b.with] ? carry(things[b.with], t) : {}; const sw = d === 'work' ? Math.abs(Math.sin(t * 6)) : 0;
      if (d === 'work') { const tp = tgt() || Lw(c, 0, 0.2, 0.6); hips(c, -0.08, 0.06); handTo('Right', Lw(c, -0.15, 1.35, 0.25).lerp(tp.clone().add(V(0, 0.15, 0)), 1 - sw), dirW(c, -1, -0.3, -0.2)); handTo('Left', Lw(c, 0.1, 1.2, 0.3).lerp(tp.clone().add(V(0, 0.2, 0)), 1 - sw), dirW(c, 1, -0.3, -0.2)); }
      else if (st.c === c) { const h = Lw(c, 0, 1.0, 0.34); handTo('Left', h.clone().add(dirW(c, 0.12, 0, 0)), dirW(c, 1, -0.4, -0.3)); handTo('Right', h.clone().add(dirW(c, -0.12, 0, 0)), dirW(c, -1, -0.4, -0.3)); } }
    else if (d === 'arms-crossed') { const ch = Lw(c, 0, 1.12, 0.26); handTo('Left', Lw(c, 0.18, 0.95, 0.5).lerp(ch.clone().add(dirW(c, -1, 0, 0).multiplyScalar(0.12)), k), dirW(c, 1, -0.6, 0)); handTo('Right', Lw(c, -0.18, 0.95, 0.5).lerp(ch.clone().add(dirW(c, 1, 0, 0).multiplyScalar(0.12)).add(V(0, -0.04, 0)), k), dirW(c, -1, -0.6, 0)); }
    else rest();
    // speaking a quoted line: the mouth opens and closes on the words (owner 2026-11-23: characters talking)
    const talking = b && b.says && t <= b.t1 + 0.25;
    face(c, talking ? (((t * 8.5) | 0) % 3 === 0 ? (b.face || 'calm') : 'shout') : ((b && b.face) || 'calm'));
    const sp = bub.get(c), on = b && b.bubble && b.bubble !== 'none' && BUB[b.bubble]; sp.visible = !!on;
    if (on) { sp.material.map = BUB[b.bubble]; const h = headC(c), kk = Math.min(1, (t - b.t) * 6); sp.position.set(h.x + 0.24, h.y + 0.42 + 0.03 * Math.sin(t * 8), h.z); sp.scale.setScalar(0.36 * kk); }
  }
  function pose(t) {
    K.resetScene();
    for (const th of list) poseThing(th, t);
    // the world's own life: every thing with a life keeps moving (Rick: 2+ moving things in every view)
    const lifeOf = (o, life, ph, base) => { if (life === 'sway') o.rotation.z = 0.05 * Math.sin(t * 1.6 + ph); else if (life === 'spin') o.rotation.y = base.ry + t * 1.4 + ph; else if (life === 'bob') o.position.y = base.y + 0.06 * Math.sin(t * 2.2 + ph);
      else if (life === 'flutter') o.rotation.x = 0.12 * Math.sin(t * 9 + ph); else if (life === 'roll') o.rotation.x = t * 2 + ph; o.updateMatrixWorld(true); };
    for (const th of list) if (th.T.life && th.T.life !== 'none' && !carry(th, t).c) lifeOf(th.obj, th.T.life, 0, { y: th.obj.position.y, ry: th.obj.rotation.y });
    for (const cp of copies) { const m = cp.th, o = cp.obj; if (cp.p0 === undefined) cp.p0 = o.position.clone();
      const d = m.obj.position.clone().sub(m.base), br = events.get(m).find(e => e.do === 'break' && t >= e.t), off = cp.p0.clone().sub(m.base);
      o.visible = m.obj.visible; o.position.copy(cp.p0).add(d);
      if (br) { const u = eio(clamp((t - br.t) / 0.9)), out = off.clone().setY(0); if (out.lengthSq() < 1e-4) out.set(Math.sin(cp.phase), 0, Math.cos(cp.phase)); out.setLength(Math.max(0.6, m.T.spread || 1) * 2.2 * u);
        o.position.add(out); o.position.y = Math.max(0, cp.p0.y + d.y + Math.sin(u * Math.PI) * (0.8 + (cp.phase % 1)) - u * cp.p0.y); o.rotation.x = u * (3 + cp.phase); }
      if (m.T.life && m.T.life !== 'none') lifeOf(o, m.T.life, cp.phase, { y: o.position.y, ry: cp.ry0 }); else o.updateMatrixWorld(true); }
    for (const c of people) posePerson(c, t);
    for (const th of list) { const st = carry(th, t); if (st.c) { const h = SR.wp(st.c.bone('RightHand')).lerp(SR.wp(st.c.bone('LeftHand')), 0.5), big = th.size.y > 0.25;
      /* carried in front: small things in the hands, big things held from below at the belly, never over the face */ th.obj.position.copy(h).add(dirW(st.c, 0, 0, 1).multiplyScalar(big ? th.size.z / 2 + 0.05 : 0)).add(V(0, big ? -Math.min(th.size.y * 0.75, 0.55) : -th.size.y * 0.5, 0)); th.obj.updateMatrixWorld(true); } }
    for (const f of fx) { const ev = events.get(f.th).filter(e => (e.do === 'smoke' || e.do === 'fire' || e.do === 'glow') && t >= e.t); const top = new THREE.Box3().setFromObject(f.th.obj);
      const life = f.th.T.life, smoke = ev.some(e => e.do === 'smoke') || life === 'smoke' || life === 'steam', fire = ev.some(e => e.do === 'fire'), glow = ev.some(e => e.do === 'glow') || fire || (life === 'flicker' && Math.sin(t * 23) * Math.sin(t * 7.3) > -0.2);
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
    else { const l = LIGHT[W.sky] || LIGHT.day; K.hemi.intensity = l.hemi; K.hemi.color.set(l.hemiC); K.sun.intensity = l.sun; K.sun.color.set(l.sunC); K.SUNDIR.set(...l.dir).normalize(); K.renderer.toneMappingExposure = l.exp * 1.18; K.U.uVig.value = 0.7; K.U.uCon.value = 1.12; }
    K.U.uSat.value = 1.15; K.U.uWarm.value = W.light === 'cool' ? -0.02 : W.light === 'neutral' ? 0.02 : 0.07;
    const f = sh.box.getCenter(V(0, 0, 0)), r = Math.max(10, sh.box.getSize(V(0, 0, 0)).length()); K.sun.target.position.copy(f); K.sun.position.copy(f).addScaledVector(K.SUNDIR, 60 + r); const sc = K.sun.shadow.camera; sc.left = sc.bottom = -r; sc.right = sc.top = r; sc.near = 1; sc.far = 200 + r * 2; sc.updateProjectionMatrix();
  }
  // shots
  // ---- the camera from the shot's intent (owner 2026-11-24: Sol's typed coordinates missed 22 of 25 times). The
  // storyboard says WHO or WHAT the picture is about, from which side (angle, or the side its written cam stands on),
  // how close (lens) and the lens length; the engine poses the scene at that moment, measures the subjects and stands
  // the camera where they fill the picture the way the lens means (Ricks Clips: close on the named thing) ----
  const FILL = { face: 0.8, 'extreme-close': 0.95, close: 0.85, medium: 0.75, wide: 0.6 };   /* Ricks fills the frame */
  const YAWOF = { front: 0, low: 0.25, high: -0.2, left: -0.75, right: 0.75, 'over-shoulder': Math.PI, top: 0 };
  function intent(s, who, t) {
    pose(t); const box = new THREE.Box3(); who.forEach(w => box.expandByObject(w.root || w)); if (box.isEmpty()) return null;
    const first = who[0], lens = s.lens || 'medium', vfov = THREE.MathUtils.degToRad(s.mm ? 2 * THREE.MathUtils.radToDeg(Math.atan(18 / Math.max(12, s.mm))) : (LENS[lens] || 36)), hfov = 2 * Math.atan(Math.tan(vfov / 2) * 1080 / 1920);
    let sub = box.clone();
    if (first.root && (lens === 'face' || lens === 'close' || lens === 'extreme-close') && who.filter(w => w.root).length === 1) { const pb = new THREE.Box3().expandByObject(first.root), h = pb.max.y - pb.min.y;
      sub = pb.clone(); sub.min.y = pb.max.y - h * (lens === 'face' ? 0.42 : lens === 'close' ? 0.68 : 0.3); }
    const c = sub.getCenter(V(0, 0, 0)), sz = sub.getSize(V(0, 0, 0)), fill = FILL[lens] || 0.6;
    const dist = Math.max(0.9, (sz.y / fill) / (2 * Math.tan(vfov / 2)), 0.55 * (Math.max(sz.x, sz.z) / fill) / (2 * Math.tan(hfov / 2)));   /* a phone frame is tall: long things run past its sides, as in Ricks */
    // the side: where the written cam stands (Sol's choice of side kept), else the angle around the first person's facing
    let dir = null;
    if (s.cam && s.cam.length === 3) { dir = V(s.cam[0] - c.x, 0, s.cam[1] - c.z); if (dir.lengthSq() < 0.01) dir = null; }
    if (!dir) { const f = first.root ? V(0, 0, 1).applyQuaternion(first.root.quaternion).setY(0) : V(0, 0, 1); if (f.lengthSq() < 1e-4) f.set(0, 0, 1); f.normalize();
      dir = f.applyAxisAngle(V(0, 1, 0), YAWOF[s.angle] ?? 0); }
    dir.normalize();
    let y = c.y + (s.angle === 'low' ? -Math.min(0.6, sz.y * 0.4) : s.angle === 'high' ? dist * 0.25 : s.angle === 'top' ? dist * 1.2 : 0.05);
    const pos = c.clone().addScaledVector(dir, s.angle === 'top' ? dist * 0.25 : dist);
    if (s.angle === 'over-shoulder' && who.filter(w => w.root).length >= 2) {   // behind the first person's shoulder, on the second's face
      const a2 = new THREE.Box3().expandByObject(who[0].root), b2 = new THREE.Box3().expandByObject(who.filter(w => w.root)[1].root), ah = a2.getCenter(V(0, 0, 0)), bh = b2.getCenter(V(0, 0, 0));
      ah.y = a2.max.y - (a2.max.y - a2.min.y) * 0.2; bh.y = b2.max.y - (b2.max.y - b2.min.y) * 0.25; const back = ah.clone().sub(bh).setY(0).normalize(), side = V(-back.z, 0, back.x);
      return { pos: ah.clone().addScaledVector(back, 0.9).addScaledVector(side, 0.45).add(V(0, 0.15, 0)), aim: bh, fov: THREE.MathUtils.radToDeg(vfov) }; }
    let floor = 0.3; for (const th of stoodOn) if (inside(footprint(th), pos)) { const h2 = surfaceAt(th, pos.x, pos.z); if (h2 !== null) floor = Math.max(floor, h2 + 0.3); }
    pos.y = Math.max(floor, y);
    return { pos, aim: c, fov: THREE.MathUtils.radToDeg(vfov) };
  }
  const raw = (B.shots || []).map(s => ({ ...s, t0: at(s.from) })).sort((a, b) => a.t0 - b.t0);
  if (!raw.length) throw new Error('board: no shots');
  raw[0].t0 = 0;
  const shots = raw.map((s, i) => {
    const ids = [...(s.frame || s.who || [])]; if (s.follow && !ids.includes(s.follow)) ids.push(s.follow);   // the camera rides with what it follows
    const who = ids.map(byId).filter(Boolean); if (!who.length) throw new Error(`board: shot ${i + 1} frames nothing`);
    let [yaw, pitch] = ANGLE[s.angle] || ANGLE.front; const fov = LENS[s.lens] || LENS.medium, mv = s.move || 'push';
    // the row's near-lens prop: the camera looks at the subjects from beyond it, so it stands between lens and subject
    const nearObj = s.near && things[s.near] ? things[s.near].obj : null;
    if (nearObj) { const c0 = V(0, 0, 0); let k2 = 0; ids.forEach(id => { const p2 = spotOf(id, s.t0); if (p2) { c0.add(p2); k2++; } }); const np = spotOf(s.near, s.t0);
      if (k2 && np) { c0.multiplyScalar(1 / k2); const dx = np.x - c0.x, dz = np.z - c0.z; if (dx * dx + dz * dz > 0.04) yaw = Math.atan2(dx, dz); } }
    const view = u => { const e = eio(u), v = { yaw, pitch, fov, k: 1, roll: 0 };
      if (mv === 'push') v.k = lerp(1.14, 1.0, e); else if (mv === 'pull') v.k = lerp(1.0, 1.14, e);
      else if (mv === 'crane-down') { v.pitch = pitch + lerp(0.3, 0, e); v.k = lerp(1.12, 1.0, e); } else if (mv === 'crane-up') { v.pitch = pitch + lerp(0, 0.25, e); }
      else if (mv === 'orbit-left') v.yaw = yaw + lerp(0.14, -0.14, e); else if (mv === 'orbit-right') v.yaw = yaw + lerp(-0.14, 0.14, e);
      else if (mv === 'pan' || mv === 'track') v.yaw = yaw + lerp(-0.08, 0.08, e);
      else if (mv === 'whip') { const w2 = clamp((u - 0.45) / 0.12); v.yaw = yaw + lerp(-0.35, 0, eio(w2)); v.roll = 0.04 * Math.sin(w2 * Math.PI); }
      else if (mv === 'snap-zoom') { v.k = u < 0.35 ? 1.18 : lerp(1.18, 0.95, eio(clamp((u - 0.35) / 0.1))); }
      else if (mv === 'dolly-zoom') { v.fov = lerp(fov + 10, fov - 8, e); v.roll = -0.07 * e; } else v.k = lerp(1.03, 1.0, e);
      return v; };
    return { name: `${i + 1} ${s.job || ''} ${s.angle || 'front'} ${s.lens || 'medium'} ${mv}: ${s.see || who.map(w => w.label || w.name).join(', ')}`.slice(0, 120), t0: s.t0, t1: i + 1 < raw.length ? raw[i + 1].t0 : DUR,
      take: s.take ?? i, follow: !!s.follow, near: nearObj,
      station: (() => { if (s.place === 'written' && s.cam && s.cam.length === 3 && s.aim && s.aim.length === 3) return { pos: V(s.cam[0], s.cam[2], s.cam[1]), aim: V(s.aim[0], s.aim[2], s.aim[1]), fov: THREE.MathUtils.radToDeg(2 * Math.atan(18 / Math.max(12, s.mm || 35))), push: mv === 'pull' ? -1 : 1 };
        const st = intent(s, who, s.t0 + 0.05); return st ? { ...st, push: mv === 'pull' ? -1 : 1 } : null; })(), eye: s.eye && things[s.eye] ? things[s.eye].obj : null,
      who, hidden: [], dof: s.lens === 'close' || s.lens === 'extreme-close' || s.lens === 'face' ? 0.01 : 0, extras: t => [...bubbleBoxes(who.filter(w => w && w.root)), ...labelBoxes(who.filter(w => !w.root)), ...calloutBoxes(who, t)], view,
      faces: s.lens === 'face' ? who.filter(w => w.root) : [] };
  });
  // things people hold, ride, sit on or kick, and flat things, are not obstacles; everything else is
  const touched = new Set(); for (const c of people) for (const b of beats.get(c)) { if (b.with) touched.add(b.with); if (['ride', 'sit', 'push', 'pull', 'hide', 'lie'].includes(b.do) && b.target) touched.add(b.target); }
  const deckProps = []; for (const th of stoodOn) { touched.add(th.id); const b = footprint(th), c0 = b.getCenter(V(0, 0, 0));
    const hs = people.filter(c => inside(b, c.start)).map(c => surfaceAt(th, c.start.x, c.start.z)).filter(h => h !== null), deck = (hs.length ? Math.min(...hs) : b.max.y) - 0.3;   /* the solid part stops under the feet: a person standing on the deck never touches it */
    const px = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshBasicMaterial({ visible: false })); px.userData.proxy = true; px.visible = false;   /* solid to the camera and to people, never an occluder (the real hull is drawn) */
    const lp = th.obj.worldToLocal(V(c0.x, (b.min.y + deck - 0.05) / 2, c0.z)); px.position.copy(lp); px.scale.set(b.max.x - b.min.x, Math.max(0.05, deck - 0.05 - b.min.y), b.max.z - b.min.z);
    px.rotation.y = -th.obj.rotation.y; px.updateMatrix(); th.obj.add(px); th.obj.updateMatrixWorld(true); deckProps.push({ obj: px, label: th.T.name, floor: false });
    th.obj.traverse(m => { if (m.isMesh && !m.userData.proxy) { const mb = new THREE.Box3().setFromObject(m); if (mb.min.y > deck - 0.15 && mb.max.y - mb.min.y > 0.3) deckProps.push({ obj: m, label: `${th.T.name} (${m.name || 'part'})`, floor: false }); } }); }
  const props = [...deckProps, ...list.filter(th => !touched.has(th.id)).map(th => ({ obj: th.obj, label: th.T.name, floor: th.size.y < 0.4 })),   /* rails, rugs, tracks: walked on and looked across, never obstacles */
    // every copy in a cluster is solid to the camera (never inside a rock, never a rock filling the lens); small ones are
    // stepped over by people (walk), big ones are obstacles
    ...copies.filter(cp => !touched.has(cp.th.id)).slice(0, 400).map(cp => ({ obj: cp.obj, label: cp.th.T.name, floor: false, walk: cp.th.size.y <= 0.6 }))];
  return { dur: DUR, people, props, room, pose, light, shots, group: G, walls: IN, maxDist: IN ? 120 : 420 };
}
