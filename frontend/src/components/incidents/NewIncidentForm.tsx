import { useState } from "react";
import { api, ApiError } from "../../services/api";
import type { Incident, Severity, System } from "../../types";

interface Props {
  systems: System[];
  onCreated: (i: Incident) => void;
  onCancel: () => void;
}

export function NewIncidentForm({ systems, onCreated, onCancel }: Props) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [severity, setSeverity] = useState<Severity>("medium");
  const [systemCode, setSystemCode] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      onCreated(await api.createIncident({ title, description, severity, system_code: systemCode || null }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create incident");
    }
  }

  return (
    <form className="card new-incident" onSubmit={submit}>
      <h3>Report an incident</h3>
      <div className="form-grid">
        <label>Title<input value={title} onChange={(e) => setTitle(e.target.value)} minLength={5} required /></label>
        <label>System
          <select value={systemCode} onChange={(e) => setSystemCode(e.target.value)}>
            <option value="">None / other</option>
            {systems.map((s) => <option key={s.code} value={s.code}>{s.code} – {s.name}</option>)}
          </select>
        </label>
        <label>Severity
          <select value={severity} onChange={(e) => setSeverity(e.target.value as Severity)}>
            {["low", "medium", "high", "critical"].map((s) => <option key={s}>{s}</option>)}
          </select>
        </label>
      </div>
      <label>Description<textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} /></label>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="row">
        <button type="submit" className="primary">Create</button>
        <button type="button" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}
