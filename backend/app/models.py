"""SQLAlchemy models for VeriDoc.

A Document goes through: uploaded -> classifying -> extracting -> validating
-> ready (or partially ready with items sitting in human review).
"""
import datetime
import enum
import uuid

from sqlalchemy import (Column, String, Integer, Float, Text, DateTime,
                         ForeignKey, Enum, JSON, Boolean)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def gen_id() -> str:
    return uuid.uuid4().hex[:12]


class DocStatus(str, enum.Enum):
    uploaded = "uploaded"
    classifying = "classifying"
    extracting = "extracting"
    validating = "validating"
    indexing = "indexing"
    ready = "ready"
    needs_review = "needs_review"
    failed = "failed"


class PageType(str, enum.Enum):
    text = "text"
    scanned = "scanned"
    table = "table"
    mixed = "mixed"


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=gen_id)
    filename = Column(String, nullable=False)
    doc_type = Column(String, default="unknown")  # invoice / financial_report / generic
    status = Column(Enum(DocStatus), default=DocStatus.uploaded)
    page_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow,
                         onupdate=datetime.datetime.utcnow)

    pages = relationship("Page", back_populates="document", cascade="all, delete-orphan")
    fields = relationship("ExtractedField", back_populates="document", cascade="all, delete-orphan")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Page(Base):
    __tablename__ = "pages"

    id = Column(String, primary_key=True, default=gen_id)
    document_id = Column(String, ForeignKey("documents.id"))
    page_number = Column(Integer, nullable=False)
    page_type = Column(Enum(PageType), default=PageType.text)
    raw_text = Column(Text, default="")
    tables_json = Column(JSON, default=list)   # list of tables, each a list of rows
    ocr_confidence = Column(Float, nullable=True)
    extraction_notes = Column(Text, default="")

    document = relationship("Document", back_populates="pages")


class ExtractedField(Base):
    """A single structured field pulled out of the document, e.g. 'Tax': 26100."""
    __tablename__ = "extracted_fields"

    id = Column(String, primary_key=True, default=gen_id)
    document_id = Column(String, ForeignKey("documents.id"))
    field_name = Column(String, nullable=False)
    field_value = Column(String, nullable=False)
    original_ai_value = Column(String, nullable=True)  # kept for audit trail if corrected
    confidence = Column(Float, default=0.0)
    source_page = Column(Integer, nullable=True)
    source_snippet = Column(Text, default="")
    status = Column(String, default="pending")  # pending / accepted / corrected / auto_accepted
    validation_notes = Column(JSON, default=list)  # list of {rule, passed, message}
    corrected_at = Column(DateTime, nullable=True)

    document = relationship("Document", back_populates="fields")


class Chunk(Base):
    """A retrievable slice of verified document content, used for RAG."""
    __tablename__ = "chunks"

    id = Column(String, primary_key=True, default=gen_id)
    document_id = Column(String, ForeignKey("documents.id"))
    page_number = Column(Integer, nullable=False)
    section_label = Column(String, default="")
    text = Column(Text, nullable=False)
    confidence = Column(Float, default=1.0)

    document = relationship("Document", back_populates="chunks")
