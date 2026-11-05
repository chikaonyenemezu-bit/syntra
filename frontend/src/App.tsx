import { useEffect, useState } from "react";
import { api, auth } from "./services/api";
import type { User } from "./types";
import { Login } from "./pages/Login";
import { OperationsCenter } from "./pages/OperationsCenter";

const NAV = [
  { name: "Operations Center", ready: true },
  { name: "Integrations & Incidents", ready: false },
  { name: "GxP Lifecycle", ready: false },
  { name: "Knowledge Assistant", ready: false },
];

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const loadUser = () => {
    if (!auth.token) { setLoading(false); return; }
    api.me().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false));
  };
  useEffect(loadUser, []);

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
          {NAV.map((n) => (
            <a key={n.name} href="#" aria-current={n.ready ? "page" : undefined}
               className={n.ready ? "nav-item active" : "nav-item disabled"}
               onClick={(e) => e.preventDefault()} aria-disabled={!n.ready}>
              {n.name}{!n.ready && <span className="soon">next</span>}
            </a>
          ))}
        </nav>
        <div className="me">
          <div><strong>{user.full_name}</strong></div>
          <div className="small muted">{user.username} · {user.role}</div>
          <button className="link small" onClick={() => { auth.set(null); setUser(null); }}>Sign out</button>
        </div>
      </aside>
      <main className="main"><OperationsCenter user={user} /></main>
    </div>
  );
}
