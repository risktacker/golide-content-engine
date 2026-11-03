// A sports car built to real proportions (about 4.5 m long, 1.9 m wide, 1.2 m high), with a
// shaped body, glass cabin, four wheels with rims and tyres, headlights and tail lights.
// Actions (owner 2026-11-03: "you say a car can fly, it actually leaves the ground"):
//   drive  - rolls forward, wheels turning with the distance travelled, body settling on its springs
//   liftoff- slows, sinks on its springs, then leaves the ground nose-up, the shadow shrinking
//   fly    - flies on, banking into a gentle turn
import { drift, inOut, orbit, smooth, span } from "./common.js";

export const DURATION = 8;
const L = 4.5, WD = 1.9, WHEEL_R = 0.36;

export function build(THREE, scene) {
  const paint = new THREE.MeshPhysicalMaterial({ color: 0xb3121b, metalness: 0.6, roughness: 0.28,
    clearcoat: 1, clearcoatRoughness: 0.05 });
  const glass = new THREE.MeshPhysicalMaterial({ color: 0x0b1018, metalness: 0.1, roughness: 0.05,
    transmission: 0, opacity: 0.92, transparent: true });
  const tyre = new THREE.MeshStandardMaterial({ color: 0x111113, roughness: 0.9 });
  const rimMat = new THREE.MeshStandardMaterial({ color: 0xc8ccd2, metalness: 1, roughness: 0.2 });
  const lightMat = new THREE.MeshBasicMaterial({ color: 0xfff4d6 });
  const tailMat = new THREE.MeshBasicMaterial({ color: 0xff2a2a });
  const dark = new THREE.MeshStandardMaterial({ color: 0x0c0c0e, roughness: 0.7 });

  const root = new THREE.Group(); scene.add(root);
  const body = new THREE.Group(); root.add(body);   // sits on the springs

  // body: a side profile extruded across the width, then the cabin on top
  const side = new THREE.Shape();
  side.moveTo(-L / 2, 0.28);
  side.lineTo(-L / 2, 0.62); side.quadraticCurveTo(-L / 2 + 0.1, 0.78, -L / 2 + 0.6, 0.8);
  side.lineTo(L / 2 - 0.5, 0.78); side.quadraticCurveTo(L / 2, 0.72, L / 2, 0.5);
  side.lineTo(L / 2, 0.28); side.lineTo(-L / 2, 0.28);
  const bodyGeo = new THREE.ExtrudeGeometry(side, { depth: WD, bevelEnabled: true, bevelSize: 0.06,
    bevelThickness: 0.08, bevelSegments: 6, curveSegments: 24 });
  bodyGeo.translate(0, 0, -WD / 2);
  body.add(new THREE.Mesh(bodyGeo, paint));
  const cab = new THREE.Shape();
  cab.moveTo(-1.3, 0.8); cab.quadraticCurveTo(-1.05, 1.22, -0.45, 1.25);
  cab.lineTo(0.35, 1.24); cab.quadraticCurveTo(0.85, 1.2, 1.15, 0.8); cab.lineTo(-1.3, 0.8);
  const cabGeo = new THREE.ExtrudeGeometry(cab, { depth: WD * 0.82, bevelEnabled: true, bevelSize: 0.05,
    bevelThickness: 0.06, bevelSegments: 5, curveSegments: 20 });
  cabGeo.translate(0, 0, -WD * 0.41);
  body.add(new THREE.Mesh(cabGeo, glass));
  // roof panel in body colour over the glass
  const roof = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.04, WD * 0.78), paint);
  roof.position.set(-0.15, 1.27, 0); body.add(roof);
  // lights
  for (const z of [-0.65, 0.65]) {
    const h = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.07, 0.38), lightMat);
    h.position.set(L / 2 + 0.05, 0.6, z); body.add(h);
    const tl = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.06, 0.5), tailMat);
    tl.position.set(-L / 2 - 0.05, 0.64, z); body.add(tl);
  }
  const grille = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.12, 0.9), dark);
  grille.position.set(L / 2 + 0.05, 0.4, 0); body.add(grille);
  // underside (seen when it flies over)
  const under = new THREE.Mesh(new THREE.BoxGeometry(L * 0.92, 0.04, WD * 0.9), dark);
  under.position.y = 0.26; body.add(under);

  // wheels: tyre + rim with 5 spokes, so turning is visible
  const wheels = [];
  for (const x of [-1.45, 1.45]) for (const z of [-WD / 2 + 0.05, WD / 2 - 0.05]) {
    const w = new THREE.Group(); w.position.set(x, WHEEL_R, z);
    const t = new THREE.Mesh(new THREE.TorusGeometry(WHEEL_R - 0.09, 0.11, 18, 40), tyre);
    w.add(t);
    const disc = new THREE.Mesh(new THREE.CylinderGeometry(WHEEL_R - 0.12, WHEEL_R - 0.12, 0.08, 32), rimMat);
    disc.rotation.x = Math.PI / 2; w.add(disc);
    for (let s = 0; s < 5; s++) {
      const spoke = new THREE.Mesh(new THREE.BoxGeometry(0.05, WHEEL_R * 1.2, 0.1), dark);
      spoke.rotation.z = (s / 5) * Math.PI * 2; spoke.position.z = z > 0 ? 0.05 : -0.05; w.add(spoke);
    }
    root.add(w); wheels.push(w);
  }
  root.userData = { body, wheels };
  root.scale.setScalar(0.62);
  return root;
}

// Where the car is and how it sits at time t (the actions, in order).
export function pose(t, root, camera, THREE) {
  const { body, wheels } = root.userData;
  // drive 0-3.2 s: accelerate, cruise; travelled distance drives the wheel spin
  const v = 1.6;                                        // units per second at cruise (scaled)
  const driveT = Math.min(t, 3.2);
  let x = -3.2 + v * (driveT - 0.4 * (1 - Math.exp(-driveT / 0.4)) * 0.4);
  // liftoff 3.2-4.4 s: sink on the springs, then rise nose-up
  const sink = Math.sin(Math.PI * span(t, 3.2, 3.7)) * 0.05;
  const rise = smooth(span(t, 3.6, 5.2));
  const fly = span(t, 4.4, 8);
  x += v * 0.8 * Math.max(0, t - 3.2) + 1.2 * fly * fly;
  const height = rise * 1.6 + fly * 0.6;
  root.position.set(x, height, 0.6 * Math.sin(fly * 1.4));
  body.position.y = -sink + 0.012 * Math.sin(t * 13) * (1 - rise);           // road buzz until airborne
  root.rotation.z = 0.22 * Math.sin(Math.PI * span(t, 3.6, 5.6)) - 0.04 * fly; // nose up as it climbs
  root.rotation.x = -0.18 * Math.sin(Math.PI * fly);                          // banks into the turn
  root.rotation.y = -0.35 * smooth(fly);
  // wheels turn with the ground speed while on the road, then slow down in the air
  const wheelSpin = (x + 3.2) / (WHEEL_R * 0.62) * (1 - 0.7 * rise);
  for (const w of wheels) w.rotation.z = -wheelSpin;
  // camera: low and close at the road, tracking, then pulling back and up as it flies
  const target = new THREE.Vector3(x * 0.85, 0.4 + height * 0.8, 0);
  orbit(camera, target, 0.55 + 0.25 * smooth(span(t, 3.4, 6)) + 0.05 * drift(t, 3),
        0.12 + 0.28 * smooth(span(t, 3.6, 6.5)), 5.2 + 2.2 * smooth(span(t, 3.8, 7)));
}
