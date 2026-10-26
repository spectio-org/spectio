import sys; sys.path.insert(0, 'tools')
from mu_common import *
import importlib.util
spec = importlib.util.spec_from_file_location('pd', 'tools/mu_projectdetail.py')
src = open('tools/mu_projectdetail.py').read()
PROJECT_HEADER = src.split("PROJECT_HEADER = '''")[1].split("'''")[0]
body = PROJECT_HEADER + '''
    <div style="display: flex; flex-direction: column; gap: 10px;">
      <div class="card" style="height: 64px; background: #F7F7FB;"></div><div class="card" style="height: 64px; background: #F7F7FB;"></div><div class="card" style="height: 64px; background: #F7F7FB;"></div>
    </div>
'''
overlay = '''  <div style="position: absolute; inset: 0; z-index: 5; background: rgba(15,16,32,0.42); display: flex; align-items: flex-start; justify-content: center; padding-top: 96px;">
    <section role="dialog" aria-modal="true" aria-labelledby="share-title" style="width: 600px; max-width: calc(100% - 32px); border-radius: 22px; background: #FFFFFF; box-shadow: 0 30px 80px -30px rgba(15,16,32,0.55); display: flex; flex-direction: column;">
      <div style="padding: 18px 20px 10px; display: flex; align-items: center; gap: 12px;">
        <div style="flex-grow: 1; display: flex; flex-direction: column; gap: 2px;"><h2 id="share-title" style="margin: 0; font-family: 'Outfit', sans-serif; font-weight: 600; font-size: 21px;">Share “Liver time course”</h2><span style="font-size: 13px; color: #4D5065;">People and groups get the role you pick; service accounts are added from Settings.</span></div>
        <button type="button" aria-label="Close" style="width: 40px; height: 40px; border: none; border-radius: 12px; background: transparent; color: #33364A; cursor: pointer;"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12 M18 6L6 18"/></svg></button>
      </div>
      <div style="padding: 6px 20px 14px; display: flex; flex-direction: column; gap: 8px;">
        <div style="display: flex; gap: 8px;">
          <label style="flex-grow: 1; display: flex; align-items: center; gap: 8px; height: 42px; padding: 0 12px; border-radius: 11px; box-shadow: inset 0 0 0 2px #7750D4; color: #6E7287;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14z M20 20l-4-4"/></svg><input type="search" value="mor" aria-label="Add people or groups" style="border: none; outline: none; font: 14px 'Inter', sans-serif; color: #0F1020; flex-grow: 1; min-width: 0; background: transparent;"></label>
          <select class="sel" style="height: 42px;" aria-label="Role for new members"><option>Reviewer</option><option>Viewer</option><option>Launcher</option><option>Editor</option><option>Owner</option></select>
          <button type="button" class="btn btn-p" style="height: 42px;">Add</button>
        </div>
        <div role="listbox" aria-label="Suggestions" style="border-radius: 12px; box-shadow: 0 0 0 1px rgba(15,16,32,0.11), 0 12px 24px -16px rgba(15,16,32,0.3); overflow: hidden;">
          <sc-for list="{{sugg}}" as="s" hint-placeholder-count="2">
            <div role="option" aria-selected="{{s.sel}}" style="display: flex; align-items: center; gap: 10px; padding: 9px 12px; background: {{s.bg}};"><span style="width: 30px; height: 30px; border-radius: {{s.rad}}; background: {{s.tbg}}; color: {{s.tfg}}; font-size: 11px; font-weight: 700; display: flex; align-items: center; justify-content: center;">{{s.t}}</span><span style="flex-grow: 1; display: flex; flex-direction: column;"><span style="font-size: 13.5px; font-weight: 600;">{{s.name}}</span><span style="font-size: 12px; color: #6E7287;">{{s.sub}}</span></span><span style="font-size: 12px; color: #6E7287;">{{s.hint}}</span></div>
          </sc-for>
        </div>
      </div>
      <div style="padding: 12px 20px; border-top: 1px solid #EEEFF5; display: flex; flex-direction: column; gap: 8px;">
        <span style="font-size: 12px; font-weight: 600; letter-spacing: 0.05em; color: #6E7287;">WHO CAN SEE THIS PROJECT</span>
        <div role="radiogroup" aria-label="Visibility" style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px;">
          <label style="border-radius: 12px; padding: 10px 12px; box-shadow: 0 0 0 1px rgba(15,16,32,0.11); background: #FFFFFF; display: flex; flex-direction: column; gap: 4px; cursor: pointer;"><span style="display: flex; align-items: center; gap: 7px; font-size: 13.5px; font-weight: 600;"><input type="radio" name="vis" style="margin: 0; accent-color: #7750D4;">Private</span><span style="font-size: 12px; color: #4D5065; line-height: 1.4;">Only the people, groups and accounts listed below.</span></label>
          <label style="border-radius: 12px; padding: 10px 12px; box-shadow: inset 0 0 0 2px #7750D4; background: #FBF9FF; display: flex; flex-direction: column; gap: 4px; cursor: pointer;"><span style="display: flex; align-items: center; gap: 7px; font-size: 13.5px; font-weight: 600;"><input type="radio" name="vis" checked style="margin: 0; accent-color: #7750D4;">Group</span><span style="font-size: 12px; color: #4D5065; line-height: 1.4;">Everyone in rnaseq-core can view; roles above add more.</span></label>
          <label style="border-radius: 12px; padding: 10px 12px; box-shadow: 0 0 0 1px rgba(15,16,32,0.11); background: #FFFFFF; display: flex; flex-direction: column; gap: 4px; cursor: pointer;"><span style="display: flex; align-items: center; gap: 7px; font-size: 13.5px; font-weight: 600;"><input type="radio" name="vis" style="margin: 0; accent-color: #7750D4;">Everyone</span><span style="font-size: 12px; color: #4D5065; line-height: 1.4;">Anyone signed in on this server can view.</span></label>
        </div>
      </div>
      <div style="padding: 12px 20px; border-top: 1px solid #EEEFF5; display: flex; flex-direction: column; gap: 6px;">
        <span style="font-size: 12px; font-weight: 600; letter-spacing: 0.05em; color: #6E7287;">HAS ACCESS · 7</span>
        <sc-for list="{{access}}" as="a" hint-placeholder-count="4">
          <div style="display: flex; align-items: center; gap: 10px; padding: 5px 0;"><span style="width: 28px; height: 28px; border-radius: {{a.rad}}; background: {{a.tbg}}; color: {{a.tfg}}; font-size: 10.5px; font-weight: 700; display: flex; align-items: center; justify-content: center;">{{a.t}}</span><span style="flex-grow: 1; font-size: 13.5px;">{{a.name}}</span><span class="chip" style="background: {{a.rbg}}; color: {{a.rfg}};">{{a.rl}}</span></div>
        </sc-for>
        <a href="ProjectDetail.dc.html" style="font-size: 12.5px; font-weight: 600; text-decoration: none;">See all 7 in Members & roles →</a>
      </div>
      <div style="padding: 12px 20px 16px; border-top: 1px solid #EEEFF5; display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
        <span style="flex-grow: 1; display: flex; align-items: center; gap: 8px; font-size: 12.5px; color: #4D5065; min-width: 0;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1 M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/></svg><code style="font-family: 'JetBrains Mono', monospace; font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">spectio.lab.example/p/liver-time-course</code></span>
        <button type="button" class="btn btn-s">Copy link</button>
        <button type="button" class="btn btn-p">Done</button>
      </div>
    </section>
  </div>
'''
js = PRINCIPAL_JS + '''  const tabsP = [['Overview', ''], ['Members & roles', '7'], ['Environments', '2'], ['Webhooks', '1'], ['Service accounts', '2']];
  const ptabs = tabsP.map(([label, n], i) => ({ label, n, cur: i === 1 ? 'page' : 'false', c: i === 1 ? '#0F1020' : '#4D5065', w: i === 1 ? 600 : 500, u: i === 1 ? 'inset 0 -2px 0 #7750D4' : 'none' }));
  return {
    ptabs,
    sugg: [
      { ...P.person('LM', '#EC5F87'), name: 'Luca Moretti', sub: 'l.moretti@lab.example · imaging-core', hint: 'Person', sel: 'true', bg: '#F6F2FE' },
      { ...P.group('MO'), name: 'mouse-models', sub: 'Group · 9 members', hint: 'Group', sel: 'false', bg: '#FFFFFF' }
    ],
    access: [
      { ...P.person('TW'), name: 'Thomas Weber (you)', ...role('owner') },
      { ...P.group('RC'), name: 'rnaseq-core', ...role('viewer') },
      { ...P.person('AS', '#2F7FA8'), name: 'Anna Smith', ...role('reviewer') },
      { ...P.service('LB'), name: 'LabID (service account)', ...role('launcher') }
    ]
  };'''
html = build('Spectio — share project', 'Settings / Projects / Liver time course', 'rnaseq-core / Liver time course', 'settings', body, js)
html = html.replace('<div style="width: 100%; height: 100vh; min-height: 760px; box-sizing: border-box;', '<div style="position: relative; width: 100%; height: 100vh; min-height: 760px; box-sizing: border-box;', 1)
html = html.replace('  </main>\n</div>\n</x-dc>', '  </main>\n' + overlay + '</div>\n</x-dc>', 1)
open('spectio-ui/project/ShareDialog.dc.html', 'w').write(html)
print('ok')
