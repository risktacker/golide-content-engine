{
  // ---------------------------------------------------------------- content (filled by the engine for each beat)
  // GOLIDE Circuit City kit (2026-11-18): the Circuit City recipe's own construction (its board, parts, gold streets,
  // silkscreen, signal light, flight and sound, unchanged), with its four fixed stops replaced by a kit of landmarks
  // the storyboard names in order: port, memory, processor, chip, battery, antenna, power, sensor. Free.
  const SCENE = __SCENE__;
  const DUR = SCENE.duration || 8;
  const KINDS = { port: [2.6, 2.2], memory: [8.6, 2.8], processor: [7, 7], chip: [3.2, 2.6], battery: [3.4, 3.4], antenna: [4.4, 2.6], power: [4.6, 2.4], sensor: [2.4, 2.4] };   // footprint [w, d]
  const STOPS = SCENE.stops.map((s, i) => ({ kind: KINDS[s.kind] ? s.kind : 'chip', name: s.name, ref: s.ref || '' }));
  const N = STOPS.length;

  // ---------------------------------------------------------------- the map
  // stops one after the other away from the camera (to -z), in a gentle zigzag; every label printed with its top edge
  // towards -z, beside its stop on the side away from the board's middle
  const K = globalThis.K;
  const GAP = 6.5;
  {
    let z = 0.55;
    STOPS.forEach((s, i) => {
      const [w, d] = KINDS[s.kind];
      s.w = w; s.d = d; s.z = z - d / 2; z -= d + GAP;
      s.x = i === 0 || i === N - 1 ? (i % 2 ? -1.6 : 1.8) : (i % 2 ? -1.8 : 1.8);
      if (s.kind === 'memory' || s.kind === 'processor') s.x *= 0.4;
      s.side = s.x >= 0 ? 1 : -1;
    });
  }
  const LAST = STOPS[N - 1];
  const BOARD = { x0: -12, x1: 12, zNear: 1.6, zFar: LAST.z - LAST.d / 2 - 4.2 };
  const measure = (pts) => {
    const cum = [0]; for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
    const len = cum[cum.length - 1];
    const at = (s) => { s = K.clamp(s, 0, len); let i = 1; while (i < pts.length - 1 && cum[i] < s) i++; const f = (s - cum[i - 1]) / Math.max(1e-6, cum[i] - cum[i - 1]); return [K.lerp(pts[i - 1][0], pts[i][0], f), K.lerp(pts[i - 1][1], pts[i][1], f)]; };
    return { pts, cum, len, at };
  };
  // the same polyline moved sideways by d, with mitred corners (used for ribbon edges and for bundles of parallel tracks)
  const offset = (pts, d) => pts.map((p, i) => {
    const dir = (a, b) => { const x = b[0] - a[0], z = b[1] - a[1], l = Math.hypot(x, z) || 1; return [x / l, z / l]; };
    const a = dir(pts[Math.max(0, i - 1)], pts[Math.max(1, i)]), b = dir(pts[Math.min(pts.length - 2, i)], pts[Math.min(pts.length - 1, i + 1)]);
    const mx = -a[1] - b[1], mz = a[0] + b[0], ml = Math.hypot(mx, mz) || 1, k = d / ((mx / ml) * -a[1] + (mz / ml) * a[0]);
    return [p[0] + mx / ml * k, p[1] + mz / ml * k];
  });
  // one pulse run along a track: leaves at t0, arrives at t1 and gathers speed on the way (power ease)
  const run = (len, t0, t1, p = 1.3) => ({ t0, t1, timeAt: (s) => t0 + (t1 - t0) * Math.pow(K.clamp(s / len), 1 / p), sAt: (t) => len * Math.pow(K.clamp((t - t0) / (t1 - t0)), p) });

  // the schedule: the pulse arrives at stop i at T.arrive[i], works there for a moment, then leaves
  const T = (() => {
    const t0 = 0.3, end = DUR - 1.4, step = (end - t0) / Math.max(1, N - 1), arrive = [], leave = [];
    for (let i = 0; i < N; i++) { arrive.push(t0 + step * i); leave.push(i === 0 ? t0 : arrive[i] + step * 0.32); }
    return { launch: t0, arrive, leave, step, end };
  })();

  // The route of the signal, shared by the picture and the score: one gold street from the far edge of each stop to
  // the near edge of the next, with 45-degree bends like real PCB routing.
  function plan() {
    const legs = [];
    for (let i = 0; i < N - 1; i++) {
      const a = STOPS[i], b = STOPS[i + 1], za = a.z - a.d / 2 - 0.35, zb = b.z + b.d / 2 + 0.35, xa = a.x, xb = b.x;
      const bend = za - 1.2, m = measure([[xa, za], [xa, bend], [xb, bend - Math.abs(xb - xa)], [xb, zb]]);
      legs.push({ path: m, run: run(m.len, T.leave[i], T.arrive[i + 1], 1.3) });
    }
    return { legs };
  }

  registerStyle({
    id: 'circuit-city-kit',
    name: 'Circuit City',
    family: 'Spaces and journeys',
    look: 'A real circuit board filmed as a city at night: matte black chips are the buildings, aluminium capacitors the towers, gold tracks the streets, and white silkscreen print names each district. Deep green solder mask, gold and tinned metal, warm signal light.',
    motion: 'A pulse of light races along the gold tracks from stop to stop and each landmark wakes as it arrives. The camera flies low and forward after it, like a helicopter shot, and settles above the last stop.',
    duration: DUR,
    fonts: ['600 200px "IBM Plex Mono"', '500 64px "IBM Plex Mono"'],
    render: { samples: 64, shutter: 0.5, tone: 'filmic', exposure: 1.15, bloom: 0.7, bloomThreshold: 1.3, vignette: 0.42, grain: 0.03, ca: 0.012, fov: 32, near: 0.2, far: 160, background: '#010304' },

    build(S) {
      const { THREE, scene, camera } = S, P = plan(), rnd = K.rng(4);
      scene.fog = new THREE.FogExp2('#02060a', 0.016);
      const ZMID = (BOARD.zNear + BOARD.zFar) / 2;
      K.env(S, { top: '#0a1422', horizon: '#04070b', bottom: '#000000', intensity: 0.75, panels: [
        { pos: [8, 18, -30], size: [28, 12], color: '#a9c8ff', power: 1.4 },
        { pos: [-22, 5, -14], size: [1.4, 10], color: '#cfe0ff', power: 7 },
        { pos: [22, 4, 6], size: [1.2, 8], color: '#ffd9a8', power: 3 },
      ] });
      K.sun(S, { pos: [-24, 18, ZMID - 10], target: [0, 0, ZMID], color: '#b9d0ff', power: 1.3, size: 27 + N * 3, soft: 1.0, mapSize: 4096 });
      const hero = new THREE.PointLight('#ffac5a', 0, 0, 2);
      hero.castShadow = true; hero.shadow.mapSize.setScalar(1024); hero.shadow.camera.near = 0.05; hero.shadow.camera.far = 40; hero.shadow.bias = -0.004; hero.shadow.normalBias = 0.03;
      scene.add(hero);

      // ---------------------------------------------------------------- materials
      const std = (o) => new THREE.MeshStandardMaterial(o);
      const grain = K.canvasTex(256, 256, (c) => { const r = K.rng(3), d = c.createImageData(256, 256); for (let i = 0; i < d.data.length; i += 4) { d.data[i] = d.data[i + 1] = d.data[i + 2] = 90 + r() * 120; d.data[i + 3] = 255; } c.putImageData(d, 0, 0); }, { data: true });
      const M = {
        gold: std({ color: '#d9a546', metalness: 1, roughness: 0.36 }),
        tin: std({ color: '#b9bdc3', metalness: 1, roughness: 0.34 }),
        steel: std({ color: '#878c93', metalness: 1, roughness: 0.4 }),
        alu: std({ color: '#c3c7cc', metalness: 1, roughness: 0.27 }),
        epoxy: std({ color: '#0c0c0d', roughness: 0.7, bumpMap: grain, bumpScale: 0.5 }),
        plastic: std({ color: '#070708', roughness: 0.5 }),
        ceramic: std({ color: '#ffffff', roughness: 0.62 }),          // tinted per instance: tan capacitors, black resistors
      };
      const col = new THREE.Color();
      const add = (geo, mat, x, y, z, cast = true, parent = scene) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.castShadow = cast; m.receiveShadow = true; parent.add(m); return m; };
      // an InstancedMesh you can keep adding to: b.put(position, rotation, scale, colour)
      const batch = (geo, mat, max, cast = true) => {
        const m = new THREE.InstancedMesh(geo, mat, max); m.count = 0; m.castShadow = cast; m.receiveShadow = true; m.frustumCulled = false; scene.add(m);
        m.put = (p, r, s, c) => { K.place(m, m.count, p, r, s); if (c) m.setColorAt(m.count, col.set(c)); m.count++; };
        return m;
      };
      // gull-wing pin, unit size: reaches 1 along +x, shoulder at height 1. Scaled per chip.
      const gull = (() => { const s = new THREE.Shape(), th = 0.15; s.moveTo(-0.15, 1); s.lineTo(0.3, 1); s.lineTo(0.56, th); s.lineTo(1, th); s.lineTo(1, 0); s.lineTo(0.47, 0); s.lineTo(0.21, 1 - th); s.lineTo(-0.15, 1 - th); s.closePath(); const g = new THREE.ExtrudeGeometry(s, { depth: 1, bevelEnabled: false }); g.translate(0, 0, -0.5); return g; })();
      const pins = batch(gull, M.tin, 1400), pads = batch(new THREE.BoxGeometry(1, 0.012, 1), M.gold, 2600, false);
      const bodies = batch(K.roundedBox(1, 1, 1, 0.1, 2), M.ceramic, 500), caps = batch(K.roundedBox(1, 1, 1, 0.12, 2), M.tin, 1000);

      // what is where: parts claim their footprint so the random dressing never lands on the route or on a label
      const taken = [], silk = [], printed = [];
      const claim = (x, z, w, d, pad = 0.12) => taken.push([x - w / 2 - pad, z - d / 2 - pad, x + w / 2 + pad, z + d / 2 + pad]);
      const free = (x, z, w, d) => x - w / 2 > BOARD.x0 + 0.4 && x + w / 2 < BOARD.x1 - 0.4 && z + d / 2 < BOARD.zNear - 0.4 && z - d / 2 > BOARD.zFar + 0.4 && !taken.some((b) => x + w / 2 > b[0] && x - w / 2 < b[2] && z + d / 2 > b[1] && z - d / 2 < b[3]);
      const claimLine = (pts, half) => { const m = measure(pts); for (let s = 0; s <= m.len; s += 0.25) { const p = m.at(s); claim(p[0], p[1], half * 2, half * 2, 0); } };

      // ---------------------------------------------------------------- parts
      // The top of a moulded package: speckle, a pin-1 dimple and laser-etched lines (a lighter, matt grey).
      const etched = (lines, w, d, o = {}) => K.canvasTex(512, Math.round(512 * d / w), (c, W, H) => {
        c.fillStyle = o.base || '#141415'; c.fillRect(0, 0, W, H);
        const r = K.rng(lines.join('') + w); for (let i = 0; i < 2600; i++) { c.fillStyle = `rgba(255,255,255,${r.range(0.01, 0.05)})`; c.fillRect(r() * W, r() * H, 1.5, 1.5); }
        c.strokeStyle = 'rgba(255,255,255,0.05)'; c.lineWidth = 3; c.strokeRect(14, 14, W - 28, H - 28);
        const g = c.createRadialGradient(46, H - 46, 2, 46, H - 46, 18); g.addColorStop(0, '#050505'); g.addColorStop(0.8, '#0a0a0a'); g.addColorStop(1, '#1e1e1f');
        c.fillStyle = g; c.beginPath(); c.arc(46, H - 46, 18, 0, 7); c.fill();
        c.fillStyle = o.ink || '#7b7972'; c.textAlign = 'center'; c.textBaseline = 'middle';
        const px = Math.min(H / (lines.length + 1.1), W * 0.8 / (0.6 * Math.max(...lines.map((l) => l.length))));
        lines.forEach((l, i) => { c.font = `${i ? 500 : 600} ${Math.round(px * (i ? 0.6 : 1))}px "IBM Plex Mono"`; c.fillText(l, W / 2, H / 2 + (i - (lines.length - 1) / 2) * px * 0.95); });
      });
      // K.roundedBox squeezes its UVs into the rounded corners, so printed tops get a flat projection from above instead
      const flatTop = (g, w, d) => { const p = g.attributes.position, uv = g.attributes.uv; for (let i = 0; i < p.count; i++) uv.setXY(i, p.getX(i) / w + 0.5, 0.5 - p.getZ(i) / d); return g; };
      const SIDE = { '+z': -Math.PI / 2, '-z': Math.PI / 2, '+x': 0, '-x': Math.PI };
      let nU = 5, nC = 0, nL = 0;
      function chip(x, z, w, d, h, o = {}) {
        const top = std({ map: etched(o.mark || ['FX' + (200 + nU * 7)], w, d), roughness: 0.6, bumpMap: grain, bumpScale: 0.5 });
        add(flatTop(K.roundedBox(w, h, d, 0.03, 2), w, d), [M.epoxy, M.epoxy, top, M.epoxy, M.epoxy, M.epoxy], x, 0.05 + h / 2, z);
        const pitch = o.pitch || 0.17, hs = 0.05 + h * 0.6;
        for (const side of o.pins || ['+z', '-z']) {
          const alongX = side[1] === 'z', span = alongX ? w : d, n = Math.floor((span - 0.2) / pitch), sg = side[0] === '+' ? 1 : -1;
          for (let i = 0; i < n; i++) {
            const u = (i - (n - 1) / 2) * pitch, px = alongX ? x + u : x + sg * w / 2, pz = alongX ? z + sg * d / 2 : z + u;
            pins.put([px, 0.014, pz], [0, SIDE[side], 0], [0.3, hs, pitch * 0.42]);
            pads.put([px + (alongX ? 0 : sg * 0.2), 0.006, pz + (alongX ? sg * 0.2 : 0)], [0, SIDE[side], 0], [0.32, 1, pitch * 0.58]);
          }
        }
        silk.push([x, z, w + (o.pins && o.pins.includes('+x') ? 0.9 : 0.16), d + (!o.pins || o.pins.includes('+z') ? 0.9 : 0.16), o.ref || 'U' + ++nU]);
        claim(x, z, w + 0.8, d + 0.8);
      }
      // surface-mount electrolytic capacitor: a black plastic base, an aluminium can with a crimp, a printed top
      const canTop = K.canvasTex(256, 256, (c) => {
        c.fillStyle = '#a3a8ae'; c.fillRect(0, 0, 256, 256);
        c.strokeStyle = 'rgba(255,255,255,0.10)'; for (let r = 8; r < 128; r += 5) { c.beginPath(); c.arc(128, 128, r, 0, 7); c.stroke(); }
        c.fillStyle = '#0a0a0b'; c.beginPath(); c.arc(128, 128, 126, Math.PI * 0.72, Math.PI * 1.28); c.fill();      // polarity mark
        c.font = '600 46px "IBM Plex Mono"'; c.textAlign = 'center'; c.fillText('220', 150, 118); c.font = '500 34px "IBM Plex Mono"'; c.fillText('16V', 150, 160);
      });
      const canTopMat = std({ map: canTop, metalness: 1, roughness: 0.42 }), canGeo = {};
      function can(x, z, r, h) {
        const key = r + '/' + h;
        canGeo[key] = canGeo[key] || new THREE.LatheGeometry([[0, h], [r - 0.07, h], [r - 0.02, h - 0.025], [r, h - 0.08], [r, 0.3], [r - 0.045, 0.26], [r - 0.045, 0.2], [r, 0.16], [r, 0]].reverse().map(([a, b]) => new THREE.Vector2(a, b)), 48);   // bottom to top, so the faces point outwards
        add(K.roundedBox(r * 2 + 0.14, 0.18, r * 2 + 0.14, 0.04, 2), M.plastic, x, 0.11, z);
        add(canGeo[key], M.alu, x, 0.2, z);
        const t = add(new THREE.CircleGeometry(r - 0.08, 40), canTopMat, x, 0.2 + h + 0.002, z, false); t.rotation.x = -Math.PI / 2; t.rotation.z = rnd.range(-0.3, 0.3);
        for (const e of [-1, 1]) { caps.put([x + e * (r + 0.16), 0.03, z], null, [0.3, 0.035, 0.4]); pads.put([x + e * (r + 0.14), 0.006, z], null, [0.55, 1, 0.6]); }
        silk.push([x, z, r * 2 + 0.34, r * 2 + 0.34, 'C' + ++nC, true]); claim(x, z, r * 2 + 0.9, r * 2 + 0.5);
      }
      // the small bricks: ceramic capacitors (tan) and resistors (black), each with tinned end caps on gold pads
      function brick(x, z, len, wid, h, ry, color) {
        const c = Math.cos(ry), s = Math.sin(ry);
        bodies.put([x, 0.014 + h / 2, z], [0, ry, 0], [len * 0.62, h, wid], color);
        for (const e of [-1, 1]) { caps.put([x + e * c * len * 0.39, 0.014 + h / 2, z - e * s * len * 0.39], [0, ry, 0], [len * 0.24, h * 1.07, wid * 1.07]); pads.put([x + e * c * len * 0.44, 0.006, z - e * s * len * 0.44], [0, ry, 0], [len * 0.4, 1, wid * 1.25]); }
      }
      const TAN = ['#8c6a48', '#7d5c3e', '#987650'], bricks = (x, z, n, dx, dz, kind) => { for (let i = 0; i < n; i++) brick(x + dx * i, z + dz * i, 0.5, 0.26, kind ? 0.14 : 0.24, dx ? Math.PI / 2 : 0, kind ? '#0b0b0c' : rnd.pick(TAN)); const w = Math.abs(dx) * (n - 1) + (dx ? 0.3 : 0.6), d = Math.abs(dz) * (n - 1) + (dx ? 0.6 : 0.3); claim(x + dx * (n - 1) / 2, z + dz * (n - 1) / 2, w, d, 0.1); };
      // a shielded power inductor: a squat grey block with a printed value
      function inductor(x, z, s) {
        const top = std({ map: etched([rnd.pick(['4R7', '100', '2R2'])], 1, 1, { base: '#2a2b2e', ink: '#b9b9b4' }), roughness: 0.85 }), side = std({ color: '#232427', roughness: 0.85 });
        add(flatTop(K.roundedBox(s, s * 0.62, s, 0.1, 3), s, s), [side, side, top, side, side, side], x, 0.02 + s * 0.31, z);
        for (const e of [-1, 1]) { caps.put([x + e * s * 0.5, 0.07, z], null, [0.12, 0.14, s * 0.6]); pads.put([x + e * s * 0.52, 0.006, z], null, [0.4, 1, s * 0.75]); }
        silk.push([x, z, s + 0.5, s + 0.24, 'L' + ++nL]); claim(x, z, s + 0.8, s + 0.4);
      }
      // an indicator LED: a milky brick that lights up, with a small light of its own
      function led(x, z, color, lamp = true) {
        const mat = std({ color: '#d9dde0', roughness: 0.35, emissive: color, emissiveIntensity: 0 });
        add(K.roundedBox(0.3, 0.17, 0.24, 0.05, 2), mat, x, 0.1, z, false);
        for (const e of [-1, 1]) { caps.put([x + e * 0.2, 0.08, z], null, [0.12, 0.15, 0.26]); pads.put([x + e * 0.24, 0.006, z], null, [0.24, 1, 0.32]); }
        claim(x, z, 0.9, 0.5); if (!lamp) { mat.emissiveIntensity = 9; return null; }
        const l = new THREE.PointLight(color, 0, 7, 2); l.position.set(x, 0.5, z); scene.add(l);
        return (k) => { mat.emissiveIntensity = 16 * k; l.intensity = 1.6 * k; };
      }
      // a metal-shell port. face = +1: mouth towards the camera, -1: mouth away. Returns (k) => set the glow inside.
      function port(x, z, face) {
        const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = face > 0 ? 0 : Math.PI; scene.add(g);
        const W = 2.6, H = 0.9, D = 2.2, y = H / 2 + 0.03;
        const rr = (w, h, r, s) => { const a = w / 2, b = h / 2; s.moveTo(-a + r, -b); s.lineTo(a - r, -b); s.absarc(a - r, -b + r, r, -Math.PI / 2, 0); s.lineTo(a, b - r); s.absarc(a - r, b - r, r, 0, Math.PI / 2); s.lineTo(-a + r, b); s.absarc(-a + r, b - r, r, Math.PI / 2, Math.PI); s.lineTo(-a, -b + r); s.absarc(-a + r, -b + r, r, Math.PI, Math.PI * 1.5); return s; };
        const tube = rr(W, H, 0.28, new THREE.Shape()); tube.holes.push(rr(W - 0.13, H - 0.13, 0.22, new THREE.Path()));
        add(new THREE.ExtrudeGeometry(tube, { depth: D, bevelEnabled: true, bevelSize: 0.012, bevelThickness: 0.012, bevelSegments: 2, curveSegments: 10 }), M.steel, 0, y, -D / 2, true, g);
        add(new THREE.ExtrudeGeometry(rr(W - 0.14, H - 0.14, 0.21, new THREE.Shape()), { depth: D * 0.4, bevelEnabled: false, curveSegments: 8 }), M.plastic, 0, y, -D / 2 + 0.02, false, g);   // the back wall
        add(new THREE.BoxGeometry(W * 0.7, 0.1, D * 0.5), std({ color: '#121214', roughness: 0.5 }), 0, y, D * 0.16, false, g);                                                  // the tongue
        const glow = std({ color: '#d9a546', metalness: 1, roughness: 0.3, emissive: '#ffb25e', emissiveIntensity: 0 });
        add(new THREE.ExtrudeGeometry(rr(W - 0.14, H - 0.14, 0.21, new THREE.Shape()), { depth: 0.03, bevelEnabled: false, curveSegments: 8 }), M.steel, 0, y, -D / 2 - 0.005, false, g);              // the closed rear of the shell
        for (let i = 0; i < 10; i++) add(new THREE.BoxGeometry(0.085, 0.014, D * 0.38), glow, (i - 4.5) * 0.17, y + 0.055, D * 0.2, false, g);                               // the contacts
        for (const sx of [-0.62, 0.62]) add(new THREE.BoxGeometry(0.5, 0.012, 0.32), M.plastic, sx, H + 0.03, 0.25, false, g);                                                // stamped windows in the shell
        for (const sx of [-1, 1]) for (const sz of [-1, 1]) { add(K.roundedBox(0.16, 0.36, 0.42, 0.04, 2), M.tin, sx * (W / 2 + 0.03), 0.18, sz * D * 0.28, true, g); pads.put([x + sx * (W / 2 + 0.12), 0.006, z + sz * D * 0.28], null, [0.5, 1, 0.7]); }
        for (let i = 0; i < 9; i++) { const px = x + (i - 4) * 0.2, pz = z - face * (D / 2 - 0.02); pins.put([px, 0.014, pz], [0, face * Math.PI / 2, 0], [0.34, 0.24, 0.085]); pads.put([px, 0.006, pz - face * 0.24], null, [0.12, 1, 0.34]); }
        const l = new THREE.PointLight('#ffb060', 0, 9, 2); l.position.set(0, y + 0.1, D * 0.25); g.add(l);
        const spill = new THREE.SpotLight('#ffb060', 0, 16, 0.8, 1, 2); spill.position.set(0, y, D / 2 - 0.3); spill.target.position.set(0, face > 0 ? -1.6 : -0.7, D / 2 + (face > 0 ? 4 : 6)); g.add(spill, spill.target);   // light falling out of the mouth onto the desk
        claim(x, z, W + 1.2, D + 1.4);
        return (k) => { glow.emissiveIntensity = 9 * k; l.intensity = 2.4 * k; spill.intensity = (face > 0 ? 60 : 800) * k; };
      }
      // ---------------------------------------------------------------- the streets
      // Every gold track is a flat ribbon. Each vertex stores the time a pulse passes it (aT) plus [strength, repeat
      // period, position across the track] (aK); the shader lights each bit of track from its own clock: a white-hot
      // head, an amber tail that cools in a third of a second and a faint ember. Motion blur comes for free.
      const rib = { pos: [], aT: [], aK: [], idx: [] };
      const track = (pts, width, timeAt, amp = 1, period = 0) => {
        const L = offset(pts, width / 2), R = offset(pts, -width / 2), m = measure(pts);
        for (let i = 0; i < pts.length - 1; i++) {
          const n = Math.max(1, Math.ceil((m.cum[i + 1] - m.cum[i]) / 0.12));
          for (let k = 0; k <= n; k++) {
            const f = k / n, s = K.lerp(m.cum[i], m.cum[i + 1], f), tt = timeAt ? timeAt(s) : 1e4, v = rib.pos.length / 3;
            rib.pos.push(K.lerp(L[i][0], L[i + 1][0], f), 0.011, K.lerp(L[i][1], L[i + 1][1], f), K.lerp(R[i][0], R[i + 1][0], f), 0.011, K.lerp(R[i][1], R[i + 1][1], f));
            rib.aT.push(tt, tt); rib.aK.push(amp, period, 0, amp, period, 1);
            if (k < n) rib.idx.push(v, v + 1, v + 2, v + 1, v + 3, v + 2);
          }
        }
        claimLine(pts, width / 2 + 0.18);
      };

      // ---------------------------------------------------------------- the landmarks
      const haze = K.canvasTex(256, 256, (c) => { c.filter = 'blur(26px)'; c.fillStyle = '#fff'; c.fillRect(64, 64, 128, 128); });
      const underglow = (x, z, w, d) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(w * 2, d * 2), new THREE.MeshBasicMaterial({ map: haze, color: 0, blending: THREE.AdditiveBlending, transparent: true, depthWrite: false })); m.rotation.x = -Math.PI / 2; m.position.set(x, 0.02, z); scene.add(m); return m.material.color; };
      const floorplan = (lit) => K.canvasTex(512, 512, (c) => {
        const r = K.rng(77); c.fillStyle = lit ? '#000' : '#6a7180'; c.fillRect(0, 0, 512, 512);
        const split = (x, y, w, h, n) => {
          if (n > 0 && (w > 230 || h > 230 || r.chance(0.5))) { const f = r.range(0.35, 0.65); if (w > h) { split(x, y, w * f, h, n - 1); split(x + w * f, y, w * (1 - f), h, n - 1); } else { split(x, y, w, h * f, n - 1); split(x, y + h * f, w, h * (1 - f), n - 1); } return; }
          const b = r.range(0.25, 1), hatch = r.chance(0.7), vert = r.chance(0.5);
          if (lit) {
            c.fillStyle = `rgba(255,255,255,${hatch ? b * 0.1 : b * 0.3})`; c.fillRect(x + 4, y + 4, w - 8, h - 8);
            c.strokeStyle = `rgba(255,255,255,${0.5 + b * 0.5})`; c.lineWidth = 4; c.strokeRect(x + 6, y + 6, w - 12, h - 12);
            if (hatch) { c.fillStyle = `rgba(255,255,255,${b})`; for (let k = 12; k < (vert ? w : h) - 14; k += 14) vert ? c.fillRect(x + k, y + 12, 6, h - 24) : c.fillRect(x + 12, y + k, w - 24, 6); }
            else for (let k = 0; k < w * h / 700; k++) c.fillRect(x + 12 + Math.floor(r() * (w - 30) / 12) * 12, y + 12 + Math.floor(r() * (h - 30) / 12) * 12, 7, 7);
          } else { c.fillStyle = r.pick(['#59606e', '#7a7468', '#566d6d', '#72688a', '#8a8f9a']); c.fillRect(x + 3, y + 3, w - 6, h - 6); }
        };
        split(26, 26, 460, 460, 4);
        c.fillStyle = lit ? 'rgba(255,255,255,0.9)' : '#b9a36a'; for (let k = 0; k < 30; k++) for (const [x, y] of [[20 + k * 16.3, 10], [20 + k * 16.3, 496], [10, 20 + k * 16.3], [496, 20 + k * 16.3]]) c.fillRect(x - 3, y - 3, 6, 6);   // bond pads
      });
      const planDim = floorplan(false), planLit = floorplan(true), dieSide = std({ color: '#17181b', metalness: 0.6, roughness: 0.4 }), cores = [];
      const amber = new THREE.Color('#ff9a3c');
      // each landmark returns (t) => its light at time t, woken when the pulse arrives (a) and calmed when it leaves (l)
      const wake = (t, a, l) => K.seg(t, a + 0.02, a + 0.12, K.ease.out) * (1 - 0.6 * K.seg(t, l, l + 0.5));
      function processor(s, a, l) {
        const { x, z } = s, sz = s.w, CORES = 4, inner = sz - 2.1, pitch = (inner - 0.3) / CORES, die = pitch * 0.85, cores = [];
        const subTop = std({ roughness: 0.55, map: K.canvasTex(1024, 1024, (c) => {
          const r = K.rng(9); c.fillStyle = '#14130f'; c.fillRect(0, 0, 1024, 1024);
          c.strokeStyle = 'rgba(190,150,70,0.22)'; c.lineWidth = 2; for (let k = 0; k < 220; k++) { const an = r() * 6.283, d0 = r.range(120, 360), d1 = d0 + r.range(60, 160); c.beginPath(); c.moveTo(512 + Math.cos(an) * d0, 512 + Math.sin(an) * d0); c.lineTo(512 + Math.cos(an) * d1, 512 + Math.sin(an) * d1); c.stroke(); }
          c.fillStyle = '#b08a3e'; for (let k = 0; k < 60; k++) for (const [px, py] of [[32 + k * 16.3, 14], [32 + k * 16.3, 1010], [14, 32 + k * 16.3], [1010, 32 + k * 16.3]]) { c.beginPath(); c.arc(px, py, 4, 0, 7); c.fill(); }
          c.beginPath(); c.moveTo(30, 994); c.lineTo(74, 994); c.lineTo(30, 950); c.fill();
        }) });
        const sub = std({ color: '#12110e', roughness: 0.6 });
        add(flatTop(K.roundedBox(sz, 0.14, sz, 0.03, 2), sz, sz), [sub, sub, subTop, sub, sub, sub], x, 0.12, z);
        const ring = new THREE.Shape(), ra = sz / 2 - 0.22, rb = inner / 2;
        ring.moveTo(-ra, -ra); ring.lineTo(ra, -ra); ring.lineTo(ra, ra); ring.lineTo(-ra, ra); ring.closePath();
        const hole = new THREE.Path(); hole.moveTo(-rb, -rb); hole.lineTo(-rb, rb); hole.lineTo(rb, rb); hole.lineTo(rb, -rb); hole.closePath(); ring.holes.push(hole);
        const frame = add(new THREE.ExtrudeGeometry(ring, { depth: 0.1, bevelEnabled: true, bevelSize: 0.025, bevelThickness: 0.025, bevelSegments: 2 }), std({ color: '#3a3d43', metalness: 1, roughness: 0.48 }), x, 0.215, z); frame.rotation.x = -Math.PI / 2;
        const waveLen = Math.min(1.35, (l - a) * 0.8);
        for (let i = 0; i < CORES; i++) for (let j = 0; j < CORES; j++) {
          const top = new THREE.MeshPhysicalMaterial({ map: planDim, color: '#aab2c4', metalness: 1, roughness: 0.26, emissive: '#ff8a2a', emissiveMap: planLit, emissiveIntensity: 0, iridescence: 1, iridescenceIOR: 1.7, iridescenceThicknessRange: [220, 420] });
          const cx = x + (i - (CORES - 1) / 2) * pitch, cz = z - (j - (CORES - 1) / 2) * pitch;
          add(new THREE.BoxGeometry(die + 0.12, 0.04, die + 0.12), M.plastic, cx, 0.2, cz, false);
          const m = add(flatTop(K.roundedBox(die, 0.1, die, 0.012, 1), die, die), [dieSide, dieSide, top, dieSide, dieSide, dieSide], cx, 0.26, cz); m.rotation.y = Math.floor(K.hash(i, j) * 4) * Math.PI / 2;
          cores.push({ top, t0: a + 0.05 + waveLen * (i + j) / (2 * (CORES - 1)), seed: i * 7 + j });
        }
        silk.push([x, z, sz + 0.3, sz + 0.3, '']); claim(x, z, sz + 1.0, sz + 1.0);
        const glow = underglow(x, z, sz * 0.78, sz * 0.78);
        // the recipe's core level: on with the wave, shimmering while it works, one beat together as the result leaves
        const level = (c, t) => {
          const d = t - c.t0; if (d <= 0) return 0;
          const on = 1 - Math.exp(-d / 0.04), flash = Math.exp(-d / 0.22), work = 0.5 + 0.22 * Math.sin(t * 31 + c.seed * 2.4) * Math.sin(t * 13.7 + c.seed);
          const out = t - l, beat = out > -0.12 ? (out < 0 ? K.smooth(-0.12, 0, out) * 0.9 : 0.9 * Math.exp(-out / 0.35)) : 0;
          return on * (work * (out > 0 ? 0.55 + 0.45 * Math.exp(-out / 0.5) : 1) + 1.1 * flash + beat);
        };
        return (t) => { let sum = 0; for (const c of cores) { const k = level(c, t); sum += k; c.top.emissiveIntensity = 4.6 * k; } glow.copy(amber).multiplyScalar(0.9 * sum / cores.length); };
      }
      function memory(s, a, l) {
        const xs = [-3.45, -1.15, 1.15, 3.45].map((u) => s.x + u), glows = [];
        xs.forEach((x, i) => { chip(x, s.z, 1.9, 2.8, 0.3, { mark: ['FX8G', 'DR5-2611 M' + (i + 1)], ref: 'U' + (i + 1) }); glows.push(underglow(x, s.z, 2.4, 3.7)); });
        return (t) => glows.forEach((g, i) => { const k = K.seg(t, a + 0.03 + 0.06 * i, a + 0.13 + 0.06 * i, K.ease.out) * (1 - 0.85 * K.seg(t, l + 0.07 * i, l + 0.07 * i + 0.4)) * (0.85 + 0.15 * Math.sin(t * 47 + i * 2)); g.copy(amber).multiplyScalar(1.5 * k); });
      }
      function plainChip(s, a, l) {
        chip(s.x, s.z, s.w - 0.6, s.d - 0.6, 0.32, { mark: [s.ref || 'FX' + (300 + s.x * 10 | 0), 'GL-' + (1000 + N * 37)], pins: ['+z', '-z', '+x', '-x'], pitch: 0.2 });
        const g = underglow(s.x, s.z, s.w, s.d);
        return (t) => g.copy(amber).multiplyScalar(1.4 * wake(t, a, l));
      }
      // a coin cell in its holder: a tinned clip over a brushed steel disc with a printed plus
      function battery(s, a, l) {
        const r = s.w / 2 - 0.25, top = K.canvasTex(256, 256, (c) => { c.fillStyle = '#b4b8bd'; c.fillRect(0, 0, 256, 256); c.strokeStyle = 'rgba(255,255,255,0.12)'; for (let q = 6; q < 128; q += 4) { c.beginPath(); c.arc(128, 128, q, 0, 7); c.stroke(); } c.fillStyle = '#2a2b2e'; c.font = '600 120px "IBM Plex Mono"'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText('+', 128, 132); });
        add(new THREE.CylinderGeometry(r + 0.12, r + 0.12, 0.2, 48), M.plastic, s.x, 0.1, s.z);
        add(new THREE.CylinderGeometry(r, r, 0.34, 64), [M.steel, std({ map: top, metalness: 1, roughness: 0.38 }), M.steel], s.x, 0.37, s.z);
        add(K.roundedBox(0.7, 0.06, r * 1.6, 0.02, 2), M.tin, s.x, 0.57, s.z);
        for (const e of [-1, 1]) pads.put([s.x + e * (r + 0.3), 0.006, s.z], null, [0.5, 1, 0.9]);
        const g = underglow(s.x, s.z, s.w, s.d), lamp = new THREE.PointLight('#ffb060', 0, 6, 2); lamp.position.set(s.x, 1.0, s.z); scene.add(lamp);
        silk.push([s.x, s.z, s.w, s.w, 'BT1', true]); claim(s.x, s.z, s.w + 0.6, s.d + 0.6);
        return (t) => { const k = wake(t, a, l); g.copy(amber).multiplyScalar(1.3 * k); lamp.intensity = 2 * k; };
      }
      // a printed antenna: a meander of gold track fed by a small radio chip; it lights from the chip outwards
      function antenna(s, a, l) {
        // wide gold meander (a real PCB antenna is a broad track), fed from its radio chip by a short track
        const x0 = s.x - s.w / 2 + 0.25, zt = s.z + s.d / 2 - 0.25, zb = s.z - s.d / 2 + 0.25, P0 = 0.62, pts = [[x0, zt]];
        for (let k = 0; k < 6; k++) { const x = x0 + P0 * (k + 1); pts.push([x - P0, k % 2 ? zt : zb]); pts.push([x, k % 2 ? zt : zb]); }
        const m = measure(pts), rr = run(m.len, a + 0.05, a + 0.05 + Math.min(0.7, (l - a) * 0.7), 1);
        track(pts, 0.24, rr.timeAt, 1.6);
        const cx = s.x + s.w / 2 + 0.55, end = pts[pts.length - 1];
        track([[end[0], end[1]], [cx - 0.75, end[1]]], 0.13, (q) => a + q / 9, 1.2);
        chip(cx, end[1], 1.3, 1.3, 0.26, { mark: ['RF', '5G'], pins: ['-x', '+x', '+z'], pitch: 0.2, ref: 'U' + (40 + N) });
        claim(s.x + 0.4, s.z, s.w + 1.6, s.d + 0.6);
        const g = underglow(s.x, s.z, s.w + 0.4, s.d + 0.3), lamp = new THREE.PointLight('#ffb060', 0, 8, 2); lamp.position.set(s.x, 1.1, s.z); scene.add(lamp);
        return (t) => { const k = wake(t, a, l); g.copy(amber).multiplyScalar(1.5 * k); lamp.intensity = 2.6 * k; };
      }
      // power: the recipe's shielded inductor between two aluminium cans
      function power(s, a, l) {
        inductor(s.x, s.z, 1.5); can(s.x - 1.8, s.z, 0.75, 2.0); can(s.x + 1.8, s.z, 0.75, 2.0);
        const g = underglow(s.x, s.z, s.w, s.d);
        return (t) => g.copy(amber).multiplyScalar(1.4 * wake(t, a, l));
      }
      // a sensor: a square package with a glass window over a lit die
      function sensor(s, a, l) {
        chip(s.x, s.z, 1.7, 1.7, 0.42, { mark: [''], pins: ['+z', '-z', '+x', '-x'], pitch: 0.22, ref: 'S1' });
        const eye = std({ color: '#0d1420', metalness: 0.4, roughness: 0.08, emissive: '#ff9a3c', emissiveIntensity: 0 });
        add(new THREE.CylinderGeometry(0.5, 0.5, 0.06, 40), eye, s.x, 0.5, s.z, false);
        add(new THREE.TorusGeometry(0.54, 0.05, 10, 40), M.steel, s.x, 0.5, s.z).rotation.x = Math.PI / 2;
        return (t) => { eye.emissiveIntensity = 5 * wake(t, a, l); };
      }
      // a port: the recipe's own metal shell, mouth towards the camera on the first stop, away on the others
      function portStop(s, i) { const f = port(s.x, s.z, i === 0 ? 1 : -1), g = underglow(s.x, s.z + 0.3, 2.6, 2.4); return { f, g }; }
      const BUILD = { processor, memory, chip: plainChip, battery, antenna, power, sensor };
      const lights = STOPS.map((s, i) => {
        if (s.kind === 'port') {
          const { f, g } = portStop(s, i);
          if (i === 0) { const tr = K.track([[0, 0.6], [T.launch - 0.04, 1.1, 'in'], [T.launch + 0.6, 0.22, 'out'], [DUR, 0.22]]); return (t) => f(tr(t)); }
          const tr = K.track([[T.arrive[i] - 0.06, 0], [T.arrive[i] + 0.12, 1.3, 'out'], [T.arrive[i] + 0.7, 0.85, 'inOut'], [DUR, 0.8]]);
          return (t) => { f(tr(t)); g.copy(amber).multiplyScalar(1.1 * tr(t)); };
        }
        const until = i === N - 1 ? DUR + 9 : T.leave[i];
        return BUILD[s.kind](s, i === 0 ? T.launch - 0.25 : T.arrive[i], until);
      });
      // ---------------------------------------------------------------- the printed labels
      // White silkscreen, stretched along the direction of flight like road markings so it still reads from a low camera.
      const STRETCH = 1.4;
      const label = (text, ref, x, z, align) => {
        const m = K.textPlane(text, { font: '600 200px "IBM Plex Mono"', height: 0.6, color: '#eceadf', lit: true, letterSpacing: 6, roughness: 0.78, pad: 20 });
        const r = K.rng(text), c = m.userData.tex.ctx; c.globalCompositeOperation = 'destination-out';       // pinholes and thin patches, as in real screen print
        for (let i = 0; i < 500; i++) { c.fillStyle = `rgba(0,0,0,${r.range(0.15, 0.9)})`; c.beginPath(); c.arc(r() * c.canvas.width, r() * c.canvas.height, r.range(0.6, 2.4), 0, 7); c.fill(); }
        m.userData.tex.needsUpdate = true;
        const w = m.userData.size[0], d = m.userData.size[1] * STRETCH, cx = align === 'left' ? x + w / 2 : align === 'right' ? x - w / 2 : x;
        m.rotation.x = -Math.PI / 2; m.scale.y = STRETCH; m.position.set(cx, 0.006, z); m.receiveShadow = true; scene.add(m);
        const s = K.textPlane(ref, { font: '500 64px "IBM Plex Mono"', height: 0.2, color: '#eceadf', lit: true, roughness: 0.78 });
        s.rotation.x = -Math.PI / 2; s.scale.y = STRETCH; s.position.set(cx - w / 2 + s.userData.size[0] / 2 + 0.1, 0.006, z - d / 2 + 0.02); s.receiveShadow = true; scene.add(s);
        claim(cx, z - 0.15, w, d + 0.5, 0.2); printed.push([cx, z - 0.12, w + 0.3, d + 0.55]);
        return m;
      };
      STOPS.forEach((s) => { if (s.name) label(s.name, s.ref || '', s.side > 0 ? s.x + 0.55 : s.x - 0.55, s.z + s.d / 2 + 1.25, s.side > 0 ? 'left' : 'right'); });

      P.legs.forEach((q) => track(q.path.pts, 0.13, q.run.timeAt));
      // side streets: bundles of parallel tracks running out of every landmark to the edge of the board, away from its label
      const STREETS = STOPS.map((s, i) => { const e = -s.side, x0 = s.x + e * (s.w / 2 + 0.2), zz = s.z + (i % 2 ? 0.6 : -0.6); return { n: 4 + (i % 3), pts: [[x0, zz], [x0 + e * 2.4, zz], [x0 + e * 4.0, zz - 1.6], [e * 11.6, zz - 1.6]] }; });
      STREETS.forEach((b, bi) => { for (let k = 0; k < b.n; k++) { const pts = offset(b.pts, (k - (b.n - 1) / 2) * 0.2), live = K.hash(bi, k) < 0.4, len = measure(pts).len, ph = K.hash(k, bi) * 3, dir = K.hash(bi, k, 3) < 0.5; track(pts, 0.075, live ? (s) => ph + (dir ? s : len - s) / 7 : null, 0.22, 2.4 + K.hash(bi, k, 9)); } });
      const uTime = { value: 0 }, ribbons = new THREE.BufferGeometry();
      ribbons.setAttribute('position', new THREE.Float32BufferAttribute(rib.pos, 3)); ribbons.setAttribute('aT', new THREE.Float32BufferAttribute(rib.aT, 1)); ribbons.setAttribute('aK', new THREE.Float32BufferAttribute(rib.aK, 3));
      ribbons.setAttribute('normal', new THREE.Float32BufferAttribute(rib.pos.map((_, i) => (i % 3 === 1 ? 1 : 0)), 3)); ribbons.setIndex(rib.idx);
      const trackMat = M.gold.clone(); trackMat.side = THREE.DoubleSide;
      trackMat.onBeforeCompile = (sh) => {
        sh.uniforms.uTime = uTime;
        sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nattribute float aT; attribute vec3 aK; varying float vT; varying vec3 vK;').replace('#include <begin_vertex>', '#include <begin_vertex>\nvT = aT; vK = aK;');
        sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nuniform float uTime; varying float vT; varying vec3 vK;').replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
          float age = uTime - vT; if (vK.y > 0.0) age = mod(age, vK.y);
          float a = max(age, 0.0), front = age < 0.0 ? exp(age / 0.006) : 1.0;
          float heat = front * (10.0 * exp(-a / 0.035) + 1.5 * exp(-a / 0.3) + (vK.y > 0.0 ? 0.0 : 0.22));
          float across = 1.0 - 0.5 * pow(abs(vK.z * 2.0 - 1.0), 3.0);
          totalEmissiveRadiance += mix(vec3(1.0, 0.42, 0.09), vec3(1.0, 0.8, 0.52), exp(-a / 0.05)) * heat * vK.x * across;`);
      };
      const streets = new THREE.Mesh(ribbons, trackMat); streets.receiveShadow = true; streets.frustumCulled = false; scene.add(streets);

      // ---------------------------------------------------------------- the rest of the city
      // a seeded scatter fills everything the landmarks, streets and labels did not claim
      claim(LAST.x, LAST.z + LAST.d / 2 + 2.2, 9, 3.8);
      for (let i = 0, n = 0; i < 300 && n < 6 + N * 3; i++) { const x = rnd.range(BOARD.x0, BOARD.x1), z = rnd.range(BOARD.zFar, -5); if (Math.abs(x) > 6 && free(x, z, 0.9, 0.5)) { led(x, z, rnd.pick(['#ffb347', '#ffb347', '#35ff7a', '#ff3b30']), false); n++; } }
      for (let i = 0, n = 0; i < 1400 && n < 30 + N * 12; i++) {
        const x = rnd.range(BOARD.x0, BOARD.x1), z = rnd.range(BOARD.zFar, BOARD.zNear), k = rnd();
        if (k < 0.2 && Math.abs(x) > 5.5) { const r = rnd.pick([0.6, 0.75, 0.9]); if (free(x, z, r * 2 + 0.9, r * 2 + 0.5)) { can(x, z, r, r === 0.9 ? 2.6 : r === 0.6 ? 1.5 : 2.0); n++; } }
        else if (k < 0.4 && Math.abs(x) > 4.5) { const w = rnd.range(1.2, 2.2), d = rnd.range(1.0, 1.7); if (free(x, z, w + 0.8, d + 0.8)) { chip(x, z, w, d, 0.28, { pitch: 0.2 }); n++; } }
        else if (k < 0.47 && Math.abs(x) > 5.5) { if (free(x, z, 2.2, 1.8)) { inductor(x, z, 1.3); n++; } }
        else { const m = rnd.int(2, 5), horiz = rnd.chance(0.5), w = horiz ? m * 0.6 : 0.6, d = horiz ? 0.6 : m * 0.55; if (free(x + (horiz ? (m - 1) * 0.3 : 0), z + (horiz ? 0 : (m - 1) * 0.275), w, d)) { bricks(x, z, m, horiz ? 0.6 : 0, horiz ? 0 : 0.55, rnd.chance(0.35) ? 1 : 0); n++; } }
      }
      // ---------------------------------------------------------------- the board itself
      // Two canvases painted from the same drawing: colour, and a data map with height in red (the copper under the
      // mask stands a little proud, which is what catches the raking light) and roughness in green.
      const PPU = 128, BW = BOARD.x1 - BOARD.x0, BD = BOARD.zNear - BOARD.zFar, r2 = K.rng(21), inner = [], vias = [];
      for (let b = 0; b < 54; b++) {
        let x = r2.range(BOARD.x0, BOARD.x1), z = r2.range(BOARD.zFar, BOARD.zNear), dir = r2.int(0, 7); const n = r2.int(2, 7), pts = [[x, z]];
        for (let s = r2.int(2, 4); s > 0; s--) { const l = r2.range(1.5, 7); x += Math.cos(dir * Math.PI / 4) * l; z += Math.sin(dir * Math.PI / 4) * l; pts.push([x, z]); dir += r2.pick([-1, 1]); }
        for (let k = 0; k < n; k++) { const o = offset(pts, (k - (n - 1) / 2) * 0.17); inner.push(o); vias.push(o[0], o[o.length - 1]); }
      }
      const gold = [...P.legs.map((q) => q.path.pts), ...STREETS.flatMap((b) => Array.from({ length: b.n }, (_, k) => offset(b.pts, (k - (b.n - 1) / 2) * 0.2)))];
      const paint = (c, scale, data) => {
        c.scale(scale, scale); c.lineJoin = 'miter'; c.lineCap = 'butt';
        const X = (x) => (x - BOARD.x0) * PPU, Z = (z) => (z - BOARD.zFar) * PPU;
        const line = (pts, w, style) => { c.strokeStyle = style; c.lineWidth = w * PPU; c.beginPath(); pts.forEach((p, i) => (i ? c.lineTo(X(p[0]), Z(p[1])) : c.moveTo(X(p[0]), Z(p[1])))); c.stroke(); };
        c.fillStyle = data ? 'rgb(0,92,0)' : '#063a22'; c.fillRect(0, 0, BW * PPU, BD * PPU);
        if (!data) { const r = K.rng(5); for (let i = 0; i < 70; i++) { const x = r() * BW * PPU, y = r() * BD * PPU, s = r.range(200, 700), g = c.createRadialGradient(x, y, 0, x, y, s); g.addColorStop(0, `rgba(${r.chance(0.5) ? '4,20,14' : '16,58,40'},0.35)`); g.addColorStop(1, 'rgba(0,0,0,0)'); c.fillStyle = g; c.fillRect(x - s, y - s, s * 2, s * 2); } }
        if (data) c.globalCompositeOperation = 'lighter';
        inner.forEach((p) => line(p, 0.075, data ? 'rgb(110,0,0)' : 'rgba(38,112,76,0.55)'));                         // copper under the mask
        c.globalCompositeOperation = 'source-over';
        c.fillStyle = data ? 'rgb(0,92,0)' : '#063a22'; printed.forEach(([x, z, w, d]) => c.fillRect(X(x - w / 2), Z(z - d / 2), w * PPU, d * PPU));   // nothing runs under the big labels
        gold.forEach((p) => line(p, 0.3, data ? 'rgb(0,92,0)' : '#063a22'));                                           // clearance around the gold streets
        if (!data) gold.forEach((p) => line(p, 0.08, '#6b4f1c'));                                                      // (their geometry sits on top; this shows in the mirrored outskirts)
        vias.forEach(([x, z]) => { if (printed.some(([px, pz, pw, pd]) => Math.abs(x - px) < pw / 2 + 0.1 && Math.abs(z - pz) < pd / 2 + 0.1)) return; c.fillStyle = data ? 'rgb(150,40,0)' : '#b98d3a'; c.beginPath(); c.arc(X(x), Z(z), 0.085 * PPU, 0, 7); c.fill(); c.fillStyle = data ? 'rgb(0,200,0)' : '#020403'; c.beginPath(); c.arc(X(x), Z(z), 0.035 * PPU, 0, 7); c.fill(); });
        // silkscreen: an outline and a reference designator for every part
        c.strokeStyle = c.fillStyle = data ? 'rgb(120,190,0)' : '#dddbd0'; c.lineWidth = 0.035 * PPU; c.font = `500 ${0.3 * PPU}px "IBM Plex Mono"`; c.textBaseline = 'bottom';
        silk.forEach(([x, z, w, d, ref, round]) => {
          c.beginPath(); if (round) { c.arc(X(x), Z(z), w / 2 * PPU, 0.25, Math.PI - 0.25); c.moveTo(X(x) + Math.cos(Math.PI + 0.25) * w / 2 * PPU, Z(z) + Math.sin(Math.PI + 0.25) * w / 2 * PPU); c.arc(X(x), Z(z), w / 2 * PPU, Math.PI + 0.25, -0.25); } else c.rect(X(x - w / 2), Z(z - d / 2), w * PPU, d * PPU); c.stroke();
          if (ref) c.fillText(ref, X(x - w / 2), Z(z - d / 2) - 0.06 * PPU);
        });
      };
      const boardMap = K.canvasTex(BW * PPU, BD * PPU, (c) => paint(c, 1, false));
      const boardData = K.canvasTex(BW * PPU / 2, BD * PPU / 2, (c, w, h) => {
        paint(c, 0.5, true); c.setTransform(1, 0, 0, 1, 0, 0);
        const d = c.getImageData(0, 0, w, h), r = K.rng(8);                                                             // fine grain: tiny bumps and roughness speckle
        for (let i = 0; i < d.data.length; i += 4) { const n = r(); d.data[i] = Math.min(255, d.data[i] + n * 16); d.data[i + 1] = Math.min(255, d.data[i + 1] + (r() - 0.5) * 34); }
        c.putImageData(d, 0, 0);
      }, { data: true });
      for (const tx of [boardMap, boardData]) { tx.wrapS = THREE.MirroredRepeatWrapping; tx.repeat.set(2, 1); tx.offset.set(-0.5, 0); }
      // the board is twice as wide as its drawing: the outskirts are the same drawing mirrored, far out of focus
      const floor = K.mirrorFloor(S, { size: 1, color: '#ffffff', surfaceRoughness: 1, roughness: 0.3, strength: 1, fresnel: true, material: { map: boardMap, bumpMap: boardData, bumpScale: 1.2, roughnessMap: boardData } });
      floor.scale.set(BW * 2, BD, 1); floor.position.set(0, 0, (BOARD.zNear + BOARD.zFar) / 2);
      add(new THREE.BoxGeometry(BW * 2, 0.5, BD), std({ color: '#3e4a2b', roughness: 0.7 }), 0, -0.252, (BOARD.zNear + BOARD.zFar) / 2, false);    // the laminate edge
      const desk = add(new THREE.PlaneGeometry(400, 400), std({ color: '#101114', roughness: 0.82, bumpMap: grain, bumpScale: 0.4 }), 0, -0.5, 0, false); desk.rotation.x = -Math.PI / 2;   // a dark bench mat under the board

      // A flight through keyframes [t, [x, y, z]] that never stops on the way: a monotone cubic, so the camera keeps
      // gliding through every key without overshoot and only comes to rest on the last one.
      const fly = (keys) => (t) => {
        const n = keys.length; let i = 1; while (i < n - 1 && keys[i][0] < t) i++;
        const [t0, p0] = keys[i - 1], [t1, p1] = keys[i], h = t1 - t0, u = K.clamp((t - t0) / h), u2 = u * u, u3 = u2 * u;
        const seg = (j, k) => (keys[j + 1][1][k] - keys[j][1][k]) / (keys[j + 1][0] - keys[j][0]);
        const slope = (j, k) => { if (j === 0) return seg(0, k); if (j === n - 1) return 0; const a = seg(j - 1, k), b = seg(j, k); return a * b <= 0 ? 0 : 2 * a * b / (a + b); };
        return p0.map((a, k) => (2 * u3 - 3 * u2 + 1) * a + (u3 - 2 * u2 + u) * h * slope(i - 1, k) + (3 * u2 - 2 * u3) * p1[k] + (u3 - u2) * h * slope(i, k));
      };
      const mix = (a, b, k) => a.map((v, i) => v + (b[i] - v) * k);
      // where the travelling light is: on the pulse while it runs, hovering over a landmark while it works
      const heroAt = (t) => {
        let p = [STOPS[0].x, 0.6, STOPS[0].z + 0.6];
        P.legs.forEach((q, i) => {
          const h = q.path.at(q.run.sAt(t)), s = STOPS[i + 1];
          p = mix(p, [h[0], 0.35, h[1]], K.seg(t, T.leave[i] - 0.08, T.leave[i] + 0.15, K.ease.inOut));
          p = mix(p, [s.x, s.kind === 'processor' ? 2.4 : 1.0, s.z + (s.kind === 'port' ? 1.8 : 0)], K.seg(t, T.arrive[i + 1] - 0.05, T.arrive[i + 1] + 0.3, K.ease.out));
        });
        return p;
      };
      const pk = [[0, 0], [T.launch - 0.05, 0], [T.launch + 0.12, 7]];
      for (let i = 1; i < N; i++) pk.push([T.arrive[i], STOPS[i].kind === 'processor' ? 15 : 9], [T.arrive[i] + 0.3, 7]);
      pk.push([DUR, 5]);
      const heroPower = K.track(pk.sort((a, b) => a[0] - b[0]).filter((k, i, A) => !i || k[0] > A[i - 1][0]));
      // the camera: low behind the first stop, gliding over each landmark as the pulse reaches it, at rest over the last
      // each stop is framed together with its printed name (the name sits in front of it, on its outer side)
      const named = (s) => { const w = s.name ? 0.84 * s.name.length + 0.6 : 0; return [s.x + s.side * (0.55 + w / 2) * 0.5, s.z + (s.name ? 0.9 : 0)]; };
      const WIDE = Math.max(1, 1.78 / (camera.aspect || 1.78));   // a square Short frame is narrower: stand further back
      const view = (s) => { const span = Math.max(s.w, s.name ? 0.84 * s.name.length + 1.2 : 0); const v = s.kind === 'processor' ? [9.4, 7.6] : [Math.max(5.6, span * 0.78), Math.max(6.4, span * 1.02)]; return [v[0] * WIDE, v[1] * WIDE]; };   // [height, distance back]
      const c0 = named(STOPS[0]), v0 = view(STOPS[0]);
      const ck = [[0, [c0[0] * 0.9, v0[0] * 0.62, c0[1] + v0[1] * 1.15], [c0[0], 0.2, c0[1] - 1.2], [c0[0], 0.3, c0[1]]]];
      STOPS.forEach((s, i) => {
        if (!i) return;
        const [h, back] = view(s), [cx, cz] = named(s), at = i === N - 1 ? T.arrive[i] + 0.4 : T.arrive[i] + 0.15;
        ck.push([at, [cx * 0.9, h, cz + back], [cx, 0, cz - 0.5], [cx, 0.3, cz]]);
      });
      ck.push([DUR, ck[ck.length - 1][1].map((v, k) => v + (k === 2 ? 0.5 : k === 1 ? 0.3 : 0)), ck[ck.length - 1][2], ck[ck.length - 1][3]]);
      const cam = { pos: fly(ck.map((k) => [k[0], k[1]])), aim: fly(ck.map((k) => [k[0], k[2]])), focus: fly(ck.map((k) => [k[0], k[3]])), ap: K.track([[0, 0.13], [DUR * 0.5, 0.1], [DUR, 0.11]]) };

      return {
        update(t) {
          uTime.value = t;
          const h = heroAt(t); hero.position.set(h[0], h[1], h[2]); hero.intensity = heroPower(t);
          lights.forEach((f) => f(t));
          K.look(camera, cam.pos(t), cam.aim(t)); K.focus(camera, cam.focus(t), cam.ap(t));
        },
      };
    },

    sound(k) {
      const P = plan(), pan = (x) => K.clamp(x / 9, -0.7, 0.7);
      const zip = (t0, t1, gain, f, x0, x1) => {
        const d = t1 - t0;
        k.tone(t0, { f: [[0, f], [d, f * 2.5]], type: 'sawtooth', dur: d, gain: 0.05 * gain, a: d * 0.35, hold: d * 0.5, filter: 'bandpass', f2: [[0, 500], [d, 2600]], q: 3, verb: 0.2, pan: pan((x0 + x1) / 2) });
        k.noise(t0, { dur: d, color: 'pink', filter: 'bandpass', f: [[0, 600], [d, 3200]], q: 1.4, gain: 0.17 * gain, a: d * 0.6, verb: 0.2, pan: pan((x0 + x1) / 2) });
      };
      k.bed('room', 0, DUR, { gain: 0.9 }); k.bed('hum', 0, DUR, { gain: 0.4 });
      k.music('pad', 0, DUR, { bpm: 60, chords: [['D3', 'A3', 'D4', 'F#4'], ['D3', 'A3', 'E4', 'G4']], gain: 0.55 });
      k.tone(0, { f: [[0, 90], [T.launch, 230]], type: 'triangle', dur: T.launch + 0.05, gain: 0.12, a: 0.22, pan: pan(STOPS[0].x) });
      k.play('click', T.launch, { gain: 1, pan: pan(STOPS[0].x) }); k.play('thud', T.launch, { gain: 0.35, pan: pan(STOPS[0].x) });
      const notes = ['E5', 'G5', 'B5', 'D6', 'E6', 'G6'];
      P.legs.forEach((q, i) => {
        const s = STOPS[i + 1], a = T.arrive[i + 1];
        zip(q.run.t0, q.run.t1, 1 + 0.1 * i, 260 + 30 * i, STOPS[i].x, s.x);
        if (i === N - 2) { k.play('tock', a, { gain: 0.9, f: 520, pan: pan(s.x) }); k.play('click', a + 0.12, { gain: 0.7, pan: pan(s.x) }); k.play('ding', a + 0.12, { f: 'D6', gain: 1, pan: pan(s.x) }); k.play('ding', a + 0.24, { f: 'A6', gain: 0.6, pan: pan(s.x) }); }
        else if (s.kind === 'processor') { k.play('thud', a + 0.03, { gain: 0.7, pan: pan(s.x) }); k.play('impact', T.leave[i + 1], { gain: 0.6, pan: pan(s.x) }); }
        else { k.play('blip', a + 0.04, { f: notes[i % notes.length], type: 'triangle', dur: 0.12, gain: 1.6, pan: pan(s.x) }); k.play('tock', a + 0.04, { gain: 0.5, f: 700 + i * 90, pan: pan(s.x) }); }
      });
    },
  });
}
