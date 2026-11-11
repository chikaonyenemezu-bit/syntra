
import { fmtDate } from "../../format";
import type { Lifecycle } from "../../types";
import { StatusBadge } from "../shared/StatusBadge";

export const REVIEW_TEXT: Record<string, string> = {
  ok: "In order",
  due_soon: "Due soon",
  overdue: "Overdue",
  not_applicable: "Not applicable",
};

export function SystemInventory({
  rows,
  onOpen,
}: {
  rows: Lifecycle[];
  onOpen: (code: string) => void;
}) {
  return (
    <div className="table-wrap lifecycle-inventory">
      <table aria-label="GxP system inventory">
        <thead>
          <tr>
            <th scope="col">System</th>
            <th scope="col">GAMP</th>
            <th scope="col">Risk</th>
            <th scope="col">Version information</th>
            <th scope="col">Validation status</th>
            <th scope="col">Next periodic review</th>
            <th scope="col" className="num">
              Open changes
            </th>
          </tr>
        </thead>

        <tbody>
          {rows.map((r) => {
            const drift =
              r.validated_version !== null &&
              r.validated_version !== r.current_version;

            const overdue = r.review_state === "overdue";

            return (
              <tr
                key={r.system.code}
                className={
                  overdue
                    ? "lifecycle-row-overdue"
                    : undefined
                }
              >
                {/* System identification */}
                <td>
                  <button
                    type="button"
                    className="link"
                    onClick={() => onOpen(r.system.code)}
                    aria-label={`Open validation record for ${r.system.code}`}
                  >
                    {r.system.code}
                  </button>

                  <div className="small muted lifecycle-system-name">
                    {r.system.name}
                  </div>
                </td>

                {/* GAMP category */}
                <td>
                  {r.system.gamp_category ?? "–"}
                </td>

                {/* Risk classification */}
                <td>
                  <StatusBadge value={r.risk_class} />
                </td>

                {/* Current and validated versions */}
                <td>
                  <div className="lifecycle-version">
                    <div>
                      <span className="small muted">
                        Current:{" "}
                      </span>

                      <strong>{r.current_version}</strong>
                    </div>

                    <div
                      className={
                        drift
                          ? "small warn-text"
                          : "small muted"
                      }
                    >
                      Validated:{" "}
                      {r.validated_version ??
                        "Not yet validated"}
                    </div>
                  </div>
                </td>

                {/* Validation status */}
                <td>
                  <StatusBadge
                    value={r.validation_status}
                  />
                </td>

                {/* Periodic review */}
                <td>
                  <div className="lifecycle-review">
                    <span className="lifecycle-review-date">
                      {r.next_review_due
                        ? fmtDate(r.next_review_due)
                        : "–"}
                    </span>

                    <StatusBadge
                      value={r.review_state}
                      text={
                        REVIEW_TEXT[r.review_state] ??
                        r.review_state
                      }
                    />
                  </div>
                </td>

                {/* Open change requests */}
                <td className="num">
                  {r.open_changes}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
