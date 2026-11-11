
import { useCallback, useEffect, useState } from "react";
import { api } from "../services/api";
import { can, needsMyAction } from "../permissions";
import type { ChangeRequest, Lifecycle, User } from "../types";
import { SystemInventory } from "../components/lifecycle/SystemInventory";
import { SystemPanel } from "../components/lifecycle/SystemPanel";
import { ChangeTable } from "../components/lifecycle/ChangeTable";
import { ChangeDrawer } from "../components/lifecycle/ChangeDrawer";
import { NewChangeForm } from "../components/lifecycle/NewChangeForm";

const POLL_MS = 15000;

export function GxPLifecycle({ user }: { user: User }) {
  const [systems, setSystems] = useState<Lifecycle[]>([]);
  const [changes, setChanges] = useState<ChangeRequest[]>([]);
  const [openOnly, setOpenOnly] = useState(true);
  const [creating, setCreating] = useState(false);
  const [systemCode, setSystemCode] = useState<string | null>(null);
  const [changeNo, setChangeNo] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [s, c] = await Promise.all([
      api.lifecycle(),
      api.changes(false),
    ]);

    setSystems(s);
    setChanges(c);
  }, []);

  useEffect(() => {
    refresh().catch(() => undefined);

    const id = setInterval(
      () => refresh().catch(() => undefined),
      POLL_MS
    );

    return () => clearInterval(id);
  }, [refresh]);

  const open = changes.filter(
    (c) => !["verified", "rejected"].includes(c.status)
  );

  const shown = openOnly ? open : changes;

  const validated = systems.filter(
    (s) => s.validation_status === "validated"
  ).length;

  const overdue = systems.filter(
    (s) => s.review_state === "overdue"
  ).length;

  const mine = changes.filter(
    (c) => needsMyAction(user, c)
  ).length;

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>GxP Lifecycle</h1>
          <p className="muted">
            System inventory, validation state, periodic
            reviews and change control, with electronic
            signatures.
          </p>
        </div>
      </header>

      <section className="kpis" aria-label="Summary">
        <div className="kpi">
          <span>Systems validated</span>
          <strong>
            {validated} / {systems.length}
          </strong>
        </div>

        <div className={`kpi ${overdue ? "kpi-bad" : ""}`}>
          <span>Periodic reviews overdue</span>
          <strong>{overdue}</strong>
        </div>

        <div className="kpi">
          <span>Open change requests</span>
          <strong>{open.length}</strong>
        </div>

        <div className={`kpi ${mine ? "kpi-action" : ""}`}>
          <span>Needs your action</span>
          <strong>{mine}</strong>
        </div>
      </section>

      <section className="card">
        <div className="section-head">
          <h2>System inventory</h2>

          <span className="small muted">
            Click a system for its validation record
            and periodic reviews
          </span>
        </div>

        <SystemInventory
          rows={systems}
          onOpen={setSystemCode}
        />
      </section>

      <section className="card">
        <div className="section-head">
          <h2>Change requests</h2>

          <div className="row">
            <div
              className="segmented"
              role="group"
              aria-label="Filter change requests"
            >
              <button
                aria-pressed={openOnly}
                onClick={() => setOpenOnly(true)}
              >
                Open
              </button>

              <button
                aria-pressed={!openOnly}
                onClick={() => setOpenOnly(false)}
              >
                All
              </button>
            </div>

            {can.createChange(user) && !creating && (
              <button
                className="primary"
                onClick={() => setCreating(true)}
              >
                New change request
              </button>
            )}
          </div>
        </div>

        {creating && (
          <NewChangeForm
            systems={systems}
            onCancel={() => setCreating(false)}
            onCreated={(c) => {
              setCreating(false);
              setChangeNo(c.number);
              refresh().catch(() => undefined);
            }}
          />
        )}

        <ChangeTable
          changes={shown}
          user={user}
          onOpen={setChangeNo}
        />
      </section>

      {systemCode && (
        <SystemPanel
          code={systemCode}
          user={user}
          changes={changes}
          onClose={() => setSystemCode(null)}
          onChanged={() =>
            refresh().catch(() => undefined)
          }
          onOpenChange={(n) => {
            setSystemCode(null);
            setChangeNo(n);
          }}
        />
      )}

      {changeNo && (
        <ChangeDrawer
          number={changeNo}
          user={user}
          onClose={() => setChangeNo(null)}
          onChanged={() =>
            refresh().catch(() => undefined)
          }
        />
      )}
    </div>
  );
}
