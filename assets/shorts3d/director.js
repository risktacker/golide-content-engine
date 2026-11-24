// GOLIDE director for the 3D Shorts engine (owner 2026-11-22: "heads and bodies well contained in every shot, framed
// as if a camera operator shot it; nothing cropped and nothing crashing into anything else in any frame").
//
// A shot names WHO it is about (people and props) and HOW it looks at them (yaw, pitch, lens, roll, push). The director
// frames them itself: the camera distance and aim are solved so every subject, over the whole shot, sits fully inside
// the phone's safe crop (130 px left, 160 px right, 230 px top on 1080x1920). Then every frame is checked:
//   - any person who shows at all is fully inside the safe crop (a half-body at an edge is a failure);
//   - no head sits under the caption band; no subject head is hidden behind a prop or another person;
//   - the camera is not inside a wall, a prop or a person; people do not pass through props or each other.
// A failing shot is repaired for free on the same storyboard: the camera orbits, rises or steps back, the lens
// changes, people standing inside furniture step clear. Nothing is sent back to a model. A shot that cannot be
// repaired stops the render with its reasons (no hidden fallback).
import * as THREE from 'three';

export function makeDirector(K, opt = {}) {
  const { camera, WW, HH } = K;
  const sx = WW / 1080, sy = HH / 1920;
  const SAFE = { l: 130 * sx, r: WW - 160 * sx, t: 230 * sy, b: HH - (opt.bottom ?? 40) * sy };
  const INSET = (opt.inset ?? 18) * sx;                       // breathing room inside the safe crop when framing
  const CAP = { l: 150 * sx, r: WW - 180 * sx, t: (opt.capTop ?? 1150) * sy, b: (opt.capBottom ?? 1390) * sy };   // captions (stickman/captions.py "short")
  const ROOM = opt.room || null;                               // {min: V, max: V} the set's inside
  const _v = new THREE.Vector3(), _tb = new THREE.Box3();

  // ---- measuring ----
  const meshBox = (o, box) => { if (!o.geometry.boundingBox || o.userData.dynGeo) o.geometry.computeBoundingBox(); _tb.copy(o.geometry.boundingBox).applyMatrix4(o.matrixWorld); box.union(_tb); };
  function personBox(c) {                                     // everything visible on a person: head, hat, body, clothes, limbs, mittens, shoes
    const box = new THREE.Box3(); c.root.updateMatrixWorld(true);
    c.root.traverseVisible(o => { if (o.isMesh && !o.isSkinnedMesh) meshBox(o, box); });
    (c.dyn || []).forEach(d => { const m = d.mesh; if (m && m.visible && m.parent) { m.updateMatrixWorld(true); m.userData.dynGeo = true; meshBox(m, box); } });
    return box;
  }
  // what the camera can see of a person: a desk between the camera and someone standing behind it hides their legs, so a
  // shot frames (and checks) them from the desk top up, like a camera operator's medium shot (owner 2026-11-22: "zoom a
  // little"). hide: Map person -> { below: y, frontZ: z } — only while the camera is in front of that desk.
  const hide = new Map();
  function shownBox(c) { const b = personBox(c), h = hide.get(c); if (h && camera.position.z > h.frontZ && b.max.y > h.below + 0.3) b.min.y = Math.max(b.min.y, h.below); return b; }
  const headBox = c => { c.head.updateMatrixWorld(true); return new THREE.Box3().setFromObject(c.head); };
  // a face shot (owner 2026-11-23, the references' reaction close-ups): head and shoulders, the body may leave the frame
  // a fixed head-and-shoulders box around the skull's centre (the head group holds the face decal's full plane and the
  // hat brim, far wider than the face): 0.3 m head radius at the cast's scale
  const faceBox = c => { c.hm.updateMatrixWorld(true); const ctr = new THREE.Box3().setFromObject(c.hm).getCenter(new THREE.Vector3()), r = 0.3 * c.root.scale.x;
    return new THREE.Box3(new THREE.Vector3(ctr.x - 0.75 * r, ctr.y - 1.8 * r, ctr.z - 0.45 * r), new THREE.Vector3(ctr.x + 0.75 * r, ctr.y + 1.2 * r, ctr.z + 0.45 * r)); };
  function coreBox(c) {                                       // the body without reaching arms: what may not pass through furniture
    const b = personBox(c), h = c.bone('Hips'); h.getWorldPosition(_v); const r = 0.3 * c.root.scale.x / 0.8;
    b.min.x = Math.max(b.min.x, _v.x - r); b.max.x = Math.min(b.max.x, _v.x + r); b.min.z = Math.max(b.min.z, _v.z - r); b.max.z = Math.min(b.max.z, _v.z + r);
    b.min.y += 0.08;                                          // shoe soles touch the floor; the floor is not a collision
    return b;
  }
  function setCam(pos, tgt, fov, roll = 0) {
    camera.position.copy(pos); camera.up.set(0, 1, 0); camera.lookAt(tgt); if (roll) camera.rotateZ(roll);
    camera.fov = fov; camera.aspect = WW / HH; camera.updateProjectionMatrix(); camera.updateMatrixWorld(true);
  }
  // screen rectangle of a box: {x0,y0,x1,y1}, or {behind:true} / {crossing:true} when it is behind or around the camera
  function rect(box) {
    const r = { x0: 1e9, y0: 1e9, x1: -1e9, y1: -1e9 }; let back = 0;
    for (let i = 0; i < 8; i++) {
      _v.set(i & 1 ? box.max.x : box.min.x, i & 2 ? box.max.y : box.min.y, i & 4 ? box.max.z : box.min.z);
      _v.applyMatrix4(camera.matrixWorldInverse); if (_v.z > -camera.near) { back++; continue; }
      _v.applyMatrix4(camera.projectionMatrix);
      const x = (_v.x + 1) / 2 * WW, y = (1 - _v.y) / 2 * HH;
      r.x0 = Math.min(r.x0, x); r.x1 = Math.max(r.x1, x); r.y0 = Math.min(r.y0, y); r.y1 = Math.max(r.y1, y);
    }
    if (back === 8) return { behind: true };
    // half behind the camera plane: cut by the camera only when it is right at the lens; far off to the side it is just
    // partly outside the picture (its front corners decide)
    if (back) { if (box.distanceToPoint(camera.position) < 2) return { crossing: true }; if (r.x1 < r.x0) return { behind: true };
      r.x0 = Math.min(r.x0, r.x0 < WW / 2 ? -1 : r.x0); r.x1 = Math.max(r.x1, r.x1 > WW / 2 ? WW + 1 : r.x1); }
    return r;
  }
  const shows = r => !r.behind && (r.crossing || (r.x1 > 0 && r.x0 < WW && r.y1 > 0 && r.y0 < HH));
  const within = (r, a, m = 0) => !r.behind && !r.crossing && r.x0 >= a.l + m && r.x1 <= a.r - m && r.y0 >= a.t + m && r.y1 <= a.b - m;
  const meets = (r, a) => !r.behind && !r.crossing && r.x1 > a.l && r.x0 < a.r && r.y1 > a.t && r.y0 < a.b;

  // ---- framing: solve distance and aim so `box` fills the safe crop, seen from (yaw, pitch) through `fov` ----
  const dirOf = (yaw, pitch) => new THREE.Vector3(Math.sin(yaw) * Math.cos(pitch), Math.sin(pitch), Math.cos(yaw) * Math.cos(pitch));
  function fit(box, v) {
    const dir = dirOf(v.yaw, v.pitch), tgt = box.getCenter(new THREE.Vector3()); let d = 1;
    const fits = (dd) => { setCam(tgt.clone().addScaledVector(dir, dd), tgt, v.fov, v.roll || 0); return within(rect(box), SAFE, INSET); };
    for (let pass = 0; pass < 3; pass++) {
      let lo = 0.15, hi = opt.maxDist ?? 120; if (!fits(hi)) return null;
      for (let i = 0; i < 32; i++) { const m = (lo + hi) / 2; if (fits(m)) hi = m; else lo = m; }
      d = hi; fits(d); const r = rect(box);
      const dx = (r.x0 + r.x1) / 2 - (SAFE.l + SAFE.r) / 2, dy = (r.y0 + r.y1) / 2 - (SAFE.t + SAFE.b) / 2;
      const wpp = 2 * d * Math.tan(v.fov * Math.PI / 360) / HH;
      const right = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 0), up = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 1);
      tgt.addScaledVector(right, dx * wpp).addScaledVector(up, -dy * wpp);
    }
    const k = Math.max(1, v.k ?? 1);                          // a push never goes closer than the framed distance
    return { pos: tgt.clone().addScaledVector(dir, d * k), tgt, fov: v.fov, roll: v.roll || 0, dist: d * k };
  }

  // ---- checks ----
  function insideAnything(p, props, people) {
    // a wall between the camera and the action is taken away like a TV set's fourth wall (scene.js), so the camera
    // may stand beyond the walls; never under the floor, over the ceiling or far out of the building
    if (ROOM && !(p.y > ROOM.min.y && p.y < ROOM.max.y)) return 'the camera is below the floor or above the ceiling';
    if (ROOM && !(p.x > ROOM.min.x - 2.5 && p.x < ROOM.max.x + 2.5 && p.z > ROOM.min.z - 2.5 && p.z < ROOM.max.z + 2.5)) return 'the camera is far outside the set';
    for (const q of props) if (q.box.clone().expandByScalar(0.06).containsPoint(p)) return `the camera is inside ${q.label}`;
    for (const c of people) if (personBox(c).expandByScalar(0.06).containsPoint(p)) return `the camera is inside ${c.label}`;
    return null;
  }
  const ray = new THREE.Raycaster();
  function hidden(c, propObjs, people) {                      // is this subject's face blocked from the camera?
    const hb = headBox(c), hc = hb.getCenter(new THREE.Vector3()), from = camera.position.clone(), d = hc.distanceTo(from);
    ray.set(from, hc.clone().sub(from).normalize()); ray.far = d - 0.12;
    const hit = ray.intersectObjects(propObjs, true).find(h => h.object.visible && !h.object.userData.noBlock);
    if (hit) return `the face of ${c.label} is hidden behind ${labelOf(hit.object)}`;
    for (const o of people) if (o !== c) { const ob = headBox(o).union(coreBox(o)); const p = ray.ray.intersectBox(ob, _v); if (p && p.distanceTo(from) < d - 0.15) return `the face of ${c.label} is hidden behind ${o.label}`; }
    return null;
  }
  // a thing the shot is about must be seen: the line from the camera to its centre may not hit something else first
  // (owner 2026-11-24, pirates trial): five lines (the centre and four points around it); hidden only when most are
  // blocked, so a mast or a rope across a ship does not count; its own copies (a row of cannons) never hide it
  const thingOf = o => { for (let x = o; x; x = x.parent) if (x.userData.thing) return x.userData.thing; return null; };
  const spread5 = (b) => { const c = b.getCenter(new THREE.Vector3()), s = b.getSize(new THREE.Vector3()).multiplyScalar(0.3);
    return [c, c.clone().add(new THREE.Vector3(s.x, s.y, 0)), c.clone().add(new THREE.Vector3(-s.x, s.y, 0)), c.clone().add(new THREE.Vector3(s.x, -s.y, s.z)), c.clone().add(new THREE.Vector3(-s.x, -s.y, -s.z))]; };
  function thingHidden(o, propObjs) {
    const b = new THREE.Box3().setFromObject(o), from = camera.position.clone();
    if (b.containsPoint(from)) return null;
    const own = new Set(); o.traverse(x => own.add(x)); const me = thingOf(o);
    const others = propObjs.filter(p => p !== o && !(me && thingOf(p) === me));
    let n = 0, label = null;
    for (const pt of spread5(b)) { const d = pt.distanceTo(from); ray.set(from, pt.clone().sub(from).normalize()); ray.far = d;
      const hit = ray.intersectObjects(others, true).find(h => h.object.visible && !own.has(h.object) && !h.object.userData.noBlock && !(me && thingOf(h.object) === me));
      if (!hit) continue; const first = ray.intersectObject(o, true)[0];
      if (!first || hit.distance < first.distance - 0.05) { n++; label = label || labelOf(hit.object); } }
    return n >= 3 ? `${o.name || 'the subject'} is hidden behind ${label}` : null;
  }
  // the middle of the picture may not be a wall: of five lines around the subjects' centre, most must be clear
  function blocked(point, propObjs) {
    const from = camera.position.clone(); let n = 0, label = null;
    const pts = [point, ...[[0.6, 0.4], [-0.6, 0.4], [0.6, -0.4], [-0.6, -0.4]].map(([x, y]) => { const r = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 0), u = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 1), k = point.distanceTo(from) * 0.08; return point.clone().addScaledVector(r, x * k).addScaledVector(u, y * k); })];
    for (const pt of pts) { const d = pt.distanceTo(from); ray.set(from, pt.clone().sub(from).normalize()); ray.far = d * 0.85;
      const hit = ray.intersectObjects(propObjs, true).find(h => h.object.visible && !h.object.userData.noBlock); if (hit) { n++; label = label || labelOf(hit.object); } }
    return n >= 3 ? `the view is blocked by ${label}` : null;
  }
  const labelOf = o => { for (let x = o; x; x = x.parent) if (x.userData.label) return x.userData.label; return 'a set piece'; };
  function collisions(people, props) {
    const out = [], cb = people.map(coreBox);
    for (let i = 0; i < people.length; i++) {
      for (let j = i + 1; j < people.length; j++) if (cb[i].intersectsBox(cb[j])) out.push(`${people[i].label} passes through ${people[j].label}`);
      for (const q of props) if (!q.floor && !q.walk && cb[i].intersectsBox(q.box)) out.push(`${people[i].label} passes through ${q.label}`);
    }
    return out;
  }
  // everything wrong with the current frame (people posed, camera set)
  function issues({ subjects, people, props, propObjs, extras = [], faces = [], things = [] }) {
    const out = [];
    const where = insideAnything(camera.position, props, people); if (where) out.push(where);
    for (const c of people) {
      if (faces.includes(c)) { const f = rect(faceBox(c)); if (f.crossing || f.behind) out.push(`${c.label} is cut by the camera`); else if (!within(f, SAFE)) out.push(`the face of ${c.label} is cropped at the frame edge`); else if (f.y1 - f.y0 < HH * 0.22) out.push(`the face of ${c.label} is too small for a face shot`);
        const hh = rect(headBox(c)); if (shows(hh) && meets(hh, CAP)) out.push(`the head of ${c.label} sits under the captions`); continue; }
      const r = rect(shownBox(c));
      if (r.crossing) out.push(`${c.label} is cut by the camera`);
      // the shot's subjects are whole; a passer-by may leave the frame edge with their body, never with their head
      else if (shows(r) && !within(r, SAFE) && (subjects.includes(c) || (() => { const h = rect(headBox(c)); return shows(h) && !within(h, SAFE); })())) out.push(`${c.label} is cropped at the frame edge`);
      else if (subjects.includes(c) && !shows(r)) out.push(`${c.label} is out of the shot`);
      else if (subjects.includes(c)) { const f = rect(personBox(c)); if (!f.behind && !f.crossing && f.y1 - f.y0 < HH * (things.length ? 0.07 : (opt.minPerson ?? 0.2))) out.push(`${c.label} is too small in the frame`); }   /* whole body, a desk in front does not count */
      const h = rect(headBox(c)); if (shows(h) && meets(h, CAP)) out.push(`the head of ${c.label} sits under the captions`);
    }
    // two heads overlapping on screen read as a crash even when neither face is fully hidden
    const heads = people.map(c => [c, rect(headBox(c))]).filter(([, r]) => shows(r) && !r.crossing);
    for (let i = 0; i < heads.length; i++) for (let j = i + 1; j < heads.length; j++) { const [a, ra] = heads[i], [b, rb] = heads[j];
      if (ra.x1 > rb.x0 && rb.x1 > ra.x0 && ra.y1 > rb.y0 && rb.y1 > ra.y0) out.push(`the heads of ${a.label} and ${b.label} overlap in the frame`); }
    for (const e of extras) { const r = rect(e.box); if (!shows(r)) continue; if (!e.noCrop && !within(r, SAFE)) out.push(`${e.label} is cropped at the frame edge`);
      // words may not sit behind a head nearer the camera (bubbles drawn on top of everything are exempt)
      if (e.onTop) continue;
      const ez = e.box.getCenter(new THREE.Vector3()).distanceTo(camera.position);
      for (const [c, h] of heads) if (h.x1 > r.x0 && r.x1 > h.x0 && h.y1 > r.y0 && r.y1 > h.y0 && headBox(c).getCenter(new THREE.Vector3()).distanceTo(camera.position) < ez - 0.05) out.push(`${e.label} is covered by the head of ${c.label}`); }
    for (const c of subjects) if (c.root) { const h = hidden(c, propObjs, people); if (h) out.push(h); }
    for (const o of things) { const h = thingHidden(o, propObjs); if (h) out.push(h); }
    // a subject's face turned away from the camera reads as nobody acting (2026-11-23): the camera goes round to the face
    for (const c of subjects) if (c.root && (opt.faces ?? true)) { const hc = headBox(c).getCenter(new THREE.Vector3()), fwd = new THREE.Vector3(0, 0, 1).applyQuaternion(c.root.quaternion); fwd.y = 0;
      if (fwd.lengthSq() > 1e-4 && fwd.normalize().dot(camera.position.clone().sub(hc).setY(0).normalize()) < -0.15) out.push(`${c.label} has their back to the camera`); }
    out.push(...collisions(people, props));
    return [...new Set(out)];
  }
  // people standing inside furniture step back (away from what they hit), a little at a time, before anything is shot
  // people standing inside furniture step clear, checked at every given moment of the Short (a lean or a new pose
  // later on must not walk them back into a desk; 2026-11-23 a pose at 7 s put a buyer through his desk)
  function separate(people, props, poseAt, moments = [0]) {
    const moved = [];
    for (const c of people) {
      for (let n = 0; n < 60; n++) {
        let hit = null, cb = null;
        for (const t of moments) { poseAt(t); cb = coreBox(c); hit = props.find(q => !q.floor && !q.walk && cb.intersectsBox(q.box)); if (hit) break; }
        if (!hit) break;
        // step out along the shallower overlap (x or z), away from the piece's centre
        const ox = Math.min(cb.max.x, hit.box.max.x) - Math.max(cb.min.x, hit.box.min.x), oz = Math.min(cb.max.z, hit.box.max.z) - Math.max(cb.min.z, hit.box.min.z);
        const qc = hit.box.getCenter(new THREE.Vector3()), pc = cb.getCenter(new THREE.Vector3());
        if (ox < oz) c.spot.x += 0.02 * (Math.sign(pc.x - qc.x) || 1); else c.spot.z += 0.02 * (Math.sign(pc.z - qc.z) || -1);
        if (n === 0) moved.push(`${c.label} stepped clear of ${hit.label}`);
      }
    }
    return moved;
  }
  return { blocked, SAFE, CAP, hide, shownBox, personBox, headBox, faceBox, coreBox, rect, setCam, fit, issues, separate, dirOf, within, shows };
}
