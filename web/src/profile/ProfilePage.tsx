import "../runs/runs.css";
import "./profile.css";
import { Button, type MantineColorScheme, useMantineColorScheme } from "@mantine/core";
import { type ReactNode, useCallback, useEffect, useState } from "react";
import { type Me, getMe, signOut } from "../api";
import { ICONS, Icon } from "../icons";
import { copyText } from "../runs/CopyMenu";
import { when } from "../runs/stateWord";
import { usePageCrumb } from "../shell/crumb";
import { PhoneTitle, usePhone } from "../shell/layout";
import { PERSON } from "../shell/TopBar";

// The Profile page of 0.0.1 (FU-P3-112; ui-spec §4.10.1; boards LiteProfile, MLiteProfile), from
// the avatar in the top bar, in single-user mode: who the server runs as, this session and Sign
// out, the config paths (read-only, each with Copy) and the theme. `GET /me` answers paths only.

const TITLE = "Profile";
const SUB = "Single-user mode: this server runs as your Unix user";
const SIGNED_OUT =
  "Signed out of this session. To sign in again, open the link that spectio serve printed, or run spectio login --print-link.";

const PATHS: { key: keyof Me["paths"]; label: string; what: string }[] = [
  { key: "config_file", label: "Config file", what: "the config file path" },
  { key: "data_dir", label: "Data directory", what: "the data directory path" },
  { key: "db_dir", label: "Database directory", what: "the database directory path" },
  { key: "observed_dir", label: "Observed runs directory", what: "the observed runs directory path" },
];
const THEMES: { value: MantineColorScheme; label: string }[] = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
  { value: "auto", label: "System" },
];

const focusIt = (el: HTMLElement | null) => el?.focus();

function Card({ id, title, focus, children }: { id: string; title: string; focus?: boolean; children: ReactNode }) {
  return (
    <section className="sp-card sp-prof-card" aria-labelledby={id}>
      <h2 id={id} tabIndex={focus ? -1 : undefined} ref={focus ? focusIt : undefined}>{title}</h2>
      {children}
    </section>
  );
}

function Paths({ paths }: { paths: Me["paths"] }) {
  const [said, setSaid] = useState("");
  const copy = (text: string, what: string) =>
    copyText(text).then(
      () => setSaid(`Copied ${what}`),
      () => setSaid(`Could not copy ${what}: the browser gave no clipboard`),
    );
  return (
    <Card id="prof-paths" title="Config paths">
      <dl className="sp-prof-paths">
        {PATHS.map(({ key, label, what }) => (
          <div key={key}>
            <dt>{label}</dt>
            <dd>
              <code>{paths[key]}</code>
              <button type="button" className="sp-key" aria-label={`Copy ${what}`} onClick={() => copy(paths[key], what)}>
                <Icon path={ICONS.copy} size={16} />
              </button>
            </dd>
          </div>
        ))}
      </dl>
      <p className="sp-sub">Read-only here: change them in spectio.toml, then restart spectio serve.</p>
      <p role="status" className="sp-sub">{said}</p>
    </Card>
  );
}

function Theme() {
  const { colorScheme, setColorScheme } = useMantineColorScheme();
  return (
    <Card id="prof-theme" title="Theme">
      <div role="radiogroup" aria-labelledby="prof-theme" className="sp-prof-themes">
        {THEMES.map(({ value, label }) => (
          <label key={value}>
            <input type="radio" name="theme" value={value} checked={colorScheme === value} onChange={() => setColorScheme(value)} />
            {label}
          </label>
        ))}
      </div>
      <p className="sp-sub">Kept in this browser. System follows your device's setting.</p>
    </Card>
  );
}

export function ProfilePage() {
  const phone = usePhone();
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [out, setOut] = useState<"no" | "busy" | "failed" | "yes">("no");
  const [outError, setOutError] = useState("");
  usePageCrumb(TITLE);
  // UX-P3FU112-01: the control that had focus is replaced (Retry by "Loading…", Sign out by its
  // status), so focus moves to the text that replaces it rather than falling back to the page.
  const [retried, setRetried] = useState(false);
  const load = useCallback(() => {
    setError(null);
    getMe().then(setMe, (e: Error) => setError(e.message));
  }, []);
  useEffect(load, [load]);
  const leave = () => {
    setOut("busy");
    signOut().then(
      () => setOut("yes"),
      (e: Error) => (setOutError(e.message), setOut("failed")),
    );
  };
  return (
    <div className="sp-page sp-prof">
      {phone ? (
        <PhoneTitle title={TITLE} sub={me ? `Single-user mode · ${me.principal.user}` : undefined} />
      ) : (
        <header className="sp-head">
          <div className="sp-head-main">
            <span className="sp-head-tile" data-section="home">
              <Icon path={PERSON} size={22} />
            </span>
            <div>
              <h1 className="sp-page-title" tabIndex={-1}>{TITLE}</h1>
              <p className="sp-sub sp-page-sub">{SUB}</p>
            </div>
          </div>
        </header>
      )}
      {error ? (
        <>
          <p role="alert" className="sp-note sp-alert">Your profile could not be read. {error}</p>
          <Button variant="default" style={{ alignSelf: "flex-start" }} onClick={() => (setRetried(true), load())}>Retry</Button>
        </>
      ) : !me ? (
        <p role="status" className="sp-sub" tabIndex={-1} ref={retried ? focusIt : undefined}>Loading your profile…</p>
      ) : (
        <>
          <Card id="prof-who" title="Who the server runs as" focus={retried}>
            <dl className="sp-facts">
              <div><dt>Unix user</dt><dd>{me.principal.user}</dd></div>
              <div><dt>UID</dt><dd>{me.principal.uid}</dd></div>
            </dl>
            <p className="sp-sub">You are the only principal: runs, files and settings are this user's.</p>
          </Card>
          <Card id="prof-session" title="This session">
            {out === "yes" ? (
              <p role="status" className="sp-note" tabIndex={-1} ref={focusIt}>{SIGNED_OUT}</p>
            ) : (
              <>
                <dl className="sp-facts">
                  <div><dt>Started</dt><dd>{when(me.session.started_at)}</dd></div>
                  <div>
                    <dt>Expires</dt>
                    <dd>{me.session.expires_at ? when(me.session.expires_at) : "Ends when the server stops, or when you sign out"}</dd>
                  </div>
                </dl>
                {out === "failed" && <p role="alert" className="sp-note sp-alert">Could not sign out. {outError}</p>}
                <Button variant="default" className="sp-prof-out" loading={out === "busy"} onClick={leave}>
                  Sign out of this session
                </Button>
              </>
            )}
          </Card>
          <Paths paths={me.paths} />
        </>
      )}
      <Theme />
    </div>
  );
}
