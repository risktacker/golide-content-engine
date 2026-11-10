// node icons.js specs.json  -> writes each spec's png
const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
const RB = '/tmp/claude-0/-home-claude/8d1d9704-a447-57ad-8375-b80b30d6e36f/scratchpad/rb';
(async () => {
  const specs = JSON.parse(fs.readFileSync(process.argv[2]));
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: 1600, height: 1000 } });
  p.on('pageerror', (e) => console.log('pageerror:', e.message));
  await p.route('**/*', (route) => { const u = new URL(route.request().url()).pathname;
    const f = u.startsWith('/three/') ? path.join(RB, 'node_modules', u) : path.join(__dirname, 'site', u);
    if (!fs.existsSync(f)) return route.fulfill({ status: 404, body: '' }); route.fulfill({ path: f, contentType: f.endsWith('.js') ? 'text/javascript' : undefined }); });
  await p.goto('http://th.test/icons.html'); await p.waitForFunction('window.ready === true');
  for (const s of specs) { const d = await p.evaluate((s) => window.draw(s), s); fs.writeFileSync(s.out, Buffer.from(d.split(',')[1], 'base64')); }
  await b.close(); console.log('ok', specs.length);
})();
