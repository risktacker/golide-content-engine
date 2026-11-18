{
  // ---------------------------------------------------------------- content (filled by the engine for each beat)
  // GOLIDE White Model kit (2026-11-18): the White Model recipe's own construction (its four whites, daylight, site
  // board, accent conduits, numbered labels and crane camera, unchanged), with its one topic-built model replaced by a
  // kit of pieces the storyboard places: nature, buildings, roads, vehicles, people. Free: no model writes code.
  const SCENE = __SCENE__;
  const ACCENT = SCENE.accent || '#ff6a00';
  const TITLE = SCENE.title || ['', ''];
  const DUR = SCENE.duration || 8;
  // ----------------------------------------------------------------

  registerStyle({
    id: 'white-model-kit',
    name: 'White Model',
    family: 'Diagrams with depth',
    look: 'An architect\'s presentation model: everything is matte white card and foam on a white site board, and one saturated accent colour is reserved for the thing being explained.',
    motion: 'Nothing in the model moves. Only the accent moves: it starts at the source and travels through the model along thin conduits, switching each part on as it arrives, and a numbered label with a thin leader line draws in at every stop.',
    duration: DUR,
    fonts: ['700 50px "Inter"', '700 44px "Inter"', '500 38px "Inter"', '600 30px "IBM Plex Mono"'],
    render: { samples: 64, shutter: 0.5, tone: 'neutral', exposure: 1.0, bloom: 0.32, bloomThreshold: 1.1, vignette: 0.3, grain: 0.012, contrast: 1.05, fov: 24, background: '#b4b8bd' },

    build(S) {
      const { THREE, K, scene, camera } = S;
      const accent = new THREE.Color(ACCENT), V = (p) => new THREE.Vector3(p[0], p[1], p[2]);

      // ================================================================ 1. THE KIT: whites, daylight, set (the recipe's own)
      const grain = K.canvasTex(256, 256, (ctx, w, h) => {
        const r = K.rng(3), im = ctx.createImageData(w, h);
        for (let i = 0; i < w * h; i++) { const v = 128 + r.gauss() * 26; im.data.set([v, v, v, 255], i * 4); }
        ctx.putImageData(im, 0, 0);
      }, { data: true, repeat: [3, 3] });
      const white = (color, roughness = 0.92) => new THREE.MeshStandardMaterial({ color, roughness, bumpMap: grain, bumpScale: 0.4 });
      const M = { card: white('#f8f6f0'), foam: white('#eef3f8', 0.8), paper: white('#fcfbf8'), plaster: white('#eeebe6', 1) };
      const put = (geo, mat, pos = [0, 0, 0], rot, parent = scene) => { const m = new THREE.Mesh(geo, mat); m.position.set(...pos); if (rot) m.rotation.set(...rot); m.castShadow = m.receiveShadow = true; parent.add(m); return m; };
      const box = (w, h, d, mat, pos, rot, parent) => put(K.roundedBox(w, h, d, 0.012, 2), mat, pos, rot, parent);
      const cyl = (r, h, mat, pos, parent, rTop = r, rot) => put(new THREE.CylinderGeometry(rTop, r, h, 28), mat, pos, rot, parent);
      const ball = (r, mat, pos, parent) => put(new THREE.SphereGeometry(r, 32, 20), mat, pos, null, parent);
      const cut = (outline, holes = [], depth = 0.08) => {
        const s = new THREE.Shape(outline.map((p) => new THREE.Vector2(p[0], p[1])));
        for (const [x0, x1, y0, y1] of holes) s.holes.push(new THREE.Path([[x0, y0], [x0, y1], [x1, y1], [x1, y0]].map((p) => new THREE.Vector2(p[0], p[1]))));
        return new THREE.ExtrudeGeometry(s, { depth, bevelEnabled: true, bevelThickness: 0.006, bevelSize: 0.006, bevelSegments: 1, curveSegments: 24 });
      };
      K.env(S, { top: '#ffffff', horizon: '#e6eaef', bottom: '#b8b4ad', intensity: 0.36 });
      K.sun(S, { pos: [-14.5, 19.6, 18], target: [0.5, 1, 0], color: '#fff7ec', power: 2.4, size: 13, soft: 1.6, mapSize: 4096 });
      K.skyLight(S, { color: '#e6eeff', power: 1.35, size: 12, center: [0.5, 1, -1], mapSize: 2048 });
      const BOARD = { x0: -15, x1: 15, z0: -9.4, z1: 8, th: 0.3, ppu: 120 };
      put(new THREE.PlaneGeometry(500, 500), new THREE.MeshStandardMaterial({ color: '#a9adb3', roughness: 1 }), [0, -BOARD.th, 0], [-Math.PI / 2, 0, 0]).castShadow = false;
      const bw = BOARD.x1 - BOARD.x0, bd = BOARD.z1 - BOARD.z0, bcx = (BOARD.x0 + BOARD.x1) / 2, bcz = (BOARD.z0 + BOARD.z1) / 2;
      box(bw, BOARD.th, bd, M.foam, [bcx, -BOARD.th / 2 - 0.002, bcz]);
      const marks = [];   // pencil marks on the board under each piece
      const glows = [];   // [material, at time] pairs: a part that turns to the accent when the flow arrives

      // ================================================================ 2. THE ACCENT RULE (the recipe's own)
      const runs = [];
      let laid = 0;
      const run = (curve, t0, t1, radius = 0.032) => {
        const len = curve.getLength(), u = { uHead: { value: 0 }, uTime: { value: 0 }, uLen: { value: len }, uOff: { value: laid }, uAccent: { value: accent } };
        const mat = new THREE.MeshStandardMaterial({ color: '#f1efea', roughness: 0.75 });
        mat.onBeforeCompile = (sh) => {
          Object.assign(sh.uniforms, u);
          sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying float vAlong;').replace('#include <begin_vertex>', '#include <begin_vertex>\nvAlong = uv.x;');
          sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nuniform float uHead, uTime, uLen, uOff; uniform vec3 uAccent; varying float vAlong;')
            .replace('#include <color_fragment>', '#include <color_fragment>\nfloat on = step(vAlong, uHead - 0.0001);\ndiffuseColor.rgb = mix(diffuseColor.rgb, uAccent, on);')
            .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
              float d = fract((uOff + vAlong * uLen - uTime * 2.2) / 0.6);
              totalEmissiveRadiance += uAccent * on * (0.4 + 0.9 * smoothstep(0.0, 0.1, d) * smoothstep(0.42, 0.3, d));`);
        };
        put(new THREE.TubeGeometry(curve, Math.max(24, Math.ceil(len * 36)), radius, 10), mat);
        runs.push({ curve, t0, t1, u }); laid += len;
        return curve;
      };
      const conduit = (pts, r = 0.07) => {
        const P = pts.map(V), path = new THREE.CurvePath(); let prev = P[0];
        for (let i = 1; i < P.length - 1; i++) {
          const a = P[i].clone().add(P[i - 1].clone().sub(P[i]).setLength(Math.min(r, P[i].distanceTo(P[i - 1]) * 0.45)));
          const b = P[i].clone().add(P[i + 1].clone().sub(P[i]).setLength(Math.min(r, P[i].distanceTo(P[i + 1]) * 0.45)));
          path.add(new THREE.LineCurve3(prev, a)); path.add(new THREE.QuadraticBezierCurve3(a, P[i], b)); prev = b;
        }
        path.add(new THREE.LineCurve3(prev, P[P.length - 1]));
        return path;
      };
      const hang = (a, b, sag) => new THREE.CatmullRomCurve3(Array.from({ length: 9 }, (_, i) => { const u = i / 8; return V([K.lerp(a[0], b[0], u), K.lerp(a[1], b[1], u) - sag * 4 * u * (1 - u), K.lerp(a[2], b[2], u)]); }));
      const arc = (a, b, lift) => new THREE.CatmullRomCurve3(Array.from({ length: 13 }, (_, i) => { const u = i / 12; return V([K.lerp(a[0], b[0], u), K.lerp(a[1], b[1], u) + lift * 4 * u * (1 - u), K.lerp(a[2], b[2], u)]); }));
      const glowMat = (base = '#f6f3ec') => white(base, 0.7);
      const bead = put(new THREE.SphereGeometry(0.075, 20, 12), new THREE.MeshBasicMaterial({ color: accent.clone().multiplyScalar(2.0) })); bead.castShadow = bead.receiveShadow = false;
      const beadLight = new THREE.PointLight(accent, 0, 3.2, 2); scene.add(beadLight);

      // ================================================================ 3. THE PIECES (GOLIDE kit): each builds at (x, z), turned ry,
      // scaled s, and returns { top: label anchor, port: where conduits meet it, glow: parts that take the accent }
      const at = (x, z, ry = 0, s = 1) => { const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = ry; g.scale.setScalar(s); scene.add(g); return g; };
      const world = (g, p) => g.localToWorld(V(p)).toArray();
      const figureGeo = (h) => {
        const body = new THREE.Shape([[-0.07, 0], [0.07, 0], [0.15, 0.72], [0.1, 0.78], [-0.1, 0.78], [-0.15, 0.72]].map((p) => new THREE.Vector2(p[0] * h, p[1] * h))), head = new THREE.Shape(); head.absarc(0, 0.9 * h, 0.1 * h, 0, Math.PI * 2);
        return new THREE.ExtrudeGeometry([body, head], { depth: 0.03, bevelEnabled: false, curveSegments: 20 });
      };
      const windows = (g, w, h, d, floors, cols, mat) => {          // window reveals: shallow dark-ish card insets on the front face
        const ws = [];
        for (let f = 0; f < floors; f++) for (let c = 0; c < cols; c++) {
          const x = -w / 2 + (c + 0.5) * w / cols, y = (f + 0.55) * h / floors;
          ws.push(box(w / cols * 0.55, h / floors * 0.45, 0.03, mat, [x, y, d / 2 + 0.012], null, g));
        }
        return ws;
      };
      const P = {
        // any thing the 35 pieces do not cover, written by the storyboard as parts (recipes.object_parts), in white card;
        // gold parts take the accent when the flow arrives (the first part when none is gold)
        custom(x, z, ry, s, p) {
          const g = at(x, z, ry, s), glow = glowMat(), parts = p.build || [];
          const hot = parts.some((q) => q.gold) ? (q) => q.gold : (q) => q === parts[0];
          let H = 0;
          for (const q of parts) {
            const [w, h, d] = q.s, mat = hot(q) ? glow : M.card;
            const geo = q.shape === 'box' ? new THREE.BoxGeometry(w, h, d) : q.shape === 'sphere' ? new THREE.SphereGeometry(0.5, 32, 20).scale(w, h, d)
              : q.shape === 'cone' ? new THREE.ConeGeometry(0.5, 1, 40).scale(w, h, d) : new THREE.CylinderGeometry(0.5, 0.5, 1, 40).scale(w, h, d);
            put(geo, mat, q.c, q.r, g); H = Math.max(H, q.c[1] + h / 2);
          }
          const W = Math.max(...parts.map((q) => q.c[0] + q.s[0] / 2), 0.5);
          return { top: world(g, [0, H + 0.6, 0]), port: world(g, [W + 0.05, 0.05, 0]), glow: [glow] };
        },
        house(x, z, ry, s) {
          const g = at(x, z, ry, s), W = 2.6, D = 2.0, E = 1.5, R = 2.35, win = glowMat();
          box(W, E, D, M.card, [0, E / 2, 0], null, g);
          const roof = cut([[-D / 2 - 0.15, E - 0.05], [D / 2 + 0.15, E - 0.05], [0, R]], [], W + 0.2);
          put(roof, M.plaster, [-(W + 0.2) / 2, 0, 0], [0, Math.PI / 2, 0], g);
          windows(g, W, E, D, 1, 3, win); box(0.38, 0.8, 0.03, M.paper, [0.85, 0.4, D / 2 + 0.014], null, g);
          return { top: world(g, [0, R + 0.25, 0]), port: world(g, [W / 2 + 0.05, 0.05, 0]), glow: [win] };
        },
        tower(x, z, ry, s) {     // an office tower
          const g = at(x, z, ry, s), W = 1.7, H = 6.2, win = glowMat();
          box(W, H, W, M.card, [0, H / 2, 0], null, g); box(W * 0.7, 0.5, W * 0.7, M.plaster, [0, H + 0.25, 0], null, g);
          windows(g, W, H, W, 9, 3, win);
          return { top: world(g, [0, H + 0.75, 0]), port: world(g, [W / 2 + 0.05, 0.05, 0]), glow: [win] };
        },
        bank(x, z, ry, s) {      // columns and a pediment
          const g = at(x, z, ry, s), W = 3.2, D = 2.0, H = 1.8, sign = glowMat();
          box(W + 0.3, 0.2, D + 0.4, M.plaster, [0, 0.1, 0], null, g); box(W, H, D - 0.6, M.card, [0, 0.2 + H / 2, -0.3], null, g);
          for (let i = 0; i < 5; i++) cyl(0.11, H, M.paper, [-W / 2 + 0.3 + i * (W - 0.6) / 4, 0.2 + H / 2, D / 2 - 0.25], g);
          put(cut([[-W / 2 - 0.15, 0], [W / 2 + 0.15, 0], [0, 0.6]], [], D), M.plaster, [0, 0.2 + H, -D / 2 + 0.2], null, g);
          box(1.1, 0.22, 0.03, sign, [0, 0.2 + H + 0.2, D / 2 + 0.22], null, g);
          return { top: world(g, [0, 0.2 + H + 0.9, 0]), port: world(g, [W / 2 + 0.1, 0.05, 0]), glow: [sign] };
        },
        factory(x, z, ry, s) {   // saw-tooth roof and a chimney
          const g = at(x, z, ry, s), W = 4.2, D = 2.4, H = 1.4, win = glowMat();
          box(W, H, D, M.card, [0, H / 2, 0], null, g);
          for (let i = 0; i < 4; i++) put(cut([[0, 0], [W / 4, 0], [W / 4, 0.55]], [], D), M.plaster, [-W / 2 + i * W / 4, H, -D / 2], null, g);
          cyl(0.22, 2.6, M.paper, [W / 2 - 0.5, H + 1.3, -0.5], g, 0.18);
          windows(g, W, H, D, 1, 5, win);
          return { top: world(g, [0, H + 2.9, 0]), port: world(g, [W / 2 + 0.05, 0.05, 0]), glow: [win] };
        },
        datacenter(x, z, ry, s) { // a long hall with rows of vents and cooling units on the roof
          const g = at(x, z, ry, s), W = 5.0, D = 2.6, H = 1.3, vents = glowMat();
          box(W, H, D, M.card, [0, H / 2, 0], null, g);
          for (let i = 0; i < 8; i++) box(0.36, 0.7, 0.03, vents, [-W / 2 + 0.4 + i * (W - 0.8) / 7, 0.6, D / 2 + 0.014], null, g);
          for (let i = 0; i < 4; i++) { box(0.7, 0.3, 0.7, M.foam, [-W / 2 + 0.8 + i * 1.15, H + 0.15, 0], null, g); cyl(0.24, 0.06, M.plaster, [-W / 2 + 0.8 + i * 1.15, H + 0.33, 0], g); }
          return { top: world(g, [0, H + 0.9, 0]), port: world(g, [W / 2 + 0.05, 0.05, 0]), glow: [vents] };
        },
        shop(x, z, ry, s) {
          const g = at(x, z, ry, s), W = 2.2, D = 1.6, H = 1.3, front = glowMat();
          box(W, H, D, M.card, [0, H / 2, 0], null, g); box(W + 0.2, 0.06, 0.5, M.plaster, [0, H * 0.82, D / 2 + 0.2], [0.25, 0, 0], g);
          box(W * 0.8, H * 0.5, 0.03, front, [0, H * 0.35, D / 2 + 0.014], null, g);
          return { top: world(g, [0, H + 0.4, 0]), port: world(g, [W / 2 + 0.05, 0.05, 0]), glow: [front] };
        },
        school(x, z, ry, s) {
          const g = at(x, z, ry, s), W = 3.6, D = 1.8, H = 1.6, win = glowMat();
          box(W, H, D, M.card, [0, H / 2, 0], null, g); box(1.0, 2.6, 1.0, M.plaster, [0, 1.3, 0.5], null, g);
          put(new THREE.ConeGeometry(0.75, 0.7, 4), M.paper, [0, 2.95, 0.5], [0, Math.PI / 4, 0], g);
          windows(g, W, H, D, 1, 6, win);
          return { top: world(g, [0, 3.6, 0]), port: world(g, [W / 2 + 0.05, 0.05, 0]), glow: [win] };
        },
        hospital(x, z, ry, s) {
          const g = at(x, z, ry, s), W = 3.4, D = 2.2, H = 2.6, cross = glowMat();
          box(W, H, D, M.card, [0, H / 2, 0], null, g); windows(g, W, H, D, 3, 5, M.paper);
          box(0.5, 0.15, 0.04, cross, [0, H + 0.45, D / 2 - 0.3], null, g); box(0.15, 0.5, 0.04, cross, [0, H + 0.45, D / 2 - 0.3], null, g);
          box(0.8, 0.9, 0.06, M.plaster, [0, H + 0.45, D / 2 - 0.36], null, g);
          return { top: world(g, [0, H + 1.1, 0]), port: world(g, [W / 2 + 0.05, 0.05, 0]), glow: [cross] };
        },
        tree(x, z, ry, s) {
          const g = at(x, z, ry, s), crown = white('#eeebe6', 1);
          cyl(0.04, 1.4, M.paper, [0, 0.7, 0], g); ball(0.55, crown, [0, 1.5, 0], g);
          return { top: world(g, [0, 2.3, 0]), port: world(g, [0, 0.05, 0.6]), glow: [crown] };
        },
        pine(x, z, ry, s) {
          const g = at(x, z, ry, s), crown = white('#eeebe6', 1);
          cyl(0.04, 0.6, M.paper, [0, 0.3, 0], g);
          for (let i = 0; i < 3; i++) put(new THREE.ConeGeometry(0.55 - i * 0.12, 0.8, 20), crown, [0, 0.8 + i * 0.45, 0], null, g);
          return { top: world(g, [0, 2.4, 0]), port: world(g, [0, 0.05, 0.6]), glow: [crown] };
        },
        forest(x, z, ry, s) {
          const g = at(x, z, ry, s), crown = white('#eeebe6', 1), r = K.rng(Math.round((x + 20) * 13 + (z + 20) * 7));
          for (let i = 0; i < 9; i++) {
            const tx = (r() - 0.5) * 3, tz = (r() - 0.5) * 2.4, h = 0.9 + r() * 0.6;
            cyl(0.035, h, M.paper, [tx, h / 2, tz], g); ball(0.32 + r() * 0.2, crown, [tx, h + 0.15, tz], g);
          }
          return { top: world(g, [0, 2.2, 0]), port: world(g, [1.7, 0.05, 0]), glow: [crown] };
        },
        mountain(x, z, ry, s) {   // stacked contour sheets, like the recipe's hill, taller
          const g = at(x, z, ry, s), peak = white('#fcfbf8', 0.85);
          const R = (a, k) => (3.0 - k * 0.42) * (1 + 0.16 * Math.sin(a * 2 + 0.6 + k * 0.3) + 0.09 * Math.sin(a * 3 + 2 + k) + 0.05 * Math.sin(a * 5 + k * 2));
          for (let k = 0; k < 7; k++) {
            const pts = Array.from({ length: 96 }, (_, i) => { const a = i / 96 * Math.PI * 2, r = R(a, k); return [r * Math.cos(a), r * Math.sin(a)]; });
            put(cut(pts, [], 0.42), k === 6 ? peak : k % 2 ? M.paper : M.card, [0, k * 0.42, 0], [-Math.PI / 2, 0, 0], g);
          }
          return { top: world(g, [0, 3.4, 0]), port: world(g, [2.4, 0.05, 0]), glow: [peak] };
        },
        hill(x, z, ry, s) {
          const g = at(x, z, ry, s), top = white('#fcfbf8', 0.85);
          const R = (a, k) => (2.4 - k * 0.5) * (1 + 0.14 * Math.sin(a * 2 + 0.6 + k * 0.3) + 0.08 * Math.sin(a * 3 + 2 + k));
          for (let k = 0; k < 4; k++) put(cut(Array.from({ length: 80 }, (_, i) => { const a = i / 80 * Math.PI * 2, r = R(a, k); return [r * Math.cos(a), r * Math.sin(a)]; }), [], 0.14), k === 3 ? top : k % 2 ? M.paper : M.card, [0, k * 0.14, 0], [-Math.PI / 2, 0, 0], g);
          return { top: world(g, [0, 1.0, 0]), port: world(g, [1.9, 0.05, 0]), glow: [top] };
        },
        lake(x, z, ry, s) {       // a still sheet of clear resin set into the board
          const g = at(x, z, ry, s), water = new THREE.MeshPhysicalMaterial({ color: '#f2f6f9', roughness: 0.08, transmission: 0.2, thickness: 0.2 });
          const pts = Array.from({ length: 80 }, (_, i) => { const a = i / 80 * Math.PI * 2; return [2.2 * Math.cos(a) * (1 + 0.1 * Math.sin(a * 3)), 1.4 * Math.sin(a)]; });
          put(cut(pts, [], 0.03), water, [0, 0.01, 0], [-Math.PI / 2, 0, 0], g);
          marks.push({ ring: [x, z, 2.3 * s] });
          return { top: world(g, [0, 0.4, 0]), port: world(g, [2.2, 0.05, 0]), glow: [water] };
        },
        river(x, z, ry, s) {      // a winding strip of resin across the board
          const g = at(x, z, ry, s), water = new THREE.MeshPhysicalMaterial({ color: '#f2f6f9', roughness: 0.08 });
          const c = new THREE.CatmullRomCurve3([[-6, 0, -0.6], [-3, 0, 0.5], [0, 0, -0.4], [3, 0, 0.6], [6, 0, -0.2]].map(V));
          const pts = c.getPoints(60), half = 0.45, L = [], R2 = [];
          pts.forEach((p, i) => { const t = c.getTangent(i / 60); L.push([p.x - t.z * half, p.z + t.x * half]); R2.push([p.x + t.z * half, p.z - t.x * half]); });
          put(cut([...L, ...R2.reverse()].map(([a, b]) => [a, -b]), [], 0.025), water, [0, 0.012, 0], [-Math.PI / 2, 0, 0], g);
          return { top: world(g, [0, 0.4, 0]), port: world(g, [6, 0.05, 0]), glow: [water] };
        },
        cloud(x, z, ry, s) {      // on a thin stand, like the recipe's sun
          const g = at(x, z, ry, s), puff = white('#fcfbf8', 0.95), Y = 4.2;
          for (const [dx, dy, r] of [[-0.5, 0, 0.42], [0, 0.18, 0.55], [0.55, 0.02, 0.4], [0.2, -0.12, 0.38]]) ball(r, puff, [dx, Y + dy, 0], g);
          put(K.tube([[0, 0, 0.4], [-0.1, 1.8, 0.35], [0, Y - 0.4, 0.1]], 0.025, { segments: 40 }), M.paper, [0, 0, 0], null, g); cyl(0.3, 0.05, M.card, [0, 0.025, 0.4], g);
          return { top: world(g, [0, Y + 0.85, 0]), port: world(g, [0, Y - 0.45, 0]), glow: [puff] };
        },
        sun(x, z, ry, s) {        // the recipe's sun on its stand
          const g = at(x, z, ry, s), Y = 4.5, core = new THREE.MeshStandardMaterial({ color: '#fbfaf6', roughness: 0.55 });
          ball(0.5, core, [0, Y, 0], g);
          put(K.tube([[0, 0, 0.6], [-0.33, 1.7, 0.55], [-0.22, 3.3, 0.43], [0.38, 4.2, 0.29]], 0.03, { segments: 60 }), M.paper, [0, 0, 0], null, g); cyl(0.34, 0.05, M.card, [0, 0.025, 0.6], g);
          return { top: world(g, [0, Y + 0.8, 0]), port: world(g, [0, Y - 0.55, 0]), glow: [core], light: world(g, [0, Y, 0]) };
        },
        rain(x, z, ry, s) {       // a cloud with fine rain wires below it
          const out = P.cloud(x, z, ry, s), g = scene.children[scene.children.length - 1];
          for (let i = 0; i < 9; i++) cyl(0.008, 1.6, M.paper, [-0.7 + i * 0.17, 2.9 - (i % 3) * 0.2, (i % 2) * 0.2 - 0.1], g);
          return out;
        },
        road(x, z, ry, s) {       // a strip with a dashed centre line, 12 long
          const g = at(x, z, ry, s), lane = glowMat('#f4f2ed');
          box(12, 0.03, 1.6, M.paper, [0, 0.015, 0], null, g);
          for (let i = 0; i < 12; i++) box(0.5, 0.012, 0.06, lane, [-5.6 + i, 0.035, 0], null, g);
          return { top: world(g, [0, 0.6, 0]), port: world(g, [6, 0.05, 0]), glow: [lane] };
        },
        bridge(x, z, ry, s) {
          const g = at(x, z, ry, s), deck = glowMat('#f4f2ed');
          box(6, 0.16, 1.3, deck, [0, 1.1, 0], null, g);
          for (const dx of [-2, 0, 2]) box(0.3, 1.1, 1.0, M.plaster, [dx, 0.55, 0], null, g);
          for (const side of [-0.6, 0.6]) put(K.tube([[-3, 1.2, side], [-1.5, 2.0, side], [0, 2.3, side], [1.5, 2.0, side], [3, 1.2, side]], 0.03, { segments: 50 }), M.paper, [0, 0, 0], null, g);
          return { top: world(g, [0, 2.7, 0]), port: world(g, [3.1, 1.2, 0]), glow: [deck] };
        },
        car(x, z, ry, s) {        // the recipe's car
          const g = at(x, z, ry, s), body = white('#eef3f8', 0.8);
          box(1.7, 0.3, 0.72, body, [0, 0.3, 0], null, g); box(0.92, 0.25, 0.62, M.paper, [-0.08, 0.56, 0], null, g);
          for (const [dx, dz] of [[-0.52, 0.33], [0.52, 0.33], [-0.52, -0.33], [0.52, -0.33]]) put(new THREE.CylinderGeometry(0.15, 0.15, 0.1, 24), M.plaster, [dx, 0.15, dz], [Math.PI / 2, 0, 0], g);
          return { top: world(g, [0, 1.1, 0]), port: world(g, [0.9, 0.05, 0]), glow: [body] };
        },
        truck(x, z, ry, s) {
          const g = at(x, z, ry, s), load = white('#eef3f8', 0.8);
          box(2.4, 1.0, 0.9, load, [-0.4, 0.75, 0], null, g); box(0.8, 0.7, 0.86, M.paper, [1.25, 0.6, 0], null, g);
          for (const dx of [-1.2, -0.3, 1.2]) for (const dz of [-0.45, 0.45]) put(new THREE.CylinderGeometry(0.18, 0.18, 0.1, 24), M.plaster, [dx, 0.18, dz], [Math.PI / 2, 0, 0], g);
          return { top: world(g, [0, 1.7, 0]), port: world(g, [1.7, 0.05, 0]), glow: [load] };
        },
        bus(x, z, ry, s) {
          const g = at(x, z, ry, s), win = glowMat();
          box(3.2, 1.0, 0.95, M.card, [0, 0.7, 0], null, g);
          for (let i = 0; i < 6; i++) box(0.36, 0.28, 0.03, win, [-1.3 + i * 0.5, 0.9, 0.49], null, g);
          for (const dx of [-1.0, 1.0]) for (const dz of [-0.48, 0.48]) put(new THREE.CylinderGeometry(0.17, 0.17, 0.1, 24), M.plaster, [dx, 0.17, dz], [Math.PI / 2, 0, 0], g);
          return { top: world(g, [0, 1.6, 0]), port: world(g, [1.7, 0.05, 0]), glow: [win] };
        },
        train(x, z, ry, s) {      // three carriages on a track
          const g = at(x, z, ry, s), win = glowMat();
          box(9.6, 0.05, 1.0, M.paper, [0, 0.025, 0], null, g);
          for (let c = 0; c < 3; c++) {
            box(2.8, 0.85, 0.8, c === 0 ? M.foam : M.card, [-3 + c * 3, 0.55, 0], null, g);
            for (let i = 0; i < 4; i++) box(0.4, 0.24, 0.03, win, [-4 + c * 3 + i * 0.65, 0.7, 0.41], null, g);
          }
          return { top: world(g, [0, 1.5, 0]), port: world(g, [4.8, 0.05, 0]), glow: [win] };
        },
        plane(x, z, ry, s) {      // on a stand, in flight
          const g = at(x, z, ry, s), body = white('#eef3f8', 0.8), Y = 3.4;
          put(new THREE.CapsuleGeometry(0.22, 2.4, 8, 20), body, [0, Y, 0], [0, 0, Math.PI / 2], g);
          box(0.7, 0.04, 3.2, M.paper, [0.1, Y, 0], null, g); box(0.4, 0.04, 1.2, M.paper, [-1.2, Y + 0.05, 0], null, g); box(0.4, 0.6, 0.04, M.paper, [-1.25, Y + 0.3, 0], null, g);
          put(K.tube([[0, 0, 0.5], [0, 1.6, 0.4], [0, Y - 0.25, 0.05]], 0.025, { segments: 40 }), M.paper, [0, 0, 0], null, g); cyl(0.3, 0.05, M.card, [0, 0.025, 0.5], g);
          return { top: world(g, [0, Y + 0.7, 0]), port: world(g, [1.4, Y, 0]), glow: [body] };
        },
        ship(x, z, ry, s) {       // a container ship
          const g = at(x, z, ry, s), cont = white('#eef3f8', 0.8);
          put(cut([[-2.4, 0], [2.0, 0], [2.6, 0.7], [-2.6, 0.7]], [], 1.2), M.card, [0, 0, -0.6], null, g);
          for (let i = 0; i < 5; i++) for (let j = 0; j < 2; j++) box(0.7, 0.36, 1.0, i % 2 ? cont : M.paper, [-1.6 + i * 0.75, 0.9 + j * 0.37, 0], null, g);
          box(0.6, 1.1, 1.0, M.plaster, [2.0, 1.25, 0], null, g);
          return { top: world(g, [0, 2.3, 0]), port: world(g, [2.6, 0.4, 0]), glow: [cont] };
        },
        pole(x, z, ry, s) {       // the recipe's power pole (wires come from the path)
          const g = at(x, z, ry, s), cap = glowMat();
          cyl(0.06, 3.2, M.card, [0, 1.6, 0], g, 0.045); box(0.98, 0.07, 0.08, M.card, [0, 3.06, 0], null, g);
          for (const dx of [-0.36, 0.36]) cyl(0.035, 0.12, cap, [dx, 3.155, 0], g);
          return { top: world(g, [0, 3.6, 0]), port: world(g, [0.36, 3.22, 0]), glow: [cap], wire: true };
        },
        turbine(x, z, ry, s) {    // a wind turbine (still: only the accent moves)
          const g = at(x, z, ry, s), hub = glowMat();
          cyl(0.12, 4.6, M.card, [0, 2.3, 0], g, 0.07); box(0.6, 0.3, 0.3, M.paper, [0, 4.65, 0.05], null, g); ball(0.14, hub, [0, 4.65, 0.25], g);
          for (let i = 0; i < 3; i++) { const a = i * 2 * Math.PI / 3 + 0.3; box(0.12, 2.0, 0.04, M.paper, [Math.sin(a) * 1.0, 4.65 + Math.cos(a) * 1.0, 0.28], [0, 0, -a], g); }
          return { top: world(g, [0, 5.9, 0]), port: world(g, [0, 0.05, 0.3]), glow: [hub] };
        },
        solar(x, z, ry, s) {      // a ground array: 2 rows of tilted panels
          const g = at(x, z, ry, s), face = glowMat('#f4f6f8');
          for (let r = 0; r < 2; r++) for (let c = 0; c < 4; c++) { box(0.7, 0.04, 0.9, face, [-1.2 + c * 0.8, 0.5, -0.6 + r * 1.2], [0.45, 0, 0], g); cyl(0.025, 0.45, M.paper, [-1.2 + c * 0.8, 0.22, -0.6 + r * 1.2], g); }
          return { top: world(g, [0, 1.2, 0]), port: world(g, [1.8, 0.05, 0]), glow: [face] };
        },
        tower_mast(x, z, ry, s) { // a phone mast
          const g = at(x, z, ry, s), dish = glowMat();
          for (const [dx, dz] of [[-0.3, -0.3], [0.3, -0.3], [0, 0.3]]) put(K.tube([[dx, 0, dz], [dx * 0.3, 2.5, dz * 0.3], [0, 5, 0]], 0.03, { segments: 30 }), M.paper, [0, 0, 0], null, g);
          for (let i = 0; i < 3; i++) box(0.18, 0.5, 0.06, dish, [Math.sin(i * 2.1) * 0.22, 4.6, Math.cos(i * 2.1) * 0.22], [0, i * 2.1, 0], g);
          return { top: world(g, [0, 5.4, 0]), port: world(g, [0, 4.6, 0]), glow: [dish] };
        },
        person(x, z, ry, s) {
          const g = at(x, z, ry, s), card = white('#fcfbf8', 0.9);
          put(figureGeo(0.72), card, [0, 0, 0], null, g);
          return { top: world(g, [0, 1.0, 0]), port: world(g, [0.3, 0.05, 0]), glow: [card] };
        },
        crowd(x, z, ry, s) {
          const g = at(x, z, ry, s), card = white('#fcfbf8', 0.9), r = K.rng(Math.round((x + 30) * 17 + (z + 30) * 5));
          for (let i = 0; i < 9; i++) put(figureGeo(0.5 + r() * 0.25), card, [(r() - 0.5) * 2.4, 0, (r() - 0.5) * 1.6], [0, (r() - 0.5) * 1.2, 0], g);
          return { top: world(g, [0, 1.0, 0]), port: world(g, [1.4, 0.05, 0]), glow: [card] };
        },
        battery(x, z, ry, s) {    // a grid battery container
          const g = at(x, z, ry, s), bar = glowMat();
          box(2.8, 1.2, 1.1, M.card, [0, 0.6, 0], null, g);
          for (let i = 0; i < 5; i++) box(0.36, 0.7, 0.03, bar, [-1.0 + i * 0.5, 0.6, 0.57], null, g);
          return { top: world(g, [0, 1.6, 0]), port: world(g, [1.45, 0.05, 0]), glow: [bar] };
        },
        dam(x, z, ry, s) {
          const g = at(x, z, ry, s), gate = glowMat();
          put(cut([[-3, 0], [3, 0], [2.6, 2.2], [-2.6, 2.2]], [], 0.9), M.plaster, [0, 0, -0.45], null, g);
          for (let i = 0; i < 4; i++) box(0.4, 0.8, 0.03, gate, [-1.5 + i, 0.6, 0.47], null, g);
          return { top: world(g, [0, 2.7, 0]), port: world(g, [0, 0.4, 0.6]), glow: [gate] };
        },
      };

      // ================================================================ 4. PLACE THE PIECES, LAY THE PATH
      const placed = {};
      for (const p of SCENE.pieces || []) {
        const make = P[p.kind];
        if (!make) continue;
        const out = make(p.at[0], p.at[1], (p.turn || 0) * Math.PI / 180, p.scale || 1, p);
        out.id = p.id || p.kind + Object.keys(placed).length;
        placed[out.id] = out;
        marks.push({ ring: [p.at[0], p.at[1], 0.3 * (p.scale || 1)] });
      }
      // the path: stops in order; the accent leaves each stop's port, runs along the board and climbs into the next
      const stops = (SCENE.path || []).map((id) => placed[id]).filter(Boolean);
      const t0 = 0.5, span = Math.max(1.2, DUR - 2.4), seg = stops.length > 1 ? span / (stops.length - 1) : span;
      stops.forEach((s, i) => { s.at = t0 + i * seg; });
      for (let i = 0; i + 1 < stops.length; i++) {
        const a = stops[i].port, b = stops[i + 1].port, ta = stops[i].at + 0.15, tb = stops[i + 1].at;
        if (stops[i].wire && stops[i + 1].wire) run(hang(a, b, 0.25), ta, tb, 0.026);
        else if (a[1] > 1.5 || b[1] > 1.5) run(arc(a, b, 1.2), ta, tb, 0.028);              // through the air: a light arc
        else run(conduit([a, [a[0], 0.04, a[2]], [b[0], 0.04, a[2]], [b[0], 0.04, b[2]], b]), ta, tb);
      }
      for (const s of stops) for (const m of s.glow || []) glows.push([m, s.at, m.color.clone()]);
      const sunPiece = Object.values(placed).find((p) => p.light);
      if (sunPiece) { const l = new THREE.PointLight(accent, 0, 5, 2); l.position.set(...sunPiece.light); scene.add(l); sunPiece.lamp = l; }
      // the board's pencil work: a faint grid, a ring under each piece
      const scored = K.canvasTex(Math.round(bw * BOARD.ppu), Math.round(bd * BOARD.ppu), (ctx, w, h) => {
        const X = (x) => (x - BOARD.x0) * BOARD.ppu, Z = (z) => (z - BOARD.z0) * BOARD.ppu;
        const line = (pts, a = 0.4, lw = 1.7) => { ctx.strokeStyle = `rgba(52,58,66,${a})`; ctx.lineWidth = lw; ctx.beginPath(); pts.forEach((p, i) => (i ? ctx.lineTo(X(p[0]), Z(p[1])) : ctx.moveTo(X(p[0]), Z(p[1])))); ctx.stroke(); };
        ctx.fillStyle = '#fbfaf6'; ctx.fillRect(0, 0, w, h);
        for (let x = Math.ceil(BOARD.x0); x < BOARD.x1; x++) line([[x, BOARD.z0], [x, BOARD.z1]], 0.1, 1.2);
        for (let z = Math.ceil(BOARD.z0); z < BOARD.z1; z++) line([[BOARD.x0, z], [BOARD.x1, z]], 0.1, 1.2);
        for (const m of marks) if (m.ring) { ctx.strokeStyle = 'rgba(52,58,66,0.26)'; ctx.lineWidth = 1.6; ctx.beginPath(); ctx.arc(X(m.ring[0]), Z(m.ring[1]), m.ring[2] * BOARD.ppu, 0, 7); ctx.stroke(); }
      });
      put(new THREE.PlaneGeometry(bw, bd), new THREE.MeshStandardMaterial({ map: scored, roughness: 0.94 }), [bcx, 0, bcz], [-Math.PI / 2, 0, 0]).castShadow = false;

      // ================================================================ 5. LABELS (the recipe's own): numbered, with leader lines
      const STEPS = (SCENE.steps || []).map((s, i) => ({ ...s, key: s.at_piece || (SCENE.path || [])[i], at: (placed[s.at_piece || (SCENE.path || [])[i]] || {}).at ?? 0.6 + i, off: s.off || null }))
        .filter((s) => placed[s.key]);
      const INK = '#1b1e22', pv = new THREE.Vector3();
      const px = (p, W, H) => { pv.set(p[0], p[1], p[2]).project(camera); return [(pv.x * 0.5 + 0.5) * W, (-pv.y * 0.5 + 0.5) * H]; };
      const halo = (ctx, text, x, y) => { ctx.strokeStyle = 'rgba(255,255,255,0.55)'; ctx.lineWidth = 6; ctx.lineJoin = 'round'; ctx.strokeText(text, x, y); ctx.fillStyle = INK; ctx.fillText(text, x, y); };
      function label(ctx, step, i, t, W, H) {
        const p = K.seg(t, step.at, step.at + 0.6); if (p <= 0) return;
        ctx.font = '700 50px "Inter"'; ctx.letterSpacing = '3px'; const wName = ctx.measureText(step.name).width;
        ctx.font = '500 38px "Inter"'; ctx.letterSpacing = '0px'; const wText = Math.max(wName, ctx.measureText(step.note || '').width), R = 25;
        const off = step.off || [-380, -170];
        const a = px(placed[step.key].top, W, H), c = [K.clamp(a[0] + off[0], 60 + R, W - 60 - R - 18 - wText), K.clamp(a[1] + off[1], 60 + R, H - 110)];
        const d = Math.hypot(a[0] - c[0], a[1] - c[1]) || 1, ux = (a[0] - c[0]) / d, uy = (a[1] - c[1]) / d;
        const grow = K.ease.out(K.clamp(p / 0.45)), ex = a[0] - ux * (d - R) * grow, ey = a[1] - uy * (d - R) * grow;
        ctx.lineCap = 'round'; ctx.strokeStyle = 'rgba(255,255,255,0.7)'; ctx.lineWidth = 6; ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(ex, ey); ctx.stroke();
        ctx.strokeStyle = INK; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(ex, ey); ctx.stroke();
        ctx.fillStyle = INK; ctx.beginPath(); ctx.arc(a[0], a[1], 6, 0, 7); ctx.fill();
        const pop = K.ease.outBack(K.clamp((p - 0.35) / 0.4)); if (pop <= 0) return;
        ctx.fillStyle = 'rgba(255,255,255,0.92)'; ctx.beginPath(); ctx.arc(c[0], c[1], R * pop, 0, 7); ctx.fill(); ctx.lineWidth = 2.5; ctx.strokeStyle = INK; ctx.stroke();
        ctx.globalAlpha = K.clamp((p - 0.45) / 0.3); ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.font = '600 30px "IBM Plex Mono"'; ctx.fillStyle = INK; ctx.fillText(String(i + 1), c[0], c[1] + 2);
        const tx = c[0] + R + 18 - (1 - K.ease.out(K.clamp((p - 0.4) / 0.5))) * 14;
        ctx.textAlign = 'left'; ctx.font = '700 50px "Inter"'; ctx.letterSpacing = '3px'; halo(ctx, step.name, tx, c[1] + 2);
        if (step.note) { ctx.font = '500 38px "Inter"'; ctx.letterSpacing = '0px'; halo(ctx, step.note, tx, c[1] + 50); }
        ctx.globalAlpha = 1;
      }

      // ================================================================ 6. CAMERA (the recipe's crane): low and close on the
      // first stop, rising and pulling back until every piece is in frame
      // framed on the stops (the story), not on wide scenery such as a long road or river
      const box3 = new THREE.Box3();
      for (const s of stops) for (const p of [s.top, s.port]) box3.expandByPoint(V(p));
      if (box3.isEmpty()) for (const o of scene.children) if (o.isGroup) box3.expandByObject(o);
      if (box3.isEmpty()) box3.set(V([-4, 0, -4]), V([4, 3, 4]));
      box3.expandByScalar(1.2);
      const ctr = box3.getCenter(new THREE.Vector3()), rad = box3.getBoundingSphere(new THREE.Sphere()).radius;
      const first = stops[0] ? stops[0].top : ctr.toArray(), far = rad / Math.tan(12 * Math.PI / 180) * 0.78;
      const cam = K.path([[0, [-21, 12, far * 0.62, first[0], first[1] * 0.7, first[2], 0.085, 1.9]],
                          [DUR * 0.45, [-14, 16, far * 0.82, K.lerp(first[0], ctr.x, 0.6), ctr.y + 0.4, K.lerp(first[2], ctr.z, 0.6), 0.08, 1.5]],
                          [DUR * 1.1, [-6, 21, far, ctr.x, ctr.y + 0.3, ctr.z, 0.07, 1.4]]]);

      // GOLIDE (no collision): each label's side is chosen once, on the held last frame, so no two labels touch;
      // the same offsets hold through the move
      let laidOut = false;
      const aimAt = (t) => { const c = cam(t), a = c[0] * Math.PI / 180, e = c[1] * Math.PI / 180, aim = [c[3], c[4], c[5]];
        K.look(camera, [aim[0] + c[2] * Math.sin(a) * Math.cos(e), aim[1] + c[2] * Math.sin(e), aim[2] + c[2] * Math.cos(a) * Math.cos(e)], aim); camera.updateMatrixWorld(); };
      function layout(ctx, W, H) {
        laidOut = true;
        const keep = camera.matrixWorld.clone(), pos = camera.position.clone(), q = camera.quaternion.clone();
        aimAt(DUR);
        const taken = [], R = 25;
        const tries = [[-380, -170], [160, -150], [-380, 110], [160, 110], [-420, -320], [200, -320], [-440, 260], [220, 260], [-60, -300]];
        STEPS.forEach((st) => {
          ctx.font = '700 50px "Inter"'; ctx.letterSpacing = '3px'; const wName = ctx.measureText(st.name).width;
          ctx.font = '500 38px "Inter"'; ctx.letterSpacing = '0px'; const w = Math.max(wName, ctx.measureText(st.note || '').width) + R * 2 + 30;
          const a = px(placed[st.key].top, W, H);
          let best = null;
          for (const off of (st.off ? [st.off] : []).concat(tries)) {
            const cx = K.clamp(a[0] + off[0], 60 + R, W - 60 - R - 18 - (w - R * 2 - 30)), cy = K.clamp(a[1] + off[1], 60 + R, H - 110);
            const b = [cx - R - 6, cy - 40, cx + w + 6, cy + 74];
            if (!taken.some((o) => b[0] < o[2] && b[2] > o[0] && b[1] < o[3] && b[3] > o[1])) { best = [off, b]; break; }
          }
          if (best) { st.off = best[0]; taken.push(best[1]); }
        });
        camera.position.copy(pos); camera.quaternion.copy(q); camera.matrixWorld.copy(keep);
      }

      return {
        update(t) {
          for (const [m, a, c0] of glows) { const k = K.seg(t, a, a + 0.3, K.ease.out); m.color.copy(c0).lerp(accent, k); m.emissive.copy(accent).multiplyScalar(k * 0.25 + 0.5 * K.seg(t, a, a + 0.08) * (1 - K.seg(t, a + 0.08, a + 0.6))); }
          if (sunPiece) sunPiece.lamp.intensity = 5 * K.seg(t, sunPiece.at, sunPiece.at + 0.4);
          let live = null;
          for (const r of runs) { const u = K.seg(t, r.t0, r.t1); r.u.uHead.value = u * 1.001; r.u.uTime.value = t; if (t >= r.t0 && t < r.t1) live = [r, u]; }
          if (live) { bead.position.copy(live[0].curve.getPointAt(live[1])); beadLight.position.copy(bead.position); beadLight.position.z += 0.4; }
          bead.visible = !!live; beadLight.intensity = live ? 0.45 : 0;
          const c = cam(t), a = c[0] * Math.PI / 180, e = c[1] * Math.PI / 180, aim = [c[3], c[4], c[5]];
          K.look(camera, [aim[0] + c[2] * Math.sin(a) * Math.cos(e), aim[1] + c[2] * Math.sin(e), aim[2] + c[2] * Math.cos(a) * Math.cos(e)], aim);
          K.focus(camera, [aim[0], aim[1], aim[2] + c[7]], c[6]);
        },
        overlay(ctx, t, W, H) {
          if (!laidOut) layout(ctx, W, H);
          camera.updateMatrixWorld();
          STEPS.forEach((s, i) => label(ctx, s, i, t, W, H));
          if (TITLE[0] || TITLE[1]) {
            ctx.textAlign = 'right'; ctx.textBaseline = 'alphabetic'; ctx.fillStyle = INK;
            const ta = 1 - K.seg(t, DUR * 0.55, DUR * 0.55 + 0.5);
            ctx.font = '600 30px "IBM Plex Mono"'; ctx.letterSpacing = '5px'; ctx.globalAlpha = 0.7 * ta; ctx.fillText(TITLE[0], W - 64, 86);
            ctx.font = '700 44px "Inter"'; ctx.letterSpacing = '0px'; ctx.globalAlpha = ta; ctx.fillText(TITLE[1], W - 66, 140); ctx.globalAlpha = 1;
          }
        },
      };
    },
  });
}
