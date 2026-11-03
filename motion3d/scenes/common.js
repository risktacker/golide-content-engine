// Shared motion helpers: easing that feels physical (a snap settles, it does not stop dead).
export const clamp01 = (x) => Math.min(1, Math.max(0, x));
export const smooth = (x) => { x = clamp01(x); return x * x * (3 - 2 * x); };
export const inOut = (x) => { x = clamp01(x); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
// Fast at the end with a small overshoot and settle: a lid or a fold that snaps shut.
export const snap = (x) => {
  x = clamp01(x);
  const c = 2.2;
  return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2);
};
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
