"""GxP lifecycle: change control and periodic review.

Change request workflow (each rule is a requirement in validation/URS.md, section 6):

    draft ──submit──▶ in_review ──approve (all required roles)──▶ approved ──implement──▶ implemented ──verify──▶ verified
                          └──reject──▶ rejected

- Only the requester edits or submits a draft.
- GxP systems need two signed approvals: System Owner and QA. Others need the System Owner only.
- Nobody approves their own change request.
- IT Operations implements (deploys). A change that requires revalidation puts the system "in validation".
- QA verifies with a signature, and never a change they implemented themselves.
- Verification updates the validated version; a revalidated system becomes "validated" again.
- Approve, reject, verify and periodic reviews are electronic signatures (password re-entry).
"""
import calendar
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models._time import utcnow
from app.models.change_request import ChangeCategory, ChangeRequest, ChangeStatus
from app.models.esignature import ESignature
from app.models.lifecycle import PeriodicReview, ReviewOutcome, SystemLifecycle, ValidationStatus
from app.models.system import System
from app.models.user import Role, User
from app.services.audit_logger import log_event
from app.services.esign import ROLE_LABEL, sign
from app.services.incident_manager import WorkflowError

DUE_SOON_DAYS = 60
EDITABLE = ["title", "description", "justification", "impact_assessment", "category", "risk",
            "requires_revalidation", "target_version"]


# --- periodic review status -----------------------------------------------------------------------

def add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    year, month = d.year + m // 12, m % 12 + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


@dataclass
class ReviewState:
    due: date | None
    state: str  # ok | due_soon | overdue | not_applicable


def review_state(lc: SystemLifecycle, today: date | None = None) -> ReviewState:
    today = today or date.today()
    base = lc.last_review_on or lc.validated_on
    if lc.validation_status != ValidationStatus.VALIDATED or base is None:
        return ReviewState(None, "not_applicable")
    due = add_months(base, lc.periodic_review_months)
    if due < today:
        return ReviewState(due, "overdue")
    if due <= today + timedelta(days=DUE_SOON_DAYS):
        return ReviewState(due, "due_soon")
    return ReviewState(due, "ok")


def lifecycle_for(db: Session, system: System) -> SystemLifecycle:
    lc = db.scalars(select(SystemLifecycle).where(SystemLifecycle.system_id == system.id)).first()
    if lc is None:
        raise WorkflowError(f"{system.code} has no lifecycle record")
    return lc


def record_periodic_review(db: Session, system: System, user: User, password: str,
                           outcome: ReviewOutcome, summary: str, today: date | None = None) -> PeriodicReview:
    if user.role != Role.QA:
        raise WorkflowError("Periodic reviews are signed by QA", forbidden=True)
    lc = lifecycle_for(db, system)
    if lc.validation_status != ValidationStatus.VALIDATED:
        raise WorkflowError(f"{system.code} is not in a validated state ({lc.validation_status})")
    if len(summary.strip()) < 20:
        raise WorkflowError("A review summary of at least 20 characters is required")
    today = today or date.today()
    review = PeriodicReview(system_id=system.id, reviewed_on=today, outcome=outcome,
                            summary=summary.strip(), reviewer=user.username)
    db.add(review)
    db.flush()
    review.number = f"PR-{review.id:06d}"
    meaning = ("Reviewed (QA): remains validated" if outcome == ReviewOutcome.REMAINS_VALIDATED
               else "Reviewed (QA): remediation required")
    sign(db, user, password, entity_type="periodic_review", entity_id=review.number, meaning=meaning,
         comment=summary)
    lc.last_review_on, lc.last_review_outcome, lc.updated_at = today, outcome, utcnow()
    log_event(db, actor=user.username, action="lifecycle.periodic_review", entity_type="system",
              entity_id=system.code, details={"review": review.number, "outcome": outcome,
                                              "next_due": str(review_state(lc, today).due)})
    return review


# --- change control --------------------------------------------------------------------------------

def required_roles(cr: ChangeRequest) -> list[str]:
    return [Role.SYSTEM_OWNER.value, Role.QA.value] if cr.system.gxp_relevant else [Role.SYSTEM_OWNER.value]


def signatures(db: Session, cr: ChangeRequest) -> list[ESignature]:
    return list(db.scalars(select(ESignature).where(ESignature.entity_type == "change_request",
                                                    ESignature.entity_id == cr.number)
                           .order_by(ESignature.id)))


def approved_roles(db: Session, cr: ChangeRequest) -> set[str]:
    """Roles that have signed an approval (a rejected request is closed, never resubmitted)."""
    return {s.signer_role for s in signatures(db, cr) if s.meaning.startswith("Approved")}


def _require(cr: ChangeRequest, *statuses: ChangeStatus) -> None:
    if cr.status not in statuses:
        allowed = " or ".join(s.value for s in statuses)
        raise WorkflowError(f"{cr.number} is '{cr.status}'; this action needs it to be {allowed}")


def _audit(db: Session, user: User, action: str, cr: ChangeRequest, **details) -> None:
    log_event(db, actor=user.username, action=f"change.{action}", entity_type="change_request",
              entity_id=cr.number, details={"system": cr.system.code, "status": cr.status, **details})


def create_change(db: Session, user: User, system: System, data: dict) -> ChangeRequest:
    if user.role not in (Role.IT_OPS, Role.SYSTEM_OWNER, Role.QA):
        raise WorkflowError(f"Role '{user.role}' cannot raise change requests", forbidden=True)
    lifecycle_for(db, system)
    cr = ChangeRequest(system=system, requested_by=user.username, status=ChangeStatus.DRAFT,
                       **{k: data[k] for k in EDITABLE if k in data})
    if cr.category == ChangeCategory.MAJOR and data.get("requires_revalidation") is None:
        cr.requires_revalidation = True
    db.add(cr)
    db.flush()
    cr.number = f"CR-{cr.id:06d}"
    _audit(db, user, "created", cr, title=cr.title, category=cr.category, risk=cr.risk,
           requires_revalidation=cr.requires_revalidation, target_version=cr.target_version)
    return cr


def update_change(db: Session, cr: ChangeRequest, user: User, data: dict) -> ChangeRequest:
    _require(cr, ChangeStatus.DRAFT)
    if user.username != cr.requested_by:
        raise WorkflowError("Only the requester can edit a draft", forbidden=True)
    changes = {}
    for k in EDITABLE:
        if k in data and data[k] != getattr(cr, k):
            changes[k] = {"from": getattr(cr, k), "to": data[k]}
            setattr(cr, k, data[k])
    if changes:
        _audit(db, user, "edited", cr, changes=changes)
    return cr


def submit(db: Session, cr: ChangeRequest, user: User) -> ChangeRequest:
    _require(cr, ChangeStatus.DRAFT)
    if user.username != cr.requested_by:
        raise WorkflowError("Only the requester can submit a change request", forbidden=True)
    for field, label in (("description", "description"), ("justification", "justification"),
                         ("impact_assessment", "impact assessment")):
        if len((getattr(cr, field) or "").strip()) < 10:
            raise WorkflowError(f"A {label} of at least 10 characters is required before submitting")
    cr.status, cr.submitted_at = ChangeStatus.IN_REVIEW, utcnow()
    _audit(db, user, "submitted", cr, required_approvals=required_roles(cr))
    return cr


def _check_approver(db: Session, cr: ChangeRequest, user: User) -> None:
    if user.role not in required_roles(cr):
        needed = " and ".join(ROLE_LABEL[r] for r in required_roles(cr))
        raise WorkflowError(f"This change needs approval by {needed}", forbidden=True)
    if user.username == cr.requested_by:
        raise WorkflowError("You cannot approve or reject your own change request", forbidden=True)


def approve(db: Session, cr: ChangeRequest, user: User, password: str, comment: str = "") -> ChangeRequest:
    _require(cr, ChangeStatus.IN_REVIEW)
    _check_approver(db, cr, user)
    if user.role in approved_roles(db, cr):
        raise WorkflowError(f"{ROLE_LABEL[user.role]} has already approved {cr.number}")
    sign(db, user, password, entity_type="change_request", entity_id=cr.number,
         meaning=f"Approved ({ROLE_LABEL[user.role]})", comment=comment)
    done = approved_roles(db, cr)
    pending = [r for r in required_roles(cr) if r not in done]
    if not pending:
        cr.status, cr.approved_at = ChangeStatus.APPROVED, utcnow()
    _audit(db, user, "approval_signed", cr, role=user.role, pending=pending)
    return cr


def reject(db: Session, cr: ChangeRequest, user: User, password: str, reason: str) -> ChangeRequest:
    _require(cr, ChangeStatus.IN_REVIEW)
    _check_approver(db, cr, user)
    if len(reason.strip()) < 10:
        raise WorkflowError("A rejection reason of at least 10 characters is required")
    sign(db, user, password, entity_type="change_request", entity_id=cr.number,
         meaning=f"Rejected ({ROLE_LABEL[user.role]})", comment=reason)
    cr.status, cr.rejected_at, cr.rejected_by, cr.rejection_reason = (
        ChangeStatus.REJECTED, utcnow(), user.username, reason.strip())
    _audit(db, user, "rejected", cr, reason=cr.rejection_reason)
    return cr


def implement(db: Session, cr: ChangeRequest, user: User, note: str) -> ChangeRequest:
    _require(cr, ChangeStatus.APPROVED)
    if user.role != Role.IT_OPS:
        raise WorkflowError("Changes are implemented by IT Operations", forbidden=True)
    if len(note.strip()) < 10:
        raise WorkflowError("An implementation note of at least 10 characters is required")
    lc = lifecycle_for(db, cr.system)
    lifecycle_changes = {}
    if cr.target_version and cr.target_version != lc.current_version:
        lifecycle_changes["current_version"] = {"from": lc.current_version, "to": cr.target_version}
        lc.current_version = cr.target_version
    if cr.requires_revalidation and lc.validation_status != ValidationStatus.IN_VALIDATION:
        lifecycle_changes["validation_status"] = {"from": lc.validation_status, "to": ValidationStatus.IN_VALIDATION}
        lc.validation_status = ValidationStatus.IN_VALIDATION
    lc.updated_at = utcnow()
    cr.status, cr.implemented_at, cr.implemented_by, cr.implementation_note = (
        ChangeStatus.IMPLEMENTED, utcnow(), user.username, note.strip())
    _audit(db, user, "implemented", cr, note=cr.implementation_note, lifecycle=lifecycle_changes)
    return cr


def verify(db: Session, cr: ChangeRequest, user: User, password: str, evidence: str,
           today: date | None = None) -> ChangeRequest:
    _require(cr, ChangeStatus.IMPLEMENTED)
    if user.role != Role.QA:
        raise WorkflowError("Changes are verified by QA", forbidden=True)
    if user.username in (cr.implemented_by, cr.requested_by):
        raise WorkflowError("You cannot verify a change you requested or implemented", forbidden=True)
    if len(evidence.strip()) < 10:
        raise WorkflowError("Verification evidence (e.g. test protocol reference) is required")
    sign(db, user, password, entity_type="change_request", entity_id=cr.number,
         meaning="Verified (QA)", comment=evidence)
    lc = lifecycle_for(db, cr.system)
    lifecycle_changes = {}
    if lc.validated_version != lc.current_version and (cr.target_version or cr.requires_revalidation):
        lifecycle_changes["validated_version"] = {"from": lc.validated_version, "to": lc.current_version}
        lc.validated_version = lc.current_version
    if cr.requires_revalidation:
        today = today or date.today()
        lifecycle_changes["validation_status"] = {"from": lc.validation_status, "to": ValidationStatus.VALIDATED}
        lifecycle_changes["validated_on"] = {"from": lc.validated_on, "to": today}
        lc.validation_status, lc.validated_on = ValidationStatus.VALIDATED, today
        lc.validation_report = cr.number
    lc.updated_at = utcnow()
    cr.status, cr.verified_at, cr.verified_by, cr.verification_evidence = (
        ChangeStatus.VERIFIED, utcnow(), user.username, evidence.strip())
    _audit(db, user, "verified", cr, evidence=cr.verification_evidence, lifecycle=lifecycle_changes)
    return cr
