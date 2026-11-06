import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.database import get_db
from app.integrations.openfda import get_source
from app.models.ingestion_job import IngestionJob
from app.models.recall import Recall
from app.models.user import Role, User
from app.schemas import (IngestionJobDetail, IngestionJobOut, IntegrationOut, RejectedRecordOut,
                         SyncRequest, SystemOut)
from app.security import get_current_user, require_roles
from app.services import fda_pipeline
from app.services.audit_logger import log_event

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


def _integration_or_404(db: Session):
    try:
        return fda_pipeline.get_integration(db)
    except fda_pipeline.IntegrationNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


def _loads(text: str):
    try:
        return json.loads(text)
    except ValueError:
        return text


def _detail(job: IngestionJob) -> IngestionJobDetail:
    out = IngestionJobDetail.model_validate(IngestionJobOut.model_validate(job).model_dump())
    out.rejected_records = [
        RejectedRecordOut(id=r.id, record_key=r.record_key, reasons=_loads(r.reasons),
                          payload=_loads(r.payload), rejected_at=r.rejected_at)
        for r in job.rejected_records
    ]
    return out


@router.get("", response_model=list[IntegrationOut])
def list_integrations(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    system = _integration_or_404(db)
    last = db.scalars(select(IngestionJob).where(IngestionJob.system_id == system.id)
                      .order_by(IngestionJob.id.desc()).limit(1)).first()
    return [IntegrationOut(
        system=SystemOut.model_validate(system),
        last_job=IngestionJobOut.model_validate(last) if last else None,
        sync_enabled=settings.fda_sync_enabled,
        sync_interval_minutes=settings.fda_sync_interval_minutes,
        lookback_days=settings.fda_lookback_days,
        rejection_threshold=settings.fda_rejection_threshold,
        recalls_total=db.scalar(select(func.count()).select_from(Recall)) or 0,
    )]


@router.post("/{code}/sync", response_model=IngestionJobDetail)
def sync_now(code: str, body: SyncRequest, db: Session = Depends(get_db),
             user: User = Depends(require_roles(Role.IT_OPS, Role.ADMIN))):
    """Run a sync now. 'sample' and 'sample_with_errors' load bundled demo data in openFDA format."""
    system = _integration_or_404(db)
    if code != system.code:
        raise HTTPException(status_code=404, detail=f"Integration {code} not found")
    log_event(db, actor=user.username, action="integration.sync_requested", entity_type="system",
              entity_id=system.code, details={"source": body.source})
    job = fda_pipeline.run_sync(db, get_source(body.source), trigger="manual", actor=user.username)
    db.commit()
    job = db.scalars(select(IngestionJob).options(selectinload(IngestionJob.rejected_records))
                     .where(IngestionJob.id == job.id)).one()
    return _detail(job)


@router.get("/jobs", response_model=list[IngestionJobOut])
def list_jobs(limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db),
              _: User = Depends(get_current_user)):
    return db.scalars(select(IngestionJob).order_by(IngestionJob.id.desc()).limit(limit)).all()


@router.get("/jobs/{number}", response_model=IngestionJobDetail)
def get_job(number: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    job = db.scalars(select(IngestionJob).options(selectinload(IngestionJob.rejected_records))
                     .where(IngestionJob.number == number)).first()
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {number} not found")
    return _detail(job)
