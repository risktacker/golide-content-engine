const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const RB = __dirname, SITE = RB + '/site';
(async () => {
  const mode = process.argv[2]; // "stills" t1,t2.. | "video" seconds
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  p.on('console', (m) => { if (m.type() === 'error') console.log('page:', m.text()); });
  p.on('pageerror', (e) => console.log('pageerror:', e.message));
  await p.route('**/*', (route) => {
    const u = new URL(route.request().url()).pathname;
    let f = u.startsWith('/three/') ? path.join(RB, 'node_modules', u) : u.startsWith('/fonts/') ? '/home/claude/golide-content-engine/app' + u : path.join(SITE, u === '/' ? 'index.html' : u);
    if (!fs.existsSync(f)) return route.fulfill({ status: 404, body: '' });
    route.fulfill({ path: f, contentType: f.endsWith('.js') ? 'text/javascript' : undefined });
  });
  await p.goto('http://rb.test/');
  await p.waitForFunction('window.ready === true', null, { timeout: 120000 });
  await p.evaluate(() => document.fonts.ready);
  const out = RB + '/frames'; fs.mkdirSync(out, { recursive: true });
  const times = mode === 'stills' ? process.argv[3].split(',').map(Number) : [...Array(Math.round(Number(process.argv[3]) * 30)).keys()].map((i) => i / 30);
  for (let i = 0; i < times.length; i++) {
    const data = await p.evaluate((t) => window.renderAt(t), times[i]);
    fs.writeFileSync(`${out}/${mode === 'stills' ? 's' : 'f'}${String(i).padStart(4, '0')}.jpg`, Buffer.from(data.split(',')[1], 'base64'));
  }
  await b.close(); console.log('done', times.length);
})();
