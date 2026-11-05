import { useState } from "react";
import { api } from "../services/api";

const DEMO = [
  ["it.ops", "IT Operations"],
  ["it.ops2", "IT Operations (2nd)"],
  ["qa.lead", "Quality Assurance"],
  ["system.owner", "System Owner"],
  ["viewer", "Read-only"],
  ["admin", "Administrator"],
];

export function Login({ onLoggedIn }: { onLoggedIn: () => void }) {
  const [username, setUsername] = useState("it.ops");
  const [password, setPassword] = useState("demo1234");
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try { await api.login(username, password); onLoggedIn(); }
    catch { setError("Incorrect username or password"); }
  }

  return (
    <main className="login">
      <form className="card login-card" onSubmit={submit}>
        <div className="login-brand">
          <h1 className="brand-name">Syntra</h1>
          <span className="brand-tag">Connected Systems Intelligence</span>
        </div>
        <p className="muted">
          Monitor connected systems, manage integrations and incidents, support GxP lifecycle
          workflows, and find answers with AI-assisted knowledge retrieval.
        </p>
        <label>Username<input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" /></label>
        <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                              autoComplete="current-password" /></label>
        {error && <p className="error" role="alert">{error}</p>}
        <button type="submit" className="primary">Sign in</button>
        <details className="small">
          <summary>Demo users (password: demo1234)</summary>
          <ul className="demo-users">
            {DEMO.map(([u, r]) => (
              <li key={u}><button type="button" className="link" onClick={() => setUsername(u)}>{u}</button> – {r}</li>
            ))}
          </ul>
        </details>
      </form>
    </main>
  );
}
