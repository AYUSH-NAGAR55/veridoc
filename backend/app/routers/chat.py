from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..pipeline import orchestrator, qa

router = APIRouter(prefix="/api/documents", tags=["chat"])


@router.post("/{document_id}/ask", response_model=schemas.AskOut)
def ask_question(document_id: str, payload: schemas.AskIn, db: Session = Depends(get_db)):
    doc = db.query(models.Document).get(document_id)
    if not doc:
        raise HTTPException(404, "Document not found.")
    if doc.status in (models.DocStatus.uploaded, models.DocStatus.classifying,
                       models.DocStatus.extracting, models.DocStatus.validating,
                       models.DocStatus.indexing):
        raise HTTPException(409, "Document is still processing — try again shortly.")

    vindex = orchestrator.get_or_rebuild_index(db, document_id)
    hits = vindex.search(payload.question, k=4)

    fields = db.query(models.ExtractedField).filter(models.ExtractedField.document_id == document_id).all()
    answer = qa.build_answer(payload.question, fields, hits)

    return schemas.AskOut(
        answer=answer.text,
        source_page=answer.source_page,
        source_label=answer.source_label,
        confidence=answer.confidence,
    )
