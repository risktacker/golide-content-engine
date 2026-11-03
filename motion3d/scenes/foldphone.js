// A book-style foldable phone (two halves on a hinge, one inner screen across both, a camera
// island on the back), to real proportions. Motion: it turns to show the back and the camera,
// then folds shut and snaps, then opens again.
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { inOut, orbit, screenTexture, smooth, snap, span, wallpaper } from "./common.js";

export const DURATION = 8;
const HW = 0.72, H = 1.55, T = 0.045;   // one half: 7.2 x 15.5 cm, 4.5 mm thick (open)

export function build(THREE, scene) {
  const frame = new THREE.MeshStandardMaterial({ color: 0xc9b89a, metalness: 0.95, roughness: 0.28 });
  const glass = new THREE.MeshStandardMaterial({ color: 0x202226, metalness: 0.3, roughness: 0.18 });
  const lens = new THREE.MeshStandardMaterial({ color: 0x050608, metalness: 0.4, roughness: 0.05 });
  const root = new THREE.Group(); scene.add(root);
  const tex = screenTexture(THREE, wallpaper, 1024, 1100);

  const half = (side) => {
    const g = new THREE.Group();
    const body = new THREE.Mesh(new RoundedBoxGeometry(HW, T, H, 4, 0.02), frame);
    body.position.set(side * HW / 2, 0, 0); g.add(body);
    const back = new THREE.Mesh(new RoundedBoxGeometry(HW * 0.96, 0.004, H * 0.98, 2, 0.015), glass);
    back.position.set(side * HW / 2, -T / 2, 0); g.add(back);
    // the inner screen: each half shows its half of one wallpaper
    const s = new THREE.Mesh(new THREE.PlaneGeometry(HW * 0.98, H * 0.97), new THREE.MeshBasicMaterial({ map: tex.clone() }));
    s.material.map.repeat.set(0.5, 1); s.material.map.offset.set(side > 0 ? 0.5 : 0, 0); s.material.map.needsUpdate = true;
    s.rotation.x = -Math.PI / 2; s.position.set(side * HW / 2, T / 2 + 0.001, 0); g.add(s);
    return g;
  };
  const left = half(-1), right = half(1);
  // camera island on the back of the right half
  const island = new THREE.Mesh(new RoundedBoxGeometry(0.34, 0.03, 0.5, 3, 0.05), glass);
  island.position.set(HW * 0.68, -T / 2 - 0.015, -H * 0.33); right.add(island);
  for (const [x, z] of [[0.6, -0.42], [0.6, -0.26], [0.76, -0.34]]) {
    const l = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.055, 0.04, 32), lens);
    l.position.set(HW * x / 0.72 * 0.72, -T / 2 - 0.03, H * z / 1.55 * 1.55 * 0.82); right.add(l);
  }
  const hingeBar = new THREE.Mesh(new THREE.CylinderGeometry(T * 0.6, T * 0.6, H * 0.98, 24), frame);
  hingeBar.rotation.x = Math.PI / 2; root.add(hingeBar);
  root.add(left, right);
  root.position.y = 0.6;
  root.userData = { left, right };
  return root;
}

export function pose(t, root, camera, THREE) {
  // fold: flat (0) to shut (each half 90 degrees up), snapping at the end; opens again after
  const shut = snap(span(t, 4.2, 5.2)) * (1 - inOut(span(t, 6.4, 7.6)));
  const a = shut * Math.PI / 2;
  root.userData.left.rotation.z = -a;
  root.userData.right.rotation.z = a;
  // the whole phone turns over to show its back, then stands for the fold
  root.rotation.x = -0.35 + Math.PI * smooth(span(t, 0.8, 2.4)) - Math.PI * smooth(span(t, 2.8, 3.9));
  root.rotation.y = 0.5 * Math.sin(t * 0.6);
  orbit(camera, new THREE.Vector3(0, 0.6, 0), 0.35 + 0.25 * smooth(span(t, 3.5, 5)), 0.5, 3.7 - 0.5 * smooth(span(t, 3.6, 4.6)));
}
