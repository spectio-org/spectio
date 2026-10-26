import sys; sys.path.insert(0, 'tools')
from mu_common import *
body = SETTINGS_HEAD + '''
    <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
      <div style="flex-grow: 1; display: flex; flex-direction: column; gap: 2px;">
        <h2 style="margin: 0; font-family: 'Outfit', sans-serif; font-weight: 600; font-size: 21px;">Service accounts</h2>
        <span style="font-size: 13.5px; color: #4D5065;">Identities for systems that act without a person: LIMS, CI, lab robots and AI agents. Each belongs to a group, has its own token and scopes, and appears by name in every history.</span>
      </div>
      <a href="#" class="btn btn-p"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14 M5 12h14"/></svg>New service account</a>
    </div>
    <div style="display: flex; flex-direction: column; gap: 10px;">
      <sc-for list="{{accounts}}" as="a" hint-placeholder-count="4">
        <article class="card" style="padding: 14px 16px; display: flex; align-items: center; gap: 16px; flex-wrap: wrap;">
          <span style="width: 44px; height: 44px; border-radius: 13px; background: {{a.tbg}}; color: {{a.tfg}}; font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0;"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="{{a.icon}}"/></svg></span>
          <span style="flex: 1 1 220px; min-width: 0; display: flex; flex-direction: column; gap: 4px;">
            <span style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;"><span style="font-size: 15px; font-weight: 600;">{{a.name}}</span><span class="chip" style="background: {{a.pbg}}; color: {{a.pfg}};">{{a.purpose}}</span></span>
            <span style="font-size: 12.5px; color: #4D5065;">{{a.desc}}</span>
          </span>
          <span style="flex: 0 1 170px; display: flex; flex-direction: column; gap: 2px; font-size: 12.5px;"><span style="color: #6E7287;">Owning group</span><span style="font-weight: 600; color: #1F536D;">{{a.group}}</span></span>
          <span style="flex: 1 1 260px; display: flex; flex-direction: column; gap: 4px; font-size: 12.5px;"><span style="color: #6E7287;">Scopes · projects</span><span style="display: flex; gap: 5px; flex-wrap: wrap;"><sc-for list="{{a.scopes}}" as="sc" hint-placeholder-count="3"><code class="chip" style="background: #F7F7FB; color: #22253A; font-family: 'JetBrains Mono', monospace; font-weight: 500; box-shadow: inset 0 0 0 1px #EEEFF5;">{{sc}}</code></sc-for></span><span style="color: #33364A;">{{a.projects}}</span></span>
          <span style="flex: 0 1 150px; display: flex; flex-direction: column; gap: 2px; font-size: 12.5px;"><span style="color: #6E7287;">Token</span><span style="color: {{a.tkfg}}; font-weight: 600;">{{a.token}}</span><span style="color: #6E7287;">{{a.used}}</span></span>
          <span style="display: flex; gap: 8px;"><a href="#" class="btn btn-s" style="height: 36px;">Rotate token</a><button type="button" aria-label="More for {{a.name}}" class="btn btn-s" style="height: 36px; width: 36px; padding: 0; justify-content: center;">⋯</button></span>
        </article>
      </sc-for>
    </div>
    <div class="card" style="padding: 14px 16px; background: #F7F7FB; box-shadow: none; display: flex; gap: 12px; align-items: flex-start;">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#4D5065" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="flex-shrink: 0; margin-top: 1px;"><path d="M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z M12 11v5 M12 8h.01"/></svg>
      <span style="font-size: 12.5px; line-height: 1.5; color: #33364A;">Runners are not listed here: each runner gets its own credential when it registers on an environment (Environments › Runners). Tokens are shown once at creation and stored hashed; rotation keeps the old token valid for 24 h so integrations can switch without downtime.</span>
    </div>
'''
js = "  const ACTIVE_TAB = 'Service accounts';\n" + TABS_JS + '''  const PUR = { lims: ['LIMS', '#EEF6FA', '#1F536D', '#EEF6FA', '#1F536D', 'M4 4h16v16H4z M4 10h16 M10 4v16'], ci: ['CI', '#F1F2F6', '#33364A', '#F1F2F6', '#33364A', 'M8 9l-4 3 4 3 M16 9l4 3-4 3 M14 5l-4 14'], robot: ['Robot', '#E3F1FB', '#1D5FC9', '#E3F1FB', '#1D5FC9', 'M5 9h14v10H5z M12 5v4 M9 13h.01 M15 13h.01 M9 16h6'], agent: ['AI agent', '#F6F2FE', '#4D368B', '#7750D4', '#FFFFFF', 'M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z'] };
  const acc = (name, p, desc, group, scopes, projects, token, used, warn) => ({ name, purpose: PUR[p][0], pbg: PUR[p][1], pfg: PUR[p][2], tbg: PUR[p][3], tfg: PUR[p][4], icon: PUR[p][5], desc, group, scopes, projects, token, used, tkfg: warn ? '#8F5806' : '#22253A' });
  return {
    tabs,
    accounts: [
      acc('LabID', 'lims', 'EMBL LabID launches runs from its projects and receives results as RO-Crates.', 'bioinfo-platform', ['runs:launch', 'runs:read', 'artifacts:read', 'gates:read'], 'Projects: Liver time course, Drug screen 2026', 'spk_svc_…8f3a', 'last used 4 min ago', false),
      acc('Pipeline CI', 'ci', 'Launches test profiles on every pipeline release and reads the results.', 'bioinfo-platform', ['runs:launch', 'runs:read'], 'Project: Pipeline CI only · environment Kubernetes · dev', 'spk_svc_…21c9', 'last used today 06:00', false),
      acc('Plate reader', 'robot', 'Signals “plate imaged” on imaging gates through a webhook callback.', 'imaging-core', ['gates:signal'], 'Project: Drug screen 2026', 'spk_svc_…77d0', 'expires in 12 days', true),
      acc('QC agent', 'agent', 'Built-in assistant: reads checks and evidence, posts suggestions on gates. Model: Lab GPU · vLLM.', 'bioinfo-platform', ['runs:read', 'gates:propose', 'artifacts:read'], 'All projects where it is granted a role', 'spk_agt_…0b44', 'last used 9 min ago', false)
    ]
  };'''
open('spectio-ui/project/SettingsServiceAccounts.dc.html', 'w').write(build('Spectio — service accounts', 'Settings / Service accounts', 'rnaseq-core / Liver time course', 'settings', body, js))
print('ok')
