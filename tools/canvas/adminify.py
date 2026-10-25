"""Wrap a former Settings board into the Administration skeleton (AdminNav + CLI equivalent)."""
import re, sys
path, active, section, cli = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
s = open(path).read()
HEADER = '''<div style="display: flex; align-items: center; gap: 16px; flex-wrap: wrap;">
      <span style="width: 48px; height: 48px; border-radius: 15px; background: #F1F2F6; color: #4D5065; display: flex; align-items: center; justify-content: center;">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/></svg>
      </span>
      <div style="flex-grow: 1; display: flex; flex-direction: column; gap: 2px;">
        <h1 style="margin: 0; font-family: 'Outfit', sans-serif; font-weight: 600; font-size: 28px;">Administration</h1>
        <span style="font-size: 14px; color: #4D5065;">People, content, activity and the health of this instance</span>
      </div>
    </div>
    <div style="display: flex; gap: 28px; align-items: flex-start;">
      <div style="position: sticky; top: 0; flex-shrink: 0;"><dc-import name="AdminNav" active="%s" hint-size="208px,860px"></dc-import></div>
      <div style="flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 16px;">''' % active
pat = re.compile(r'<div style="display: flex; align-items: center; gap: 16px; flex-wrap: wrap;">.*?</nav>', re.S)
assert pat.search(s), 'header not found'
s = pat.sub(lambda m: HEADER, s, count=1)
lines = cli.split('\\n')
term = '\n'.join(lines)
CLI = '''        <details class="cli-eq">
          <summary><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 17l6-6-6-6 M12 19h8"/></svg>CLI equivalent<span style="font-weight: 500; color: #6E7287; font-size: 12.5px;">same API, same permissions</span></summary>
          <pre class="term">%s</pre>
        </details>
      </div>
    </div>
  </main>''' % term
idx = s.rfind('</main>')
s = s[:idx] + CLI.replace('  </main>', '') + s[idx:]
css = '''.cli-eq{border-radius:14px;box-shadow:0 0 0 1px rgba(15,16,32,0.11);background:#FFFFFF}
.cli-eq summary{list-style:none;cursor:pointer;display:flex;align-items:center;gap:10px;padding:12px 14px;font-size:14px;font-weight:600;color:#22253A}
.cli-eq summary::-webkit-details-marker{display:none}
.cli-eq .term{margin:0 12px 12px;padding:14px 16px;border-radius:11px;background:#0F1020;color:#E4E6F0;font:400 12.5px/1.7 'JetBrains Mono',ui-monospace,monospace;white-space:pre-wrap}
.term .c{color:#8C90A6}
'''
s = s.replace('</style>', css + '</style>', 1)
if 'JetBrains+Mono' not in s:
    s = s.replace('family=Inter:wght@400;500;600', 'family=Inter:wght@400;500;600&amp;family=JetBrains+Mono:wght@400', 1)
s = re.sub(r'crumbs="Settings / [^"]*"', 'crumbs="Administration / %s"' % section, s)
open(path, 'w').write(s)
print('ok', path)
