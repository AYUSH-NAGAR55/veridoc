import datetime

from pydantic import BaseModel


class PageOut(BaseModel):
    page_number: int
    page_type: str
    ocr_confidence: float | None = None
    extraction_notes: str = ""
    preview: str = ""

    class Config:
        from_attributes = True


class ValidationNote(BaseModel):
    rule: str
    passed: bool
    message: str


class FieldOut(BaseModel):
    id: str
    document_id: str
    field_name: str
    field_value: str
    original_ai_value: str | None = None
    confidence: float
    source_page: int | None = None
    source_snippet: str = ""
    status: str
    validation_notes: list[dict] = []

    class Config:
        from_attributes = True


class DocumentOut(BaseModel):
    id: str
    filename: str
    doc_type: str
    status: str
    page_count: int
    error_message: str | None = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class DocumentDetailOut(DocumentOut):
    pages: list[PageOut] = []
    fields: list[FieldOut] = []


class CorrectFieldIn(BaseModel):
    corrected_value: str


class AskIn(BaseModel):
    question: str


class AskOut(BaseModel):
    answer: str
    source_page: int | None
    source_label: str
    confidence: float
