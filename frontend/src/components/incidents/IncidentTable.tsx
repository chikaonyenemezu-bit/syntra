import { fmtTime } from "../../format";
import type { Incident } from "../../types";
import { StatusBadge } from "../shared/StatusBadge";

interface Props {
  incidents: Incident[];
  onOpen: (i: Incident) => void;
}

export function IncidentTable({ incidents, onOpen }: Props) {
  if (!incidents.length) return <p className="muted empty">No incidents. All quiet.</p>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Number</th><th>System</th><th>Title</th><th>Severity</th><th>Status</th><th>Opened</th><th>GxP</th>
          </tr>
        </thead>
        <tbody>
          {incidents.map((i) => (
            <tr key={i.id}>
              <td><button className="link" onClick={() => onOpen(i)}>{i.number}</button></td>
              <td>{i.system_code ?? "–"}</td>
              <td className="title-cell">
                {i.title}
                {i.recovered_at && i.status !== "closed" && <span className="tag tag-ok">Recovered</span>}
              </td>
              <td><StatusBadge value={i.severity} /></td>
              <td><StatusBadge value={i.status} /></td>
              <td className="nowrap">{fmtTime(i.opened_at)}</td>
              <td>{i.gxp_impact ? "Yes" : "No"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
