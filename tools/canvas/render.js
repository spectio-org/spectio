// Local approximation of the design-canvas runtime: sc-for / sc-if / {{expr}} / dc-import.
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const [,, file, W, H, out, ...extra] = process.argv;
const dir = path.dirname(file);
const blobs = { // asset urls → local files
  '/_blob/636203cdee0bc09b61efe0fa351e239b': 'logos/logo-nextflow.png',
  '/_blob/b04c0e1634ffbccff3a43d65ce1316d4': 'logos/logo-nf-core.png',
  '/_blob/7a35665829f51132cb3bcb9a4c3e638c': 'logos/logo-snakemake.png',
};
const scratch = path.resolve(dir, '../..');
const toData = p => 'data:image/png;base64,' + fs.readFileSync(path.join(scratch, p)).toString('base64');
function prep(src) {
  const x = src.match(/<x-dc>([\s\S]*?)<\/x-dc>/)[1];
  const helmet = (x.match(/<helmet>([\s\S]*?)<\/helmet>/) || [,''])[1];
  let tpl = x.replace(/<helmet>[\s\S]*?<\/helmet>/, '');
  tpl = tpl.replace(/<sc-for\b/g, '<template data-for').replace(/<\/sc-for>/g, '</template>')
           .replace(/<sc-if\b/g, '<template data-if').replace(/<\/sc-if>/g, '</template>');
  const script = (src.match(/<script type="text\/x-dc"[^>]*>([\s\S]*?)<\/script>/) || [,''])[1];
  return { helmet, tpl, script };
}
const comps = {};
for (const f of fs.readdirSync(dir)) if (f.endsWith('.dc.html')) comps[f.replace('.dc.html','')] = prep(fs.readFileSync(path.join(dir, f), 'utf8'));
let main = comps[path.basename(file).replace('.dc.html','')];
const blobMap = {}; for (const [k,v] of Object.entries(blobs)) { try { blobMap[k] = toData(v); } catch(e){} }
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: +W, height: +H } });
  await p.setContent('<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0"></body></html>');
  const err = await p.evaluate(({ comps, mainName, blobMap }) => {
    const usedHelmet = new Set();
    const ev = (expr, scope) => { try { return Function(...Object.keys(scope), 'return (' + expr + ')')(...Object.values(scope)); } catch (e) { return undefined; } };
    const interp = (s, scope) => s.replace(/\{\{([^}]+)\}\}/g, (_, e) => { const v = ev(e.trim(), scope); return v === undefined || v === null ? '' : String(v); });
    const one = (s, scope) => { const m = s.match(/^\{\{([^}]+)\}\}$/); return m ? ev(m[1].trim(), scope) : s; };
    function vals(name, props) {
      const c = comps[name]; if (!c) return {};
      class DCLogic { constructor() { this.props = props; } }
      try { const C = Function('DCLogic', c.script + ';return Component')(DCLogic); const o = new C(); o.props = props; return o.renderVals ? o.renderVals() : {}; } catch (e) { console.error(name, e.message); return {}; }
    }
    function render(node, scope) {
      for (const ch of [...node.childNodes]) {
        if (ch.nodeType === 3) { if (ch.nodeValue.includes('{{')) ch.nodeValue = interp(ch.nodeValue, scope); continue; }
        if (ch.nodeType !== 1) continue;
        if (ch.tagName === 'TEMPLATE' && ch.hasAttribute('data-for')) {
          const list = one(ch.getAttribute('list') || '', scope) || []; const as = ch.getAttribute('as') || 'item';
          const frag = document.createDocumentFragment();
          list.forEach((it, i) => { const c = ch.content.cloneNode(true); const wrap = document.createElement('div'); wrap.appendChild(c); render(wrap, { ...scope, [as]: it, $index: i }); while (wrap.firstChild) frag.appendChild(wrap.firstChild); });
          ch.replaceWith(frag); continue;
        }
        if (ch.tagName === 'TEMPLATE' && ch.hasAttribute('data-if')) {
          const v = one(ch.getAttribute('value') || '', scope);
          if (v) { const wrap = document.createElement('div'); wrap.appendChild(ch.content.cloneNode(true)); render(wrap, scope); const frag = document.createDocumentFragment(); while (wrap.firstChild) frag.appendChild(wrap.firstChild); ch.replaceWith(frag); } else ch.remove();
          continue;
        }
        for (const a of [...ch.attributes]) if (a.value.includes('{{')) ch.setAttribute(a.name, interp(a.value, scope));
        if (ch.tagName === 'IMG' && blobMap[ch.getAttribute('src')]) ch.setAttribute('src', blobMap[ch.getAttribute('src')]);
        if (ch.tagName === 'DC-IMPORT') {
          const name = ch.getAttribute('name'); const props = {};
          for (const a of ch.attributes) if (!['name', 'hint-size', 'style'].includes(a.name)) props[a.name] = a.value;
          const host = document.createElement('div'); host.setAttribute('style', ch.getAttribute('style') || '');
          host.innerHTML = mount(name, props); ch.replaceWith(host); continue;
        }
        render(ch, scope);
      }
    }
    function mount(name, props) {
      const c = comps[name]; if (!c) return '<div>missing ' + name + '</div>';
      if (!usedHelmet.has(name)) { usedHelmet.add(name); const h = document.createElement('div'); h.innerHTML = c.helmet; for (const n of [...h.childNodes]) document.head.appendChild(n); }
      const wrap = document.createElement('div'); wrap.innerHTML = c.tpl; render(wrap, vals(name, props)); 
      if (wrap.children.length === 1) { const only = wrap.firstElementChild; if (!only.style.height && props.__fill) only.style.height = '100%'; }
      return wrap.innerHTML;
    }
    document.body.innerHTML = mount(mainName, {});
    return 'ok';
  }, { comps, mainName: path.basename(file).replace('.dc.html',''), blobMap });
  await p.waitForTimeout(1500);
  for (const sel of extra) { await p.click(sel).catch(()=>{}); await p.waitForTimeout(300); }
  await p.screenshot({ path: out, fullPage: false });
  await b.close(); console.log(err, out);
})();
