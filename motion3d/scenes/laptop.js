// A laptop, built to real proportions (14-inch class: 31 x 22 cm, 1.5 cm thick), with a hinged lid,
// keyboard, trackpad, ports, rubber feet and vents underneath, so every side is real.
// Motion: a full orbit (front, side, back, from below), then the lid closes and snaps shut.
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { drift, inOut, orbit, screenTexture, smooth, snap, span, wallpaper } from "./common.js";

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
  well.position.set(0, BASE + 0.028, -D * 0.12); root.add(well);
  const keyGeo = new RoundedBoxGeometry(0.17, 0.012, 0.15, 2, 0.006);
  for (let r = 0; r < 6; r++) for (let c = 0; c < 14; c++) {
    const k = new THREE.Mesh(keyGeo, keyMat);
    k.position.set(-W * 0.4 + c * 0.191, BASE + 0.034 - 0.012, -D * 0.31 + r * 0.157); root.add(k);
  }
  const pad = new THREE.Mesh(new RoundedBoxGeometry(1.25, 0.006, 0.78, 2, 0.04),
    new THREE.MeshStandardMaterial({ color: 0x8d9096, metalness: 0.6, roughness: 0.25 }));
  pad.position.set(0, BASE + 0.029, D * 0.27); root.add(pad);
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
  const hinge = new THREE.Group(); hinge.position.set(0, BASE + 0.034, -D / 2 + 0.02); root.add(hinge);
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
  // lid: open at 110 degrees; closes 5.2 to 6.6 s, hits shut, bounces up a touch and settles
  const close = snap(span(t, 5.2, 6.6));
  root.userData.hinge.rotation.x = -THREE.MathUtils.degToRad(110) * (1 - close);
  // the laptop itself moves freely: it drifts across the frame, tilts and turns on all axes,
  // rolling over to show its underside, never locked to one straight axis
  const turn = inOut(span(t, 0.2, 4.8));
  root.rotation.y = -0.5 + turn * Math.PI * 2 + 0.15 * drift(t, 1);
  root.rotation.x = -0.9 * Math.sin(Math.PI * span(t, 2.4, 4.4)) + 0.06 * drift(t, 2);
  root.rotation.z = 0.12 * drift(t, 3) * (1 - smooth(span(t, 4.8, 5.4)));
  root.position.set(0.9 * drift(t * 0.8, 4), 0.35 + 0.25 * drift(t, 5) + 0.6 * Math.sin(Math.PI * span(t, 2.4, 4.4)),
                    0.5 * drift(t, 6));
  // the camera breathes a little too, then settles in for the close
  const dist = 7.4 - 1.5 * smooth(span(t, 4.8, 6.0));
  // the camera keeps the laptop in frame wherever it drifts (it trails a little, like a hand)
  orbit(camera, new THREE.Vector3(root.position.x * 0.75, root.position.y + 0.45, root.position.z * 0.6),
        0.15 * drift(t, 7), 0.36 + 0.05 * drift(t, 8), dist + 0.6);
}
