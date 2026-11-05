from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit_event import AuditEvent
from app.models.user import Role, User
from app.schemas import AuditEventOut, ChainCheckOut
from app.security import require_roles
from app.services.audit_logger import verify_chain

router = APIRouter(prefix="/api/audit", tags=["audit"])

reviewer = require_roles(Role.QA, Role.ADMIN, Role.IT_OPS)


@router.get("", response_model=list[AuditEventOut])
def list_events(entity_type: str | None = None, entity_id: str | None = None,
                actor: str | None = None, limit: int = Query(200, ge=1, le=2000),
                db: Session = Depends(get_db), _: User = Depends(reviewer)):
    q = select(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit)
    if entity_type:
        q = q.where(AuditEvent.entity_type == entity_type)
    if entity_id:
        q = q.where(AuditEvent.entity_id == entity_id)
    if actor:
        q = q.where(AuditEvent.actor == actor)
    return db.scalars(q).all()


@router.get("/verify", response_model=ChainCheckOut)
def verify(db: Session = Depends(get_db), _: User = Depends(require_roles(Role.QA, Role.ADMIN))):
    r = verify_chain(db)
    return ChainCheckOut(valid=r.valid, records_checked=r.records_checked,
                         first_broken_id=r.first_broken_id, reason=r.reason)
