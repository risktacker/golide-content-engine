// Renders one 3D scene to an MP4: node render.mjs <scene> <out.mp4> [w] [h] [fps]
// Each frame is drawn at an exact time (no real-time playback), so the result is the same every run.
import { createRequire } from "node:module";
const { chromium } = createRequire(import.meta.url)("playwright");
import { spawn } from "node:child_process";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const [scene, out, w = "1280", h = "720", fps = "30"] = process.argv.slice(2);
const browser = await chromium.launch({ args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
const page = await browser.newPage({ viewport: { width: +w, height: +h } });
page.on("console", (m) => { if (m.type() === "error") console.error("page:", m.text()); });
page.on("pageerror", (e) => console.error("page error:", e.message));
await page.route("http://golide.3d/**", async (route) => {
  const rel = decodeURIComponent(new URL(route.request().url()).pathname).replace(/^\//, "");
  const type = rel.endsWith(".js") ? "text/javascript" : rel.endsWith(".html") ? "text/html" : "application/octet-stream";
  try { route.fulfill({ body: await readFile(path.join(here, rel)), contentType: type }); }
  catch { route.fulfill({ status: 404, body: "" }); }
});
await page.goto(`http://golide.3d/stage.html?scene=${scene}&w=${w}&h=${h}`);
await page.waitForFunction(() => window.READY === true, null, { timeout: 60000 });
const duration = await page.evaluate(() => window.DURATION);
const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", fps, "-i", "-",
  "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", out], { stdio: ["pipe", "inherit", "inherit"] });
const canvas = await page.$("canvas");
const frames = Math.round(duration * +fps);
for (let i = 0; i < frames; i++) {
  await page.evaluate((t) => window.renderAt(t), i / +fps);
  ff.stdin.write(await canvas.screenshot({ type: "jpeg", quality: 92 }));
}
ff.stdin.end();
await new Promise((r) => ff.on("close", r));
await browser.close();
console.log(JSON.stringify({ scene, out, frames }));
