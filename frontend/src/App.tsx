import { useEffect, useState } from "react";
import { api, auth } from "./services/api";
import type { User } from "./types";
import { Login } from "./pages/Login";
import { OperationsCenter } from "./pages/OperationsCenter";
import { IntegrationsIncidents } from "./pages/IntegrationsIncidents";
import { GxPLifecycle } from "./pages/GxPLifecycle";
import { KnowledgeAssistant } from "./pages/KnowledgeAssistant";

type Page = "operations" | "integrations" | "lifecycle" | "assistant";

const NAV: { name: string; page: Page }[] = [
  { name: "Operations Center", page: "operations" },
  { name: "Integrations & Incidents", page: "integrations" },
  { name: "GxP Lifecycle", page: "lifecycle" },
  { name: "Knowledge Assistant", page: "assistant" },
];

function pageFromHash(): Page {
  const h = window.location.hash.split("?")[0];
  return h === "#/integrations" ? "integrations" : h === "#/lifecycle" ? "lifecycle"
    : h === "#/assistant" ? "assistant" : "operations";
}

/** A question passed in the link, e.g. #/assistant?q=What+should+I+do+about+INC-000002 */
function questionFromHash(): string | null {
  const query = window.location.hash.split("?")[1];
  return query ? new URLSearchParams(query).get("q") : null;
}

function BrandMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 42 42" fill="none" aria-hidden="true">
      <path d="M9 11H32L21 31 9 11Z" stroke="currentColor" strokeWidth="2.5" />
      <circle cx="9" cy="11" r="4.5" fill="currentColor" />
      <circle cx="32" cy="11" r="4.5" fill="currentColor" />
      <circle cx="21" cy="31" r="4.5" fill="currentColor" />
    </svg>
  );
}

function NavIcon({ page }: { page: Page }) {
  return (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none"
         stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"
         strokeLinejoin="round" aria-hidden="true">
      {page === "operations" ? (
        <path d="M2 12h5l3-7 4 14 3-7h5" />
      ) : page === "integrations" ? (
        <>
          <rect x="2" y="4" width="7" height="7" rx="1.5" />
          <rect x="15" y="13" width="7" height="7" rx="1.5" />
          <path d="M9 7.5h5a4 4 0 0 1 4 4v1.5M15 16.5h-5a4 4 0 0 1-4-4v-1.5" />
        </>
      ) : page === "lifecycle" ? (
        <>
          <path d="M12 2 20 6v6c0 5-3 8-8 10-5-2-8-5-8-10V6z" />
          <path d="m8 12 3 3 5-6" />
        </>
      ) : (
        <path d="m12 2 2.5 7.5L22 12l-7.5 2.5L12 22l-2.5-7.5L2 12l7.5-2.5z" />
      )}
    </svg>
  );
}

function PanelIcon({ collapsed }: { collapsed: boolean }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
         stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"
         strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M9 4v16" />
      <path d={collapsed ? "m13 9 3 3-3 3" : "m17 9-3 3 3 3"} />
    </svg>
  );
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState<Page>(pageFromHash);
  const [question, setQuestion] = useState<string | null>(questionFromHash);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const loadUser = () => {
    if (!auth.token) { setLoading(false); return; }
    api.me().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false));
  };
  useEffect(loadUser, []);

  useEffect(() => {
    const onHash = () => { setPage(pageFromHash()); setQuestion(questionFromHash()); };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  if (loading) return null;
  if (!user) return <Login onLoggedIn={loadUser} />;

  const signOut = () => { auth.set(null); setUser(null); };
  const initials = user.full_name.trim().split(/\s+/).slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "").join("") || "U";

  return (
    <div className={`shell${sidebarCollapsed ? " shell-collapsed" : ""}`}>
      <aside className="sidebar" aria-label="Application sidebar">
        <div className="sidebar-brand-row">
          <div className="brand">
            <BrandMark />
            <div className="brand-copy">
              <span className="brand-name">Syntra</span>
              <span className="brand-tag">Connected Systems Intelligence</span>
            </div>
          </div>
          <button type="button" className="sidebar-toggle"
                  aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
                  aria-expanded={!sidebarCollapsed}
                  onClick={() => setSidebarCollapsed((value) => !value)}>
            <PanelIcon collapsed={sidebarCollapsed} />
          </button>
        </div>

        <nav aria-label="Main">
          {NAV.map((n) => (
            <a key={n.page} href={`#/${n.page}`} title={n.name}
               aria-label={n.name} aria-current={page === n.page ? "page" : undefined}
               className={page === n.page ? "nav-item active" : "nav-item"}>
              <NavIcon page={n.page} />
              <span className="nav-label">{n.name}</span>
            </a>
          ))}
        </nav>

        <div className="me">
          <div className="profile-top">
            <span className="profile-avatar" aria-hidden="true">{initials}</span>
            <div className="profile-info">
              <strong>{user.full_name}</strong>
              <span className="small muted">{user.username} · {user.role}</span>
            </div>
          </div>
          <button type="button" className="link small sidebar-signout" onClick={signOut}>
            Sign out
          </button>
          <button type="button" className="sidebar-signout-compact" onClick={signOut}
                  title="Sign out" aria-label="Sign out">
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"
                 strokeLinejoin="round" aria-hidden="true">
              <path d="M9 4H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h4" />
              <path d="M15 16l4-4-4-4M19 12H9" />
            </svg>
          </button>
        </div>
      </aside>

      <main className="main">
        {page === "integrations" ? <IntegrationsIncidents user={user} />
          : page === "lifecycle" ? <GxPLifecycle user={user} />
          : page === "assistant" ? <KnowledgeAssistant user={user} initialQuestion={question} />
          : <OperationsCenter user={user} />}
      </main>
    </div>
  );
}
