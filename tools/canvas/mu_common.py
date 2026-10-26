# Shared pieces for the multi-user boards.
HEAD = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>@@TITLE@@</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@600;700&amp;family=Inter:wght@400;500;600&amp;family=JetBrains+Mono:wght@400&amp;display=swap" rel="stylesheet">
<style>
body{margin:0}
main > *{flex-shrink:0}
a{color:#6344B2}a:hover{color:#4D368B}
.st-tab{height:36px;padding:0 10px;border-radius:9px;display:flex;align-items:center;gap:6px;font-size:13px;text-decoration:none;white-space:nowrap}
.st-tab:hover{color:#0F1020}
.chip{display:inline-flex;align-items:center;gap:5px;height:24px;padding:0 8px;border-radius:7px;font-size:12px;font-weight:600;white-space:nowrap}
.btn{height:40px;padding:0 14px;border-radius:11px;border:none;font:600 13.5px 'Inter',sans-serif;display:inline-flex;align-items:center;gap:8px;cursor:pointer;text-decoration:none;white-space:nowrap}
.btn-p{background:#7750D4;color:#FFFFFF}
.btn-s{background:#FFFFFF;color:#22253A;box-shadow:inset 0 0 0 1px #DFE1EA}
.tbl{width:100%;border-collapse:collapse;font-size:13.5px}
.tbl th{text-align:left;font-size:12.5px;font-weight:600;color:#33364A;background:#F7F7FB;padding:10px 14px}
.tbl td{padding:11px 14px;border-top:1px solid #EEEFF5;vertical-align:middle}
.card{border-radius:16px;box-shadow:0 0 0 1px rgba(15,16,32,0.11);background:#FFFFFF}
.sel{height:34px;padding:0 30px 0 10px;border-radius:9px;border:1px solid #C4C7D4;background:#FFFFFF;font:500 13px 'Inter',sans-serif;color:#0F1020}
@@CSS@@
</style>
</helmet>
'''
SHELL_OPEN = '''<div style="width: 100%; height: 100vh; min-height: 760px; box-sizing: border-box; background: #FFFFFF; color: #0F1020; font-family: 'Inter', system-ui, sans-serif; display: grid; grid-template-rows: auto minmax(0, 1fr); grid-template-columns: auto minmax(0, 1fr);">
  <div style="grid-column: 1 / 3;"><dc-import name="AppTopbar" crumbs="@@CRUMBS@@" project="@@PROJECT@@" hint-size="100%,76px"></dc-import></div>
  <div style="min-height: 0; display: flex; flex-direction: column;"><dc-import name="AppSidebar" active="@@ACTIVE@@" hint-size="276px,100%" style="display: block; flex: 1 1 auto; min-height: 0;"></dc-import></div>
  <main style="min-height: 0; overflow: auto; min-width: 0; padding: 8px 24px 32px 14px; box-sizing: border-box; display: flex; flex-direction: column; gap: 16px;">
'''
SHELL_CLOSE = '''  </main>
</div>
'''
SETTINGS_HEAD = '''    <div style="display: flex; align-items: center; gap: 16px; flex-wrap: wrap;">
      <span style="width: 48px; height: 48px; border-radius: 15px; background: #F1F2F6; color: #4D5065; display: flex; align-items: center; justify-content: center;">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 6h10 M18 6h2 M16 4v4 M4 12h4 M12 12h8 M10 10v4 M4 18h12 M18 16v4"/></svg>
      </span>
      <div style="flex-grow: 1; display: flex; flex-direction: column; gap: 2px;">
        <h1 style="margin: 0; font-family: 'Outfit', sans-serif; font-weight: 600; font-size: 28px;">Settings</h1>
        <span style="font-size: 14px; color: #4D5065;">Server-wide configuration · changes are logged with who made them</span>
      </div>
    </div>
    <nav aria-label="Settings sections" style="align-self: flex-start; display: flex; gap: 2px; padding: 3px; border-radius: 12px; background: #EEEFF5; flex-wrap: wrap;">
      <sc-for list="{{tabs}}" as="t" hint-placeholder-count="9">
        <a href="{{t.href}}" class="st-tab" aria-current="{{t.cur}}" style="background: {{t.bg}}; box-shadow: {{t.sh}}; color: {{t.c}}; font-weight: {{t.w}};"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="{{t.icon}}"/></svg>{{t.label}}<span style="font-size: 10.5px; font-weight: 600; color: #6E7287;">{{t.tag}}</span></a>
      </sc-for>
    </nav>
'''
TABS_JS = '''  const tabDefs = [
    ['General', '#', 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z M3 12h2 M19 12h2 M12 3v2 M12 19v2', ''],
    ['Projects', 'Projects.dc.html', 'M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z', ''],
    ['Users & groups', 'SettingsUsers.dc.html', 'M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M2 21a7 7 0 0 1 14 0 M17 11a3 3 0 1 0 0-6 M22 21a6 6 0 0 0-4-5.6', ''],
    ['Service accounts', 'SettingsServiceAccounts.dc.html', 'M9 7V3 M15 7V3 M6 7h12v4a6 6 0 0 1-12 0z M12 17v4', ''],
    ['Tokens', 'Profile.dc.html', 'M15 7a4 4 0 1 1-3.9 5H3v3h3v3h3v-3h2.1A4 4 0 0 1 15 7z', ''],
    ['AI & agents', 'AIAgents.dc.html', 'M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z', ''],
    ['Webhooks', '#', 'M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1 M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1', ''],
    ['Notifications', '#', 'M6 8a6 6 0 1 1 12 0c0 7 3 8 3 8H3s3-1 3-8 M10 20a2 2 0 0 0 4 0', ''],
    ['Branding', '#', 'M12 3a9 9 0 1 0 0 18c1 0 1.5-.8 1.5-1.5 0-1-.8-1.3-.8-2.2 0-.8.7-1.3 1.5-1.3H17a4 4 0 0 0 4-4c0-5-4-9-9-9z', '']
  ];
  const tabs = tabDefs.map(([label, href, icon, tag]) => { const on = label === ACTIVE_TAB; return { label, href, icon, tag, cur: on ? 'page' : 'false', bg: on ? '#FFFFFF' : 'transparent', sh: on ? '0 1px 2px rgba(15,16,32,0.12)' : 'none', c: on ? '#0F1020' : '#4D5065', w: on ? 600 : 500 }; });
'''
PRINCIPAL_JS = '''  const P = {
    person: (t, bg) => ({ kind: 'person', t, tbg: bg || '#8B5CF6', tfg: '#FFFFFF', rad: '50%' }),
    group: (t) => ({ kind: 'group', t, tbg: '#EEF6FA', tfg: '#1F536D', rad: '9px' }),
    service: (t) => ({ kind: 'service', t, tbg: '#EEEFF5', tfg: '#33364A', rad: '9px' }),
    agent: () => ({ kind: 'agent', t: 'AI', tbg: '#7750D4', tfg: '#FFFFFF', rad: '9px' })
  };
  const VIS = { private: ['Private', '#F1F2F6', '#33364A', 'M6 11h12v9H6z M8 11V8a4 4 0 0 1 8 0v3'], group: ['Group', '#EEF6FA', '#1F536D', 'M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M2 21a7 7 0 0 1 14 0 M17 11a3 3 0 1 0 0-6 M22 21a6 6 0 0 0-4-5.6'], instance: ['Everyone', '#E8F6EF', '#157A4B', 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z M3 12h18 M12 3c3 3 3 15 0 18 M12 3c-3 3-3 15 0 18'] };
  const vis = (k) => ({ vl: VIS[k][0], vbg: VIS[k][1], vfg: VIS[k][2], vic: VIS[k][3] });
  const ROLE = { owner: ['Owner', '#F6F2FE', '#4D368B'], editor: ['Editor', '#F2F1FB', '#423B97'], reviewer: ['Reviewer', '#FDF3E2', '#8F5806'], launcher: ['Launcher', '#FDF2F5', '#A54666'], viewer: ['Viewer', '#F1F2F6', '#33364A'] };
  const role = (k) => ({ rl: ROLE[k][0], rbg: ROLE[k][1], rfg: ROLE[k][2] });
'''
def build(title, crumbs, project, active, body, js, css=''):
    s = HEAD.replace('@@TITLE@@', title).replace('@@CSS@@', css)
    shell = SHELL_OPEN.replace('@@CRUMBS@@', crumbs).replace('@@PROJECT@@', project).replace('@@ACTIVE@@', active)
    return s + shell + body + SHELL_CLOSE + '</x-dc>\n<script type="text/x-dc" data-dc-script data-props=\'{"$preview":{"width":1440,"height":1180}}\'>\nclass Component extends DCLogic {\nrenderVals() {\n' + js + '\n}\n}\n</script>\n</body>\n</html>\n'
