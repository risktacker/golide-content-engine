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
  const D = makeDirector(K, { room: S.room, capTop: 1420, capBottom: 1640 });   // captions in the lower third (stickman/captions.py "short3d")
  const props = S.props.map(p => { p.obj.userData.label = p.label; return { ...p, box: new THREE.Box3().setFromObject(p.obj) }; });
  const propObjs = S.props.filter(p => !p.floor).map(p => p.obj);
  const isPerson = s => !!s.root;
  const boxOf = s => isPerson(s) ? D.shownBox(s) : new THREE.Box3().setFromObject(s);
  const useHide = sh => { D.hide.clear(); (sh.hidden || []).forEach(h => D.hide.set(h.who, h)); };
  const SAMPLE = 0.1;
  const times = sh => { const a = []; for (let t = sh.t0 + 0.02; t < sh.t1 - 0.03; t += SAMPLE) a.push(t); a.push(sh.t1 - 0.02); return a; };
  const shotAt = t => { let s = S.shots[0]; for (const x of S.shots) if (t >= x.t0) s = x; return s; };

  const stepped = D.separate(S.people, props, () => S.pose(0));   // nobody starts inside a desk
  function frameShot(sh) {                                         // what the shot must hold, over its whole length
    useHide(sh); const b = new THREE.Box3();
    for (const t of times(sh)) { S.pose(t); sh.who.forEach(s => b.union(boxOf(s))); (sh.extras?.(t) || []).forEach(e => b.union(e.box)); }
    sh.box = b;
  }
  function camAt(sh, t) {
    const u = THREE.MathUtils.clamp((t - sh.t0) / (sh.t1 - sh.t0), 0, 1), v = { ...sh.view(u, t) }, f = sh.fix || {};
    v.yaw += f.yaw || 0; v.pitch += f.pitch || 0; v.fov *= f.fovK || 1; v.k = (v.k ?? 1) * (f.dist || 1);
    const c = D.fit(sh.box, v); if (!c) throw new Error(`shot ${sh.name}: its subjects cannot fit the frame at ${v.fov.toFixed(0)} degrees`);
    K.look(c.pos, c.tgt, c.fov, c.roll); camera().updateMatrixWorld(true); return c;
  }
  const camera = () => K.camera;
  function problems(sh) {
    const out = [];
    useHide(sh);
    for (const t of times(sh)) {
      S.pose(t); camAt(sh, t);
      for (const p of D.issues({ subjects: sh.who.filter(isPerson), people: S.people, props, propObjs, extras: [...(sh.extras?.(t) || []), ...(S.words?.(t) || [])] })) out.push({ t: +t.toFixed(2), p });
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
  function direct() {
    const sizes = {}; props.filter(q => q.obj.name).forEach(q => { const s = q.box.getSize(new THREE.Vector3()); sizes[q.label] = s.toArray().map(v => +v.toFixed(2)); });
    const report = { scene: name, ok: true, stepped, props: sizes, shots: [] };
    for (const sh of S.shots) {
      frameShot(sh); let first = null, done = null;
      for (const fx of FIXES) { sh.fix = fx; const pr = problems(sh); if (!first) first = pr; if (!pr.length) { done = fx; break; } }
      const summary = pr => [...new Set(pr.map(x => x.p))];
      const entry = { name: sh.name, t0: +sh.t0.toFixed(2), t1: +sh.t1.toFixed(2), found: summary(first) };
      if (done) { entry.ok = true; entry.repair = Object.keys(done).length ? done : null; }
      else { sh.fix = {}; entry.ok = false; entry.still = summary(problems(sh)); report.ok = false; }
      report.shots.push(entry);
    }
    return report;
  }
  // ---- rendering ----
  const ov = document.createElement('canvas'); ov.width = K.WW; ov.height = K.HH; const og = ov.getContext('2d');
  function frame(t, debug = false) {
    const sh = shotAt(t); if (!sh.box) frameShot(sh); useHide(sh);
    S.pose(t); const c = camAt(sh, t); S.light(t, c, sh);
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
