from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.change_request import ChangeRequest, ChangeStatus
from app.models.esignature import ESignature
from app.models.lifecycle import PeriodicReview, SystemLifecycle
from app.models.system import System
from app.models.user import Role, User
from app.schemas import (ESignatureOut, LifecycleDetail, LifecycleOut, PeriodicReviewCreate,
                         PeriodicReviewOut, SystemOut)
from app.security import get_current_user, require_roles
from app.services import lifecycle_manager
from app.services.esign import SignatureError, record_failed_signature
from app.services.incident_manager import WorkflowError

router = APIRouter(prefix="/api/lifecycle", tags=["gxp lifecycle"])

OPEN = [ChangeStatus.DRAFT, ChangeStatus.IN_REVIEW, ChangeStatus.APPROVED, ChangeStatus.IMPLEMENTED]


def _out(db: Session, lc: SystemLifecycle, cls=LifecycleOut):
    rs = lifecycle_manager.review_state(lc)
    open_changes = db.scalar(select(func.count()).select_from(ChangeRequest).where(
        ChangeRequest.system_id == lc.system_id, ChangeRequest.status.in_(OPEN))) or 0
    return cls(system=SystemOut.model_validate(lc.system), risk_class=lc.risk_class,
               current_version=lc.current_version, validated_version=lc.validated_version,
               validation_status=lc.validation_status, validated_on=lc.validated_on,
               validation_report=lc.validation_report, periodic_review_months=lc.periodic_review_months,
               last_review_on=lc.last_review_on, last_review_outcome=lc.last_review_outcome,
               next_review_due=rs.due, review_state=rs.state, open_changes=open_changes)


def _get(db: Session, code: str) -> SystemLifecycle:
    lc = db.scalars(select(SystemLifecycle).options(joinedload(SystemLifecycle.system))
                    .where(SystemLifecycle.system.has(System.code == code))).first()
    if lc is None:
        raise HTTPException(status_code=404, detail=f"No lifecycle record for {code}")
    return lc


def _detail(db: Session, lc: SystemLifecycle) -> LifecycleDetail:
    out = _out(db, lc, LifecycleDetail)
    reviews = db.scalars(select(PeriodicReview).where(PeriodicReview.system_id == lc.system_id)
                         .order_by(PeriodicReview.id.desc())).all()
    sigs = {s.entity_id: s for s in db.scalars(select(ESignature).where(
        ESignature.entity_type == "periodic_review", ESignature.entity_id.in_([r.number for r in reviews])))}
    out.reviews = [PeriodicReviewOut(number=r.number, reviewed_on=r.reviewed_on, outcome=r.outcome,
                                     summary=r.summary, reviewer=r.reviewer,
                                     signature=ESignatureOut.model_validate(sigs[r.number]) if r.number in sigs else None)
                   for r in reviews]
    return out


@router.get("", response_model=list[LifecycleOut])
def list_lifecycle(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.scalars(select(SystemLifecycle).options(joinedload(SystemLifecycle.system))).all()
    return sorted((_out(db, lc) for lc in rows), key=lambda o: o.system.code)


@router.get("/{code}", response_model=LifecycleDetail)
def get_lifecycle(code: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return _detail(db, _get(db, code))


@router.post("/{code}/reviews", response_model=LifecycleDetail, status_code=201)
def record_review(code: str, body: PeriodicReviewCreate, db: Session = Depends(get_db),
                  user: User = Depends(require_roles(Role.QA))):
    lc = _get(db, code)
    try:
        lifecycle_manager.record_periodic_review(db, lc.system, user, body.password, body.outcome, body.summary)
    except SignatureError as e:
        db.rollback()
        record_failed_signature(db, user, "system", code, "Periodic review")
        db.commit()
        raise HTTPException(status_code=403, detail=str(e))
    except WorkflowError as e:
        db.rollback()
        raise HTTPException(status_code=403 if e.forbidden else 409, detail=str(e))
    db.commit()
    return _detail(db, _get(db, code))
