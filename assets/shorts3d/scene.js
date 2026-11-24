// GOLIDE scenes on the 3D Shorts engine (thuann-vn/claude-3d-animated-shorts, MIT). The engine's viewer page builds its
// cast, rig, office/home set, lights and grade; this module takes over at its skit branch (assets/shorts3d/hook.py) and
// runs one GOLIDE scene module (`?golide=<name>` loads ./<name>.js and ./<name>.words.json).
//
// A scene module exports build(K, words) -> { dur, people, props, room, pose(t), light(t), shots }:
//   words(t) -> [{box, label}]: words painted in the set (a TV headline); if they show they must be whole (checked, not framed)
//   shots: [{ name, t0, t1, who: [people or props], extras(t) -> [{box, label}], view(u, t) -> {yaw, pitch, fov, k, roll}, dof }]
// The director (director.js) frames each shot on its `who`, checks every frame and repairs failures for free.
// window.GOLIDE = { ready, dur, direct() -> report, frame(t, debug) -> jpeg dataURL }.
import * as THREE from 'three';
import { makeDirector } from './director.js';

export async function run(K) {
  K.ui.style.display = 'none';
  const name = K.Q.get('golide');
  const words = await (await fetch(`./golide/${name}.words.json`)).json();
  const S = await (await import(`./${name}.js`)).build(K, words);
  const D = makeDirector(K, { room: S.room, capTop: 1420, capBottom: 1640, maxDist: S.maxDist });   // captions in the lower third (stickman/captions.py "short3d")
  const props = S.props.map(p => { p.obj.userData.label = p.label; return { ...p, box: new THREE.Box3().setFromObject(p.obj) }; });
  const propObjs = S.props.filter(p => !p.floor).map(p => p.obj);
  const poseT = t => { S.pose(t); props.forEach(p => p.box.setFromObject(p.obj)); };   // things move: their boxes follow them
  const isPerson = s => !!s.root;
  const boxOf = (s, sh) => isPerson(s) ? ((sh && sh.faces || []).includes(s) ? D.faceBox(s) : D.shownBox(s)) : new THREE.Box3().setFromObject(s);
  const useHide = sh => { D.hide.clear(); (sh.hidden || []).forEach(h => D.hide.set(h.who, h)); };
  const SAMPLE = 0.1;
  const times = (sh, step = SAMPLE) => { const a = []; for (let t = sh.t0 + 0.02; t < sh.t1 - 0.03; t += step) a.push(t); a.push(sh.t1 - 0.02); return a; };
  const shotAt = t => { let s = S.shots[0]; for (const x of S.shots) if (t >= x.t0) s = x; return s; };

  const moments = []; for (let t = 0; t < S.dur; t += 0.5) moments.push(t);
  const stepped = D.separate(S.people, props, t => poseT(t), moments);   // nobody inside a desk at any moment
  // the fourth wall (owner 2026-11-23 run): walls between the camera and the action are hidden with what hangs on them
  const SETG = S.group || K.O;
  const walls = SETG.children.filter(o => o.isMesh && o.geometry.type === 'BoxGeometry').map(o => ({ o, b: new THREE.Box3().setFromObject(o) }))
    .filter(w => { const s = w.b.getSize(new THREE.Vector3()); return s.y > 2 && (s.x > 6 || s.z > 6) && Math.min(s.x, s.z) < 0.6; });
  const onWall = walls.map(w => { const s = w.b.getSize(new THREE.Vector3()), alongX = s.x > s.z, c = w.b.getCenter(new THREE.Vector3());
    return SETG.children.filter(o => o !== w.o && o.visible && (() => { const q = new THREE.Box3().setFromObject(o).getCenter(new THREE.Vector3()); return alongX ? Math.abs(q.z - c.z) < 0.6 : Math.abs(q.x - c.x) < 0.6; })()); });
  const wallVisible = walls.map(w => w.o.visible);
  function fourthWall(pos, tgt) {
    walls.forEach((w, i) => { const s = w.b.getSize(new THREE.Vector3()), c = w.b.getCenter(new THREE.Vector3()), alongX = s.x > s.z;
      const between = alongX ? (pos.z - c.z) * (tgt.z - c.z) < 0 : (pos.x - c.x) * (tgt.x - c.x) < 0;
      w.o.visible = wallVisible[i] && !between; onWall[i].forEach(o => { if (o.userData.wallKeep === undefined) o.userData.wallKeep = o.visible; o.visible = o.userData.wallKeep && !between; }); });
  }
  function frameShot(sh) {                                         // what the shot must hold, over its whole length
    useHide(sh); const b = new THREE.Box3(), at = [];
    for (const t of times(sh)) { poseT(t); const m = new THREE.Box3(); sh.who.forEach(s => m.union(boxOf(s, sh))); (sh.extras?.(t) || []).filter(e => !(sh.faces?.length && e.onTop)).forEach(e => m.union(e.box));   /* a face shot frames the face; bubbles and labels are checked, not framed */ b.union(m); at.push({ t, box: m }); }
    sh.box = b; sh.at = at;
    // subjects that travel (a vehicle, someone running): the camera follows them instead of framing the whole trip
    const size = m => m.getSize(new THREE.Vector3()).length(), big = Math.max(...at.map(x => size(x.box)));
    sh.track = size(b) > big * 1.8 || !!(sh.faces && sh.faces.length) || !!sh.follow;   // face shots follow the face; a followed thing is ridden with
  }
  // the box the camera frames at time t: the whole shot, or (tracking) the subjects around that moment, smoothed
  function boxAt(sh, t) {
    if (!sh.track) return sh.box;
    const b = new THREE.Box3(); for (const x of sh.at) if (Math.abs(x.t - t) <= 0.45) b.union(x.box);
    if (b.isEmpty()) { let best = sh.at[0]; for (const x of sh.at) if (Math.abs(x.t - t) < Math.abs(best.t - t)) best = x; b.copy(best.box); }
    return b;
  }
  function camAt(sh, t) {
    const u = THREE.MathUtils.clamp((t - sh.t0) / (sh.t1 - sh.t0), 0, 1), v = { ...sh.view(u, t) }, f = sh.fix || {};
    if (f.yawAbs !== undefined) v.yaw = f.yawAbs; if (f.pitchAbs !== undefined) v.pitch = f.pitchAbs;
    v.yaw += f.yaw || 0; v.pitch += f.pitch || 0; v.fov *= f.fovK || 1; v.k = (v.k ?? 1) * (f.dist || 1);
    // a station the storyboard wrote (camera position, aim, lens): played exactly as written, with a slow rest drift
    if (sh.station) { const st = sh.station, pos = st.pos.clone(), tg = st.aim.clone(), side = new THREE.Vector3().subVectors(tg, pos).cross(new THREE.Vector3(0, 1, 0)).normalize();
      const dd = pos.distanceTo(tg); pos.addScaledVector(side, (u - 0.5) * Math.min(0.35, dd * 0.06)); pos.lerp(tg, 0.05 * u * (st.push ?? 1));
      const c3 = { pos, tgt: tg, fov: st.fov, roll: 0, dist: pos.distanceTo(tg) }; K.look(c3.pos, c3.tgt, c3.fov, 0); camera().updateMatrixWorld(true); fourthWall(c3.pos, c3.tgt); return c3; }
    // the impossible view (the plan's eye): the camera sits inside a thing (in the gap, in the drawer, behind the glass)
    // and looks at the subjects; the move only creeps a little toward them
    if (sh.eye) { const eb = new THREE.Box3().setFromObject(sh.eye), tg = boxAt(sh, t).getCenter(new THREE.Vector3());
      const pos = eb.getCenter(new THREE.Vector3()); pos.y = Math.max(0.12, eb.min.y + (eb.max.y - eb.min.y) * (sh.eyeY ?? 0.6)); pos.lerp(tg, 0.12 * u);
      const c2 = { pos, tgt: tg, fov: v.fov, roll: v.roll || 0, dist: pos.distanceTo(tg) };
      K.look(c2.pos, c2.tgt, c2.fov, c2.roll); camera().updateMatrixWorld(true); fourthWall(c2.pos, c2.tgt); return c2; }
    const c = D.fit(boxAt(sh, t), v); if (!c) throw new Error(`shot ${sh.name}: its subjects cannot fit the frame at ${v.fov.toFixed(0)} degrees`);
    K.look(c.pos, c.tgt, c.fov, c.roll); camera().updateMatrixWorld(true); fourthWall(c.pos, c.tgt); return c;
  }
  const camera = () => K.camera;
  // every problem of a shot, checked every 0.1 s; `quick` (the repair search): every 0.25 s, stop at the first one
  const staging = new Set();
  function problems(sh, quick = false) {
    const out = [];
    useHide(sh);
    for (const t of times(sh, quick ? 0.25 : SAMPLE)) {
      poseT(t); camAt(sh, t);
      { const own = new Set(); sh.who.forEach(w => (w.root || w).traverse?.(x => own.add(x))); const tid = o => { for (let x = o; x && x.userData; x = x.parent) if (x.userData.thing) return x.userData.thing; return null; }, mine = new Set(sh.who.map(tid).filter(Boolean));   /* a row of the subject's own copies is the picture, not a wall */
        const objs = propObjs.filter(o => o !== sh.near && o !== sh.eye && !own.has(o) && !mine.has(tid(o)));
        const b2 = D.blocked(boxAt(sh, t).getCenter(new THREE.Vector3()), objs); if (b2) { out.push({ t: +t.toFixed(2), p: b2 }); if (quick) return out; } }
      for (const p of D.issues({ subjects: sh.who.filter(isPerson), people: S.people, propObjs: propObjs.filter(o => o !== sh.near && o !== sh.eye), props: sh.eye ? props.filter(q => q.obj !== sh.eye) : props, extras: [...(sh.extras?.(t) || []), ...(S.words?.(t) || []).filter(e => !e.subjectOnly || sh.who.includes(e.subjectOnly))], faces: (sh.faces || []).filter(f => sh.who.includes(f)), things: sh.who.filter(w => !isPerson(w)) })) {
        // people passing through things is staging, not framing: the camera cannot fix it, so it never moves the camera (reported once)
        if (p.includes(' passes through ')) { staging.add(p); continue; }
        out.push({ t: +t.toFixed(2), p }); if (quick) return out; }
    }
    return out;
  }
  // free repairs, tried in order on the same storyboard: step back, orbit, rise or drop, change the lens
  const FIXES = [{}, { dist: 1.1 }, { dist: 1.22 }];
  for (const p of [-0.12, -0.24]) FIXES.push({ pitch: p });
  for (const y of [0.12, -0.12, 0.24, -0.24, 0.36, -0.36, 0.5, -0.5]) for (const p of [0, 0.1, -0.08, -0.18]) FIXES.push({ yaw: y, pitch: p });
  // a wider lens brings the camera closer (out of walls, in front of people who would block the view)
  for (const fk of [1.2, 1.35, 1.5]) for (const y of [0, 0.12, -0.12, 0.24, -0.24, 0.36, -0.36, 0.5, -0.5]) for (const p of [0, -0.12, 0.1]) FIXES.push({ fovK: fk, yaw: y, pitch: p });
  for (const y of [0, 0.2, -0.2]) FIXES.push({ fovK: 0.85, yaw: y });
  // the last free repairs, in order (owner 2026-11-22: never pay a model to retry): another angle, then fewer people,
  // then the shot before holds a little longer. Only a first shot that nothing fixes stops the render.
  const ANGLES = [[0, 0.06], [0, 0.25], [-0.4, 0.1], [0.4, 0.1], [-0.9, 0.1], [0.9, 0.1], [0, -0.12], [-1.5, 0.1], [1.5, 0.1], [-2.2, 0.12], [2.2, 0.12], [Math.PI, 0.12]];   // round the back too: people turn and walk anywhere
  const ANGLE_FIXES = []; for (const [ya, pa] of ANGLES) for (const fk of [1, 1.2, 1.4]) for (const d of [1, 1.15]) ANGLE_FIXES.push({ yawAbs: ya, pitchAbs: pa, fovK: fk, dist: d });
  const tryFixes = (sh, list) => { for (const fx of list) { sh.fix = fx; if (!problems(sh, true).length && !problems(sh).length) return fx; } return null; };
  // the director's decisions are made ONCE (the check job) and handed to every render machine, which only applies them
  function apply(saved) {
    const all = [...S.shots], keep = [];
    for (const d of saved) {
      const sh = all[d.i]; if (!sh) throw new Error(`direction: no shot ${d.i}`);
      if (d.merged) { keep[keep.length - 1].t1 = d.t1; continue; }
      sh.who = d.who.map(k => sh.who0[k]); sh.fix = d.fix || {}; if (d.nostation) sh.station = null; if (d.station_pos && sh.station) sh.station.pos.set(...d.station_pos); keep.push(sh);
    }
    S.shots.length = 0; S.shots.push(...keep); S.shots.forEach(frameShot);
    window.GOLIDE.shots = S.shots.map(s => ({ name: s.name, t0: s.t0, t1: s.t1 }));
    return { scene: name, ok: true, applied: true, stepped, shots: S.shots.map(s => ({ name: s.name, t0: s.t0, t1: s.t1, ok: true, found: [] })) };
  }
  function direct(saved) {
    S.shots.forEach((sh, i) => { sh.idx = i; sh.who0 = [...sh.who]; });
    if (saved) return apply(saved);
    const report = { scene: name, ok: true, stepped, shots: [], decisions: [] };
    const summary = pr => [...new Set(pr.map(x => x.p))];
    for (let i = 0; i < S.shots.length; i++) {
      const sh = S.shots[i]; frameShot(sh); sh.fix = {};
      const entry = { name: sh.name, t0: +sh.t0.toFixed(2), t1: +sh.t1.toFixed(2), found: summary(problems(sh)), box: sh.box.getSize(new THREE.Vector3()).toArray().map(v => +v.toFixed(2)), faces: (sh.faces || []).map(f => [D.faceBox(f).getSize(new THREE.Vector3()).toArray().map(v => +v.toFixed(2)), D.headBox(f).getSize(new THREE.Vector3()).toArray().map(v => +v.toFixed(2))]), ex: (sh.extras?.(sh.t0 + 0.5) || []).map(e => [e.label, e.box.getSize(new THREE.Vector3()).toArray().map(v => +v.toFixed(2))]), cam: (() => { poseT(sh.t0 + 0.1); const c = camAt(sh, sh.t0 + 0.1); return [+c.dist.toFixed(2), +c.fov.toFixed(1)]; })() };
      // a written station is the plan and is kept as written; only a station that cannot work at all (camera inside a
      // thing, below the ground, the subject out of the shot or hidden) falls back to the director's own framing
      const HARD = /camera is|out of the shot|is hidden behind|cut by the camera|blocked/;
      // a station written inside a thing first steps toward its aim until it is out (free), before anything is dropped
      if (sh.station && entry.found.some(q => /camera is inside/.test(q))) { const st = sh.station, from = st.pos.clone();
        for (let k = 1; k <= 12 && entry.found.some(q => /camera is inside/.test(q)); k++) { st.pos.copy(from).lerp(st.aim, 0.05 * k); entry.found = summary(problems(sh)); }
        if (entry.found.some(q => /camera is inside/.test(q))) st.pos.copy(from); else entry.station_moved = st.pos.toArray().map(v => +v.toFixed(2)); }
      if (sh.station) { if (entry.found.some(q => HARD.test(q))) { entry.station_dropped = entry.found.filter(q => HARD.test(q)); sh.station = null; sh.nostation = true; entry.found = summary(problems(sh)); }
        else { entry.ok = true; entry.station = true; if (entry.found.length) { entry.kept_with = entry.found; (report.warnings = report.warnings || []).push(`${sh.name}: ${entry.found.join('; ')}`); }
          report.decisions.push({ i: sh.idx, fix: {}, who: sh.who.map(w => sh.who0.indexOf(w)), ...(entry.station_moved ? { station_pos: entry.station_moved } : {}) }); report.shots.push(entry); continue; } }
      let done = entry.found.length ? tryFixes(sh, FIXES) : {};
      if (!done) { done = tryFixes(sh, ANGLE_FIXES); if (done) entry.repair_note = 'another angle'; }
      if (!done) {                                                     // fewer people: the people first, then each one alone
        const whoAll = sh.who, people = whoAll.filter(isPerson), subsets = [];
        if (people.length && people.length < whoAll.length) subsets.push(people);
        for (let k = people.length - 1; k >= 1; k--) subsets.push(people.slice(0, k)); people.forEach(p => subsets.push([p]));
        for (const sub of subsets) { sh.who = sub; frameShot(sh); done = tryFixes(sh, [{}, ...FIXES, ...ANGLE_FIXES]); if (done) { entry.repair_note = `only ${sub.map(x => x.label).join(', ')}`; break; } }
        if (!done) { sh.who = whoAll; frameShot(sh); }
      }
      if (!done && i > 0 && false) {                                   // 2026-11-23: never merge a landing away (it carries its own story); the best attempt is kept below
        const prev = S.shots[i - 1], keepT1 = prev.t1, keepBox = prev.box, keepFix = prev.fix;
        prev.t1 = sh.t1; frameShot(prev); prev.fix = keepFix;
        if (!problems(prev).length || tryFixes(prev, [{}, ...FIXES, ...ANGLE_FIXES])) {
          const pd = report.decisions.find(x => x.i === prev.idx); if (pd) pd.fix = prev.fix;
          report.decisions.push({ i: sh.idx, merged: true, t1: +sh.t1.toFixed(3) });
          S.shots.splice(i, 1); i--; entry.ok = true; entry.repair_note = `merged into the shot before (${prev.name})`; report.shots.push(entry); continue;
        }
        prev.t1 = keepT1; prev.box = keepBox; prev.fix = keepFix;
      }
      if (done) { sh.fix = done; entry.ok = true; entry.repair = Object.keys(done).length ? done : null; }
      else {
        // nothing made it perfect: keep the attempt with the fewest problem moments and say so in the report
        // (owner 2026-11-22: a paid storyboard never ends without a video; nothing goes back to Sol)
        let best = {}, bestN = Infinity;
        // the plan's own angle is worth keeping: an attempt that throws it away (another angle) must be clearly better
        const weight = q => /out of the shot|is hidden behind|camera is|cut by the camera|blocked/.test(q.p) ? 3 : 1;
        for (const fx of [{}, ...FIXES.slice(0, 20), ...ANGLE_FIXES]) { sh.fix = fx; const n = problems(sh).reduce((a, q) => a + weight(q), 0) + (fx.yawAbs !== undefined ? 6 : 0); if (n < bestN) { best = fx; bestN = n; if (!n) break; } }
        sh.fix = best; entry.ok = true; entry.kept_with = summary(problems(sh));
        (report.warnings = report.warnings || []).push(`${sh.name}: ${entry.kept_with.join('; ')}`);
      }
      report.decisions.push({ i: sh.idx, fix: sh.fix, who: sh.who.map(w => sh.who0.indexOf(w)), ...(sh.nostation ? { nostation: true } : {}) });
      report.shots.push(entry);
    }
    window.GOLIDE.shots = S.shots.map(s => ({ name: s.name, t0: s.t0, t1: s.t1 }));
    if (staging.size) report.staging = [...staging];   // people through things: for the storyboard, not the camera
    return report;
  }
  // ---- rendering ----
  const ov = document.createElement('canvas'); ov.width = K.WW; ov.height = K.HH; const og = ov.getContext('2d');
  // ONE travelling camera (Rick: few cuts, lands on a new picture about every second): between two landings of the same
  // move the camera flies from where the last one ended to where this one starts; a new move is a cut
  // CAMERA V2, stolen from the Ricks Clips kit (CINEMATOGRAPHY.md section 7): the camera rests on a station, then TRAVELS
  // to the next one and lands ON its word; travel time grows with distance (1.5 s + 0.25 s per metre, at most 6 s), inside
  // the rest before it minus a 0.7 s hold; the ease is on the picture (slow off, cruise, slow in). A new move is a cut.
  const HOLD = 0.7;
  function nextOf(sh) { const i = S.shots.indexOf(sh), n = S.shots[i + 1]; return n && n.take !== undefined && n.take === sh.take ? n : null; }
  function camFly(sh, t) {
    const c = camAt(sh, t), n = nextOf(sh);
    if (!n) return c;
    if (!n.box) frameShot(n);
    const b = camAt(n, n.t0), a0 = camAt(sh, Math.max(sh.t0, n.t0 - 0.01));
    const dist = a0.pos.distanceTo(b.pos), tr = Math.max(0.5, Math.min(6, 1.5 + 0.25 * dist, (n.t0 - sh.t0) - HOLD));
    if (t < n.t0 - tr) { camAt(sh, t); return c; }
    const a = camAt(sh, t), k = THREE.MathUtils.smootherstep((t - (n.t0 - tr)) / tr, 0, 1);
    const pos = a.pos.clone().lerp(b.pos, k), tgt = a.tgt.clone().lerp(b.tgt, k), fov = THREE.MathUtils.lerp(a.fov, b.fov, k);
    const roll = Math.sin(k * Math.PI) * 0.07 * Math.sign(b.pos.x - a.pos.x || 1);   // roll only inside a travel, back to level on landing
    if (props.some(q => !q.floor && q.box.containsPoint(pos))) { camAt(sh, t); return c; }   // never through a thing: rest, then cut
    K.look(pos, tgt, fov, roll); camera().updateMatrixWorld(true); fourthWall(pos, tgt); return { ...a, pos, tgt, fov, roll, dist: pos.distanceTo(tgt) };
  }
  function frame(t, debug = false) {
    const sh = shotAt(t); if (!sh.box) frameShot(sh); useHide(sh);
    poseT(t); const c = camFly(sh, t); S.light(t, c, sh);
    K.post.bokeh.enabled = !!sh.dof; if (sh.dof) { K.post.bokeh.uniforms.focus.value = c.dist; K.post.bokeh.uniforms.aperture.value = sh.dof; }
    K.U.uTime.value = t; K.post.render();
    if (!debug) return K.renderer.domElement.toDataURL('image/jpeg', 0.92);
    og.drawImage(K.renderer.domElement, 0, 0); og.lineWidth = 3;
    const R = (r, col) => { if (r.behind || r.crossing) return; og.strokeStyle = col; og.strokeRect(r.x0, r.y0, r.x1 - r.x0, r.y1 - r.y0); };
    og.setLineDash([12, 8]); R({ x0: D.SAFE.l, y0: D.SAFE.t, x1: D.SAFE.r, y1: D.SAFE.b }, '#00e5ff'); R({ x0: D.CAP.l, y0: D.CAP.t, x1: D.CAP.r, y1: D.CAP.b }, '#ffd400'); og.setLineDash([]);
    S.people.forEach(p => { const r = D.rect(D.shownBox(p)); if (D.shows(r)) R(r, D.within(r, D.SAFE) ? '#3cff6b' : '#ff2d2d'); });
    og.fillStyle = '#fff'; og.font = `bold ${Math.round(26 * K.WW / 1080)}px sans-serif`; og.fillText(`${sh.name}  t=${t.toFixed(2)}`, 20, 40);
    return ov.toDataURL('image/jpeg', 0.9);
  }
  window.GOLIDE = { ready: true, dur: S.dur, direct, frame, shots: S.shots.map(s => ({ name: s.name, t0: s.t0, t1: s.t1 })) };
  window.frame = t => frame(t); window.DUR = S.dur; window.ready = true;
}
