from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.incident import Incident, IncidentStatus
from app.models.user import Role, User
from app.schemas import IncidentCreate, IncidentOut, ResolveRequest
from app.security import get_current_user, require_roles
from app.services import incident_manager
from app.services.incident_manager import WorkflowError
from app.api.systems import get_system_or_404

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


def to_out(inc: Incident) -> IncidentOut:
    out = IncidentOut.model_validate(inc)
    out.system_code = inc.system.code if inc.system else None
    return out


def get_or_404(db: Session, number: str) -> Incident:
    inc = db.scalars(select(Incident).options(joinedload(Incident.system))
                     .where(Incident.number == number)).first()
    if inc is None:
        raise HTTPException(status_code=404, detail=f"Incident {number} not found")
    return inc


def run(db: Session, fn, *args) -> IncidentOut:
    try:
        inc = fn(db, *args)
    except WorkflowError as e:
        db.rollback()
        raise HTTPException(status_code=403 if e.forbidden else 409, detail=str(e))
    db.commit()
    return to_out(inc)


@router.get("", response_model=list[IncidentOut])
def list_incidents(status: IncidentStatus | None = None, system_code: str | None = None,
                   limit: int = Query(100, ge=1, le=500),
                   db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    q = select(Incident).options(joinedload(Incident.system)).order_by(Incident.id.desc()).limit(limit)
    if status:
        q = q.where(Incident.status == status)
    if system_code:
        q = q.where(Incident.system_id == get_system_or_404(db, system_code).id)
    return [to_out(i) for i in db.scalars(q)]


@router.get("/{number}", response_model=IncidentOut)
def get_incident(number: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return to_out(get_or_404(db, number))


@router.post("", response_model=IncidentOut, status_code=201)
def create_incident(body: IncidentCreate, db: Session = Depends(get_db),
                    user: User = Depends(require_roles(Role.IT_OPS, Role.SYSTEM_OWNER, Role.QA))):
    system = get_system_or_404(db, body.system_code) if body.system_code else None
    inc = incident_manager.open_incident(db, title=body.title, description=body.description,
                                         severity=body.severity, actor=user.username,
                                         source="manual", system=system)
    db.commit()
    return to_out(get_or_404(db, inc.number))


@router.post("/{number}/acknowledge", response_model=IncidentOut)
def acknowledge(number: str, db: Session = Depends(get_db),
                user: User = Depends(require_roles(Role.IT_OPS))):
    return run(db, incident_manager.acknowledge, get_or_404(db, number), user)


@router.post("/{number}/resolve", response_model=IncidentOut)
def resolve(number: str, body: ResolveRequest, db: Session = Depends(get_db),
            user: User = Depends(require_roles(Role.IT_OPS))):
    return run(db, incident_manager.resolve, get_or_404(db, number), user, body.note)


@router.post("/{number}/close", response_model=IncidentOut)
def close(number: str, db: Session = Depends(get_db),
          user: User = Depends(require_roles(Role.IT_OPS, Role.QA))):
    return run(db, incident_manager.close, get_or_404(db, number), user)
