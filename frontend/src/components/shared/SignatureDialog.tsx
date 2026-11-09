import { useState } from "react";
import { useEscape } from "./useEscape";
import { ApiError } from "../../services/api";
import type { User } from "../../types";

interface Props {
  user: User;
  title: string;
  meaning: string;            // what the signature means, shown before signing
  textLabel: string;          // comment / reason / evidence / summary
  textMin?: number;           // 0 = optional
  textPlaceholder?: string;
  onSign: (password: string, text: string) => Promise<void>;
  onCancel: () => void;
}

/** Electronic signature: the user re-enters their password and confirms the meaning (21 CFR Part 11). */
export function SignatureDialog({ user, title, meaning, textLabel, textMin = 0, textPlaceholder, onSign, onCancel }: Props) {
  const [password, setPassword] = useState("");
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  useEscape(onCancel);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null);
    try { await onSign(password, text); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Signing failed"); setPassword(""); }
    finally { setBusy(false); }
  }

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <form className="modal" role="dialog" aria-modal="true" aria-labelledby="sig-title"
            onSubmit={submit} onClick={(e) => e.stopPropagation()}>
        <h2 id="sig-title">{title}</h2>
        <div className="sig-meaning">
          <span className="small muted">Signature meaning</span>
          <strong>{meaning}</strong>
          <span className="small muted">Signed as {user.full_name} ({user.username}), with the current date and time.</span>
        </div>
        <label>{textLabel}{textMin > 0 && <span className="muted small"> (required)</span>}
          <textarea rows={3} value={text} onChange={(e) => setText(e.target.value)} placeholder={textPlaceholder}
                    minLength={textMin || undefined} required={textMin > 0} />
        </label>
        <label>Password
          <input type="password" autoComplete="current-password" value={password} autoFocus
                 onChange={(e) => setPassword(e.target.value)} required />
        </label>
        <p className="small muted">
          Entering your password is your legally binding electronic signature, equivalent to a handwritten one.
        </p>
        {error && <p className="error" role="alert">{error}</p>}
        <div className="row">
          <button type="submit" className="primary" disabled={busy || !password || text.trim().length < textMin}>
            {busy ? "Signing…" : "Sign"}
          </button>
          <button type="button" onClick={onCancel}>Cancel</button>
        </div>
      </form>
    </div>
  );
}
