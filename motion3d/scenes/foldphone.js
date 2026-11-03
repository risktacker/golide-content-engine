// A book-style foldable phone (two halves on a hinge, one inner screen across both, a camera
// island on the back), to real proportions. Motion: it turns to show the back and the camera,
// then folds shut and snaps, then opens again.
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { drift, inOut, orbit, screenTexture, smooth, snap, span, wallpaper } from "./common.js";

export const DURATION = 8;
const HW = 0.72, H = 1.55, T = 0.045;   // one half: 7.2 x 15.5 cm, 4.5 mm thick (open)

export function build(THREE, scene) {
  const frame = new THREE.MeshStandardMaterial({ color: 0xc9b89a, metalness: 0.95, roughness: 0.28 });
  const glass = new THREE.MeshStandardMaterial({ color: 0x202226, metalness: 0.3, roughness: 0.18 });
  const lens = new THREE.MeshStandardMaterial({ color: 0x050608, metalness: 0.4, roughness: 0.05 });
  const root = new THREE.Group(); scene.add(root);
  const tex = screenTexture(THREE, wallpaper, 1024, 1100);

  // Each half folds around its own inner edge on the screen side (a pivot), so when shut the
  // two screens face each other with a hair of gap and the backs stay outside: nothing merges.
  const GAP = 0.004;
  const half = (side) => {
    const pivot = new THREE.Group();
    pivot.position.set(side * GAP, T / 2, 0);
    const g = new THREE.Group(); g.position.set(0, -T / 2, 0); pivot.add(g);
    const body = new THREE.Mesh(new RoundedBoxGeometry(HW, T, H, 4, 0.02), frame);
    body.position.set(side * HW / 2, 0, 0); g.add(body);
    const back = new THREE.Mesh(new RoundedBoxGeometry(HW * 0.96, 0.004, H * 0.98, 2, 0.015), glass);
    back.position.set(side * HW / 2, -T / 2 - 0.001, 0); g.add(back);
    // the inner screen: each half shows its half of one wallpaper, only on the screen side
    const s = new THREE.Mesh(new THREE.PlaneGeometry(HW * 0.98, H * 0.97),
      new THREE.MeshBasicMaterial({ map: tex.clone(), side: THREE.FrontSide }));
    s.material.map.repeat.set(0.5, 1); s.material.map.offset.set(side > 0 ? 0.5 : 0, 0); s.material.map.needsUpdate = true;
    s.rotation.x = -Math.PI / 2; s.position.set(side * HW / 2, T / 2 + 0.001, 0); g.add(s);
    pivot.userData.inner = g;
    return pivot;
  };
  const left = half(-1), right = half(1);
  // camera island on the back of the right half
  const island = new THREE.Mesh(new RoundedBoxGeometry(0.34, 0.03, 0.5, 3, 0.05), glass);
  island.position.set(HW * 0.68, -T / 2 - 0.015, -H * 0.33); right.userData.inner.add(island);
  for (const [x, z] of [[0.6, -0.42], [0.6, -0.26], [0.76, -0.34]]) {
    const l = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.055, 0.04, 32), lens);
    l.position.set(HW * x, -T / 2 - 0.03, H * z * 0.82); right.userData.inner.add(l);
  }
  const hingeBar = new THREE.Mesh(new THREE.CylinderGeometry(T * 0.55, T * 0.55, H * 0.98, 24), frame);
  hingeBar.rotation.x = Math.PI / 2; hingeBar.position.y = 0; root.add(hingeBar);
  root.add(left, right);
  root.position.y = 0.6;
  root.userData = { left, right };
  return root;
}

export function pose(t, root, camera, THREE) {
  // fold: flat to shut (each half turns 90 degrees about its own edge), hits shut, bounces a
  // touch and settles; opens again after. Never past 90: the halves cannot pass through.
  const shut = snap(span(t, 4.2, 5.4)) * (1 - inOut(span(t, 6.4, 7.6)));
  const a = shut * Math.PI / 2;
  root.userData.left.rotation.z = -a;
  root.userData.right.rotation.z = a;
  // free movement: it floats across the frame, turns over to show the back and the camera,
  // tilts on every axis, then faces the camera for the fold
  root.rotation.x = -0.35 + Math.PI * smooth(span(t, 0.8, 2.4)) - Math.PI * smooth(span(t, 2.8, 3.9)) + 0.08 * drift(t, 1);
  root.rotation.y = 0.5 * drift(t * 0.7, 2);
  root.rotation.z = 0.18 * drift(t, 3);
  root.position.set(0.7 * drift(t * 0.6, 4), 0.75 + 0.18 * drift(t, 5), 0.4 * drift(t, 6));
  orbit(camera, new THREE.Vector3(root.position.x * 0.75, root.position.y, root.position.z * 0.6), 0.3 + 0.12 * drift(t, 7), 0.45 + 0.05 * drift(t, 8),
        3.9 - 0.4 * smooth(span(t, 3.6, 4.6)));
}
