import os
import shutil
import uuid

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..pipeline import orchestrator

router = APIRouter(prefix="/api/documents", tags=["documents"])

STORAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "storage")
os.makedirs(STORAGE_DIR, exist_ok=True)


@router.post("", response_model=schemas.DocumentOut)
def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported.")

    doc = models.Document(filename=file.filename, status=models.DocStatus.uploaded)
    db.add(doc)
    db.commit()
    db.refresh(doc)

    safe_name = f"{doc.id}_{uuid.uuid4().hex[:6]}.pdf"
    dest_path = os.path.join(STORAGE_DIR, safe_name)
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    background_tasks.add_task(_run_pipeline, doc.id, dest_path)
    return doc


def _run_pipeline(document_id: str, pdf_path: str):
    from ..database import SessionLocal
    db = SessionLocal()
    try:
        orchestrator.process_document(db, document_id, pdf_path)
    finally:
        db.close()


@router.get("", response_model=list[schemas.DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    return db.query(models.Document).order_by(models.Document.created_at.desc()).all()


@router.get("/{document_id}", response_model=schemas.DocumentDetailOut)
def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(models.Document).get(document_id)
    if not doc:
        raise HTTPException(404, "Document not found.")
    out = schemas.DocumentDetailOut.model_validate(doc)
    for p, page_row in zip(out.pages, sorted(doc.pages, key=lambda x: x.page_number)):
        p.preview = (page_row.raw_text or "")[:220]
    return out


@router.delete("/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(models.Document).get(document_id)
    if not doc:
        raise HTTPException(404, "Document not found.")
    orchestrator.DOCUMENT_INDEXES.pop(document_id, None)
    db.delete(doc)
    db.commit()
    return {"ok": True}
