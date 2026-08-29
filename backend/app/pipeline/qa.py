"""Steps 9 & 10 — Ask questions, get a grounded answer.

Two answer paths:
  1. The question matches a verified structured field closely (e.g. "what
     was the revenue" -> the "Revenue" field) -> answer directly from that
     field, citing its page and confidence.
  2. Otherwise, fall back to retrieval over the chunk index and surface the
     most relevant passage as the answer, with its source and a similarity-
     derived confidence.

No hosted LLM is available in this environment, so composition here is
template + extractive rather than generative — the retrieval/validation
scaffolding is the part of the spec this build focuses on proving out,
and it is written so a real LLM call can be dropped into `_compose_answer`
without touching the retrieval or citation logic.
"""
import re
from dataclasses import dataclass

FIELD_ALIASES = {
    "revenue": "Revenue", "sales": "Revenue",
    "tax": "Tax", "gst": "Tax", "vat": "Tax",
    "subtotal": "Subtotal",
    "total": "Total",
    "invoice number": "Invoice Number", "invoice no": "Invoice Number",
    "invoice date": "Invoice Date", "date": "Invoice Date",
    "vendor": "Vendor", "seller": "Vendor",
    "expenses": "Operating expenses", "operating expenses": "Operating expenses",
    "net income": "Net income", "profit": "Net income",
    "assets": "Assets", "liabilities": "Liabilities",
    "company": "Company",
}


@dataclass
class Answer:
    text: str
    source_page: int | None
    source_label: str
    confidence: float


def match_field_alias(question: str) -> str | None:
    q = question.lower()
    for alias, field_name in FIELD_ALIASES.items():
        if alias in q:
            return field_name
    return None


def answer_from_fields(question: str, fields: list) -> Answer | None:
    """fields: list of ExtractedField ORM rows"""
    target = match_field_alias(question)
    if not target:
        return None
    for f in fields:
        if f.field_name == target and f.status in ("auto_accepted", "accepted", "corrected"):
            return Answer(
                text=f"The {f.field_name.lower()} is {f.field_value}.",
                source_page=f.source_page,
                source_label=f"Extracted field — {f.field_name}",
                confidence=f.confidence if f.status != "corrected" else 0.99,
            )
    return None


def answer_from_chunks(question: str, hits: list[tuple[dict, float]]) -> Answer | None:
    if not hits:
        return None
    best_chunk, sim = hits[0]
    sentence = _best_sentence(best_chunk["text"], question)
    label = best_chunk.get("section_label") or "Document text"
    confidence = round(min(0.55 + sim * 0.4, 0.97), 3)
    return Answer(
        text=sentence,
        source_page=best_chunk["page_number"],
        source_label=label,
        confidence=confidence,
    )


def _best_sentence(text: str, question: str) -> str:
    rough_sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = []
    for s in rough_sentences:
        sentences.extend(line.strip() for line in s.split("\n") if line.strip())

    q_words = set(re.findall(r"[a-zA-Z]{3,}", question.lower()))
    best, best_score = (sentences[0] if sentences else text.strip()[:400]), -1
    for s in sentences:
        s_words = set(re.findall(r"[a-zA-Z]{3,}", s.lower()))
        score = len(q_words & s_words)
        if score > best_score and s.strip():
            best_score = score
            best = s.strip()
    return best


def build_answer(question: str, fields: list, index_hits: list[tuple[dict, float]]) -> Answer:
    field_answer = answer_from_fields(question, fields)
    if field_answer:
        return field_answer
    chunk_answer = answer_from_chunks(question, index_hits)
    if chunk_answer:
        return chunk_answer
    return Answer(
        text="I couldn't find anything in this document that answers that. Try rephrasing, or check the document actually covers this.",
        source_page=None, source_label="", confidence=0.0,
    )
