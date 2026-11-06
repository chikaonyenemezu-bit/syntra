import { fmtDate } from "../../format";
import type { Lifecycle } from "../../types";
import { StatusBadge } from "../shared/StatusBadge";

export const REVIEW_TEXT: Record<string, string> = {
  ok: "In order", due_soon: "Due soon", overdue: "Overdue", not_applicable: "Not applicable",
};

export function SystemInventory({ rows, onOpen }: { rows: Lifecycle[]; onOpen: (code: string) => void }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>System</th><th>GAMP</th><th>Risk</th><th>Version</th><th>Validation</th>
            <th>Next periodic review</th><th className="num">Open changes</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const drift = r.validated_version !== r.current_version;
            return (
              <tr key={r.system.code}>
                <td>
                  <button className="link" onClick={() => onOpen(r.system.code)}>{r.system.code}</button>
                  <div className="small muted">{r.system.name}</div>
                </td>
                <td>{r.system.gamp_category ?? "–"}</td>
                <td><StatusBadge value={r.risk_class} /></td>
                <td className="nowrap">
                  {r.current_version}
                  {drift && (
                    <div className="small warn-text" title="The running version differs from the validated version">
                      validated: {r.validated_version ?? "none"}
                    </div>
                  )}
                </td>
                <td><StatusBadge value={r.validation_status} /></td>
                <td className="nowrap">
                  {r.next_review_due ? fmtDate(r.next_review_due) : "–"}{" "}
                  <StatusBadge value={r.review_state} text={REVIEW_TEXT[r.review_state]} />
                </td>
                <td className="num">{r.open_changes}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
