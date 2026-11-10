// usage: node sockshot.js <socket> <linkToken> <outPrefix> <path> [clickText]
const { chromium } = require('playwright'); const http = require('http');
const [sock, token, out, path, click] = process.argv.slice(2);
async function relay(route) {
  const r = route.request(); const u = new URL(r.url()); const all = await r.allHeaders();
  return new Promise((res) => {
    const h = { ...all }; for (const k of Object.keys(h)) if (k.startsWith(':')) delete h[k]; delete h['accept-encoding']; h.host = u.host;
    if (r.isNavigationRequest()) console.error('NAV', u.pathname, JSON.stringify(Object.keys(h)), (h.cookie||'').length);
    const q = http.request({ socketPath: sock, path: u.pathname + u.search, method: r.method(), headers: h }, (rs) => {
      const b = []; rs.on('data', (c) => b.push(c)); rs.on('end', () => {
        const hh = {}; for (const [k, v] of Object.entries(rs.headers)) hh[k] = Array.isArray(v) ? v.join('\n') : v;
        route.fulfill({ status: rs.statusCode, headers: hh, body: Buffer.concat(b) }).then(res, res); }); });
    q.on('error', () => route.abort().then(res, res)); const pd = r.postDataBuffer(); if (pd) q.write(pd); q.end();
  });
}
(async () => {
  const b = await chromium.launch();
  for (const [w, hgt, tag] of [[1440, 1100, 'desk'], [390, 1600, 'phone']]) {
    const c = await b.newContext({ viewport: { width: w, height: hgt }, deviceScaleFactor: 2 });
    await c.route('http://127.0.0.1:8791/**', relay);
    const p = await c.newPage();
    const [cn, cv] = token.split('='); await c.addCookies([{ name: cn, value: cv, url: 'http://127.0.0.1:8791' }]);
    await p.goto('http://127.0.0.1:8791' + path); await p.waitForTimeout(3000);
    if (click) { await p.getByText(click).first().click().catch(() => {}); await p.waitForTimeout(6000); }
    await p.screenshot({ path: `${out}-${tag}.png`, fullPage: tag === 'phone' });
    await c.close();
  }
  await b.close();
})();
