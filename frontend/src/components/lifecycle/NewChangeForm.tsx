import { useState } from "react";
import { api, ApiError } from "../../services/api";
import type { ChangeRequest, Lifecycle, NewChange } from "../../types";

interface Props {
  systems: Lifecycle[];
  onCreated: (c: ChangeRequest) => void;
  onCancel: () => void;
}

export function NewChangeForm({ systems, onCreated, onCancel }: Props) {
  const [form, setForm] = useState<NewChange>({
    system_code: systems[0]?.system.code ?? "", title: "", description: "", justification: "",
    impact_assessment: "", category: "minor", risk: "low", requires_revalidation: false, target_version: null,
  });
  const [error, setError] = useState<string | null>(null);
  const set = <K extends keyof NewChange>(k: K, v: NewChange[K]) => setForm((f) => ({ ...f, [k]: v }));
  const current = systems.find((s) => s.system.code === form.system_code);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      onCreated(await api.createChange({ ...form, target_version: form.target_version?.trim() || null }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create the change request");
    }
  }

  return (
    <form className="card new-incident" onSubmit={submit}>
      <h3>New change request</h3>
      <p className="small muted">Saved as a draft. You can review it before submitting it for approval.</p>
      <div className="form-grid">
        <label>System
          <select value={form.system_code} onChange={(e) => set("system_code", e.target.value)}>
            {systems.map((s) => <option key={s.system.code} value={s.system.code}>{s.system.code} – {s.system.name}</option>)}
          </select>
        </label>
        <label>Category
          <select value={form.category} onChange={(e) => {
            const category = e.target.value as NewChange["category"];
            setForm((f) => ({ ...f, category, requires_revalidation: category === "major" }));
          }}>
            <option value="minor">Minor: no impact on validated functions</option>
            <option value="major">Major: affects GxP functions</option>
          </select>
        </label>
        <label>Risk
          <select value={form.risk} onChange={(e) => set("risk", e.target.value as NewChange["risk"])}>
            <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option>
          </select>
        </label>
        <label>Target version <span className="small muted">(running: {current?.current_version ?? "–"})</span>
          <input value={form.target_version ?? ""} onChange={(e) => set("target_version", e.target.value)} placeholder="e.g. 3.3.0" />
        </label>
      </div>
      <label>Title<input value={form.title} onChange={(e) => set("title", e.target.value)} minLength={5} required /></label>
      <label>Description: what will change
        <textarea rows={2} value={form.description} onChange={(e) => set("description", e.target.value)} required minLength={10} />
      </label>
      <label>Justification: why it is needed
        <textarea rows={2} value={form.justification} onChange={(e) => set("justification", e.target.value)} required minLength={10} />
      </label>
      <label>Impact assessment: GxP, data integrity and validation impact
        <textarea rows={2} value={form.impact_assessment} onChange={(e) => set("impact_assessment", e.target.value)} required minLength={10} />
      </label>
      <label className="checkbox">
        <input type="checkbox" checked={form.requires_revalidation}
               onChange={(e) => set("requires_revalidation", e.target.checked)} />
        Requires revalidation (the system is "in validation" until QA verifies the change)
      </label>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="row">
        <button type="submit" className="primary">Create draft</button>
        <button type="button" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}
