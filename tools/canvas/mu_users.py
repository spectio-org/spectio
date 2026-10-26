import sys; sys.path.insert(0, 'tools')
from mu_common import *
body = SETTINGS_HEAD + '''
    <div role="note" style="display: flex; align-items: center; gap: 14px; flex-wrap: wrap; border-radius: 14px; padding: 12px 14px 12px 16px; background: #EEF6FA; box-shadow: inset 4px 0 0 #2F7FA8;">
      <span style="width: 32px; height: 32px; border-radius: 10px; background: #FFFFFF; color: #2F7FA8; display: flex; align-items: center; justify-content: center; flex-shrink: 0;"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z M12 11v5 M12 8h.01"/></svg></span>
      <span style="flex: 1 1 360px; display: flex; flex-direction: column; gap: 2px; font-size: 13px; color: #173D50;"><strong style="font-size: 13.5px;">Single-user mode is on.</strong><span>Everything below already exists for one person. Turn on sign-in (OIDC, e.g. EMBL SSO or LS Login) to invite people; your local account is linked to your sign-in, nothing is migrated.</span></span>
      <a href="#" class="btn btn-p" style="background: #2F7FA8;">Set up sign-in</a>
      <button type="button" aria-label="Dismiss" style="width: 36px; height: 36px; border: none; border-radius: 10px; background: transparent; color: #1F536D; cursor: pointer;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12 M18 6L6 18"/></svg></button>
    </div>

    <section class="card" style="overflow: hidden;">
      <div style="padding: 14px 16px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
        <div style="flex-grow: 1; display: flex; flex-direction: column; gap: 2px;"><h2 style="margin: 0; font-size: 16px; font-weight: 600;">Users · 1</h2><span style="font-size: 12.5px; color: #4D5065;">People who can sign in. Roles on projects come from grants; “Admin” manages this server. Faded rows show what appears once sign-in is on.</span></div>
        <label style="display: flex; align-items: center; gap: 8px; height: 36px; padding: 0 10px; border-radius: 10px; box-shadow: inset 0 0 0 1px #DFE1EA; color: #6E7287; width: 240px;"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14z M20 20l-4-4"/></svg><input type="search" placeholder="Search users" aria-label="Search users" style="border: none; outline: none; font: inherit; font-size: 13px; background: transparent; min-width: 0; flex-grow: 1;"></label>
        <a href="#" class="btn btn-s">Invite people</a>
      </div>
      <div style="overflow-x: auto;">
        <table class="tbl" style="min-width: 900px;">
          <thead><tr><th>Name</th><th>Groups</th><th>Sign-in</th><th>Last seen</th><th>Server role</th></tr></thead>
          <tbody>
            <sc-for list="{{users}}" as="u" hint-placeholder-count="7">
              <tr style="opacity: {{u.op}};">
                <td><span style="display: flex; align-items: center; gap: 10px;"><span style="width: 32px; height: 32px; border-radius: 16px; background: {{u.bg}}; color: #FFFFFF; font-size: 11px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">{{u.t}}</span><span style="display: flex; flex-direction: column;"><span style="font-weight: 600;">{{u.name}}</span><span style="font-size: 12px; color: #6E7287;">{{u.email}}</span></span></span></td>
                <td><span style="display: flex; gap: 5px; flex-wrap: wrap;"><sc-for list="{{u.groups}}" as="g" hint-placeholder-count="2"><span class="chip" style="background: #EEF6FA; color: #1F536D;">{{g}}</span></sc-for></span></td>
                <td><span class="chip" style="background: {{u.abg}}; color: {{u.afg}};">{{u.auth}}</span></td>
                <td style="color: #33364A; white-space: nowrap;">{{u.seen}}</td>
                <td><span style="display: flex; gap: 6px; align-items: center;"><span class="chip" style="background: {{u.sbg}}; color: {{u.sfg}};">{{u.srole}}</span><span class="chip" style="background: transparent; color: #6E7287; box-shadow: inset 0 0 0 1px {{u.exr}};">{{u.ex}}</span></span></td>
              </tr>
            </sc-for>
          </tbody>
        </table>
      </div>
    </section>

    <section style="display: flex; flex-direction: column; gap: 10px;">
      <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
        <div style="flex-grow: 1; display: flex; flex-direction: column; gap: 2px;"><h2 style="margin: 0; font-size: 16px; font-weight: 600;">Groups · 1</h2><span style="font-size: 12.5px; color: #4D5065;">A lab, team or facility. Groups own projects and environments (clusters and their credentials).</span></div>
        <a href="#" class="btn btn-p"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14 M5 12h14"/></svg>Create group</a>
      </div>
      <div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px;">
        <sc-for list="{{groups}}" as="g" hint-placeholder-count="4">
          <a href="#" class="card" style="text-decoration: none; color: inherit; padding: 14px; display: flex; flex-direction: column; gap: 10px; opacity: {{g.op}};">
            <span style="display: flex; align-items: center; gap: 10px;"><span style="width: 36px; height: 36px; border-radius: 11px; background: #EEF6FA; color: #1F536D; display: flex; align-items: center; justify-content: center;"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M2 21a7 7 0 0 1 14 0 M17 11a3 3 0 1 0 0-6 M22 21a6 6 0 0 0-4-5.6"/></svg></span><span style="display: flex; flex-direction: column;"><span style="font-weight: 600; font-size: 14.5px;">{{g.name}}</span><span style="font-size: 12px; color: #6E7287;">{{g.admins}}</span></span></span>
            <span style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; border-top: 1px solid #EEEFF5; padding-top: 10px;">
              <span style="display: flex; flex-direction: column;"><span style="font-family: 'Outfit', sans-serif; font-weight: 600; font-size: 18px;">{{g.members}}</span><span style="font-size: 11.5px; color: #6E7287;">members</span></span>
              <span style="display: flex; flex-direction: column;"><span style="font-family: 'Outfit', sans-serif; font-weight: 600; font-size: 18px;">{{g.projects}}</span><span style="font-size: 11.5px; color: #6E7287;">projects</span></span>
              <span style="display: flex; flex-direction: column;"><span style="font-family: 'Outfit', sans-serif; font-weight: 600; font-size: 18px;">{{g.envs}}</span><span style="font-size: 11.5px; color: #6E7287;">environments</span></span>
            </span>
          </a>
        </sc-for>
      </div>
      <span style="font-size: 12.5px; color: #4D5065;">Users and groups are shared with depictio when both apps use the same identity provider; group membership can later be synced from the directory (SCIM).</span>
    </section>
'''
js = "  const ACTIVE_TAB = 'Users & groups';\n" + TABS_JS + '''  const AUTH = { oidc: ['OIDC · EMBL SSO', '#E8F6EF', '#157A4B'], ls: ['OIDC · LS Login', '#E8F6EF', '#157A4B'], local: ['Local account', '#F1F2F6', '#33364A'], invited: ['Invited', '#FDF3E2', '#8F5806'] };
  const SR = { admin: ['Admin', '#F6F2FE', '#4D368B'], user: ['User', '#F7F7FB', '#4D5065'] };
  const u = (t, bg, name, email, groups, a, seen, sr, real) => ({ t, bg, name, email, groups, op: real ? 1 : 0.5, ex: real ? '' : 'Example', exr: real ? 'transparent' : '#DFE1EA', auth: AUTH[a][0], abg: AUTH[a][1], afg: AUTH[a][2], seen, srole: SR[sr][0], sbg: SR[sr][1], sfg: SR[sr][2] });
  return {
    tabs,
    users: [
      u('TW', '#8B5CF6', 'Thomas Weber', 'local account · tweber', ['personal'], 'local', 'now', 'admin', true),
      u('AS', '#2F7FA8', 'Anna Smith', 'a.smith@lab.example', ['rnaseq-core'], 'oidc', 'today 09:40', 'user'),
      u('LM', '#EC5F87', 'Luca Moretti', 'l.moretti@lab.example', ['imaging-core'], 'oidc', 'today 08:12', 'user'),
      u('KB', '#A54666', 'Kai Berg', 'k.berg@lab.example', ['rnaseq-core', 'clinical-genomics'], 'oidc', 'yesterday', 'user'),
      u('NO', '#5A4FCF', 'Nora Olsen', 'n.olsen@lab.example', ['microbiome-lab'], 'oidc', '3 days ago', 'admin'),
      u('JD', '#1F9D63', 'Jo Dupont', 'j.dupont@partner.example', ['clinical-genomics'], 'ls', 'last week', 'user'),
      u('MR', '#9A9EB0', 'Mia Roth', 'm.roth@lab.example', ['imaging-core'], 'invited', '—', 'user')
    ],
    groups: [
      { name: 'personal', admins: 'created at first start · admin: TW', members: '1', projects: '1', envs: '2', op: 1 },
      { name: 'rnaseq-core', admins: 'Example · admins: TW, AS', members: '6', projects: '3', envs: '2', op: 0.5 },
      { name: 'imaging-core', admins: 'Example · admin: LM', members: '9', projects: '2', envs: '1', op: 0.5 },
      { name: 'clinical-genomics', admins: 'Example · admin: KB', members: '4', projects: '1', envs: '1', op: 0.5 }
    ]
  };'''
open('spectio-ui/project/SettingsUsers.dc.html', 'w').write(build('Spectio — users and groups', 'Settings / Users & groups', 'rnaseq-core / Liver time course', 'settings', body, js))
print('ok')
