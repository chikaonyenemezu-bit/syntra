from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.change_request import ChangeRequest, ChangeStatus
from app.models.system import System
from app.models.user import User
from app.schemas import (ChangeCreate, ChangeOut, ChangeUpdate, ESignatureOut, ImplementRequest,
                         RejectRequest, SignRequest, VerifyRequest)
from app.security import get_current_user
from app.services import lifecycle_manager as lm
from app.services.esign import SignatureError, record_failed_signature
from app.services.incident_manager import WorkflowError

router = APIRouter(prefix="/api/changes", tags=["change control"])

OPEN = [ChangeStatus.DRAFT, ChangeStatus.IN_REVIEW, ChangeStatus.APPROVED, ChangeStatus.IMPLEMENTED]


def to_out(db: Session, cr: ChangeRequest) -> ChangeOut:
    out = ChangeOut.model_validate(cr)
    out.system_code = cr.system.code
    out.required_approvals = lm.required_roles(cr)
    done = lm.approved_roles(db, cr)
    out.pending_approvals = ([r for r in out.required_approvals if r not in done]
                             if cr.status == ChangeStatus.IN_REVIEW else [])
    out.signatures = [ESignatureOut.model_validate(s) for s in lm.signatures(db, cr)]
    return out


def get_or_404(db: Session, number: str) -> ChangeRequest:
    cr = db.scalars(select(ChangeRequest).options(joinedload(ChangeRequest.system))
                    .where(ChangeRequest.number == number)).first()
    if cr is None:
        raise HTTPException(status_code=404, detail=f"Change request {number} not found")
    return cr


def run(db: Session, user: User, number: str, fn, *args, meaning: str = "") -> ChangeOut:
    cr = get_or_404(db, number)
    try:
        fn(db, cr, user, *args)
    except SignatureError as e:
        db.rollback()
        record_failed_signature(db, user, "change_request", number, meaning)
        db.commit()
        raise HTTPException(status_code=403, detail=str(e))
    except WorkflowError as e:
        db.rollback()
        raise HTTPException(status_code=403 if e.forbidden else 409, detail=str(e))
    db.commit()
    return to_out(db, get_or_404(db, number))


@router.get("", response_model=list[ChangeOut])
def list_changes(status: ChangeStatus | None = None, system_code: str | None = None,
                 open_only: bool = False, limit: int = Query(100, ge=1, le=500),
                 db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    q = select(ChangeRequest).options(joinedload(ChangeRequest.system)).order_by(ChangeRequest.id.desc()).limit(limit)
    if status:
        q = q.where(ChangeRequest.status == status)
    if open_only:
        q = q.where(ChangeRequest.status.in_(OPEN))
    if system_code:
        q = q.where(ChangeRequest.system.has(code=system_code))
    return [to_out(db, cr) for cr in db.scalars(q)]


@router.get("/{number}", response_model=ChangeOut)
def get_change(number: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return to_out(db, get_or_404(db, number))


@router.post("", response_model=ChangeOut, status_code=201)
def create_change(body: ChangeCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    system = db.scalars(select(System).where(System.code == body.system_code)).first()
    if system is None:
        raise HTTPException(status_code=404, detail=f"System {body.system_code} not found")
    try:
        cr = lm.create_change(db, user, system, body.model_dump(exclude={"system_code"}))
    except WorkflowError as e:
        db.rollback()
        raise HTTPException(status_code=403 if e.forbidden else 409, detail=str(e))
    db.commit()
    return to_out(db, get_or_404(db, cr.number))


@router.patch("/{number}", response_model=ChangeOut)
def update_change(number: str, body: ChangeUpdate, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    return run(db, user, number, lm.update_change, body.model_dump(exclude_unset=True))


@router.post("/{number}/submit", response_model=ChangeOut)
def submit(number: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return run(db, user, number, lm.submit)


@router.post("/{number}/approve", response_model=ChangeOut)
def approve(number: str, body: SignRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return run(db, user, number, lm.approve, body.password, body.comment, meaning="Approval")


@router.post("/{number}/reject", response_model=ChangeOut)
def reject(number: str, body: RejectRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return run(db, user, number, lm.reject, body.password, body.reason, meaning="Rejection")


@router.post("/{number}/implement", response_model=ChangeOut)
def implement(number: str, body: ImplementRequest, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    return run(db, user, number, lm.implement, body.note)


@router.post("/{number}/verify", response_model=ChangeOut)
def verify(number: str, body: VerifyRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return run(db, user, number, lm.verify, body.password, body.evidence, meaning="Verification")
