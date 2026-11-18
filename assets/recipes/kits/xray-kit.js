{
  // ---------------------------------------------------------------- content (filled by the engine for each beat)
  // GOLIDE X-Ray kit (2026-11-18): the X-Ray recipe's own construction (its film, section cut, scanner bed, scanning
  // plane, flow rays, callouts, crane camera and sound, unchanged), with its one topic-built object (the flask) replaced
  // by a library of real objects whose inner parts are known: phone, laptop, chip, battery cell, server. The
  // storyboard names the object, up to three of its parts in order and what flows. Free: no model writes code.
  const SCENE = __SCENE__;
  const DUR = SCENE.duration || 8, Q = DUR / 8;                    // the recipe's own 8-second timing, stretched to the beat
  const COOL = '#b0d0ec', ACCENT = SCENE.accent || '#ff9a22';
  const MM = 28;
  const SCAN = [0.7 * Q, 2.75 * Q];
  const FLOW = SCENE.flow || 'current';                            // heat, air: wavy rays; current, data, force: straight
  const K0 = globalThis.K;

  // ---------------------------------------------------------------- the object: ANY object, from the storyboard's parts
  // (the engine's part format, read and scaled by recipes.object_parts). The shell is the part named like one, else
  // the biggest; film density follows size (small, compact parts read dense), the look before the scan follows the name.
  const OBJ = (() => {
    const by = {}, vol = (p) => p.s[0] * p.s[1] * p.s[2];
    SCENE.build.forEach((p) => (by[p.name] = by[p.name] || []).push(p));
    const names = Object.keys(by), total = (n) => by[n].reduce((v, p) => v + vol(p), 0);
    const big = names.reduce((a, b) => (total(b) > total(a) ? b : a));
    const SHELL = /^(shell|body|case|casing|housing|chassis|frame|hull|can|skin|cover|outer|enclosure)/;
    const look = (n, g) => g ? 'copper' : /glass|lens|screen|window|display/.test(n) ? 'glass' : /board|pcb/.test(n) ? 'pcb' : /die|silicon|wafer/.test(n) ? 'silicon' : /copper|coil|wire|winding|cable/.test(n) ? 'copper' : 'dark';
    const parts = {};
    names.forEach((n) => {
      const shell = SHELL.test(n) || (n === big && names.length > 1 && !names.some((m) => SHELL.test(m)));
      const v = total(n) / by[n].length;
      parts[n] = { shapes: by[n], lit: shell ? 'alu' : look(n, by[n][0].gold), k: shell ? 0.08 : K0.clamp(0.95 / (1 + Math.cbrt(v)), 0.25, 1.3), shell };
    });
    const span = (k) => { const lo = Math.min(...SCENE.build.map((p) => p.c[k] - p.s[k] / 2)), hi = Math.max(...SCENE.build.map((p) => p.c[k] + p.s[k] / 2)); return hi - lo; };
    return { len: span(0), depth: span(2), height: span(1), parts };
  })();
  const LEN = OBJ.len, HALF = LEN / 2, AXIS_Y = OBJ.height / 2;
  // the story's parts, lit one at a time; `at` is when the flow reaches the part and it flares, as in the recipe
  const PARTS = (SCENE.parts || []).filter((p) => OBJ.parts[p.part]).slice(0, 3).map((p, i, A) => ({ ...p, at: (A.length === 1 ? 4.6 : 3.5 + i * (2.8 / (A.length - 1))) * Q }));
  const centre = (name) => { const sh = OBJ.parts[name].shapes.length <= 2 ? OBJ.parts[name].shapes.slice(0, 1) : OBJ.parts[name].shapes, c = [0, 0, 0]; sh.forEach((p) => p.c.forEach((v, k) => (c[k] += v / sh.length))); return c; };
  const top = (name) => Math.max(...OBJ.parts[name].shapes.map((p) => p.c[1] + p.s[1] / 2));
  const FLOOR = Math.max(...Object.keys(OBJ.parts).map(top)) + 0.06;   // the flow is drawn in a plane just above the object

  // ---------------------------------------------------------------- the flow (shared by picture and sound)
  // into each part from the one before it (the first from the object's near edge): three rays side by side
  const HEAT = (() => {
    const rays = [], wavy = FLOW === 'heat' || FLOW === 'air';
    const wave = (a, c) => {
      const pts = [], dx = c[0] - a[0], dy = c[1] - a[1], l = Math.hypot(dx, dy), n = 60;
      for (let i = 0; i <= n; i++) { const f = i / n, w = wavy ? Math.sin(f * l / 0.2 * 2 * Math.PI) * 0.055 * Math.min(1, f * l / 0.16, (1 - f) * l / 0.16) : 0; pts.push([a[0] + dx * f - dy / l * w, a[1] + dy * f + dx / l * w]); }
      return pts;
    };
    PARTS.forEach((p, i) => {
      const c = centre(p.part), to = [c[0], -c[2]];
      const from = i ? (() => { const b = centre(PARTS[i - 1].part); return [b[0], -b[2]]; })() : [-HALF - 0.9, -c[2]];
      const dx = to[0] - from[0], dy = to[1] - from[1], l = Math.hypot(dx, dy) || 1, nx = -dy / l, ny = dx / l, stopShort = 0.45;
      [-0.28, 0, 0.28].forEach((o, j) => {
        const a = [from[0] + nx * o + (i ? dx / l * 0.45 : 0), from[1] + ny * o + (i ? dy / l * 0.45 : 0)], b = [to[0] + nx * o - dx / l * stopShort, to[1] + ny * o - dy / l * stopShort];
        const dur = 0.42 + 0.04 * j;
        rays.push({ part: i, pts: wave(a, b), t0: p.at - dur - 0.02 * j, dur, bar: [b[0], b[1], Math.atan2(dy, dx) + Math.PI / 2] });
      });
    });
    rays.forEach((r) => { r.stop = r.t0 + r.dur; });
    return rays;
  })();

  registerStyle({
    id: 'x-ray-kit',
    name: 'X-Ray',
    family: 'Filters over 3D',
    look: 'A radiograph you can move around: the object turns into glowing film on a dark scanner bed, every wall brightest where you look through the most material, with one warm accent for the part that matters right now.',
    motion: 'The object starts solid. A scanning plane sweeps along it, the cut face glows as a live cross-section, and everything behind the plane is left see-through. Then the inner parts light up one at a time as something runs into them.',
    duration: DUR,
    fonts: ['700 78px "Space Grotesk"', '500 44px "Space Grotesk"', '500 30px "IBM Plex Mono"'],
    render: { samples: 48, shutter: 0.5, tone: 'neutral', exposure: 1.0, bloom: 0.5, bloomThreshold: 0.9, vignette: 0.34, grain: 0.025, fov: 22, background: '#050607' },

    build(S) {
      const { THREE, K, scene, camera, renderer } = S;
      renderer.localClippingEnabled = true;
      // ================================================================ the X-ray kit (reusable for any object)
      // ONE CUT PLANE divides the world: solid, lit things live on its positive side, the X-ray on the other.
      const cutPlane = new THREE.Plane(new THREE.Vector3(1, 0, 0), 0);          // lit materials are clipped by this
      const CUT = { value: new THREE.Vector4() }, REF = { value: new THREE.Vector4(0, 1, 0, 0) };
      const setCut = (x) => { cutPlane.constant = -x; CUT.value.set(-1, 0, 0, x); };

      // 1. THE FILM. Give it to any CLOSED mesh. Back faces add their distance from the eye, front faces subtract
      // theirs, so what is left in the (float) frame is the length of the ray inside the part: a real radiograph.
      // Thin walls come out as bright rims with a faint skin, solids glow from the middle, overlaps add up, and none
      // of it needs normals, sorting or depth. The cut plane is applied by clamping the distance, so a cut part
      // stays "closed". Distances are measured from a reference plane through the object to keep the numbers small.
      // Rules: the mesh must be watertight with faces pointing outward (every core three.js solid is); the film is
      // drawn over everything (no depth test), so keep the camera on the X-ray side of the cut; `density` is brightness
      // per world unit of material, around 0.1-0.2 for bulky solids and 0.7-1 for thin walls.
      // For open sheets (a plane, a cloth, a label) pass `sheet` = its thickness: then each surface adds
      // thickness / cos(view angle), the same thing for a wall too thin to model.
      const xray = (color, density, sheet = 0) => new THREE.ShaderMaterial({
        uniforms: { uColor: { value: new THREE.Color(color) }, uK: { value: density }, uSheet: { value: sheet }, uCut: CUT, uRef: REF },
        vertexShader: 'varying vec3 vW, vN; void main(){ vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; vN = mat3(modelMatrix) * normal; gl_Position = projectionMatrix * viewMatrix * w; }',
        fragmentShader: `uniform vec3 uColor; uniform float uK, uSheet; uniform vec4 uCut, uRef; varying vec3 vW, vN;
          void main(){
            vec3 ro = cameraPosition, rd = vW - ro; float d = length(rd), len; rd /= d;
            if (uSheet > 0.0) {
              if (dot(uCut.xyz, vW) + uCut.w < 0.0) discard;
              len = uSheet / max(abs(dot(normalize(vN), rd)), 0.07);
            } else {
              float dn = dot(uCut.xyz, rd); dn = abs(dn) < 1e-5 ? 1e-5 : dn;
              float sc = -(dot(uCut.xyz, ro) + uCut.w) / dn;              // where this ray meets the cut plane
              d = dn > 0.0 ? max(d, sc) : min(d, sc);                     // only count the part on the X-ray side
              len = (gl_FrontFacing ? -1.0 : 1.0) * (d + (dot(uRef.xyz, ro) + uRef.w) / dot(uRef.xyz, rd));
            }
            gl_FragColor = vec4(uColor * uK * len, 1.0);
          }`,
        side: THREE.DoubleSide, transparent: true, depthTest: false, depthWrite: false,
        blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneFactor,
      });

      // 2. THE SECTION CUT. A lit, closed mesh is clipped by the cut plane, and its back faces are drawn in a flat
      // glowing colour. Seen through the cut, the back faces of a closed solid cover exactly the area where the
      // plane passes through material, so this IS the cap: a clean cross-section with no stencil buffer. (Parts must
      // not overlap each other; nested parts, like a bottle inside a bottle, are fine.)
      const sectioned = (geo, mat, capColor, capGain) => {
        mat.clippingPlanes = [cutPlane]; mat.clipShadows = true;
        const m = new THREE.Mesh(geo, mat); m.castShadow = true; m.receiveShadow = true;
        const cap = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: new THREE.Color(capColor).multiplyScalar(capGain), side: THREE.BackSide, clippingPlanes: [cutPlane] }));
        m.add(cap); return m;
      };

      // 3. CLOSED SOLIDS OF REVOLUTION. revolve(loop) spins a closed outline of [radius, height] points; wall(line, t)
      // gives the outline of a wall of thickness t around a centre line; offset(line, d) shifts a line sideways.
      const fine = (pts, n = 150) => new THREE.CatmullRomCurve3(pts.map(([r, y]) => new THREE.Vector3(r, y, 0)), false, 'centripetal').getSpacedPoints(n).map((v) => [Math.max(0, v.x), v.y]);
      const offset = (line, d) => line.map((p, i) => { const a = line[Math.max(0, i - 1)], b = line[Math.min(line.length - 1, i + 1)], dx = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dx, dy) || 1; return [Math.max(0, p[0] + dy / l * d), p[1] - dx / l * d]; });
      const wall = (line, t) => offset(line, t / 2).concat(offset(line, -t / 2).reverse());
      const revolve = (loop, seg = 128) => {
        let area = 0; loop.forEach((p, i) => { const q = loop[(i + 1) % loop.length]; area += p[0] * q[1] - q[0] * p[1]; });
        const pts = (area < 0 ? loop.slice().reverse() : loop).map(([r, y]) => new THREE.Vector2(r, y));   // counter-clockwise = faces outward
        if (pts[0].x > 1e-6 || pts[pts.length - 1].x > 1e-6) pts.push(pts[0].clone());
        return new THREE.LatheGeometry(pts, seg);
      };

      // ================================================================ the scene
      K.env(S, { top: '#0b0d11', horizon: '#08090c', bottom: '#020203', panels: [
        { pos: [0, 12, 5], size: [20, 2.6], color: '#eef4ff', power: 7 },       // a long strip overhead: the highlight that runs down the steel
        { pos: [0, 15, -2], size: [26, 12], color: '#dfe8f5', power: 1.1 },      // a big soft ceiling so the steel is never black
        { pos: [-13, 4, 3], size: [3, 7], color: '#cfe0ff', power: 6 },
        { pos: [5, 4, -13], size: [12, 3], color: '#8fb6ff', power: 2.2 },
      ] });
      const key = K.spot(S, { pos: [-5, 11, 7.5], target: [0, 1, 0], color: '#fff3e2', power: 1500, angle: 0.62, penumbra: 0.95, soft: 0.8 });
      // the scanner bed: dark anodised plate, and a layer of fine printed marks (grid, plate outline, centre line, scale bar)
      const bed = new THREE.Mesh(new THREE.PlaneGeometry(120, 120), new THREE.MeshStandardMaterial({ color: '#0e1115', roughness: 0.62, metalness: 0.2 }));
      bed.rotation.x = -Math.PI / 2; bed.receiveShadow = true; scene.add(bed);
      const BW = 26, PX = 4096 / BW;
      const marksTex = K.canvasTex(4096, 4096, (c) => {
        const X = (x) => (x + BW / 2) * PX, Z = X, line = (x0, z0, x1, z1, a, w = 2) => { c.strokeStyle = `rgba(168,207,242,${a})`; c.lineWidth = w; c.beginPath(); c.moveTo(X(x0), Z(z0)); c.lineTo(X(x1), Z(z1)); c.stroke(); };
        c.fillStyle = '#000'; c.fillRect(0, 0, 4096, 4096);
        const step = 10 / MM, x0 = -HALF;                                        // a 10 mm grid that starts at the base of the flask
        for (let i = -30; i <= 60; i++) { const major = i % 5 === 0, x = x0 + i * step; if (Math.abs(x) < 9.5) line(x, -5.5, x, 5.5, major ? 0.13 : 0.05, major ? 2 : 1.5); }
        for (let i = -15; i <= 15; i++) { const major = i % 5 === 0, z = i * step; line(-9.5, z, 9.5, z, major ? 0.13 : 0.05, major ? 2 : 1.5); }
        c.setLineDash([36, 10, 6, 10]); line(-6.2, 0, 6.2, 0, 0.5, 2); c.setLineDash([]);     // the centre line of the part
        // the detector plate: outline and corner brackets, and a registration cross on every 50 mm node
        const px = 5.7, pz = 3.6; c.strokeStyle = 'rgba(168,207,242,0.3)'; c.lineWidth = 2; c.strokeRect(X(-px), Z(-pz), 2 * px * PX, 2 * pz * PX);
        for (const sx of [-1, 1]) for (const sz of [-1, 1]) { line(sx * px, sz * pz, sx * (px - 0.45), sz * pz, 0.85, 5); line(sx * px, sz * pz, sx * px, sz * (pz - 0.45), 0.85, 5); }
        for (let i = -5; i <= 30; i += 5) for (let j = -10; j <= 10; j += 5) { const x = x0 + i * step, z = j * step; if (Math.abs(x) < px) { line(x - 0.07, z, x + 0.07, z, 0.32, 2.5); line(x, z - 0.07, x, z + 0.07, 0.32, 2.5); } }
        // a scale bar, as on any radiograph
        const bl = 50 / MM, bx = HALF - bl, bz = OBJ.depth / 2 + 0.75;   // GOLIDE: just under the object's right end line(bx, bz, bx + bl, bz, 0.9, 4); line(bx, bz - 0.09, bx, bz + 0.09, 0.9, 4); line(bx + bl, bz - 0.09, bx + bl, bz + 0.09, 0.9, 4);
        c.font = '500 44px "IBM Plex Mono"'; c.textAlign = 'left'; c.textBaseline = 'bottom'; c.fillStyle = 'rgba(168,207,242,0.9)'; c.fillText('50 mm', X(bx), Z(bz - 0.12));
      });
      const marks = new THREE.Mesh(new THREE.PlaneGeometry(BW, BW), new THREE.MeshBasicMaterial({ map: marksTex, blending: THREE.AdditiveBlending, transparent: true, depthWrite: false }));
      marks.rotation.x = -Math.PI / 2; marks.position.y = 0.004; scene.add(marks);

      // brushed metal: fine rings around the axis, used for roughness and a slight bump
      const brush = K.canvasTex(64, 2048, (c) => { const r = K.rng(3); for (let y = 0; y < 2048; y++) { const v = Math.round(160 + r.range(-22, 22) + (r.chance(0.03) ? r.range(-30, 25) : 0)); c.fillStyle = `rgb(${v},${v},${v})`; c.fillRect(0, y, 64, 1); } }, { data: true });
      const steel = (color, rough) => new THREE.MeshStandardMaterial({ color, metalness: 0.9, roughness: rough, roughnessMap: brush, bumpMap: brush, bumpScale: 0.03 });
      const plastic = (color) => new THREE.MeshStandardMaterial({ color, metalness: 0, roughness: 0.42 });

      // ---- the object. Each part is one closed geometry with two looks: lit and sectioned, and X-ray film.
      const LIT = { alu: () => steel('#c4c8ce', 0.5), dark: () => plastic('#15171a'), pcb: () => new THREE.MeshStandardMaterial({ color: '#0d3a24', roughness: 0.5 }),
        glass: () => new THREE.MeshStandardMaterial({ color: '#0b0f16', metalness: 0.3, roughness: 0.08 }), copper: () => new THREE.MeshStandardMaterial({ color: '#d98a54', metalness: 1, roughness: 0.3 }),
        silicon: () => new THREE.MeshStandardMaterial({ color: '#59606e', metalness: 1, roughness: 0.3 }) };
      const obj = new THREE.Group(); scene.add(obj);
      const lit = new THREE.Group(), film = new THREE.Group(); obj.add(lit, film);
      const X = {}, KD = {};
      const shapeGeo = (p) => {
        const [w, h, d] = p.s; let g;
        if (p.shape === 'box') g = K.roundedBox(w, h, d, Math.min(0.04, w * 0.3, h * 0.3, d * 0.3), 2);
        else if (p.shape === 'sphere') g = new THREE.SphereGeometry(0.5, 32, 20).scale(w, h, d);
        else if (p.shape === 'cone') g = new THREE.ConeGeometry(0.5, 1, 48).scale(w, h, d);
        else g = new THREE.CylinderGeometry(0.5, 0.5, 1, 48).scale(w, h, d);
        g.applyMatrix4(new THREE.Matrix4().makeRotationFromEuler(new THREE.Euler(...p.r))); g.translate(...p.c); return g;
      };
      const story = new Set(PARTS.map((p) => p.part));
      for (const [name, def] of Object.entries(OBJ.parts)) {
        X[name] = []; KD[name] = def.k;
        for (const sh of def.shapes) {
          const geo = shapeGeo(sh);
          lit.add(sectioned(geo, LIT[def.lit](), def.shell ? COOL : story.has(name) ? ACCENT : COOL, def.shell ? 1.7 : 1.0));
          const m = xray(COOL, def.k); X[name].push(m); const f = new THREE.Mesh(geo, m); f.frustumCulled = false; film.add(f);
        }
      }
      // ---- the scanning plane: a faint sheet with a bright frame, and its line on the bed
      const sheet = new THREE.Mesh(new THREE.PlaneGeometry(6.2, 4.1), new THREE.ShaderMaterial({
        uniforms: { uColor: { value: new THREE.Color(COOL) }, uGain: { value: 1 } },
        vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
        fragmentShader: `uniform vec3 uColor; uniform float uGain; varying vec2 vUv;
          void main(){ vec2 e = min(vUv, 1.0 - vUv) * vec2(6.2, 4.1); float frame = smoothstep(0.035, 0.0, min(e.x, e.y)) * 1.6, floorLine = smoothstep(0.07, 0.0, vUv.y * 4.1) * 3.0;
            gl_FragColor = vec4(uColor * uGain * (0.035 + 0.05 * (1.0 - vUv.y) + frame + floorLine), 1.0); }`,
        side: THREE.DoubleSide, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      }));
      sheet.rotation.y = Math.PI / 2; scene.add(sheet);
      sheet.scale.set(Math.max(1, OBJ.depth / 5), Math.max(1, (FLOOR + 1) / 4), 1);
      // ---- heat: ribbons, arrow heads and the small bars where a ray is stopped, all in one plane that turns to face the camera
      const heat = new THREE.Group(); heat.matrixAutoUpdate = false; scene.add(heat);
      const HOT = new THREE.Color(ACCENT).lerp(new THREE.Color('#ffffff'), 0.4);      // rays are the accent, a step whiter so they read on the warm drink
      const glow = (gain = 1) => new THREE.MeshBasicMaterial({ color: HOT.clone().multiplyScalar(gain), blending: THREE.AdditiveBlending, transparent: true, depthTest: false, depthWrite: false });
      const ribbon = (pts, w) => {
        const pos = [], aS = [], aV = [], idx = [], acc = [0];
        for (let i = 1; i < pts.length; i++) acc.push(acc[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
        pts.forEach((p, i) => {
          const a = pts[Math.max(0, i - 1)], b = pts[Math.min(pts.length - 1, i + 1)], dx = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dx, dy) || 1, s = acc[i] / acc[acc.length - 1];
          pos.push(p[0] - dy / l * w / 2, p[1] + dx / l * w / 2, 0, p[0] + dy / l * w / 2, p[1] - dx / l * w / 2, 0); aS.push(s, s); aV.push(1, -1);
          if (i) idx.push(2 * i - 2, 2 * i - 1, 2 * i, 2 * i - 1, 2 * i + 1, 2 * i);
        });
        const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('aS', new THREE.Float32BufferAttribute(aS, 1)); g.setAttribute('aV', new THREE.Float32BufferAttribute(aV, 1)); g.setIndex(idx);
        return { g, acc };
      };
      const rayMat = () => new THREE.ShaderMaterial({
        uniforms: { uColor: { value: HOT }, uHead: { value: 0 }, uGain: { value: 1 }, uFlow: { value: 0 } },
        vertexShader: 'attribute float aS, aV; varying float vS, vV; void main(){ vS = aS; vV = aV; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
        fragmentShader: `uniform vec3 uColor; uniform float uHead, uGain, uFlow; varying float vS, vV;
          void main(){ if (vS > uHead) discard;
            float tip = exp(-(uHead - vS) * 7.0), pulse = pow(0.5 + 0.5 * sin(6.2832 * (vS * 2.0 - uFlow)), 6.0);   // a hot tip, and slow pulses that keep pushing
            gl_FragColor = vec4(uColor * uGain * (1.0 - vV * vV) * (1.7 + 2.5 * tip + 1.6 * pulse), 1.0); }`,
        side: THREE.DoubleSide, transparent: true, depthTest: false, depthWrite: false, blending: THREE.AdditiveBlending,
      });
      const headGeo = new THREE.BufferGeometry(); headGeo.setAttribute('position', new THREE.Float32BufferAttribute([0.04, 0, 0, -0.16, 0.085, 0, -0.16, -0.085, 0], 3));
      heat.matrix.makeRotationX(-Math.PI / 2).setPosition(0, FLOOR, 0); heat.matrixWorldNeedsUpdate = true;
      const rays = HEAT.map((r) => {
        const { g, acc } = ribbon(r.pts, 0.07), mat = rayMat();
        const line = new THREE.Mesh(g, mat), head = new THREE.Mesh(headGeo, glow(3.2)), bar = new THREE.Mesh(new THREE.PlaneGeometry(0.36, 0.055), glow(1));
        head.material.side = THREE.DoubleSide; bar.material.side = THREE.DoubleSide;
        bar.position.set(r.bar[0], r.bar[1], 0); bar.rotation.z = r.bar[2];
        for (const m of [line, head, bar]) { m.frustumCulled = false; m.renderOrder = 5; heat.add(m); }
        const at = (f) => {
          const d = f * acc[acc.length - 1]; let i = 1; while (i < acc.length - 1 && acc[i] < d) i++;
          const a = r.pts[i - 1], b = r.pts[i], k = (d - acc[i - 1]) / (acc[i] - acc[i - 1] || 1), p0 = r.pts[0], p1 = r.pts[r.pts.length - 1];
          return [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, Math.atan2(p1[1] - p0[1], p1[0] - p0[0])];
        };
        return { r, mat, head, bar, at };
      });

      // ---- camera: [azimuth, elevation, distance, target x, y, z]. One move, still travelling on the last frame.
      // The recipe's crane, its distance sized to the object (and a square Short frame stands further back).
      const WIDE = Math.max(1, 1.78 / (camera.aspect || 1.78)), Dz = Math.max(LEN * 1.5 / 8.4, OBJ.depth * 2.6 / 8.4) * WIDE;
      const camPath = K.path([[0, [-50, 22, 15.0 * Dz, -0.75, AXIS_Y, 0]], [1.4 * Q, [-44, 31, 13.6 * Dz, -0.3, AXIS_Y, 0]], [3.2 * Q, [-9, 65, 15.6 * Dz, 0, AXIS_Y, 0.05]], [5.4 * Q, [-2, 72, 15.9 * Dz, 0, AXIS_Y, 0.1]], [9.2 * Q, [0.4, 80, 14.3 * Dz, 0, AXIS_Y, 0.1]]]);
      const camAt = (t) => { const [az, el, d, tx, ty, tz] = camPath(t), a = az * Math.PI / 180, e = el * Math.PI / 180; return { pos: [tx + d * Math.cos(e) * Math.sin(a), ty + d * Math.sin(e), tz + d * Math.cos(e) * Math.cos(a)], aim: [tx, ty, tz] }; };

      // ---- timing helpers
      const scanX = (t) => { const k = K.seg(t, SCAN[0], SCAN[1]); return K.lerp(-HALF - 0.55, HALF + 0.55, 0.45 * k + 0.55 * k * k * (3 - 2 * k)); };
      const flare = (t, t0, rest = 0.5) => (t < t0 ? 0 : K.seg(t, t0, t0 + 0.1) * (rest + (1 - rest) * Math.exp(-(t - t0 - 0.1) * 2.4)));   // a part lights up, then settles to `rest`
      const cool = new THREE.Color(COOL), accent = new THREE.Color(ACCENT), AX = new THREE.Vector3(1, 0, 0), C = new THREE.Vector3(0, AXIS_Y, 0);
      const toCam = new THREE.Vector3(), up2 = new THREE.Vector3(), v3 = new THREE.Vector3();

      return {
        update(t) {
          const cam = camAt(t); K.look(camera, cam.pos, cam.aim); K.focus(camera, cam.aim, K.lerp(0.022, 0.03, K.seg(t, 0, 3.5 * Q)) / Dz);

          // the scan: the cut plane travels, the solid side is lit and capped, the other side is film
          const sx = scanX(t), done = t >= SCAN[1];
          setCut(sx); lit.visible = !done; film.visible = t > SCAN[0];
          sheet.position.set(sx, 2.05 * sheet.scale.y, 0); sheet.material.uniforms.uGain.value = K.seg(t, SCAN[0] - 0.3, SCAN[0] + 0.05) * (1 - K.seg(t, SCAN[1] - 0.12, SCAN[1] + 0.3));
          const dim = K.seg(t, SCAN[0] + 0.9, SCAN[1] + 0.4, K.ease.inOut);
          key.intensity = 1500 * (1 - 0.93 * dim); scene.environmentIntensity = 1 - 0.8 * dim; marks.material.color.setScalar(0.55 + 0.5 * dim);

          // film distances are measured from the plane through the object that faces the camera
          toCam.set(cam.pos[0], cam.pos[1], cam.pos[2]).sub(C).normalize();
          REF.value.set(toCam.x, toCam.y, toCam.z, -toCam.dot(C));

          // the story's parts light up one at a time, then settle so the finished picture keeps all of them
          PARTS.forEach((p, i) => { const f = flare(t, p.at, i === PARTS.length - 1 ? 0.5 : 0.35); for (const m of X[p.part]) { m.uniforms.uColor.value.copy(cool).lerp(accent, Math.min(1, f * 1.5)); m.uniforms.uK.value = KD[p.part] * (1 + 2.2 * f); } });

          for (const { r, mat, head, bar, at } of rays) {
            const f = K.seg(t, r.t0, r.t0 + r.dur), on = t > r.t0, hit = K.seg(t, r.stop, r.stop + 0.09), age = Math.max(0, t - r.stop);
            mat.uniforms.uHead.value = on ? f : -1; mat.uniforms.uFlow.value = t * 0.9 - r.t0; mat.uniforms.uGain.value = 1.15 - 0.4 * K.seg(t, r.t0 + r.dur, r.t0 + r.dur + 0.8);
            const [hx, hy, ha] = at(f); head.visible = on && f < 1; head.position.set(hx, hy, 0); head.rotation.z = ha;
            bar.visible = hit > 0; bar.scale.set(K.lerp(0.3, 1, K.ease.outBack(hit)), 1 + 2.2 * Math.exp(-age * 9) * hit, 1); bar.material.color.copy(HOT).multiplyScalar(1.5 + 5 * Math.exp(-age * 6));
          }
        },

        // Callouts: the recipe's pole from a point on the part to its name and note, both ends tracked in 3D. Each
        // label stands clear of the object (above it for parts in the far half, below for the near half) and of the
        // labels already placed, and inside the frame.
        overlay(ctx, t, W, H) {
          camera.updateMatrixWorld();
          const P = (p) => { v3.set(p[0], p[1], p[2]).project(camera); return [(v3.x * 0.5 + 0.5) * W, (0.5 - v3.y * 0.5) * H]; };
          const s = H / 1080, mix = (k) => `rgb(${Math.round(K.lerp(214, 255, k))},${Math.round(K.lerp(232, 150, k))},${Math.round(K.lerp(247, 60, k))})`;
          ctx.textBaseline = 'alphabetic'; ctx.lineCap = 'butt';
          // the object's outline on screen
          let y0 = 1e9, y1 = -1e9, x0 = 1e9, x1 = -1e9;
          for (const x of [-HALF, HALF]) for (const z of [-OBJ.depth / 2, OBJ.depth / 2]) for (const y of [0, FLOOR]) { const q = P([x, y, z]); y0 = Math.min(y0, q[1]); y1 = Math.max(y1, q[1]); x0 = Math.min(x0, q[0]); x1 = Math.max(x1, q[0]); }

          // the position readout that rides on the scanning plane
          const sa = K.seg(t, SCAN[0] - 0.1, SCAN[0] + 0.2) * (1 - K.seg(t, SCAN[1] - 0.25, SCAN[1]));
          if (sa > 0) {
            v3.set(scanX(t), 4.1 * sheet.scale.y, 3.1 * sheet.scale.x).project(camera); const mm = Math.round(K.clamp((scanX(t) + HALF) * MM, 0, LEN * MM));
            ctx.globalAlpha = sa; ctx.fillStyle = '#d6e8f7'; ctx.font = `500 ${34 * s}px "IBM Plex Mono"`; ctx.letterSpacing = '0px'; ctx.shadowColor = 'rgba(0,0,0,0.8)'; ctx.shadowBlur = 10 * s;
            const label = String(mm).padStart(3, '0') + ' mm';
            ctx.fillText(label, K.clamp((v3.x * 0.5 + 0.5) * W + 14 * s, 40 * s, W - ctx.measureText(label).width - 40 * s), K.clamp((0.5 - v3.y * 0.5) * H - 12 * s, 60 * s, H - 40 * s));
          }

          const placed = [[x0 + 6 * s, y0 + 6 * s, x1 - 6 * s, y1 - 6 * s]], texts = [];   // the object itself; the labels so far
          { const a = P([HALF - 50 / MM - 0.1, 0, OBJ.depth / 2 + 0.25]), b = P([HALF + 0.1, 0, OBJ.depth / 2 + 0.85]); placed.push([Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])]); }   // the printed scale bar
          PARTS.forEach((p) => {
            const k = K.seg(t, p.at - 0.08, p.at + 0.3, K.ease.out), kn = K.seg(t, p.at + 0.02, p.at + 0.35, K.ease.out), ko = K.seg(t, p.at + 0.22, p.at + 0.6, K.ease.out);
            const c = centre(p.part), [ax, ay] = P([c[0], top(p.part), c[2]]), dir = c[2] < 0 ? -1 : 1;
            ctx.font = `700 ${78 * s}px "Space Grotesk"`; ctx.letterSpacing = `${2 * s}px`; const wn = ctx.measureText(p.name).width;
            ctx.font = `500 ${44 * s}px "Space Grotesk"`; ctx.letterSpacing = `${0.5 * s}px`; const wo = ctx.measureText(p.note || '').width;
            const bw = Math.max(wn, wo) + 22 * s, bh = 126 * s;
            // candidates: its own side of the object first, the pole's right then left, then the other side, then stacked out
            const ownPole = () => false;   // the pole stops short of its label's edge, so it never runs into its own letters
            // the pole (and its elbow) from the part to a label at (x, e) may not cross a label already placed
            const poleSegs = (x, e) => {
              if (x > x1 || x + bw < x0) { const hx = x > ax ? x - 10 * s : x + bw + 10 * s; return [[Math.min(ax, hx), ay - 3 * s, Math.max(ax, hx), ay + 3 * s]]; }
              const far = e - bh > ay ? e - bh : e, segs = [[ax - 3 * s, Math.min(ay, far), ax + 3 * s, Math.max(ay, far)]];
              if (x > ax + 30 * s) segs.push([ax, far - 3 * s, x, far + 3 * s]); else if (x + bw < ax) segs.push([x + bw, far - 3 * s, ax, far + 3 * s]);
              return segs;
            };
            const poleClear = (x, e) => !poleSegs(x, e).some((g) => texts.some((q) => g[0] < q[2] + 6 * s && g[2] > q[0] - 6 * s && g[1] < q[3] + 4 * s && g[3] > q[1] - 4 * s));
            const fits = (x, e) => !ownPole(x, e) && poleClear(x, e) && x >= 40 * s && x + bw <= W - 40 * s && e - bh >= 40 * s && e <= H - 30 * s && !placed.some((q) => x < q[2] + 24 * s && x + bw > q[0] - 24 * s && e - bh < q[3] + 12 * s && e > q[1] - 12 * s);
            const cands = [];
            for (let st = 0; st < 4; st++) for (const d of [dir, -dir]) for (const right of [true, false]) {
              const e = (d < 0 ? y0 - 24 * s : y1 + bh + 24 * s) + d * st * (bh + 18 * s);
              cands.push([right ? ax + 22 * s : ax - 22 * s - bw, e]);
            }
            // then centred over or under its pole (kept inside the frame), for a label too wide to stand beside it
            for (const d of [dir, -dir]) cands.push([K.clamp(ax - bw / 2, 40 * s, W - 40 * s - bw), d < 0 ? y0 - 24 * s : y1 + bh + 24 * s]);
            // then slid along the top or bottom, the pole bending to reach it
            for (let j = 1; j <= 4; j++) for (const d of [dir, -dir]) for (const sgn of [1, -1]) cands.push([sgn > 0 ? ax + 22 * s + j * (bw * 0.5 + 20 * s) : ax - 22 * s - bw - j * (bw * 0.5 + 20 * s), d < 0 ? y0 - 24 * s : y1 + bh + 24 * s]);
            // then beside the object, level with the part (a short arm out to the side)
            for (let st = 0; st < 3; st++) for (const right of [ax > (x0 + x1) / 2]) cands.push([right ? x1 + 40 * s : x0 - 40 * s - bw, ay + bh / 2 + (st % 2 ? 1 : -1) * Math.ceil(st / 2) * (bh + 18 * s)]);
            const inside = cands.map(([x, e]) => [K.clamp(x, 40 * s, W - 40 * s - bw), K.clamp(e, bh + 40 * s, H - 30 * s)]);
            const clash = ([x, e]) => placed.reduce((n, q) => n + Math.max(0, Math.min(x + bw, q[2]) - Math.max(x, q[0])) * Math.max(0, Math.min(e, q[3]) - Math.max(e - bh, q[1])), 0);
            let [tx, end] = cands.find(([x, e]) => fits(x, e)) || inside.reduce((best, c) => (clash(c) + (ownPole(...c) ? 1e9 : 0) + (poleClear(...c) ? 0 : 1e8) < clash(best) + (ownPole(...best) ? 1e9 : 0) + (poleClear(...best) ? 0 : 1e8) ? c : best));
            placed.push([tx, end - bh, tx + bw, end]); texts.push([tx, end - bh, tx + bw, end]);
            { const far = end - bh > ay ? end - bh : end; placed.push([ax - 4 * s, Math.min(ay, far), ax + 4 * s, Math.max(ay, far)]); }   // its pole
            if (k <= 0) return;
            const below = end - bh > ay, hot = flare(t, p.at, 0.0), tip = ay + ((below ? end - bh - 12 * s : end + 12 * s) - ay) * k, col = mix(Math.min(1, hot * 1.3));
            ctx.globalAlpha = 1; ctx.shadowColor = 'rgba(0,0,0,0.85)'; ctx.shadowBlur = 14 * s; ctx.strokeStyle = col; ctx.fillStyle = col;
            ctx.lineWidth = 3 * s; ctx.beginPath();
            if (tx > x1 || tx + bw < x0) { const hx = tx > ax ? tx - 10 * s : tx + bw + 10 * s, ex = ax + (hx - ax) * k; ctx.moveTo(ax + Math.sign(hx - ax) * 11 * s, ay); ctx.lineTo(ex, ay); }
            else { ctx.moveTo(ax, ay + Math.sign(tip - ay) * 11 * s); ctx.lineTo(ax, tip); if (tx > ax + 30 * s) ctx.lineTo(ax + (tx - 8 * s - ax) * k, tip); else if (tx + bw < ax) ctx.lineTo(ax + (tx + bw + 6 * s - ax) * k, tip); }
            ctx.stroke();
            ctx.beginPath(); ctx.arc(ax, ay, 10 * s, 0, 7); ctx.stroke(); ctx.beginPath(); ctx.arc(ax, ay, 3.5 * s, 0, 7); ctx.fill();
            const top1 = end - bh;
            ctx.globalAlpha = kn; ctx.fillStyle = '#f4f8fb'; ctx.font = `700 ${78 * s}px "Space Grotesk"`; ctx.letterSpacing = `${2 * s}px`; ctx.fillText(p.name, tx + (1 - kn) * 26 * s, top1 + 57 * s);
            if (p.note) { ctx.globalAlpha = ko; ctx.fillStyle = '#a9c7df'; ctx.font = `500 ${44 * s}px "Space Grotesk"`; ctx.letterSpacing = `${0.5 * s}px`; ctx.fillText(p.note, tx + (1 - ko) * 18 * s, top1 + 114 * s); }
          });
          ctx.globalAlpha = 1; ctx.shadowBlur = 0;
        },
      };
    },

    sound(k) {
      const K = globalThis.K;
      k.bed('room', 0, DUR, { gain: 0.9 }); k.bed('hum', 0, DUR, { gain: 0.45 });
      const d = SCAN[1] - SCAN[0];
      k.play('click', SCAN[0] - 0.02, { gain: 0.9 });
      k.tone(SCAN[0], { f: [[0, 92], [d, 138]], type: 'sawtooth', dur: d + 0.1, gain: 0.07, a: 0.12, hold: d - 0.25, filter: 'lowpass', f2: 700 });
      k.noise(SCAN[0], { dur: d + 0.15, color: 'pink', filter: 'bandpass', f: [[0, 700], [d, 2400]], q: 2.2, gain: 0.1, a: 0.2, hold: d - 0.4, verb: 0.15 });
      k.withMinor(() => { for (let i = 1; i <= 9; i++) k.play('tick', SCAN[0] + d * i / 10, { gain: 0.45, f: 5200, pan: -0.6 + i * 0.12 }); });
      k.play('tock', SCAN[1], { gain: 0.7, f: 420 }); k.play('thud', SCAN[1] + 0.02, { gain: 0.3 });
      for (const r of HEAT) {
        const pan = K.clamp(r.pts[0][0] / 5, -0.7, 0.7);
        if (FLOW === 'heat' || FLOW === 'air') { k.withMinor(() => k.play('swish', r.t0, { gain: 0.3, pan })); k.play('ding', r.stop, { gain: 0.25, f: 1568 + 180 * pan, pan }); }
        else k.play('tock', r.stop, { gain: 0.5, f: 300 + 25 * pan, pan });
      }
      PARTS.forEach((p, i) => { k.play('whoosh', p.at - 0.45, { gain: 0.3, dur: 0.45 }); k.play('click', p.at + 0.06, { gain: 0.6, pan: i % 2 ? 0.4 : -0.3 }); k.tone(p.at, { f: [110, 98, 82][i], dur: 0.9, gain: 0.14, a: 0.02 }); });
      k.play('ding', DUR - 1.05, { gain: 0.35, f: 'D6' }); k.play('ding', DUR - 0.95, { gain: 0.3, f: 'A6' });
    },
  });
}
