// Shared motion helpers: easing that feels physical (a snap settles, it does not stop dead).
export const clamp01 = (x) => Math.min(1, Math.max(0, x));
export const smooth = (x) => { x = clamp01(x); return x * x * (3 - 2 * x); };
export const inOut = (x) => { x = clamp01(x); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
// A real snap shut: it accelerates into the stop, hits it, bounces back a little and settles.
// Never goes past 1 (a lid or a fold cannot pass through the body it closes on).
export const snap = (x) => {
  x = clamp01(x);
  const hit = 0.62;                       // reaches the stop 62% of the way through
  if (x < hit) { const u = x / hit; return u * u * u; }
  const u = (x - hit) / (1 - hit);        // then a damped rebound below 1
  return 1 - 0.09 * Math.sin(Math.PI * u) * Math.exp(-2.2 * u);
};
// Free, unforced drift: several slow waves added together, so the motion never runs straight
// along one axis (owner 2026-11-03: "it has to move free in the screen").
export const drift = (t, seed = 0) =>
  Math.sin(t * 0.47 + seed) * 0.6 + Math.sin(t * 0.83 + seed * 2.1) * 0.3 + Math.sin(t * 1.31 + seed * 3.7) * 0.1;
export const span = (t, a, b) => clamp01((t - a) / (b - a));
// Camera on a sphere around a target: yaw (around), pitch (up/down, negative = from below).
export function orbit(camera, target, yaw, pitch, dist) {
  camera.position.set(
    target.x + dist * Math.cos(pitch) * Math.sin(yaw),
    target.y + dist * Math.sin(pitch),
    target.z + dist * Math.cos(pitch) * Math.cos(yaw));
  camera.lookAt(target);
}
export function screenTexture(THREE, draw, w = 1024, h = 640) {
  const c = document.createElement("canvas"); c.width = w; c.height = h;
  draw(c.getContext("2d"), w, h);
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
  return tex;
}
export function wallpaper(g, w, h) {
  const grad = g.createLinearGradient(0, 0, w, h);
  grad.addColorStop(0, "#1b3a8f"); grad.addColorStop(0.5, "#7b2bb5"); grad.addColorStop(1, "#f08a3c");
  g.fillStyle = grad; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 7; i++) {
    g.strokeStyle = `rgba(255,255,255,${0.05 + i * 0.02})`; g.lineWidth = 18;
    g.beginPath(); g.moveTo(-50, h * (0.2 + i * 0.12));
    g.bezierCurveTo(w * 0.3, h * (0.05 + i * 0.1), w * 0.6, h * (0.6 + i * 0.05), w + 50, h * (0.3 + i * 0.1));
    g.stroke();
  }
}
