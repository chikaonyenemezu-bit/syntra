from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.system import System
from app.models.telemetry import Telemetry
from app.models.user import User
from app.schemas import SystemOut, TelemetryOut
from app.security import get_current_user

router = APIRouter(prefix="/api/systems", tags=["systems"])


def get_system_or_404(db: Session, code: str) -> System:
    system = db.scalars(select(System).where(System.code == code)).first()
    if system is None:
        raise HTTPException(status_code=404, detail=f"System {code} not found")
    return system


@router.get("", response_model=list[SystemOut])
def list_systems(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(System).order_by(System.code)).all()


@router.get("/{code}", response_model=SystemOut)
def get_system(code: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return get_system_or_404(db, code)


@router.get("/{code}/telemetry", response_model=list[TelemetryOut])
def system_telemetry(code: str, limit: int = Query(60, ge=1, le=1000),
                     db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    system = get_system_or_404(db, code)
    rows = db.scalars(
        select(Telemetry).where(Telemetry.system_id == system.id)
        .order_by(Telemetry.id.desc()).limit(limit)
    ).all()
    return list(reversed(rows))
