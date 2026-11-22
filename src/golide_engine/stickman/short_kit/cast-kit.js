// ===== GOLIDE cast kit (2026-11-18, the owner's fast-cut Elon test): chunky modern puppets with definition =====
// T.modernFront(p, O, opts): O = { tunic (top colour), skin, hair, style: short|swoop|slick|spiky|curly|bun, pants, shoes,
//   jacket: true + shirt + tie, hood: true, sleeve, belt, moustache, hat: cap|police|top|cowboy|beanie|hardhat|chef|crown|helmet|nurse|grad
//   (+ hatColour), shades: true, beard: colour, holds: phone|laptop|briefcase|coffee|cash|paper|mic|trophy|bag|sign:WORDS
//   (or opts.holds per frame, opts.holdIn 'L' for the left hand) }
// Movement helpers for story.js (import { walkPath, sitDown, jumpAt, shakeAt, followCam, nod, lookAround } from './toon.js'):
//   walkPath(f, f0, f1, from, to) -> { x, z, step, facing, done }; sitDown(f, f0) -> 0..1 (pass seated when 1, bob down
//   before); jumpAt(f, f0, height) -> y offset; shakeAt(f, f0, dur) -> head tilt; nod(f, f0) -> head tilt; followCam(f, f0, f1,
//   from, to, height, back) -> a camera that tracks a walker; coinFx / sparkFx / heartFx / angerFx / sweatFx / questionFx /
//   ideaFx / zzzFx fx cards (T.coinFx(p, t) ...).; opts as romanFront (expr, blink, look, facing, seed, L, R,
//   tilt, headTilt, bob, step, wv, swirl, lift) plus seated: true (no legs, for karts and chairs).
// Arm poses: hang point up wave hip temple cross reach. T.billFx(p, rot, squash): a falling $100 bill for fx cards.
// GOLIDE modern cast: chunkier puppets with definition, drawn whole (not over the kit's body): a round torso with
// shoulders, thick sleeved arms with cuffs and mitten hands, trousers with a crease and hem, shoes with soles and a
// shine, a belt, the top (T-shirt, hoodie, jacket with shirt and tie), fuller hair, heavier ink and a shadow side.
// The kit's own head, face and hair helpers draw the head (same faces and expressions).
// hairstyles of our own: a cap over the head whose hairline always stays above the brows, with sideburns at the ears
const hairDo = (p, style, col, cx, hc, H, u, ow, thick, seed) => {
  const A = H.a * 1.08, B = H.b * 1.08, hl = hc - 0.5 * H.b, dark = mul(col, [0.72, 0.72, 0.8]), lite = mix(col, '#ffffff', 0.28);
  let crown = ellPts(cx, hc - 0.02 * H.b, A, B, 180, 360, 0, 44);
  if (style === 'spiky') crown = crown.map(([x, y], i) => i % 4 === 2 ? [x + (x - cx) * 0.08, y - 14 * u] : [x, y]);
  if (style === 'curly') crown = crown.map(([x, y], i) => { const k = 1 + 0.07 * Math.sin(i * 1.9 + seed); return [cx + (x - cx) * k, hc + (y - hc) * k]; });
  const dip = { short: [0, 2, 6, 2, 0], swoop: [10, 8, 5, 1, -2], slick: [-6, -8, -9, -8, -6], spiky: [4, 0, 5, 0, 4], curly: [3, 7, 3, 7, 3], bun: [0, 2, 3, 2, 0] }[style] || [0, 2, 4, 2, 0];
  const line = [[cx + A, hc], [cx + H.a * 0.96, hc + 0.12 * H.b], [cx + H.a * 0.84, hc + 0.08 * H.b], [cx + H.a * 0.8, hl + 4 * u]];
  for (let k = 0; k < 5; k++) { const x = cx + H.a * (0.6 - k * 0.3); line.push([x, hl + dip[4 - k] * u]); }
  line.push([cx - H.a * 0.8, hl + 4 * u], [cx - H.a * 0.84, hc + 0.08 * H.b], [cx - H.a * 0.96, hc + 0.12 * H.b], [cx - A, hc]);
  const cap = [...crown, ...line];
  if (style === 'bun') { const bp = blobPts(cx, hc - B - 8 * u, { a: 0.36 * H.a, b: 0.32 * H.b, nTop: 2, nBot: 2, egg: 0, asym: 0, rot: 0, noise: 0.02, seed }); p.poly(bp, col, 0); p.inkRing(bp, ow * 0.85, thick); }
  p.poly(cap, col, 0);
  p.clip(cap, () => {                                    // strands and a shine
    for (let i = -3; i <= 3; i++) p.stroke(curve([cx + i * 12 * u, hc - B * 0.95], [cx + i * 14 * u + 6 * u, hc - B * 0.6], [cx + i * 15 * u + (style === 'swoop' ? 14 : 4) * u, hl + 2 * u]), 1.8 * u, dark);
    p.stroke(ellPts(cx - 0.25 * A, hc - 0.55 * B, 0.3 * A, 0.18 * B, 200, 320, 0, 12), 4 * u, lite);
  });
  p.inkRing(cap, ow * 0.9, thick);
};
// hats over the hair: the brim sits on the brow line, the crown above the head (one ink weight with the head)
const kitHat = (p, kind, col, cx, hc, H, u, ow, thick) => {
  const top = hc - H.b, brow = hc - 0.42 * H.b, c = col || { cap: '#2f5fb8', police: '#1f2a44', top: '#17161b', cowboy: '#8a5a2b', beanie: '#c7322e', hardhat: '#f2c230', chef: '#f7f5ef', crown: '#e9b43a' }[kind] || '#2f5fb8';
  const dark = mul(c, [0.72, 0.72, 0.8]);
  const crown = (w, h, y0) => blobPts(cx, y0 - h / 2, { a: w, b: h / 2, nTop: 3, nBot: 6, egg: 0, asym: 0, rot: 0, noise: 0, seed: 2 });
  if (kind === 'top') { const cr = crown(0.62 * H.a, 1.15 * H.b, brow + 2 * u); p.poly(cr, c, ow * 0.8); p.band([[cx - 0.62 * H.a, brow - 14 * u], [cx + 0.62 * H.a, brow - 14 * u]], '#c7322e', 9 * u, 1.4 * u, 'butt');
    p.ell(cx, brow + 2 * u, 0.98 * H.a, 0.13 * H.b, c, ow * 0.8); return; }
  if (kind === 'cowboy') { p.ell(cx, brow + 2 * u, 1.35 * H.a, 0.2 * H.b, c, ow * 0.8); const cr = crown(0.66 * H.a, 0.78 * H.b, brow); p.poly(cr, c, ow * 0.8);
    p.band([[cx - 0.66 * H.a, brow - 8 * u], [cx + 0.66 * H.a, brow - 8 * u]], dark, 7 * u, 1.2 * u, 'butt'); return; }
  if (kind === 'chef') { const cr = crown(0.7 * H.a, 1.1 * H.b, brow); p.poly(cr, c, ow * 0.8); for (const s of [-1, 0, 1]) p.ell(cx + s * 0.42 * H.a, top - 0.45 * H.b, 0.34 * H.a, 0.3 * H.b, c, ow * 0.7);
    p.band([[cx - 0.7 * H.a, brow - 6 * u], [cx + 0.7 * H.a, brow - 6 * u]], '#e6e2d8', 12 * u, 1.2 * u, 'butt'); return; }
  if (kind === 'crown') { const pts = [[cx - 0.7 * H.a, brow], [cx - 0.7 * H.a, top - 0.2 * H.b], [cx - 0.35 * H.a, top + 0.1 * H.b], [cx, top - 0.35 * H.b], [cx + 0.35 * H.a, top + 0.1 * H.b], [cx + 0.7 * H.a, top - 0.2 * H.b], [cx + 0.7 * H.a, brow]];
    p.poly(pts, c, ow * 0.8); for (const s of [-1, 0, 1]) p.dot(cx + s * 0.35 * H.a, brow - 12 * u, 5 * u, s ? '#2f78c4' : '#c7322e'); return; }
  if (kind === 'beanie') { const cr = ellPts(cx, brow, 1.02 * H.a, 0.95 * H.b, 180, 360, 0, 30); p.poly(cr, c, ow * 0.8);
    p.band([[cx - 1.0 * H.a, brow - 6 * u], [cx + 1.0 * H.a, brow - 6 * u]], dark, 16 * u, 1.4 * u, 'round'); p.ell(cx, brow - 0.98 * H.b, 12 * u, 10 * u, dark, ow * 0.6); return; }
  if (kind === 'hardhat') { const cr = ellPts(cx, brow, 1.0 * H.a, 0.85 * H.b, 180, 360, 0, 30); p.poly(cr, c, ow * 0.8); p.ell(cx, brow + 2 * u, 1.18 * H.a, 0.1 * H.b, c, ow * 0.8);
    p.stroke([[cx, brow - 0.82 * H.b], [cx, brow]], 6 * u, dark); return; }
  if (kind === 'helmet') { const cr = ellPts(cx, brow + 4 * u, 1.08 * H.a, 0.92 * H.b, 180, 360, 0, 30); p.poly(cr, col || '#5b6b3a', ow * 0.8);
    p.stroke([[cx - 1.08 * H.a, brow + 4 * u], [cx + 1.08 * H.a, brow + 4 * u]], 5 * u, mul(col || '#5b6b3a', [0.7, 0.7, 0.78])); return; }
  if (kind === 'nurse') { p.poly([[cx - 0.55 * H.a, brow], [cx - 0.45 * H.a, top - 0.15 * H.b], [cx + 0.45 * H.a, top - 0.15 * H.b], [cx + 0.55 * H.a, brow]], '#ffffff', ow * 0.7);
    p.stroke([[cx, top + 0.02 * H.b], [cx, top + 0.3 * H.b]], 6 * u, '#c7322e'); p.stroke([[cx - 0.14 * H.a, top + 0.16 * H.b], [cx + 0.14 * H.a, top + 0.16 * H.b]], 6 * u, '#c7322e'); return; }
  if (kind === 'grad') { const cr = ellPts(cx, brow, 0.9 * H.a, 0.5 * H.b, 180, 360, 0, 24); p.poly(cr, '#17161b', ow * 0.8);
    p.poly([[cx - 1.25 * H.a, top - 0.05 * H.b], [cx, top - 0.35 * H.b], [cx + 1.25 * H.a, top - 0.05 * H.b], [cx, top + 0.25 * H.b]], '#17161b', ow * 0.7);
    p.stroke([[cx, top - 0.05 * H.b], [cx + 0.9 * H.a, top + 0.35 * H.b]], 3 * u, '#e9b43a'); return; }
  // cap and police: a dome with a brim to the front; police adds a badge and a band
  const cr = ellPts(cx, brow, 1.0 * H.a, 0.72 * H.b, 180, 360, 0, 30); p.poly(cr, c, ow * 0.8);
  if (kind === 'police') { p.band([[cx - 1.0 * H.a, brow - 7 * u], [cx + 1.0 * H.a, brow - 7 * u]], '#17161b', 12 * u, 1.2 * u, 'butt'); p.poly(blobPts(cx, brow - 0.42 * H.b, { a: 9 * u, b: 9 * u, nTop: 2, nBot: 2, egg: 0, asym: 0, rot: 0, noise: 0, seed: 1 }), '#e9b43a', 1.6 * u); }
  p.poly([[cx - 0.85 * H.a, brow], [cx + 0.85 * H.a, brow], [cx + 0.7 * H.a, brow + 0.16 * H.b], [cx - 0.7 * H.a, brow + 0.16 * H.b]], kind === 'police' ? '#17161b' : dark, ow * 0.6);
};
// more faces (2026-11-22): every feeling a story needs, built from the library's own eyes, brows and mouths; any name
// the writer uses that is still unknown draws the nearest known face, never a crash
Object.assign(FACE, {
  smirk: { eye: ['lid', 'lid'], brow: [2, -3], mouth: 'grin' }, angry: { ...FACE.stern, brow: [6, -6] }, mad: { ...FACE.stern, brow: [6, -6] },
  sad: { ...FACE.nervous, brow: [-4, 3] }, worried: FACE.nervous, scared: FACE.shock, surprised: FACE.shock, amazed: FACE.shock,
  happy: FACE.smile, excited: FACE.laugh, proud: FACE.smile_closed || FACE.smile, confident: FACE.grin, focused: FACE.stern,
  thinking: FACE.nervous, bored: FACE.dazed || FACE.neutral, tired: FACE.dazed || FACE.neutral, relieved: FACE.relief,
  sleepy: FACE.snore || FACE.neutral, determined: FACE.stern, curious: FACE.neutral, evil: { eye: ['lid', 'lid'], brow: [6, -6], mouth: 'grin' },
});
const faceName = (e) => (FACE[e] ? e : 'neutral');
export const modernFront = (p, O, opts = {}) => {
  const { expr: expr0 = 'neutral', blink = 0, look = 0, facing = 0, seed = 3, L = 'hang', R = 'hang', tilt = 0, headTilt = 0,
    bob = 0, light = rad(-120), step = 0, seated = false } = opts;
  const expr = faceName(expr0), lid = lidOf(blink), skin = O.skin ?? SKIN;
  const H = headBlob(seed, 124, facing), W = 2 * H.a, HH = 2 * H.b, u = W / 100;
  const sole = 975, legsL = 1.12, torsoL = 1.02;
  const torsoBot = sole - legsL * HH - bob * HH, chin = torsoBot - torsoL * HH, hc = chin - H.b * 0.96, hipY = torsoBot - 0.1 * HH;
  const thick = thickAngle(light), ow = 6.2 * u, cx = 300, tcx = cx + 3 * u * facing;
  const top = O.tunic, topD = mul(top, [0.68, 0.68, 0.78]), pants = O.pants || '#2c3e5c', shoe = O.shoes || '#17161b';
  p.rot = null;
  // ---- legs: trousers and shoes ----
  if (!seated) for (const side of [-1, 1]) {
    const up = step ? Math.max(0, Math.sin(Math.PI * 2 * (step + (side > 0 ? 0.5 : 0)))) * 34 : 0;
    const hx = tcx + side * 17 * u, fx = cx + side * 21 * u, fy = sole - 5 * u - up;
    const leg = curve([hx, hipY], [(hx + fx) / 2 + side * 2 * u, (hipY + fy) / 2], [fx, fy - 7 * u]);
    p.stroke(leg, 19 * u + 2 * ow * 0.55, INK); p.stroke(leg, 19 * u, pants);
    p.stroke(leg.map(([x, y]) => [x - side * 5 * u, y]), 4 * u, mul(pants, [0.78, 0.78, 0.86]));      // shadow side
    p.stroke(leg.map(([x, y]) => [x + side * 2 * u, y]), 1.4 * u, mul(pants, [0.62, 0.62, 0.72]));    // crease
    p.ell(fx + side * 7 * u, fy - 3 * u, 16 * u, 8 * u, shoe, ow * 0.55);
    p.stroke([[fx - side * 7 * u, fy + 3.4 * u], [fx + side * 22 * u, fy + 3.4 * u]], 2.6 * u, O.soles || '#ece6da');
    p.ell(fx + side * 12 * u, fy - 7 * u, 4.5 * u, 2 * u, '#ffffff70', 0);
  }
  // ---- torso: a round body with shoulders ----
  p.rot = tilt ? [rad(tilt), cx, hipY] : null;
  const T = { a: 0.5 * W, b: 0.5 * (torsoBot - (chin - 0.2 * HH)), nTop: 1.7, nBot: 2.4, egg: 0.06, asym: 0.03 * facing, rot: 0, noise: 0.004, seed: seed + 7 };
  const tcy = torsoBot - T.b, tp = blobPts(tcx, tcy, T);
  const S = (side) => [tcx + side * 0.8 * T.a, chin + 0.2 * HH];
  const arm = (side, pose) => {
    const s = S(side), X = (k) => tcx + side * (T.a * 1.05 + k * u);
    switch (pose) {
      case 'point': return { pts: [s, [X(26), s[1] + 0.04 * HH], [X(58), s[1] - 0.06 * HH]], finger: true };
      case 'up': return { pts: [s, [X(16), s[1] - 0.3 * HH], [X(22), s[1] - 0.72 * HH]] };
      case 'wave': return { pts: [s, [X(18), s[1] - 0.18 * HH], [X(30 + 10 * Math.sin(opts.wv || 0)), s[1] - 0.6 * HH]] };
      case 'hip': return { pts: [s, [X(20), s[1] + 0.3 * HH], [tcx + side * T.a * 0.92, torsoBot - 0.3 * HH]] };
      case 'temple': return { pts: [s, [X(24), s[1] + 0.05 * HH], [cx + side * (H.a + 14 * u), hc - 0.08 * HH]], swirl: true };
      case 'cross': return { pts: [s, [X(2), s[1] + 0.34 * HH], [tcx - side * 0.42 * T.a, s[1] + 0.28 * HH]], front: true };
      case 'reach': { const lf = (opts.lift || 0) * 0.6 * HH; return { pts: [s, [X(36), s[1] - 0.08 * HH - lf * 0.6], [X(72), s[1] - 0.42 * HH - lf]] }; }
      default: return { pts: [s, [X(5), s[1] + 0.46 * HH], [X(3), torsoBot - 0.02 * HH]] };
    }
  };
  const arms = [arm(-1, L), arm(1, R)];
  const drawArm = (a) => {
    const c = curve(a.pts[0], a.pts[1], a.pts[2]), [hx, hy] = a.pts[2];
    p.stroke(c, 15 * u + 2 * ow * 0.5, INK); p.stroke(c, 15 * u, O.sleeve || top);
    p.stroke(c.map(([x, y]) => [x, y + 3 * u]).slice(2), 4 * u, O.jacket ? mul(top, [0.8, 0.8, 0.88]) : topD);
    const n = c.length, q = c[Math.max(0, n - 3)];            // a cuff near the wrist
    p.stroke([[q[0] - 6 * u, q[1]], [q[0] + 6 * u, q[1]]], 3 * u, O.jacket ? (O.shirt || '#f4f2ec') : mul(top, [0.78, 0.78, 0.86]));
    p.ell(hx, hy, 9 * u, 8.5 * u, skin, ow * 0.45);         // mitten hand + thumb
    p.ell(hx + Math.sign(hx - cx) * -6 * u, hy - 5 * u, 3.6 * u, 4.6 * u, skin, ow * 0.35);
    if (a.finger) { const dx = hx - a.pts[1][0], dy = hy - a.pts[1][1], l = Math.hypot(dx, dy) || 1;
      p.stroke([[hx, hy], [hx + dx / l * 15 * u, hy + dy / l * 15 * u]], 6 * u, INK); p.stroke([[hx, hy], [hx + dx / l * 14 * u, hy + dy / l * 14 * u]], 3.6 * u, skin); }
  };
  arms.filter((a) => !a.front).forEach(drawArm);
  p.gradFill(tp, top, topD, light);
  p.clip(tp, () => { p.ell(tcx - facing * 4 * u - 0.55 * T.a, tcy, 0.34 * T.a, T.b * 1.1, mul(top, [0.82, 0.82, 0.9]), 0); });  // shadow side
  const tTop = chin + 0.04 * HH, mid = (tTop + torsoBot) / 2;
  p.clip(tp, () => {
    if (O.jacket) {
      p.poly([[tcx - 11 * u, tTop - 4 * u], [tcx + 11 * u, tTop - 4 * u], [tcx + 5 * u, torsoBot], [tcx - 5 * u, torsoBot]], O.shirt || '#f4f2ec', 1.6 * u);
      if (O.tie) p.poly([[tcx - 3.5 * u, tTop + 3 * u], [tcx + 3.5 * u, tTop + 3 * u], [tcx + 5 * u, mid + 10 * u], [tcx, mid + 17 * u], [tcx - 5 * u, mid + 10 * u]], O.tie, 1.4 * u);
      for (const s of [-1, 1]) p.poly([[tcx + s * 11 * u, tTop - 4 * u], [tcx + s * 24 * u, tTop + 4 * u], [tcx + s * 8 * u, mid + 4 * u], [tcx + s * 5 * u, mid - 4 * u]], mul(top, [0.8, 0.8, 0.88]), 1.8 * u);
      for (const k of [0, 1]) p.dot(tcx - 7 * u, mid + 14 * u + k * 12 * u, 2.2 * u, '#1b1a20');
    } else {
      p.stroke(curve([tcx - 13 * u, tTop - 2 * u], [tcx, tTop + 10 * u], [tcx + 13 * u, tTop - 2 * u]), 3.6 * u, topD);
      if (O.hood) { p.stroke(curve([tcx - 22 * u, tTop - 4 * u], [tcx, tTop + 16 * u], [tcx + 22 * u, tTop - 4 * u]), 7 * u, mul(top, [0.86, 0.86, 0.92]));
        for (const s of [-1, 1]) p.stroke([[tcx + s * 6 * u, tTop + 10 * u], [tcx + s * 7 * u, mid + 4 * u]], 1.8 * u, '#f4f2ec');
        p.poly([[tcx - 16 * u, mid + 10 * u], [tcx + 16 * u, mid + 10 * u], [tcx + 18 * u, torsoBot - 6 * u], [tcx - 18 * u, torsoBot - 6 * u]], mul(top, [0.86, 0.86, 0.92]), 1.6 * u); }
    }
    if (!seated) p.band([[tcx - T.a, torsoBot - 5 * u], [tcx + T.a, torsoBot - 5 * u]], O.belt || '#1b1a20', 5 * u, 1.4 * u, 'butt');
  });
  p.inkRing(tp, ow, thick);
  if (!seated) p.poly([[tcx - 4.5 * u, torsoBot - 8.5 * u], [tcx + 4.5 * u, torsoBot - 8.5 * u], [tcx + 4.5 * u, torsoBot - 1.5 * u], [tcx - 4.5 * u, torsoBot - 1.5 * u]], '#d2b56a', 1.3 * u);
  arms.filter((a) => a.front).forEach(drawArm);
  if (O.holds || opts.holds) heldItem(p, opts.holds || O.holds, arms[opts.holdIn === 'L' ? 0 : 1].pts[2], u, ow);
  // ---- head: fuller hair behind, the kit's head, face and hair on top ----
  const [cpx, cpy] = rotAbout([cx, chin], rad(tilt), [cx, hipY]);
  const Ah = tilt + headTilt;
  p.rot = Ah ? [rad(Ah), cx, chin, cpx - cx, cpy - chin] : null;
  const hp = blobPts(cx, hc, H);
  if (O.hair) { const big = O.style === 'curly' ? 1.14 : O.style === 'bun' ? 1.06 : 1.1; const hb = blobPts(cx - facing * 2 * u, hc - (O.style === 'curly' ? 0.12 : 0.07) * HH, { ...H, a: H.a * big, b: H.b * big * 0.97, noise: O.style === 'curly' ? 0.06 : 0.03, seed: seed + 3 });
    p.poly(hb, O.hair, 0); p.inkRing(hb, ow * 0.9, thick); }
  p.shadedFill(hp, skin, mul(skin, SH_SKIN), light, H.a);
  p.inkRing(hp, ow, thick);
  for (const s of [-1, 1]) p.ell(cx + s * (H.a - 1 * u), hc + 0.08 * H.b, 7 * u, 10 * u, skin, ow * 0.45);   // ears
  if (O.hair) hairDo(p, O.style || 'short', O.hair, cx, hc, H, u, ow, thick, seed);
  faceFront(p, cx, hc, W, expr, facing, look, lid, false, skin, O.moustache, false);
  if (O.beard) { const bp = [...ellPts(cx, hc + 0.42 * H.b, 0.72 * H.a, 0.5 * H.b, 0, 180, 0, 20), [cx - 0.72 * H.a, hc + 0.3 * H.b], [cx + 0.72 * H.a, hc + 0.3 * H.b]];
    p.poly(ellPts(cx, hc + 0.5 * H.b, 0.7 * H.a, 0.46 * H.b, 10, 170, 0, 18), O.beard, ow * 0.6); }
  if (O.shades) { for (const s of [-1, 1]) p.poly(blobPts(cx + s * 0.3 * H.a + facing * 6 * u, hc - 0.02 * H.b, { a: 0.27 * H.a, b: 0.17 * H.b, nTop: 2.6, nBot: 1.6, egg: 0, asym: 0, rot: 0, noise: 0, seed: 1 }), '#17161b', ow * 0.5);
    p.stroke([[cx - 0.04 * H.a + facing * 6 * u, hc - 0.06 * H.b], [cx + 0.04 * H.a + facing * 6 * u, hc - 0.06 * H.b]], 3 * u, '#17161b');
    for (const s of [-1, 1]) p.stroke([[cx + s * 0.38 * H.a + facing * 6 * u, hc - 0.1 * H.b], [cx + s * 0.22 * H.a + facing * 6 * u, hc - 0.02 * H.b]], 2.4 * u, '#ffffff90'); }
  if (O.hat) kitHat(p, O.hat, O.hatColour, cx, hc, H, u, ow, thick);
  p.rot = null;
  if (arms.some((a) => a.swirl)) {
    const a = arms.find((x) => x.swirl), [hx, hy] = a.pts[2], ph = opts.swirl || 0, pts = [];
    for (let i = 0; i < 40; i++) { const t = i / 40 * Math.PI * 4 + ph, r = (4 + i * 0.7) * u; pts.push([hx + Math.cos(t) * r, hy - 40 * u + Math.sin(t) * r]); }
    p.stroke(pts, 3 * u, '#ffffff'); p.stroke(pts, 1.4 * u, INK);
  }
};
// crowd(T, n, at, opts): n people as cards in loose rows around at = [x, y, z] (an audience, a queue, an army). opts:
// uniform (an O that everyone wears, e.g. soldiers), spread [w, d], expr, arms, seed, facing, s. Returns card entries for
// actorsAt: out.push(...T.crowd(T, 24, [x, DECK, z], { uniform: SOLDIER, expr: 'stern' }, f)).
const CROWD_TOPS = ['#c7322e', '#2f78c4', '#3fa36b', '#e9b43a', '#8a3bd2', '#e86a92', '#f1efe8', '#2b2d34', '#c86f3d'];
const CROWD_HAIR = ['#1b1a20', '#6b4a2a', '#c9a04a', '#2b211c', '#8a8a92'];
export const crowd = (T_, n, at, opts = {}, f = 0) => { const { uniform = null, spread = [8, 4], expr = 'neutral', arms = 'hang', seed = 1, facing = 0, s = 0.9 } = opts;
  const out = [], cols = Math.ceil(Math.sqrt(n * spread[0] / spread[1])), rows = Math.ceil(n / cols);
  for (let k = 0; k < n; k++) { const c = k % cols, r = Math.floor(k / cols), j = (k * 37 + seed * 13) % 100 / 100;
    const O = uniform ? { ...uniform } : { tunic: CROWD_TOPS[(k + seed) % CROWD_TOPS.length], hair: CROWD_HAIR[(k * 3 + seed) % CROWD_HAIR.length], style: ['short', 'swoop', 'curly', 'bun', 'spiky', 'slick'][(k + seed * 2) % 6] };
    const bob = Math.round(0.006 * Math.sin((f + k * 9) * 0.2) * 1000) / 1000;
    const x = at[0] - spread[0] / 2 + (c + 0.5) * spread[0] / cols + (j - 0.5) * 0.4, z = at[2] - r * spread[1] / Math.max(1, rows - 1 || 1) + (j - 0.5) * 0.3;
    out.push({ key: 'crowd' + k + (uniform ? 'u' : '') + expr + arms + bob, draw: (p) => modernFront(p, O, { expr, L: arms, R: arms, seed: seed + k, facing, bob }), x, y: at[1], z, s });
  } return out; };
// things in a hand, drawn at the hand in the card's own ink
const heldItem = (p, what, at, u, ow) => { const [hx, hy] = at, g = p.g; const kind = String(what).split(':')[0], words = String(what).split(':').slice(1).join(':');
  const box = (x0, y0, x1, y1, fill, r = 4) => p.poly([[x0 + r, y0], [x1 - r, y0], [x1, y0 + r], [x1, y1 - r], [x1 - r, y1], [x0 + r, y1], [x0, y1 - r], [x0, y0 + r]], fill, ow * 0.5);
  if (kind === 'phone') { box(hx - 11 * u, hy - 34 * u, hx + 11 * u, hy + 4 * u, '#17161b'); box(hx - 8 * u, hy - 30 * u, hx + 8 * u, hy, '#5aa8ff', 2 * u); return; }
  if (kind === 'laptop') { box(hx - 36 * u, hy - 30 * u, hx + 30 * u, hy + 2 * u, '#c9ccd2'); box(hx - 31 * u, hy - 26 * u, hx + 25 * u, hy - 3 * u, '#10141c', 2 * u); p.dot(hx - 3 * u, hy - 14 * u, 4 * u, '#ffffff'); return; }
  if (kind === 'briefcase') { box(hx - 26 * u, hy + 2 * u, hx + 26 * u, hy + 38 * u, '#5a3a24'); p.stroke([[hx - 9 * u, hy + 2 * u], [hx - 9 * u, hy - 6 * u], [hx + 9 * u, hy - 6 * u], [hx + 9 * u, hy + 2 * u]], 4 * u, '#3a2414'); return; }
  if (kind === 'coffee') { box(hx - 10 * u, hy - 22 * u, hx + 10 * u, hy + 6 * u, '#f1efe8'); p.band([[hx - 10 * u, hy - 10 * u], [hx + 10 * u, hy - 10 * u]], '#8a5a33', 8 * u, 1 * u, 'butt'); box(hx - 12 * u, hy - 26 * u, hx + 12 * u, hy - 21 * u, '#2b2d34', 2 * u); return; }
  if (kind === 'cash') { for (let k = 0; k < 3; k++) box(hx - 26 * u + k * 3 * u, hy - 12 * u - k * 5 * u, hx + 26 * u + k * 3 * u, hy + 10 * u - k * 5 * u, '#9fbf98', 2 * u); p.band([[hx - 4 * u, hy - 24 * u], [hx - 4 * u, hy + 10 * u]], '#e8d7a6', 8 * u, 1 * u, 'butt'); return; }
  if (kind === 'paper') { box(hx - 18 * u, hy - 46 * u, hx + 18 * u, hy + 2 * u, '#ffffff', 2 * u); for (let k = 0; k < 5; k++) p.stroke([[hx - 12 * u, hy - 38 * u + k * 8 * u], [hx + 12 * u, hy - 38 * u + k * 8 * u]], 2 * u, '#9aa2ad'); return; }
  if (kind === 'mic') { p.stroke([[hx, hy], [hx + 4 * u, hy - 26 * u]], 7 * u, '#2b2d34'); p.ell(hx + 5 * u, hy - 32 * u, 10 * u, 11 * u, '#8e959e', ow * 0.5); return; }
  if (kind === 'trophy') { p.poly([[hx - 18 * u, hy - 46 * u], [hx + 18 * u, hy - 46 * u], [hx + 10 * u, hy - 18 * u], [hx - 10 * u, hy - 18 * u]], '#e9b43a', ow * 0.5); box(hx - 12 * u, hy - 8 * u, hx + 12 * u, hy + 2 * u, '#7a5434', 2 * u); p.stroke([[hx, hy - 18 * u], [hx, hy - 8 * u]], 5 * u, '#e9b43a'); return; }
  if (kind === 'bag') { p.ell(hx, hy + 22 * u, 24 * u, 24 * u, '#d8b36a', ow * 0.5); p.stroke([[hx - 8 * u, hy + 2 * u], [hx + 8 * u, hy + 2 * u]], 5 * u, '#8a6a3a'); g.save(); g.fillStyle = '#5a3a24'; g.font = `900 ${22 * u}px sans-serif`; g.textAlign = 'center'; g.fillText('$', hx, hy + 30 * u); g.restore(); return; }
  if (kind === 'sign') { p.stroke([[hx, hy + 6 * u], [hx, hy - 60 * u]], 5 * u, '#7a5434'); box(hx - 46 * u, hy - 96 * u, hx + 46 * u, hy - 56 * u, '#ffffff', 3 * u);
    g.save(); let fs = 20 * u; g.font = `900 ${fs}px sans-serif`; while (g.measureText(words).width > 84 * u && fs > 6 * u) { fs -= u; g.font = `900 ${fs}px sans-serif`; } g.fillStyle = '#17161b'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(words, hx, hy - 76 * u); g.restore(); }
};
// movement helpers (pure functions of the frame)
const sm_ = (t) => { t = Math.max(0, Math.min(1, t)); return t * t * (3 - 2 * t); };
export const walkPath = (f, f0, f1, from, to) => { const t = Math.max(0, Math.min(1, (f - f0) / Math.max(1, f1 - f0))), e = sm_(t);
  const x = from[0] + (to[0] - from[0]) * e, z = from[1] + (to[1] - from[1]) * e, moving = t > 0 && t < 1;
  return { x, z, step: moving ? Math.round(((f - f0) / 14) % 1 * 100) / 100 : 0, facing: Math.sign(to[0] - from[0]) || 0, done: t >= 1 }; };
export const sitDown = (f, f0, dur = 10) => sm_((f - f0) / dur);
export const jumpAt = (f, f0, h = 0.5, dur = 14) => { const t = (f - f0) / dur; return t > 0 && t < 1 ? Math.round(4 * h * t * (1 - t) * 1000) / 1000 : 0; };
export const shakeAt = (f, f0, dur = 18, deg = 9) => { const t = (f - f0) / dur; return t > 0 && t < 1 ? Math.round(deg * Math.sin(t * Math.PI * 6) * (1 - t)) : 0; };
export const nod = (f, f0, dur = 16, deg = 8) => { const t = (f - f0) / dur; return t > 0 && t < 1 ? Math.round(deg * Math.abs(Math.sin(t * Math.PI * 3))) : 0; };
export const lookAround = (f, seed = 1) => Math.round(Math.sin((f + seed * 17) * 0.06) * 100) / 100;
export const followCam = (f, f0, f1, from, to, height = 1.9, back = 6.5, fov = 46) => { const w = walkPath(f, f0, f1, from, to);
  return { pos: [w.x - Math.sign(to[0] - from[0]) * 1.2, height + 0.4, w.z + back], look: [w.x, height - 0.2, w.z], fov }; };
// fx cards (t = 0..1 through the effect)
export const coinFx = (p, t = 0) => { p.ell(300, 500, 70, 70, '#e9b43a', 10); p.ell(300, 500, 46, 46, '#f5d56a', 0); p.g.save(); p.g.fillStyle = '#b07d22'; p.g.font = '900 70px sans-serif'; p.g.textAlign = 'center'; p.g.textBaseline = 'middle'; p.g.fillText('$', 300, 504); p.g.restore(); };
export const sparkFx = (p, t = 0) => { for (let k = 0; k < 8; k++) { const a = k / 8 * Math.PI * 2, r0 = 40 + t * 120, r1 = 90 + t * 180; p.stroke([[300 + Math.cos(a) * r0, 500 + Math.sin(a) * r0], [300 + Math.cos(a) * r1, 500 + Math.sin(a) * r1]], 14, k % 2 ? '#ffd23f' : '#ffffff'); } };
export const heartFx = (p) => p.poly([[300, 620], [190, 500], [200, 420], [260, 400], [300, 450], [340, 400], [400, 420], [410, 500]], '#e8445a', 12);
export const angerFx = (p) => { for (const [a, b] of [[[250, 420], [290, 470]], [[350, 420], [310, 470]], [[250, 580], [290, 530]], [[350, 580], [310, 530]]]) p.stroke([a, b], 22, '#e23b3b'); };
export const sweatFx = (p) => p.poly([[300, 380], [340, 470], [300, 520], [260, 470]], '#9fd4ff', 10);
export const questionFx = (p) => { p.g.save(); p.g.font = '900 260px sans-serif'; p.g.textAlign = 'center'; p.g.lineWidth = 18; p.g.strokeStyle = '#17161b'; p.g.strokeText('?', 300, 600); p.g.fillStyle = '#ffd23f'; p.g.fillText('?', 300, 600); p.g.restore(); };
export const ideaFx = (p) => { p.ell(300, 460, 90, 100, '#ffe36a', 12); p.poly([[255, 540], [345, 540], [330, 610], [270, 610]], '#b9bfc9', 10); for (let k = 0; k < 6; k++) { const a = -Math.PI * (0.1 + k * 0.16); p.stroke([[300 + Math.cos(a) * 120, 460 + Math.sin(a) * 130], [300 + Math.cos(a) * 170, 460 + Math.sin(a) * 180]], 12, '#ffd23f'); } };
export const zzzFx = (p) => { p.g.save(); p.g.font = '900 140px sans-serif'; p.g.lineWidth = 14; p.g.strokeStyle = '#17161b'; for (const [x, y, s] of [[200, 640, 1], [300, 500, 1.3], [400, 340, 1.6]]) { p.g.font = `900 ${110 * s}px sans-serif`; p.g.strokeText('Z', x, y); p.g.fillStyle = '#ffffff'; p.g.fillText('Z', x, y); } p.g.restore(); };
export const billFx = (p, rot = 0, sq = 1) => { const g = p.g; g.save(); g.translate(300, 500); g.rotate(rot); g.scale(1, sq);
  g.fillStyle = '#cfdcc4'; g.fillRect(-170, -72, 340, 144); g.strokeStyle = '#3f6a4a'; g.lineWidth = 9; g.strokeRect(-160, -62, 320, 124);
  g.fillStyle = '#9fbf98'; g.beginPath(); g.ellipse(0, 0, 40, 52, 0, 0, 7); g.fill(); g.fillStyle = '#2f5a3c'; g.font = '900 52px sans-serif';
  g.textBaseline = 'middle'; g.fillText('100', -148, -30); g.fillText('100', 62, 34); g.restore(); };
// ===== end of the GOLIDE cast kit =====
