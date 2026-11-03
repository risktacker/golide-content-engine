import { createRequire } from "node:module";
const { chromium } = createRequire(import.meta.url)("playwright");
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
const here = path.dirname(fileURLToPath(import.meta.url));
const [scene, outPrefix, ...times] = process.argv.slice(2);
const browser = await chromium.launch({ args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
page.on("pageerror", (e) => console.error("page error:", e.message));
page.on("console", (m) => { if (m.type() === "error") console.error("page:", m.text()); });
await page.route("http://golide.3d/**", async (route) => {
  const rel = decodeURIComponent(new URL(route.request().url()).pathname).replace(/^\//, "");
  const type = rel.endsWith(".js") ? "text/javascript" : "text/html";
  try { route.fulfill({ body: await readFile(path.join(here, rel)), contentType: type }); } catch { route.fulfill({ status: 404, body: "" }); }
});
await page.goto(`http://golide.3d/stage.html?scene=${scene}`);
await page.waitForFunction(() => window.READY === true, null, { timeout: 60000 });
const canvas = await page.$("canvas");
for (const t of times) { await page.evaluate((x) => window.renderAt(x), +t); await canvas.screenshot({ path: `${outPrefix}-${t}.png` }); }
await browser.close();
