from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas import Token, UserOut
from app.security import create_access_token, get_current_user, verify_password
from app.services.audit_logger import log_event

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalars(select(User).where(User.username == form.username)).first()
    if user is None or not user.active or not verify_password(form.password, user.password_hash):
        # Failed logins are audited too (Annex 11 §12: security incidents).
        log_event(db, actor=form.username or "unknown", action="auth.login_failed",
                  entity_type="user", entity_id=form.username or "unknown")
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    log_event(db, actor=user.username, action="auth.login", entity_type="user", entity_id=user.username)
    db.commit()
    return Token(access_token=create_access_token(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
