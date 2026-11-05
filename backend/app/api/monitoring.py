from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.incident import Incident, IncidentStatus, Severity
from app.models.system import System
from app.models.user import Role, User
from app.schemas import FaultRequest, MonitoringSummary, SystemOut
from app.security import get_current_user, require_roles
from app.services.audit_logger import log_event
from app.api.systems import get_system_or_404

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

ACTIVE = [IncidentStatus.OPEN, IncidentStatus.ACKNOWLEDGED]


@router.get("/summary", response_model=MonitoringSummary)
def summary(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    by_status = dict(db.execute(select(System.status, func.count()).group_by(System.status)).all())
    active = db.scalar(select(func.count()).select_from(Incident).where(Incident.status.in_(ACTIVE)))
    critical = db.scalar(select(func.count()).select_from(Incident).where(
        Incident.status.in_(ACTIVE), Incident.severity == Severity.CRITICAL))
    awaiting = db.scalar(select(func.count()).select_from(Incident).where(
        Incident.status == IncidentStatus.RESOLVED))
    return MonitoringSummary(
        systems_total=sum(by_status.values()), systems_by_status=by_status,
        incidents_active=active or 0, incidents_critical_active=critical or 0,
        incidents_awaiting_closure=awaiting or 0,
    )


@router.post("/simulators/{code}/fault", response_model=SystemOut)
def set_fault(code: str, body: FaultRequest, db: Session = Depends(get_db),
              user: User = Depends(require_roles(Role.ADMIN, Role.IT_OPS))):
    """Demo control: inject or clear a fault in a simulated system."""
    system = get_system_or_404(db, code)
    old = system.simulated_fault
    system.simulated_fault = body.mode
    log_event(db, actor=user.username, action="simulator.fault_set", entity_type="system",
              entity_id=system.code, details={"from": old, "to": body.mode, "demo_only": True})
    db.commit()
    return system
