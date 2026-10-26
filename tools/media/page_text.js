// Preload for tools/canvas/render.js (node --require): before the screenshot, dump the rendered
// page text (innerText) and markup without data: URIs to $SPECTIO_PAGE_TEXT, so shots.py can fail
// on any forbidden term that is visible. Does not modify render.js.
const fs = require('fs'), path = require('path');
const pw = require(require.resolve('playwright', { paths: [path.resolve(__dirname, '../canvas'), process.cwd()] }));
const launch = pw.chromium.launch.bind(pw.chromium);
pw.chromium.launch = async (...a) => {
  const b = await launch(...a);
  const newPage = b.newPage.bind(b);
  b.newPage = async (...x) => {
    const p = await newPage(...x);
    const shot = p.screenshot.bind(p);
    p.screenshot = async (o) => {
      const t = await p.evaluate(() => document.body.innerText + '\n' + document.body.innerHTML.replace(/data:[^"')]+/g, ''));
      fs.writeFileSync(process.env.SPECTIO_PAGE_TEXT, t);
      return shot(o);
    };
    return p;
  };
  return b;
};
