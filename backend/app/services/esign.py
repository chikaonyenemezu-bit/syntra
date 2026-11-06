"""Executing an electronic signature: re-authenticate, then record who signed what, when, and why."""
from sqlalchemy.orm import Session

from app.models.esignature import ESignature
from app.models.user import User
from app.security import verify_password
from app.services.audit_logger import log_event

ROLE_LABEL = {"system_owner": "System Owner", "qa": "QA", "it_ops": "IT Operations",
              "admin": "Administrator", "viewer": "Viewer"}


class SignatureError(Exception):
    """The password was wrong. The caller must roll back, then record the failed attempt."""


def sign(db: Session, user: User, password: str, *, entity_type: str, entity_id: str,
         meaning: str, comment: str = "") -> ESignature:
    if not password or not verify_password(password, user.password_hash):
        raise SignatureError("Signature failed: the password is incorrect")
    sig = ESignature(entity_type=entity_type, entity_id=entity_id, signer=user.username,
                     signer_name=user.full_name, signer_role=user.role, meaning=meaning,
                     comment=comment.strip())
    db.add(sig)
    db.flush()
    log_event(db, actor=user.username, action="esign.signed", entity_type=entity_type, entity_id=entity_id,
              details={"meaning": meaning, "signer_name": user.full_name, "role": user.role,
                       "signature_id": sig.id, "comment": sig.comment})
    return sig


def record_failed_signature(db: Session, user: User, entity_type: str, entity_id: str, meaning: str) -> None:
    log_event(db, actor=user.username, action="esign.failed", entity_type=entity_type, entity_id=entity_id,
              details={"meaning": meaning, "reason": "incorrect password"})
