
"""Incident API: monitoring, investigation, QA review, and lifecycle."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.incident import Incident, IncidentStatus
from app.models.incident_documentation import IncidentInvestigation
from app.models.user import Role, User
from app.schemas import (
    IncidentCreate,
    IncidentOut,
    InvestigationSubmit,
    QAReviewSubmit,
    ResolveRequest,
)
from app.security import get_current_user, require_roles
from app.services import incident_manager
from app.services.incident_manager import WorkflowError
from app.api.systems import get_system_or_404


router = APIRouter(
    prefix="/api/incidents",
    tags=["incidents"],
)


# --------------------------------------------------
# Response models
# --------------------------------------------------

class InvestigationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    revision: int
    root_cause: str
    gxp_impact_assessment: str
    corrective_actions: str
    recovery_verification: str
    evidence_references: str
    submitted_by: str
    submitted_at: datetime


class QAReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    investigation_id: int
    decision: str
    justification: str
    reviewed_by: str
    reviewed_at: datetime


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def to_out(inc: Incident) -> IncidentOut:
    out = IncidentOut.model_validate(inc)

    out.system_code = (
        inc.system.code if inc.system else None
    )

    return out


def get_or_404(
    db: Session,
    number: str,
) -> Incident:

    inc = db.scalars(
        select(Incident)
        .options(joinedload(Incident.system))
        .where(Incident.number == number)
    ).first()

    if inc is None:
        raise HTTPException(
            status_code=404,
            detail=f"Incident {number} not found",
        )

    return inc


def run(
    db: Session,
    fn,
    *args,
) -> IncidentOut:

    try:
        inc = fn(db, *args)

        db.commit()

        return to_out(inc)

    except WorkflowError as error:
        db.rollback()

        raise HTTPException(
            status_code=(
                403 if error.forbidden else 409
            ),
            detail=str(error),
        ) from error

    except Exception:
        db.rollback()
        raise


# --------------------------------------------------
# List incidents
# --------------------------------------------------

@router.get(
    "",
    response_model=list[IncidentOut],
)
def list_incidents(
    status: IncidentStatus | None = None,
    system_code: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = (
        select(Incident)
        .options(joinedload(Incident.system))
        .order_by(Incident.id.desc())
        .limit(limit)
    )

    if status:
        q = q.where(Incident.status == status)

    if system_code:
        system = get_system_or_404(
            db,
            system_code,
        )

        q = q.where(
            Incident.system_id == system.id
        )

    return [
        to_out(incident)
        for incident in db.scalars(q)
    ]


# --------------------------------------------------
# Get incident
# --------------------------------------------------

@router.get(
    "/{number}",
    response_model=IncidentOut,
)
def get_incident(
    number: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return to_out(
        get_or_404(db, number)
    )


# --------------------------------------------------
# Create incident
# --------------------------------------------------

@router.post(
    "",
    response_model=IncidentOut,
    status_code=201,
)
def create_incident(
    body: IncidentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            Role.IT_OPS,
            Role.SYSTEM_OWNER,
            Role.QA,
        )
    ),
):
    system = (
        get_system_or_404(
            db,
            body.system_code,
        )
        if body.system_code
        else None
    )

    try:
        inc = incident_manager.open_incident(
            db,
            title=body.title,
            description=body.description,
            severity=body.severity,
            actor=user.username,
            source="manual",
            system=system,
        )

        db.commit()

        return to_out(
            get_or_404(db, inc.number)
        )

    except Exception:
        db.rollback()
        raise


# --------------------------------------------------
# Acknowledge incident
# --------------------------------------------------

@router.post(
    "/{number}/acknowledge",
    response_model=IncidentOut,
)
def acknowledge(
    number: str,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(Role.IT_OPS)
    ),
):
    return run(
        db,
        incident_manager.acknowledge,
        get_or_404(db, number),
        user,
    )


# --------------------------------------------------
# Submit structured investigation
# --------------------------------------------------

@router.post(
    "/{number}/investigations",
    response_model=InvestigationOut,
    status_code=201,
)
def submit_investigation(
    number: str,
    body: InvestigationSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(Role.IT_OPS)
    ),
):
    inc = get_or_404(db, number)

    try:
        investigation = (
            incident_manager.submit_investigation(
                db,
                inc,
                user,
                root_cause=body.root_cause,
                gxp_impact_assessment=(
                    body.gxp_impact_assessment
                ),
                corrective_actions=(
                    body.corrective_actions
                ),
                recovery_verification=(
                    body.recovery_verification
                ),
                evidence_references=(
                    body.evidence_references
                ),
            )
        )

        result = InvestigationOut.model_validate(
            investigation
        )

        db.commit()

        return result

    except WorkflowError as error:
        db.rollback()

        raise HTTPException(
            status_code=(
                403 if error.forbidden else 409
            ),
            detail=str(error),
        ) from error

    except Exception:
        db.rollback()
        raise


# --------------------------------------------------
# Retrieve investigation history
# --------------------------------------------------

@router.get(
    "/{number}/investigations",
    response_model=list[InvestigationOut],
)
def list_investigations(
    number: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    inc = get_or_404(db, number)

    investigations = db.scalars(
        select(IncidentInvestigation)
        .where(
            IncidentInvestigation.incident_id
            == inc.id
        )
        .order_by(
            IncidentInvestigation.revision.desc()
        )
    ).all()

    return [
        InvestigationOut.model_validate(item)
        for item in investigations
    ]


# --------------------------------------------------
# QA review
# --------------------------------------------------

@router.post(
    "/{number}/qa-review",
    response_model=QAReviewOut,
    status_code=201,
)
def submit_qa_review(
    number: str,
    body: QAReviewSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(Role.QA)
    ),
):
    inc = get_or_404(db, number)

    try:
        review = incident_manager.review_investigation(
            db,
            inc,
            user,
            decision=body.decision,
            justification=body.justification,
        )

        result = QAReviewOut.model_validate(review)

        db.commit()
        return result

    except WorkflowError as error:
        db.rollback()

        raise HTTPException(
            status_code=(
                403 if error.forbidden else 409
            ),
            detail=str(error),
        ) from error

    except Exception:
        db.rollback()
        raise


# --------------------------------------------------
# Resolve incident
# --------------------------------------------------

@router.post(
    "/{number}/resolve",
    response_model=IncidentOut,
)
def resolve(
    number: str,
    body: ResolveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(Role.IT_OPS)
    ),
):
    return run(
        db,
        incident_manager.resolve,
        get_or_404(db, number),
        user,
        body.note,
    )


# --------------------------------------------------
# Close incident
# --------------------------------------------------

@router.post(
    "/{number}/close",
    response_model=IncidentOut,
)
def close(
    number: str,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            Role.IT_OPS,
            Role.QA,
        )
    ),
):
    return run(
        db,
        incident_manager.close,
        get_or_404(db, number),
        user,
    )
