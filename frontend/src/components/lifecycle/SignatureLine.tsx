import { fmtTime, ROLE_LABEL } from "../../format";
import type { ESignature } from "../../types";

/** Signature manifestation: printed name, date/time and meaning (21 CFR Part 11 §11.50). */
export function SignatureLine({ sig, showComment = true }: { sig: ESignature; showComment?: boolean }) {
  return (
    <div className="signature">
      <div className="signature-head">
        <strong>{sig.meaning}</strong>
        <span className="small muted">{fmtTime(sig.signed_at)}</span>
      </div>
      <div className="small">
        Signed by {sig.signer_name} <span className="muted">({sig.signer}, {ROLE_LABEL[sig.signer_role] ?? sig.signer_role})</span>
      </div>
      {showComment && sig.comment && <div className="small muted signature-comment">“{sig.comment}”</div>}
    </div>
  );
}
