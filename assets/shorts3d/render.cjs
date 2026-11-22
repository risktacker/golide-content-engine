// GOLIDE 3D Shorts runner (in place of the engine's own render.cjs, which it follows): serves the engine folder, opens
// index.html?viewer=1&golide=<scene>, runs the director (report.json) and renders.
//   node render.cjs <engineDir> <scene> <outDir> <w> <h> <fps> stills <t1,t2,...> [debug]
//   node render.cjs <engineDir> <scene> <outDir> <w> <h> <fps> video <part> <parts>     -> <outDir>/part-<part>.mp4
// A shot the director cannot repair stops here with exit code 3 (report.json says why); nothing is rendered past it.
const http = require('http'), fs = require('fs'), path = require('path'), { spawn } = require('child_process');
const [, , ENG, SCENE, OUT, w = '1080', h = '1920', fps = '30', mode = 'stills', a = '', b = ''] = process.argv;
const puppeteer = require(path.join(path.resolve(ENG), 'node_modules', 'puppeteer-core'));
const ROOT = path.resolve(ENG), TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json' };
const CHROME = process.env.CHROME || '/usr/bin/google-chrome';
(async () => {
  const srv = http.createServer((q, r) => { const f = path.join(ROOT, decodeURIComponent(q.url.split('?')[0])); if (!f.startsWith(ROOT) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { r.writeHead(404); return r.end(); }
    r.writeHead(200, { 'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream' }); fs.createReadStream(f).pipe(r); }).listen(0);
  // the engine's flags are for a Mac GPU; CHROME may be a wrapper adding software WebGL (see the workflow)
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, protocolTimeout: 0, args: ['--ignore-gpu-blocklist'] });
  const page = await browser.newPage(); const errors = [];
  page.on('pageerror', e => { errors.push(e.message); console.log('PAGE ERROR', e.message); });
  page.on('response', r => { if (r.status() >= 400 && !r.url().endsWith('favicon.ico')) console.log('HTTP', r.status(), r.url()); });
  await page.goto(`http://127.0.0.1:${srv.address().port}/index.html?w=${w}&h=${h}&look=c&style=ph&viewer=1&golide=${SCENE}`);
  await page.waitForFunction('window.GOLIDE && window.GOLIDE.ready || window.__err', { timeout: 300000 }).catch(e => { throw new Error('the scene never got ready: ' + (errors.join(' | ') || e.message)); });
  fs.mkdirSync(OUT, { recursive: true });
  const report = await page.evaluate(() => window.GOLIDE.direct());
  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 1));
  for (const s of report.shots) console.log(`${s.ok ? 'OK  ' : 'FAIL'} ${s.name} [${s.t0}-${s.t1}]` + (s.found.length ? `  found: ${s.found.join('; ')}` : '') + (s.repair ? `  repaired: ${JSON.stringify(s.repair)}` : '') + (s.still ? `  STILL: ${s.still.join('; ')}` : ''));
  for (const m of report.stepped) console.log('set:', m);
  const dur = await page.evaluate(() => window.GOLIDE.dur);
  if (mode === 'stills') {
    const ts = a ? a.split(',').map(Number) : (await page.evaluate(() => window.GOLIDE.shots)).flatMap(s => [s.t0 + 0.05, (s.t0 + s.t1) / 2, s.t1 - 0.05]);
    for (const t of ts) { const d = await page.evaluate((t, dbg) => window.GOLIDE.frame(t, dbg), t, b === 'debug'); fs.writeFileSync(path.join(OUT, `still-${t.toFixed(2)}.jpg`), Buffer.from(d.split(',')[1], 'base64')); }
    console.log(`${ts.length} stills -> ${OUT}`);
  }
  if (!report.ok) { await browser.close(); srv.close(); console.error('director: a shot could not be repaired; see report.json'); process.exit(3); }
  if (mode === 'video') {
    const n = Math.round(dur * +fps), part = +a || 0, parts = +b || 1, f0 = Math.floor(n * part / parts), f1 = Math.floor(n * (part + 1) / parts), t0 = Date.now();
    const out = path.join(OUT, `part-${part}.mp4`);
    const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', fps, '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-crf', '17', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', out]);
    const done = new Promise(r => ff.on('close', r));
    for (let f = f0; f < f1; f++) { const d = await page.evaluate(t => window.GOLIDE.frame(t), f / +fps); if (!ff.stdin.write(Buffer.from(d.split(',')[1], 'base64'))) await new Promise(r => ff.stdin.once('drain', r)); if ((f - f0) % 15 === 0) console.log(`part ${part}: ${f - f0}/${f1 - f0}`); }
    ff.stdin.end(); await done; console.log(`part ${part}: frames ${f0}-${f1 - 1} in ${((Date.now() - t0) / 1000).toFixed(0)}s -> ${out}`);
  }
  await browser.close(); srv.close();
})().catch(e => { console.error(e); process.exit(1); });
