from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.recall import Recall
from app.models.user import User
from app.schemas import RecallOut, RecallPage
from app.security import get_current_user

router = APIRouter(prefix="/api/recalls", tags=["recalls"])


@router.get("", response_model=RecallPage)
def search_recalls(q: str | None = Query(None, max_length=100), classification: str | None = None,
                   status: str | None = None, limit: int = Query(50, ge=1, le=200),
                   offset: int = Query(0, ge=0), db: Session = Depends(get_db),
                   _: User = Depends(get_current_user)):
    """Search by product, firm, reason, recall number or lot information."""
    filters = []
    if q:
        like = f"%{q.strip()}%"
        filters.append(or_(Recall.product_description.ilike(like), Recall.recalling_firm.ilike(like),
                           Recall.reason_for_recall.ilike(like), Recall.recall_number.ilike(like),
                           Recall.code_info.ilike(like)))
    if classification:
        filters.append(Recall.classification == classification)
    if status:
        filters.append(Recall.status == status)
    total = db.scalar(select(func.count()).select_from(Recall).where(*filters)) or 0
    items = db.scalars(select(Recall).where(*filters)
                       .order_by(Recall.report_date.desc(), Recall.recall_number.desc())
                       .offset(offset).limit(limit)).all()
    return RecallPage(total=total, items=items)


@router.get("/{recall_number}", response_model=RecallOut)
def get_recall(recall_number: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    recall = db.scalars(select(Recall).where(Recall.recall_number == recall_number)).first()
    if recall is None:
        raise HTTPException(status_code=404, detail=f"Recall {recall_number} not found")
    return recall
