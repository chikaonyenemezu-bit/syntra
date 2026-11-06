"""Demo users and systems. All demo users share the password 'demo1234' (never use in production)."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lifecycle import RiskClass, SystemLifecycle, ValidationStatus
from app.models.system import System
from app.models.user import Role, User
from app.security import hash_password
from app.services.audit_logger import log_event

DEMO_PASSWORD = "demo1234"

DEMO_USERS = [
    ("it.ops", "Wilson (IT Operations)", Role.IT_OPS),
    ("it.ops2", "Second IT Ops Engineer", Role.IT_OPS),
    ("qa.lead", "QA Lead", Role.QA),
    ("qa.reviewer", "QA Reviewer", Role.QA),
    ("system.owner", "Head of Production (System Owner MES)", Role.SYSTEM_OWNER),
    ("viewer", "Read-only Viewer", Role.VIEWER),
    ("admin", "Platform Administrator", Role.ADMIN),
]

DEMO_SYSTEMS = [
    dict(code="MES-01", name="Manufacturing Execution System", system_type="MES",
         description="Electronic batch records for solid dosage Tablet Line 2",
         gxp_relevant=True, gamp_category=4, owner="Head of Production"),
    dict(code="LIMS-01", name="Laboratory Information Management System", system_type="LIMS",
         description="QC sample management, test results and stability studies",
         gxp_relevant=True, gamp_category=4, owner="Head of Quality Control"),
    dict(code="ERP-01", name="Enterprise Resource Planning", system_type="ERP",
         description="Materials, inventory, process orders and batch status",
         gxp_relevant=True, gamp_category=4, owner="Head of Supply Chain"),
    dict(code="INT-FDA-01", name="openFDA Drug Recall Interface", system_type="INTEGRATION",
         description="Scheduled import of FDA drug enforcement reports (recalls) with record-level validation",
         gxp_relevant=True, gamp_category=5, owner="Head of Quality Assurance"),
]


# Starting point of each system's GxP lifecycle. Dates are chosen so the demo shows every review state:
# LIMS overdue, ERP due soon, MES in order, the openFDA interface not yet validated.
DEMO_LIFECYCLE = {
    "MES-01": dict(risk_class=RiskClass.HIGH, current_version="3.2.1", validated_version="3.2.1",
                   validation_status=ValidationStatus.VALIDATED, validated_on=date(2025, 3, 14),
                   validation_report="VR-MES-2025-002", periodic_review_months=24),
    "LIMS-01": dict(risk_class=RiskClass.HIGH, current_version="8.1.0", validated_version="8.1.0",
                    validation_status=ValidationStatus.VALIDATED, validated_on=date(2024, 8, 19),
                    validation_report="VR-LIMS-2024-007", periodic_review_months=24),
    "ERP-01": dict(risk_class=RiskClass.MEDIUM, current_version="6.0.4", validated_version="6.0.4",
                   validation_status=ValidationStatus.VALIDATED, validated_on=date(2023, 11, 27),
                   validation_report="VR-ERP-2023-011", periodic_review_months=24,
                   last_review_on=date(2024, 12, 9), last_review_outcome="remains_validated"),
    "INT-FDA-01": dict(risk_class=RiskClass.MEDIUM, current_version="0.2.0", validated_version=None,
                       validation_status=ValidationStatus.IN_VALIDATION, validated_on=None,
                       validation_report=None, periodic_review_months=12),
}


def seed(db: Session) -> None:
    for username, full_name, role in DEMO_USERS:
        if not db.scalars(select(User).where(User.username == username)).first():
            db.add(User(username=username, full_name=full_name, role=role,
                        password_hash=hash_password(DEMO_PASSWORD)))
            log_event(db, actor="system", action="user.created", entity_type="user",
                      entity_id=username, details={"role": role.value, "source": "demo seed"})
    for data in DEMO_SYSTEMS:
        if not db.scalars(select(System).where(System.code == data["code"])).first():
            db.add(System(**data))
            log_event(db, actor="system", action="system.registered", entity_type="system",
                      entity_id=data["code"], details={k: v for k, v in data.items() if k != "description"})
    db.flush()
    for code, data in DEMO_LIFECYCLE.items():
        system = db.scalars(select(System).where(System.code == code)).first()
        if system and not db.scalars(select(SystemLifecycle).where(SystemLifecycle.system_id == system.id)).first():
            db.add(SystemLifecycle(system_id=system.id, **data))
            log_event(db, actor="system", action="lifecycle.registered", entity_type="system", entity_id=code,
                      details={**data, "source": "demo seed (initial validation state)"})
    db.commit()
