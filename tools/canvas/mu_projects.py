import sys; sys.path.insert(0, 'tools')
from mu_common import *
body = SETTINGS_HEAD + '''
    <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
      <div style="flex-grow: 1; display: flex; flex-direction: column; gap: 2px;">
        <h2 style="margin: 0; font-family: 'Outfit', sans-serif; font-weight: 600; font-size: 21px;">Projects</h2>
        <span style="font-size: 13.5px; color: #4D5065;">A project owns runs, workflows and webhooks. It belongs to one group and is shared with people, groups or service accounts.</span>
      </div>
      <a href="#" class="btn btn-p"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14 M5 12h14"/></svg>New project</a>
    </div>

    <div role="toolbar" aria-label="Project filters" style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
      <label style="display: flex; align-items: center; gap: 8px; height: 40px; padding: 0 12px; border-radius: 11px; box-shadow: inset 0 0 0 1px #DFE1EA; flex: 1 1 260px; color: #6E7287;">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14z M20 20l-4-4"/></svg>
        <input type="search" placeholder="Search projects or groups" aria-label="Search projects" style="border: none; outline: none; font: inherit; font-size: 13.5px; color: #0F1020; flex-grow: 1; min-width: 0; background: transparent;">
      </label>
      <div role="group" aria-label="Scope" style="display: flex; padding: 3px; border-radius: 12px; background: #EEEFF5;">
        <sc-for list="{{scopes}}" as="sc" hint-placeholder-count="3">
          <span style="height: 34px; padding: 0 12px; border-radius: 9px; display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: {{sc.w}}; background: {{sc.bg}}; box-shadow: {{sc.sh}}; color: {{sc.c}};">{{sc.t}}<span style="font-weight: 500; color: #6E7287;">{{sc.n}}</span></span>
        </sc-for>
      </div>
      <a href="#" class="btn btn-s">Group: owning group ▾</a>
    </div>

    <div class="card" style="overflow-x: auto;">
      <table class="tbl" style="min-width: 980px;">
        <thead><tr><th>Project</th><th>Owning group</th><th>Visibility</th><th>My role</th><th>Runs</th><th>Last activity</th><th>Members</th></tr></thead>
        <tbody>
          <sc-for list="{{projects}}" as="p" hint-placeholder-count="6">
            <tr>
              <td><a href="ProjectDetail.dc.html" style="text-decoration: none; color: inherit; display: flex; align-items: center; gap: 10px;"><span style="width: 10px; height: 10px; border-radius: 3px; background: {{p.dot}}; flex-shrink: 0;"></span><span style="display: flex; flex-direction: column;"><span style="font-weight: 600;">{{p.name}}</span><span style="font-size: 12px; color: #6E7287;">{{p.desc}}</span></span></a></td>
              <td><span style="display: flex; align-items: center; gap: 8px;"><span style="width: 26px; height: 26px; border-radius: 8px; background: #EEF6FA; color: #1F536D; display: flex; align-items: center; justify-content: center;"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M2 21a7 7 0 0 1 14 0 M17 11a3 3 0 1 0 0-6 M22 21a6 6 0 0 0-4-5.6"/></svg></span>{{p.group}}</span></td>
              <td><span class="chip" style="background: {{p.vbg}}; color: {{p.vfg}};"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="{{p.vic}}"/></svg>{{p.vl}}</span></td>
              <td><span class="chip" style="background: {{p.rbg}}; color: {{p.rfg}};">{{p.rl}}</span></td>
              <td style="color: #33364A;">{{p.runs}}</td>
              <td style="color: #33364A; white-space: nowrap;">{{p.last}}</td>
              <td><span style="display: flex; align-items: center;"><sc-for list="{{p.members}}" as="m" hint-placeholder-count="3"><span title="{{m.name}}" style="width: 28px; height: 28px; margin-left: -6px; border-radius: 14px; box-shadow: 0 0 0 2px #FFFFFF; background: {{m.bg}}; color: #FFFFFF; font-size: 10.5px; font-weight: 600; display: flex; align-items: center; justify-content: center;">{{m.t}}</span></sc-for><span style="margin-left: 6px; font-size: 12px; color: #6E7287;">{{p.more}}</span></span></td>
            </tr>
          </sc-for>
        </tbody>
      </table>
    </div>
    <span style="font-size: 12.5px; color: #4D5065;">In single-user mode there is one project, “default”, and this page only shows it. Projects map one-to-one to depictio projects when both apps share a server.</span>
'''
js = "  const ACTIVE_TAB = 'Projects';\n" + TABS_JS + PRINCIPAL_JS + '''  const av = (t, bg, name) => ({ t, bg, name });
  const A = { TW: av('TW', '#8B5CF6', 'Thomas Weber'), AS: av('AS', '#2F7FA8', 'Anna Smith'), LM: av('LM', '#EC5F87', 'Luca Moretti'), KB: av('KB', '#A54666', 'Kai Berg'), NO: av('NO', '#5A4FCF', 'Nora Olsen') };
  const proj = (name, desc, dot, group, v, r, runs, last, members, more) => ({ name, desc, dot, group, ...vis(v), ...role(r), runs, last, members, more });
  const scope = (t, n, on) => ({ t, n, w: on ? 600 : 500, bg: on ? '#FFFFFF' : 'transparent', sh: on ? '0 1px 2px rgba(15,16,32,0.12)' : 'none', c: on ? '#0F1020' : '#4D5065' });
  return {
    tabs,
    scopes: [scope('All I can see', '6', true), scope('Mine', '3'), scope('Shared with me', '3')],
    projects: [
      proj('Liver time course', 'bulk RNA-seq · nf-core/rnaseq', '#7750D4', 'rnaseq-core', 'group', 'owner', '41', 'today 10:12', [A.TW, A.AS, A.KB], '+2'),
      proj('Drug screen 2026', 'Cell Painting plates · cellpose-segmentation', '#2F7FA8', 'imaging-core', 'private', 'reviewer', '96', 'today 09:21', [A.LM, A.TW, A.NO], '+4'),
      proj('Rare disease trios', 'WGS trios · nf-core/sarek, raredisease', '#EC5F87', 'clinical-genomics', 'private', 'launcher', '18', 'yesterday', [A.KB, A.TW], ''),
      proj('PBMC atlas', 'single-cell · nf-core/scrnaseq', '#5A4FCF', 'rnaseq-core', 'instance', 'editor', '12', '3 days ago', [A.AS, A.NO, A.TW], '+1'),
      proj('Soil metagenomes', 'nf-core/mag, taxprofiler', '#A54666', 'microbiome-lab', 'group', 'viewer', '27', 'last week', [A.NO, A.LM], ''),
      proj('Pipeline CI', 'test profiles for every release', '#4D5065', 'bioinfo-platform', 'private', 'owner', '210', 'today 06:00', [A.TW], '+ CI')
    ]
  };'''
open('spectio-ui/project/Projects.dc.html', 'w').write(build('Spectio — projects', 'Settings / Projects', 'rnaseq-core / Liver time course', 'settings', body, js))
print('ok')
