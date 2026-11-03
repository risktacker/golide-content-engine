// A laptop, built to real proportions (14-inch class: 31 x 22 cm, 1.5 cm thick), with a hinged lid,
// keyboard, trackpad, ports, rubber feet and vents underneath, so every side is real.
// Motion: a full orbit (front, side, back, from below), then the lid closes and snaps shut.
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { inOut, orbit, screenTexture, smooth, snap, span, wallpaper } from "./common.js";

export const DURATION = 9;
const W = 3.1, D = 2.2, BASE = 0.09, LID = 0.06;

export function build(THREE, scene) {
  const alu = new THREE.MeshStandardMaterial({ color: 0x9a9da3, metalness: 0.95, roughness: 0.32 });
  const dark = new THREE.MeshStandardMaterial({ color: 0x15161a, metalness: 0.2, roughness: 0.6 });
  const keyMat = new THREE.MeshStandardMaterial({ color: 0x0c0c0e, roughness: 0.75 });
  const root = new THREE.Group(); scene.add(root);

  const base = new THREE.Mesh(new RoundedBoxGeometry(W, BASE, D, 4, 0.06), alu);
  base.position.y = BASE / 2 + 0.03; root.add(base);
  // keyboard: 6 rows of keys in a recessed well
  const well = new THREE.Mesh(new THREE.BoxGeometry(W * 0.86, 0.005, D * 0.42), dark);
  well.position.set(0, BASE + 0.033, -D * 0.12); root.add(well);
  const keyGeo = new RoundedBoxGeometry(0.17, 0.02, 0.15, 2, 0.02);
  for (let r = 0; r < 6; r++) for (let c = 0; c < 14; c++) {
    const k = new THREE.Mesh(keyGeo, keyMat);
    k.position.set(-W * 0.4 + c * 0.191, BASE + 0.04, -D * 0.31 + r * 0.157); root.add(k);
  }
  const pad = new THREE.Mesh(new RoundedBoxGeometry(1.25, 0.006, 0.78, 2, 0.04),
    new THREE.MeshStandardMaterial({ color: 0x8d9096, metalness: 0.6, roughness: 0.25 }));
  pad.position.set(0, BASE + 0.032, D * 0.27); root.add(pad);
  // ports on the left and right edges
  for (const [x, z] of [[-W / 2, -0.4], [-W / 2, -0.15], [W / 2, -0.3]]) {
    const p = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.03, 0.12), dark);
    p.position.set(x, BASE / 2 + 0.03, z); root.add(p);
  }
  // underside: four rubber feet and two vent strips
  for (const x of [-1.3, 1.3]) for (const z of [-0.9, 0.9]) {
    const f = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 0.03, 20), dark);
    f.position.set(x, 0.015, z); root.add(f);
  }
  for (const x of [-0.9, 0.9]) {
    const v = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.004, 0.05), dark);
    v.position.set(x, 0.029, -0.95); root.add(v);
  }

  // lid: pivots on the back edge of the base
  const hinge = new THREE.Group(); hinge.position.set(0, BASE + 0.03, -D / 2 + 0.02); root.add(hinge);
  const lid = new THREE.Mesh(new RoundedBoxGeometry(W, LID, D, 4, 0.05), alu);
  lid.position.set(0, LID / 2, D / 2 - 0.02); hinge.add(lid);
  const screen = new THREE.Mesh(new THREE.PlaneGeometry(W * 0.92, D * 0.86),
    new THREE.MeshBasicMaterial({ map: screenTexture(THREE, wallpaper) }));
  screen.rotation.x = Math.PI / 2; screen.position.set(0, -0.001, D / 2 - 0.02); hinge.add(screen);
  const bezel = new THREE.Mesh(new THREE.PlaneGeometry(W * 0.98, D * 0.95), new THREE.MeshBasicMaterial({ color: 0x050505 }));
  bezel.rotation.x = Math.PI / 2; bezel.position.set(0, -0.0005, D / 2 - 0.02); hinge.add(bezel);
  root.userData.hinge = hinge;
  return root;
}

export function pose(t, root, camera, THREE) {
  // lid: open at 110 degrees, closes 5.2 to 6.4 s with a snap, then a short pause
  const close = snap(span(t, 5.2, 6.4));
  const open = THREE.MathUtils.degToRad(110);
  root.userData.hinge.rotation.x = -(open * (1 - close));
  // camera: one full turn around (back at ~2.5 s), dipping below to show the underside
  const turn = inOut(span(t, 0.2, 4.8));
  const yaw = -0.5 + turn * Math.PI * 2;
  const pitch = 0.42 - 0.62 * Math.sin(Math.PI * span(t, 2.4, 4.4)) + 0.15 * smooth(span(t, 5, 6));
  const dist = 7.6 - 1.4 * smooth(span(t, 4.8, 6.0));
  orbit(camera, new THREE.Vector3(0, 0.55 - 0.3 * smooth(span(t, 5, 6.2)), 0), yaw, pitch, dist);
}
