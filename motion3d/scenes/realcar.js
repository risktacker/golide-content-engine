// A real car model (glTF file), not hand-built. Actions: drive (wheels turn with the distance),
// lift off (sinks on its springs, then rises nose-up, shadow shrinking), fly (banks into a turn).
// Model: three.js example "ferrari.glb" (for this prototype only; production uses licence-clear
// or generated models).
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { drift, orbit, smooth, span } from "./common.js";

export const DURATION = 8;

export async function build(THREE, scene) {
  const draco = new DRACOLoader();
  draco.setDecoderPath("./node_modules/three/examples/jsm/libs/draco/gltf/");
  const loader = new GLTFLoader(); loader.setDRACOLoader(draco);
  const gltf = await loader.loadAsync("./models/ferrari.glb");
  const car = gltf.scene.children[0];
  const paint = new THREE.MeshPhysicalMaterial({ color: 0xb3121b, metalness: 1, roughness: 0.42,
    clearcoat: 1, clearcoatRoughness: 0.03 });
  const detail = new THREE.MeshStandardMaterial({ color: 0xffffff, metalness: 1, roughness: 0.4 });
  const glass = new THREE.MeshPhysicalMaterial({ color: 0xffffff, metalness: 0.25, roughness: 0, transmission: 1 });
  car.getObjectByName("body").material = paint;
  for (const n of ["rim_fl", "rim_fr", "rim_rr", "rim_rl"]) { const o = car.getObjectByName(n); if (o) o.material = detail; }
  const g = car.getObjectByName("glass"); if (g) g.material = glass;
  // a road, so leaving the ground reads: dark asphalt, edge lines and dashed centre line
  const road = new THREE.Group();
  const asphalt = new THREE.Mesh(new THREE.PlaneGeometry(6, 140),
    new THREE.MeshStandardMaterial({ color: 0x1b1d21, roughness: 0.95 }));
  asphalt.rotation.x = -Math.PI / 2; asphalt.position.set(0, 0.001, 30); asphalt.receiveShadow = true; road.add(asphalt);
  const paintLine = new THREE.MeshStandardMaterial({ color: 0xd8d8d0, roughness: 0.6 });
  for (const x of [-2.8, 2.8]) {
    const e = new THREE.Mesh(new THREE.PlaneGeometry(0.12, 140), paintLine);
    e.rotation.x = -Math.PI / 2; e.position.set(x, 0.002, 30); road.add(e);
  }
  for (let z = -40; z < 100; z += 4) {
    const d = new THREE.Mesh(new THREE.PlaneGeometry(0.14, 2), new THREE.MeshStandardMaterial({ color: 0xe9c46a, roughness: 0.6 }));
    d.rotation.x = -Math.PI / 2; d.position.set(0, 0.002, z); road.add(d);
  }
  scene.add(road);
  const root = new THREE.Group(); root.add(car); scene.add(root);
  // centre the model on its own middle so the camera frames the whole car
  const box = new THREE.Box3().setFromObject(car), mid = box.getCenter(new THREE.Vector3());
  car.position.x -= mid.x; car.position.z -= mid.z;
  root.userData = {
    car,
    wheels: ["wheel_fl", "wheel_fr", "wheel_rl", "wheel_rr"].map((n) => car.getObjectByName(n)).filter(Boolean),
  };
  return root;
}

export function pose(t, root, camera, THREE) {
  const { car, wheels } = root.userData;
  // drive 0-3.2 s along the road (the model faces +z), wheels turning with the distance
  const v = 3.2;
  const roadT = Math.min(t, 3.4);
  const rise = smooth(span(t, 3.5, 5.3));
  const fly = span(t, 4.4, 8);
  const z = -6 + v * roadT + v * 1.1 * Math.max(0, t - 3.4) + 2.5 * fly * fly;
  const sink = Math.sin(Math.PI * span(t, 3.1, 3.6)) * 0.06;
  const height = rise * 2.2 + fly * 0.8;
  root.position.set(1.4 * Math.sin(fly * 1.3), height - sink, z);
  root.rotation.x = 0.25 * Math.sin(Math.PI * span(t, 3.5, 5.6)) - 0.04 * fly;    // nose up as it climbs
  root.rotation.z = 0.2 * Math.sin(Math.PI * fly);                                 // banks into the turn
  root.rotation.y = 0.4 * smooth(fly);
  car.position.y = 0.008 * Math.sin(t * 17) * (1 - rise);                          // road buzz until airborne
  const spin = (z + 6) / 0.33 * (1 - 0.8 * rise);
  for (const w of wheels) w.rotation.x = spin;
  // camera: low beside the road, tracking; pulls back and up as it takes off
  const target = new THREE.Vector3(root.position.x, 0.55 + height * 0.9, z);
  orbit(camera, target, 1.05 - 0.55 * smooth(span(t, 3.2, 6.5)) + 0.04 * drift(t, 3),
        0.12 + 0.3 * smooth(span(t, 3.6, 6.8)), 8.5 + 2.5 * smooth(span(t, 3.8, 7.5)));
}
