import { fmtDate } from "../../format";
import { needsMyAction } from "../../permissions";
import type { ChangeRequest, User } from "../../types";
import { StatusBadge } from "../shared/StatusBadge";

interface Props {
  changes: ChangeRequest[];
  user: User;
  onOpen: (number: string) => void;
}

export function ChangeTable({ changes, user, onOpen }: Props) {
  if (!changes.length) return <p className="muted empty">No change requests.</p>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr><th>Number</th><th>System</th><th>Title</th><th>Category</th><th>Risk</th><th>Status</th><th>Requested</th></tr>
        </thead>
        <tbody>
          {changes.map((c) => (
            <tr key={c.id}>
              <td className="nowrap">
                <button className="link" onClick={() => onOpen(c.number)}>{c.number}</button>
                {needsMyAction(user, c) && <span className="tag tag-action">Your action</span>}
              </td>
              <td className="nowrap">{c.system_code}</td>
              <td className="title-cell">
                {c.title}
                {c.requires_revalidation && <span className="tag">Revalidation</span>}
              </td>
              <td>{c.category === "major" ? "Major" : "Minor"}</td>
              <td><StatusBadge value={c.risk} /></td>
              <td><StatusBadge value={c.status} /></td>
              <td className="nowrap">{fmtDate(c.created_at)}<div className="small muted">{c.requested_by}</div></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
