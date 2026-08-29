"""Step 4 — Extract important structured information.

VeriDoc ships without a hosted LLM available in this environment (the
architecture is designed around a local Ollama model — see
`pipeline/llm_client.py` for the swap-in point). In place of that, this
module uses a document-understanding layer built from field-anchored
regular expressions and layout heuristics, tuned for the two document
families called out in the spec: invoices and financial reports.

Each field extraction records *why* it believes what it believes
(the matched span, the pattern that fired) so the validator and the
confidence step downstream have something real to grade.
"""
import re
from dataclasses import dataclass, field as dc_field

CURRENCY_NUM = r"[₹$€£]?\s?[\d][\d,]*\.?\d*"

INVOICE_PATTERNS = {
    "Vendor": [r"(?:vendor|seller|from|bill\s?from)\s*[:\-]\s*(.+)"],
    "Invoice Number": [r"(?:invoice\s?(?:no|number|#)|inv\s?#)\s*[:\-]?\s*([A-Za-z0-9\-\/]+)"],
    "Invoice Date": [r"(?:invoice\s?date|date)\s*[:\-]\s*([0-9]{1,4}[\-\/][0-9]{1,2}[\-\/][0-9]{1,4}|[A-Za-z]+\s\d{1,2},?\s\d{4})"],
    "Subtotal": [r"sub\s?-?\s?total\s*[:\-]?\s*(" + CURRENCY_NUM + ")"],
    "Tax": [r"(?:tax|gst|vat)\s*(?:\(\s*\d+%\s*\))?\s*[:\-]?\s*(" + CURRENCY_NUM + ")"],
    "Total": [r"(?<!sub)(?:^|\n)\s*total\s*[:\-]?\s*(" + CURRENCY_NUM + ")", r"grand\s?total\s*[:\-]?\s*(" + CURRENCY_NUM + ")"],
}

FINANCIAL_PATTERNS = {
    "Company": [r"(?:company|entity|organisation|organization)\s*[:\-]\s*(.+)"],
    "Revenue": [r"(?:total\s?)?revenue\s*[:\-]?\s*(" + CURRENCY_NUM + r"\s?(?:crore|cr|million|mn|lakh|bn|billion)?)"],
    "Operating expenses": [r"operating\s?expenses?\s*[:\-]?\s*(" + CURRENCY_NUM + r"\s?(?:crore|cr|million|mn|lakh|bn|billion)?)"],
    "Expenses": [r"(?<!operating\s)(?:total\s?)?expenses?\s*[:\-]?\s*(" + CURRENCY_NUM + r"\s?(?:crore|cr|million|mn|lakh|bn|billion)?)"],
    "Net income": [r"net\s?(?:income|profit)\s*[:\-]?\s*(" + CURRENCY_NUM + r"\s?(?:crore|cr|million|mn|lakh|bn|billion)?)"],
    "Assets": [r"(?:total\s?)?assets\s*[:\-]?\s*(" + CURRENCY_NUM + r"\s?(?:crore|cr|million|mn|lakh|bn|billion)?)"],
    "Liabilities": [r"(?:total\s?)?liabilities\s*[:\-]?\s*(" + CURRENCY_NUM + r"\s?(?:crore|cr|million|mn|lakh|bn|billion)?)"],
}

INVOICE_HINTS = ("invoice", "bill to", "purchase order", "po number")
FINANCIAL_HINTS = ("revenue", "net income", "balance sheet", "operating expenses", "annual report", "quarterly report")


@dataclass
class RawFieldHit:
    field_name: str
    value: str
    page_number: int
    snippet: str
    pattern_specificity: float   # 0-1, how "anchored" the match looked


def detect_doc_type(all_text: str) -> str:
    lowered = all_text.lower()
    invoice_score = sum(lowered.count(h) for h in INVOICE_HINTS)
    financial_score = sum(lowered.count(h) for h in FINANCIAL_HINTS)
    if invoice_score == 0 and financial_score == 0:
        return "generic"
    return "invoice" if invoice_score >= financial_score else "financial_report"


def extract_fields(doc_type: str, pages: list[tuple[int, str]]) -> list[RawFieldHit]:
    """pages: list of (page_number, text)"""
    patterns = INVOICE_PATTERNS if doc_type == "invoice" else FINANCIAL_PATTERNS
    if doc_type == "generic":
        return []

    hits: list[RawFieldHit] = []
    seen_fields = set()

    for page_number, text in pages:
        for field_name, regex_list in patterns.items():
            if field_name in seen_fields:
                continue
            for pattern in regex_list:
                m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if m:
                    value = m.group(1).strip().rstrip(".,")
                    if not value:
                        continue
                    snippet_start = max(0, m.start() - 30)
                    snippet_end = min(len(text), m.end() + 30)
                    snippet = text[snippet_start:snippet_end].strip().replace("\n", " ")

                    specificity = 0.9 if ":" in pattern or "-" in pattern else 0.7
                    hits.append(RawFieldHit(
                        field_name=field_name,
                        value=value,
                        page_number=page_number,
                        snippet=snippet,
                        pattern_specificity=specificity,
                    ))
                    seen_fields.add(field_name)
                    break
    return hits
