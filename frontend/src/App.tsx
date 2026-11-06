import { useEffect, useState } from "react";
import { api, auth } from "./services/api";
import type { User } from "./types";
import { Login } from "./pages/Login";
import { OperationsCenter } from "./pages/OperationsCenter";
import { IntegrationsIncidents } from "./pages/IntegrationsIncidents";
import { GxPLifecycle } from "./pages/GxPLifecycle";

type Page = "operations" | "integrations" | "lifecycle";

const NAV: { name: string; page: Page | null }[] = [
  { name: "Operations Center", page: "operations" },
  { name: "Integrations & Incidents", page: "integrations" },
  { name: "GxP Lifecycle", page: "lifecycle" },
  { name: "Knowledge Assistant", page: null },
];

function pageFromHash(): Page {
  const h = window.location.hash;
  return h === "#/integrations" ? "integrations" : h === "#/lifecycle" ? "lifecycle" : "operations";
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState<Page>(pageFromHash);

  const loadUser = () => {
    if (!auth.token) { setLoading(false); return; }
    api.me().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false));
  };
  useEffect(loadUser, []);

  useEffect(() => {
    const onHash = () => setPage(pageFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  if (loading) return null;
  if (!user) return <Login onLoggedIn={loadUser} />;

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-name">Syntra</span>
          <span className="brand-tag">Connected Systems Intelligence</span>
        </div>
        <nav aria-label="Main">
          {NAV.map((n) => n.page ? (
            <a key={n.name} href={`#/${n.page}`} aria-current={page === n.page ? "page" : undefined}
               className={page === n.page ? "nav-item active" : "nav-item"}>
              {n.name}
            </a>
          ) : (
            <span key={n.name} className="nav-item disabled" aria-disabled="true">
              {n.name}<span className="soon">next</span>
            </span>
          ))}
        </nav>
        <div className="me">
          <div><strong>{user.full_name}</strong></div>
          <div className="small muted">{user.username} · {user.role}</div>
          <button className="link small" onClick={() => { auth.set(null); setUser(null); }}>Sign out</button>
        </div>
      </aside>
      <main className="main">
        {page === "integrations" ? <IntegrationsIncidents user={user} />
          : page === "lifecycle" ? <GxPLifecycle user={user} />
          : <OperationsCenter user={user} />}
      </main>
    </div>
  );
}
