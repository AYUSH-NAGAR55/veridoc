import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("", response_model=list[schemas.FieldOut])
def get_review_queue(db: Session = Depends(get_db)):
    return (
        db.query(models.ExtractedField)
        .filter(models.ExtractedField.status == "pending")
        .order_by(models.ExtractedField.confidence.asc())
        .all()
    )


@router.post("/{field_id}/accept", response_model=schemas.FieldOut)
def accept_field(field_id: str, db: Session = Depends(get_db)):
    field = db.query(models.ExtractedField).get(field_id)
    if not field:
        raise HTTPException(404, "Field not found.")
    field.status = "accepted"
    field.confidence = max(field.confidence, 0.95)
    field.corrected_at = datetime.datetime.utcnow()
    db.commit()
    _maybe_mark_document_ready(db, field.document_id)
    return field


@router.post("/{field_id}/correct", response_model=schemas.FieldOut)
def correct_field(field_id: str, payload: schemas.CorrectFieldIn, db: Session = Depends(get_db)):
    field = db.query(models.ExtractedField).get(field_id)
    if not field:
        raise HTTPException(404, "Field not found.")
    field.field_value = payload.corrected_value
    field.status = "corrected"
    field.confidence = 0.99
    field.corrected_at = datetime.datetime.utcnow()
    db.commit()
    _maybe_mark_document_ready(db, field.document_id)
    return field


def _maybe_mark_document_ready(db: Session, document_id: str):
    remaining = (
        db.query(models.ExtractedField)
        .filter(models.ExtractedField.document_id == document_id, models.ExtractedField.status == "pending")
        .count()
    )
    if remaining == 0:
        doc = db.query(models.Document).get(document_id)
        if doc and doc.status == models.DocStatus.needs_review:
            doc.status = models.DocStatus.ready
            db.commit()
