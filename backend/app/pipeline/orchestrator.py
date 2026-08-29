"""Wires together Steps 2-8 for a single uploaded document."""
import traceback

from sqlalchemy.orm import Session

from .. import models
from . import classifier, extractor, structurer, validator, indexer

# In-memory vector index per document. A real deployment would persist
# this (e.g. FAISS index files on disk) rather than keep it in process
# memory, but for a single-process demo this is simplest and fastest.
DOCUMENT_INDEXES: dict[str, indexer.VectorIndex] = {}


def process_document(db: Session, document_id: str, pdf_path: str):
    doc = db.query(models.Document).get(document_id)
    if doc is None:
        return
    try:
        doc.status = models.DocStatus.classifying
        db.commit()

        assessments = classifier.classify_pdf(pdf_path)
        doc.page_count = len(assessments)
        db.commit()

        doc.status = models.DocStatus.extracting
        db.commit()

        page_texts = []
        ocr_conf_by_page = {}
        all_text_parts = []

        for assessment in assessments:
            extraction = extractor.extract_page(pdf_path, assessment)
            page_row = models.Page(
                document_id=doc.id,
                page_number=assessment.page_number,
                page_type=models.PageType(assessment.page_type),
                raw_text=extraction.text,
                tables_json=extraction.tables,
                ocr_confidence=extraction.ocr_confidence,
                extraction_notes=extraction.notes,
            )
            db.add(page_row)
            page_texts.append((assessment.page_number, extraction.text))
            all_text_parts.append(extraction.text)
            if extraction.ocr_confidence is not None:
                ocr_conf_by_page[assessment.page_number] = extraction.ocr_confidence
        db.commit()

        full_text = "\n".join(all_text_parts)
        doc.doc_type = structurer.detect_doc_type(full_text)
        db.commit()

        doc.status = models.DocStatus.validating
        db.commit()

        raw_hits = structurer.extract_fields(doc.doc_type, page_texts)
        validated_fields = validator.validate_and_score(doc.doc_type, raw_hits, ocr_conf_by_page)

        any_pending = False
        for vf in validated_fields:
            if vf.auto_status == "pending":
                any_pending = True
            field_row = models.ExtractedField(
                document_id=doc.id,
                field_name=vf.field_name,
                field_value=vf.value,
                original_ai_value=vf.value,
                confidence=vf.confidence,
                source_page=vf.source_page or None,
                source_snippet=vf.source_snippet,
                status=vf.auto_status,
                validation_notes=vf.notes,
            )
            db.add(field_row)
        db.commit()

        doc.status = models.DocStatus.indexing
        db.commit()

        chunks = []
        for page_number, text in page_texts:
            chunks.extend(indexer.chunk_page_text(text, page_number))
        vindex = indexer.VectorIndex()
        vindex.fit(chunks)
        DOCUMENT_INDEXES[doc.id] = vindex

        for c in chunks:
            db.add(models.Chunk(
                document_id=doc.id, page_number=c["page_number"],
                section_label=c.get("section_label", ""), text=c["text"], confidence=1.0,
            ))
        db.commit()

        doc.status = models.DocStatus.needs_review if any_pending else models.DocStatus.ready
        db.commit()

    except Exception as exc:  # noqa: BLE001
        doc.status = models.DocStatus.failed
        doc.error_message = f"{exc}\n{traceback.format_exc()[-800:]}"
        db.commit()


def get_or_rebuild_index(db: Session, document_id: str) -> indexer.VectorIndex:
    if document_id in DOCUMENT_INDEXES:
        return DOCUMENT_INDEXES[document_id]
    chunks = db.query(models.Chunk).filter(models.Chunk.document_id == document_id).all()
    vindex = indexer.VectorIndex()
    vindex.fit([{"page_number": c.page_number, "section_label": c.section_label, "text": c.text} for c in chunks])
    DOCUMENT_INDEXES[document_id] = vindex
    return vindex
