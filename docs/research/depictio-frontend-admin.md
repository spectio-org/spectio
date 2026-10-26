# depictio frontend, branding, users & groups, admin shell — audit for Spectio

Source: depictio checkout `scratchpad/dep`, v1.19.2 (commit 0d1aa0a, 2026-10-23). Paths are relative to the repository root. Inferences are marked **[inf]**.

## 1. JS packages (pnpm workspace)

`pnpm-workspace.yaml` lists `packages/*` and `depictio/viewer`. The viewer pulls the shared packages as local paths (`depictio/viewer/package.json`: `"depictio-react-core": "file:../../packages/depictio-react-core"`, same for `depictio-components`). Stack: React 18.3, Mantine 7.14+ (`core`, `dates`, `hooks`, `notifications`, `code-highlight`, `carousel`, `tiptap`, `colors-generator`), AG Grid 32, lucide-react, Iconify, Vite 5.

| Package | Version | Published | What it is |
|---|---|---|---|
| `packages/depictio-react-core` | 0.1.0, `"private": true` | **no** (npm) | Main shared library. `main: src/index.ts`; no build step, consumed as TypeScript source; 215 export statements in `src/index.ts`. Peers: Mantine, AG Grid, Plotly, react-grid-layout, genome-spy, 3dmol, `depictio-components` |
| `packages/depictio-components` | 0.1.0, private | no | Small shared React component set (`src/lib/index.ts`, webpack build). Peers: Mantine core/hooks, Iconify, React 18 |
| `packages/tool-studio` | 0.2.0, private | no | A separate Vite app (`App.tsx`, Monaco, Pyodide, zustand) for authoring catalog tools; depends on react-core |
| `packages/plotly-complexheatmap`, `packages/plotly-upset` | Python (hatchling `pyproject.toml`) | pinned 0.1.0, PyPI publication pending (`dev/design/local-server-profile.md` §Risks 1) | Python Plotly figure libraries, not JS |

What `depictio-react-core` contains, by area:
- **Theme and branding.**
  - `brandTheme.ts`: `buildDepictioTheme`, `depictioTheme`, `brandCssVariablesResolver`, `BrandingContext`/`useBranding`, `useBrandAccent(s)`, `mergeBrandThemes`, `BRAND_PALETTES` (`brandPrimary`/`brandSecondary`/`brandTertiary`) and `LOGO_PALETTES` (`logoOrange`, `logoTeal`, 10 shades each).
  - `brandColors.ts`.
  - `components/branding/`: `BrandThemeForm`, `BrandThemePreview`, `BrandScope`, `useResolvedBrandTheme`.
- **API client.**
  - `api.ts`, 8,035 lines. `API_BASE = '/depictio/api/v1'` is hard-coded (l.22).
  - `authFetch` (l.182) adds `Authorization: Bearer`, refreshes the token on 401 and retries.
  - Typed functions for every endpoint: users, groups, tokens, branding, backups, monitoring, and so on.
- **Admin URL state.** `adminUrlState.ts` (`ADMIN_TABS`, `MONITORING_PANES`, `adminUrl`, `parseAdminUrl`) and `listingUrlState.ts`.
- **Dashboard rendering.** `components/` holds `DashboardGrid`, `ComponentRenderer`, `FigureRenderer`, `TableRenderer`, `MultiQCRenderer`, `JBrowseRenderer`, `MapRenderer`, `ImageRenderer`, `StepFlow`, `SectionAccordion`, `TabTiles` and others. `components/chrome/` holds per-card action buttons (Download, Export, Fullscreen, Inspect, Comments, Annotate). `chrome/` has `ChromeButton`, `ChromeButtonGroup`, `chromeStyle`.
- **Hooks and data utilities.** `hooks/` (`useCollapseState`, `useInView`, `useRealtimeJournal`, …), `realtime.ts`, `telemetry.ts`, `fetchQueue.ts`, filter and selection modules, `runFolder*.ts`.
- **Not in react-core.** The app chrome is not here: AppShell, sidebar, header, glass shell and dock live in the **viewer** under `depictio/viewer/src/chrome/`. So are auth pages, the current-user hook and all admin screens.

## 2. Branding and customisation

### 2.1 Model: `depictio/models/models/branding.py`

Branding has three layers, each one overriding the previous field by field (l.1–22). `None` means "inherit", so an untouched theme serialises to `{}`.
1. Deployment defaults from `DEPICTIO_BRANDING_*` environment variables (`BrandingConfig`, `api/v1/configs/settings_models.py:2179`).
2. Instance overrides, stored in the singleton `instance_settings` document and edited from /admin → Branding.
3. A per-dashboard override, `DashboardData.brand_theme`.

`merge_brand_themes()` folds the layers. `resolve_brand_theme()` applies the final defaults (`tint_mode="accent"`) and derives the figure colorway (8 colours) and the sequential scale (8 stops). This is done server-side so Python figures and React stay identical.

`BrandTheme` (l.311, `extra="forbid"`):

| Group | Fields |
|---|---|
| Identity | `app_name` (≤120; browser tab title and login greeting), `logo_mode` (`inherit` / `none` / `custom`), `logo_url`, `logo_url_dark` (falls back to `logo_url`) |
| Brand colours | `primary`, `secondary`, `tertiary`. Each is a hex value or a Mantine palette name, expanded to a 10-shade palette with the brand colour placed on shade 6, the shade a filled control paints with (l.64–68) |
| Status colours | `success`, `warning`, `danger` (override Mantine green / yellow / red) |
| Tint | `tint_mode`: `accent` (default) or `full` |
| Surfaces | `surfaces_light` and `surfaces_dark` (`BrandSurfaces`: `app_bg`, `section_bg`, `nav_bg`, `heading`) |
| Type and shape | `font_family`, `headings_font_family` (≤300), `default_radius` (xs–xl) |
| Figures | `plots` (`BrandPlots`: `template`, `colorway[]`, `sequential[]`) |
| Extra | `palettes: dict[str, list[str]]` (named palettes) |

- **Chrome style.** A separate `InstanceLook.default_chrome` takes `glass` or `base` (l.43–56). It is instance-only, so a dashboard cannot change the app chrome, and each reader can still choose their own in Profile.
- **Presets.** `BRAND_PRESETS` (l.507) has `depictio` (default), `trec`, `embl` and `ocean`. A preset only seeds the form; everything stays editable.
- **"Powered by Depictio".** The badge shows exactly when the depictio wordmark is hidden, i.e. once `logo_mode` is `custom` or `none` (`BrandingConfig` docstring).

### 2.2 Environment variables: `BrandingConfig` (`settings_models.py:2179`)

Three levels, the later one winning:
1. `DEPICTIO_BRANDING_PRESET=trec`;
2. `DEPICTIO_BRANDING_THEME='<JSON BrandTheme>'`, the only way to set nested blocks such as surfaces;
3. flat variables: `..._LOGO_URL`, `..._LOGO_URL_DARK`, `..._APP_NAME`, and the remaining fields.

### 2.3 API (`api/v1/endpoints/utils_endpoints/routes.py`, under `/depictio/api/v1/utils`)

| Route | Line | Who | Purpose |
|---|---|---|---|
| `GET /utils/public-config` | 171 | anyone | Bootstrap payload: `branding` (effective theme), Google Analytics, `feedback` link (read in `viewer/src/main.tsx:354–370`) |
| `GET /utils/branding/presets` | 264 | anyone | Preset list for the panel |
| `POST /utils/branding/resolve` | 290 | signed in | Resolve a draft theme (dashboard editors use it too) |
| `GET /utils/branding` | 305 | admin | Panel state: `overrides`, `env_defaults`, `effective`, `default_chrome` |
| `PUT /utils/branding` | 312 | admin | Replace the overrides; null fields fall back to env |
| `PUT /utils/branding/look` | 323 | admin | Set `default_chrome` |
| `DELETE /utils/branding` | 336 | admin | Reset all overrides |
| `POST /utils/branding/logo/{light\|dark}` | 348 | admin | Logo upload, stored in `branding_assets` |
| `GET /utils/branding/logo/{variant}` | 384 | anyone | Serve the logo |

Logo uploads accept PNG, JPEG and WebP, checked by magic bytes. SVG is not accepted [inf: SVG can carry scripts]. Maximum 2 MB (`api/v1/services/branding.py:237–241,250`). Logos are excluded from dashboard version snapshots (CLAUDE.md).

### 2.4 Admin Branding panel (`depictio/viewer/src/admin/AdminBrandingPanel.tsx`, 457 lines)

- **Header** (l.276–360): title "Instance branding" with the help text "Rebrand this deployment without touching its configuration… Cleared fields fall back to the deployment's `DEPICTIO_BRANDING_*` defaults". Buttons: **Presets** menu, **Import** (JSON file), **Export**.
- **Chrome style**: a `SegmentedControl` (`data-testid="branding-default-chrome"`) with Glass and Base and a one-line tagline for each.
- **Body**: a `Grid`, 7/5 columns at `md`.
  - **Left**: logo upload slots "Logo" and "Logo (dark mode)" (l.396–405), each with an upload `FileButton` and a "Remove the override" icon. Below them sits `BrandThemeForm` (`packages/depictio-react-core/src/components/branding/BrandThemeForm.tsx`, an Accordion; each item shows how many fields are set):
    - `identity` (instance scope only): "Instance name";
    - `logo` (instance only);
    - `colors` "Brand colors": Primary / Secondary / Tertiary;
    - `status` "Status colors": Success / Warning / Danger;
    - `surfaces`: Page background, Cards & sections, Header & sidebar, Titles, each for light and dark;
    - `type` "Typography & shape": Font stack, Heading font stack, Corner radius (Sharp xs, Small, Medium, Large, Round xl);
    - `figures`: Plot template (Follow the UI theme, Plotly, Plotly white, Plotly dark, ggplot2, Seaborn, Simple white, Presentation), and Colorway as "From palette" or "Custom" with add/remove swatches.
  - **Right**: "Preview" (`BrandThemePreview.tsx`), a mini page with badges, a section heading, and buttons in five variants (filled, light, outline, subtle, default).
- **Footer**: **Reset** (`mdi:restore`) and **Save** (l.439–447). On save, `setBranding(state.effective)` repaints the running UI (l.44).
- **Per-dashboard scope**: the same `BrandThemeForm` with `scope` set to the dashboard, without the identity and logo sections, opened from the dashboard appearance panel.

### 2.5 Runtime

- **Fetching and caching** (`depictio/viewer/src/branding.ts`): branding arrives from `/utils/public-config` after first paint and is cached in localStorage (`readCachedBranding` / `cacheBranding`) to avoid a flash. An external store (`getBranding` / `setBranding` / `subscribeBranding`) feeds the theme root. `usePageTitle(page)` sets the tab title to `<app_name> — <page>`.
- **Theme building** (`brandTheme.ts:222`): `buildDepictioTheme()` sets Mantine's `primaryColor` (falling back to `blue`), `fontFamily`, `defaultRadius` (`md` by default) and heading fonts.
- **CSS variables** (`brandTheme.ts:287`): `brandCssVariablesResolver()` writes `--mantine-color-body` (app_bg), `--mantine-color-default` and `--depictio-section-bg` (section_bg), `--depictio-nav-bg`, `--depictio-heading-color`, and `--depictio-brand-primary|secondary|tertiary`. Secondary falls back to `teal` and tertiary to `orange`.
- **Section colours** use the logo palettes (`logoTeal` for Projects, `logoOrange` for Dashboards) unless the brand sets a secondary or tertiary (`brandAccent`).

### 2.6 Other customisation

- **Elsewhere in `public-config` and settings:**
  - Google Analytics (`GoogleAnalyticsConfig`, l.2123);
  - an opt-in Feedback link (`FeedbackConfig`, l.2140);
  - `saml_login_label` for the SSO button text (l.546);
  - `password_login_disabled` (l.463);
  - version check (`VersionCheckConfig`, l.2073, with an admin toggle in Admin → Settings: "Check for new versions", interval, repository, current and latest version, last check, last error; `AdminSettingsPanel.tsx:186–236`);
  - telemetry and analytics configs.
- **Not found:** announcements or banners, custom login-page text beyond `app_name` and the SAML label, custom footer, custom homepage. The About page (`viewer/src/about/AboutApp.tsx`) is static; `landing/LandingHint` is a hint, not a configurable homepage. [inf: these are absent, based on a grep of `settings_models.py` for about / announce / footer / homepage.]

## 3. Users and groups

### 3.1 Admin → Users (`depictio/viewer/src/admin/AdminUsersPanel.tsx`, 341 lines)

- **Layout.** An accordion list, one row per user, with no table columns.
  - The row header shows a user icon and the email, plus badges: "You", "Inactive" (red), and "System admin" (primary colour, shield icon) or "User" (plain).
  - The expanded row uses `Facts` (`admin/Facts.tsx`): User ID, Registration date, Last login, Account status (badge), Verified (Yes/No), and "Password: Must be changed at next sign-in" when it applies.
  - In the Classic chrome there is also a "User status" `SegmentedControl` with Standard and System Admin (l.183–190), disabled for oneself.
- **Actions.** "Delete user", disabled for oneself with the tooltip "You cannot delete your own account", with a confirmation modal (`DeleteUserModal.tsx`).
  - "Create user" (`UserPlus`) opens `CreateUserModal.tsx`: Email, Display name (optional), Initial password (pre-generated, 14 characters, with "Generate another" and "Copy"), a "Ask for a new password at first sign-in" switch and a "System admin" switch.
  - When password login is disabled, the modal says the person signs in with single sign-on (l.144).
- **Not found:** filters, search, invitations, deactivate/reactivate, admin-triggered password reset, impersonation.
- **API** (`packages/depictio-react-core/src/api.ts`):
  - `GET /auth/list` (l.5964);
  - `DELETE /auth/delete/{id}` (l.5971);
  - `POST /auth/admin/create_user` (l.5992);
  - `POST /auth/turn_sysadmin/{id}/{True|False}` (l.6009), a verb-style path.

### 3.2 Groups: one workspace, two scopes

- **Two entry points, one component** (`depictio/viewer/src/groups/GroupsWorkspace.tsx`, 533 lines). Admin → Groups is `AdminGroupsPanel.tsx` → `<GroupsWorkspace scope="admin" />`, covering every group. `/groups` is `GroupsApp.tsx`, titled "My Groups", scope `mine`: the caller's groups, editable where the caller is a group admin, reached from the group badges on the Profile page.
- **Master-detail** (`Grid` 5/7 or 4/8). Screenshot: `research/depictio-shots/user-groups_admin-workspace.png`.
  - **Left panel**: a "Search groups…" box, a **+ Create** button (admin scope), and an AG Grid with columns Group (sortable) and Members, plus a "N groups" footer.
  - **Right panel**: `GroupDetailPanel.tsx`, 894 lines.
    - Header: group icon, name, an "N members" badge, an **SSO** badge (grape) with the tooltip "Synced from SSO — manual changes may be overwritten at next login." (l.545–548, repeated as a notice at l.628–641), and **Delete group**.
    - Editable fields: Name and Description, with **Save**.
    - **P.I. block.** If `pending_pi_email` is set: "P.I. pending — <email> becomes P.I. and group admin at their [first sign-in]", with a clear action. Otherwise a "Principal Investigator" email input (`pi@example.com`) with a set button (l.648–712).
    - **Members**: a count and a "Filter members…" box. The AG Grid has columns Member (email plus a "You" badge), Name (`display_name`), Group admin (checkbox), P.I. (a crown marks the current P.I.; others get a "Designate as P.I." action) and remove.
    - Below: a "Type to search users…" picker, or an email field, with **+ Add member**.
- **Permission rules.**
  - `canManage` covers rename, add/remove and the group-admin toggle: admin scope, or the caller is a group admin.
  - `canEditPI` is admin scope only, so P.I. designation is for system admins only, server-side as well (l.55–62).
  - Only the admin scope can delete, and the protected groups `admin` and `users` can never be deleted (`PROTECTED_GROUP_NAMES`, l.42).
  - `CreateGroupModal.tsx`: Group name ("A short, unique name"), Description (optional), Principal Investigator (optional).
- **API**:
  - `GET /groups/list` (admin) and `GET /groups/mine`;
  - `GET`, `PATCH` and `DELETE /groups/{id}`, plus `POST /groups`;
  - `POST` and `DELETE /groups/{id}/members/{uid}`;
  - `POST /groups/{id}/admins/{uid}/{True|False}`;
  - `POST /groups/{id}/pending-pi` and `POST /groups/{id}/pi/{uid}`;
  - `GET /projects/group_members_preview/{pid}/{gid}` (api.ts l.5276–5432).
- Screenshot `user-groups_pending-pi.png` shows the pending-P.I. state.

### 3.3 Profile (`depictio/viewer/src/profile/ProfileApp.tsx`, 734 lines)

- **Avatar.** Click the avatar to change it (`FileButton`), and Remove. It may come from the identity provider ("picture from your <provider> account"). API: `PUT` / `DELETE /auth/me/avatar`.
- **Info rows** (l.642–653): Email, Name, Title, Role (Administrator / User), Database ID, Registration date, Last login.
- **Groups row** (`GroupsInfoRow`, l.162–190): one badge per group, a crown where the user is P.I. and a shield where they are admin, each linking to `/groups?group=<id>`.
- **Password**: `PasswordForm.tsx`, calling `POST /auth/edit_password`.
- The chrome preference (Glass / Base) and account preferences appear in the `server-info-account/account-*.png` screenshots.

### 3.4 CLI agents (`/cli-agents`, `depictio/viewer/src/cli-agents/CliAgentsPanel.tsx`)

- **Purpose.** Subtitle: "Security configurations to access Depictio via the command line interface." Button **Add configuration**. Empty state: "No CLI configurations yet".
- **Each configuration** shows its name and "Expires: <datetime>", plus delete (`DeleteTokenModal`, which asks the user to type "delete").
- **Create** (`CreateTokenModal`, field Name) makes a long-lived token, then `DisplayTokenModal` shows the generated `CLI.yaml` to copy or download (screenshot `cli-config-create.png`). It is not available in public mode (l.132).
- **API**: `GET /auth/list_tokens`, `POST /auth/me/tokens`, `DELETE /auth/me/tokens/{id}`, `POST /auth/generate_agent_config`.
- **Monitoring "Agents" pane**: `GET /monitoring/agents` and `POST /monitoring/agents/{id}/trigger` (api.ts l.6646–6663) list registered CLI agents or watchers and can trigger them. [inf: belongs to the ops audit.]

### 3.5 Project permissions (`depictio/viewer/src/projects/detail/PermissionsApp.tsx`, 1,539 lines; Glass layout l.842–1064)

1. **Visibility**: a chip, the title "Public" or "Private", the text "Anyone signed in can view this project." or "Only listed members can view this project.", and a `Switch` ("Public project"). Turning it on opens a confirmation modal, "Change Project Visibility".
2. **Members**: a header with a count and the hint "**Owners** manage members and visibility, **editors** change the project's content, **viewers** can only look."
   - Each row has the email, an Owner / Editor / Viewer `SegmentedControl` and a remove button.
   - An add-by-email input at the bottom. Empty state: "No members yet. Add a teammate by email below."
3. **Groups**: same pattern. Each row has the group name, an Owner / Editor / Viewer `SegmentedControl` and remove, with a "Search groups" picker. Empty state: "No groups yet. Share this project with a group below."

Also: `AccessOverview.tsx` shows the effective access (a 403 for non-managers). The Classic layout uses AG Grids with Email | Owner | Editor | Viewer checkbox columns (l.660–729). API: `POST /projects/update_project_permissions` (l.5140).

## 4. Admin shell and chrome

- **Two chromes.** `InstanceLook.default_chrome` selects `glass` (the default) or `base` ("Classic"). Each reader can override it in Profile (`chrome/variants/index.ts`: `writeChromePref`, `applyInstanceDefault`).
- **Glass page layout** (`depictio/viewer/src/chrome/variants/glass/Shell.tsx`, header comment):
  - a full-width **top bar** (logo │ breadcrumb … settings, theme, avatar);
  - a **sidebar** labelled WORKSPACE with Dashboards, Projects, Administration and About, folding to an icon rail, with an "Online · vX" and "Single user mode" status at the bottom;
  - a floating, movable **dock** for page actions.
  - Below `sm`: a bottom bar (Tabs, Filters, Search, More), compact top bar, bottom sheets.
- **AdminApp** (`depictio/viewer/src/admin/AdminApp.tsx`):
  - **Glass.** `GlassPage` with `section="admin"`, the title "Administration" and the description "Users, content, branding and the health of this instance." Inside, a vertical, unstyled `Tabs` acts as a settings-style section nav, 208 px wide and sticky, with 32 px gap to the content (`chrome/variants/glass/pages/admin.css`).
    - Nav groups (l.72–106):
      - **People**: Users, Groups;
      - **Content**: Projects (teal), Dashboards (orange);
      - **Activity**: Tasks, Ingestion, Watchers, Logs, Health, all "trusted";
      - **Instance**: Branding, Backups (trusted), Maintenance, Settings.
    - Group labels are 11 px uppercase, `letter-spacing .06em`. Tabs are 36 px high, radius 10, 13.5 px / weight 550. The active tab is `--gl-accent-soft` at weight 650. Icons are lucide at stroke 1.6 (`STROKE`).
  - **Base / Classic.** A Mantine `AppShell` (header 64, navbar 260) with one horizontal tab row: Users, Groups, Projects, Dashboards, Branding, Log & Task, Backups, Maintenance, Settings.
  - **Behaviour.**
    - URL-routed as `/admin/<tab>` and `/admin/<pane>`, with ingestion filters in the query string (react-core `adminUrlState`). The last tab is remembered in localStorage (`admin-active-tab`).
    - Non-admins get a "Forbidden" page ("The administration page is only available to system administrators.").
    - Monitoring and Backups are hidden in public and demo modes (`admin/access.ts`: `canSeeMonitoring`, `canSeeBackups`). Single-user mode always shows them.
- **Visual style** (screenshots `glass-chrome/admin-light.png`, `user-groups_admin-workspace.png`):
  - pale blue-grey page background, white panels with a 1 px hairline and radius ~16–20, generous padding;
  - the shield icon in a soft blue tile next to a large bold title;
  - dense AG Grid tables with light rows and the selected row in pale blue;
  - small pill badges ("You", "System Admin", "SSO", "N members"); soft-filled primary buttons (+ Create, Save, Delete group); red trash icons.
  - In the older v1.11 Glass screenshot (`admin-light.png`), the sections are a horizontal segmented pill bar instead of the left section nav.
- **Screenshots** in `docs/images`:
  - `glass-chrome/admin-light.png`, `glass-chrome/auth-login-light.png`;
  - `user-groups_admin-workspace.png`, `user-groups_my-groups.png`, `user-groups_pending-pi.png`;
  - `server-info-account/{admin-settings,account-settings,account-preferences,cli-config-create}.png`;
  - `v0.12/react/admin_monitoring_{tasks,task_detail,logs,health,ingestion*,agents}_{light,dark}.png`.
  - Copied to `research/depictio-shots/`: `admin-light.png`, `user-groups_admin-workspace.png`, `user-groups_pending-pi.png`, `admin-settings.png`, `cli-config-create.png`, `admin_monitoring_tasks_light.png`.
  - No dedicated branding screenshot was found.

## 5. Reusable for Spectio

**Depend on, or vendor, directly**
- `depictio-react-core` has the theme engine (`buildDepictioTheme`, `brandCssVariablesResolver`, `BrandingContext`, `mergeBrandThemes`) and the branding editor (`BrandThemeForm`, `BrandThemePreview`).
  - **Blocker 1**: it is private, unpublished, unbuilt TypeScript source.
  - **Blocker 2**: `api.ts` hard-codes `API_BASE = '/depictio/api/v1'`.
  - **Blocker 3**: it pulls heavy peers (Plotly, AG Grid, genome-spy, 3dmol).
  - **Proposal**: depictio extracts `@depictio/theme` (brandTheme.ts, brandColors.ts, components/branding) as a small published package with only Mantine as a peer. Spectio depends on it; until then, Spectio vendors those five files.
- **Python**: depend on `depictio.models.models.branding` (`BrandTheme`, `merge_brand_themes`, `resolve_brand_theme`, presets), or copy it. It is pure Pydantic. One shared model means one brand JSON can be imported or exported between the two apps (the panel already has Import / Export).

**Port as patterns (copy, rename the API calls)**
- `authFetch` (bearer token, refresh on 401, retry).
- URL-routed admin sections (`adminUrlState`), plus remembering the last tab.
- The groups master-detail workspace: one component for both admin and "my groups" scopes, with `canManage` / `canEditPI` flags.
- `Facts` key–value rows, the confirmation modal that asks to type "delete", and the create-user modal with a generated password.

**Mirror field for field**
- **Branding.**
  - Spectio gets the same `BrandTheme` fields and the same three layers: env `SPECTIO_BRANDING_*`, the admin panel, and a per-workflow or per-project override in place of depictio's per-dashboard one [inf].
  - When co-hosted, Spectio reads depictio's effective branding from `/depictio/api/v1/utils/public-config` and only adds its own section colours.
  - Same rules: presets, Import / Export JSON, logo light and dark (PNG, JPEG, WebP, ≤2 MB, no SVG), "Powered by" badge logic.
- **Users.** Spectio mirrors depictio's facts and its create form. It adds search, deactivate, and principal kinds (service accounts, runners, agents), which depictio lacks.
- **Groups.** Columns Member / Name / Group admin / P.I.; the pending-P.I.-by-email flow; the SSO badge with its tooltip; protected `admin` and `users` groups; P.I. set by system admins only.
- **Project sharing.** Visibility / Members / Groups sections with Owner / Editor / Viewer segmented controls and the same hint sentence. Spectio adds Launcher and Reviewer as capabilities on top of Editor, in an "advanced" row, so the three-role surface stays identical.
- **Profile.** Same rows (Email, Name, Title, Role, ID, Registration date, Last login), avatar, group badges with crown and shield, and password. "CLI configurations" becomes Spectio's Tokens section, with the same create → show-config-once flow.
- **Admin navigation.** Same groups and order:
  - **People**: Users, Groups, plus Service accounts;
  - **Content**: Projects, plus Workflows and Environments;
  - **Activity**: Tasks, Logs, Health, plus Runs/Events;
  - **Instance**: Branding, Backups, Maintenance, Settings, plus AI & agents, Webhooks, Plugins.
  - The settings-style left section nav is 208 px, with 11 px uppercase group labels.

**Conflicts with Spectio's current design**
1. **Admin entry.** depictio's admin is a full page inside its WORKSPACE sidebar ("Administration" item). Spectio currently has a "Settings" item with horizontal tabs. **Proposal**: rename it to "Administration" (admin only) and use depictio's left section nav inside the content area, keeping Spectio's fixed 276 px sidebar and full-width top bar, which match Glass's top bar and sidebar.
2. **Sidebar widths.** depictio's Glass sidebar is about 210 px with Dashboards, Projects, Administration, About. Spectio's is 276 px with 7 items. When co-hosted, the app switcher must not reorder either app's items. [inf]
3. **No dock in Spectio.** depictio's floating dock is dashboard-specific. Spectio keeps its page action bars.
4. **Role vocabulary.** Spectio's five roles against depictio's three: show three in the sharing UI and the extra two as capabilities (see [`api-and-data-model.md`](../specs/api-and-data-model.md) §13).
5. **Settings to split out of "Settings".** Spectio's current Settings tabs (General, Projects, Users & groups, Service accounts, Tokens, AI & agents, Webhooks, Notifications, Branding) should be redistributed into the four depictio groups. Personal tokens move to Profile, as depictio does with CLI agents.
6. **Icons.** depictio's admin uses lucide at stroke 1.6, while Spectio's boards use hand-drawn 1.7-stroke paths. Close enough; align on 1.6 if Spectio vendors lucide.
