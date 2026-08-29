"""Steps 5 & 6 — Validate the extraction, then decide a confidence level.

The validator does not just trust what the structurer found. It:
  - re-parses numbers/dates and flags ones that don't parse cleanly
  - cross-checks arithmetic (subtotal + tax = total)
  - flags fields that are missing entirely
  - folds all of that, plus OCR/pattern confidence, into one score per field

Fields at or above ACCEPT_THRESHOLD are auto-accepted. Everything else
is queued for human review (Step 7).
"""
import re
from dataclasses import dataclass

ACCEPT_THRESHOLD = 0.90

REQUIRED_FIELDS = {
    "invoice": ["Vendor", "Invoice Number", "Invoice Date", "Subtotal", "Tax", "Total"],
    "financial_report": ["Company", "Revenue", "Operating expenses", "Net income"],
}

DATE_PATTERNS = [
    r"^\d{4}[\-\/]\d{1,2}[\-\/]\d{1,2}$",
    r"^\d{1,2}[\-\/]\d{1,2}[\-\/]\d{2,4}$",
    r"^[A-Za-z]+\s\d{1,2},?\s\d{4}$",
]


@dataclass
class ValidatedField:
    field_name: str
    value: str
    numeric_value: float | None
    confidence: float
    source_page: int
    source_snippet: str
    notes: list   # list of {"rule": str, "passed": bool, "message": str}
    auto_status: str  # "auto_accepted" | "pending"


def parse_number(raw: str) -> float | None:
    cleaned = re.sub(r"[₹$€£,\s]", "", raw)
    multiplier = 1.0
    lowered = raw.lower()
    if "crore" in lowered or re.search(r"\bcr\b", lowered):
        multiplier = 1  # keep unit as stated; comparisons stay within same unit
    cleaned = re.sub(r"(crore|cr|million|mn|lakh|bn|billion)", "", cleaned, flags=re.IGNORECASE).strip()
    try:
        return float(cleaned) * multiplier
    except ValueError:
        return None


def is_valid_date(raw: str) -> bool:
    return any(re.match(p, raw.strip()) for p in DATE_PATTERNS)


def validate_and_score(doc_type: str, hits: list, ocr_confidence_by_page: dict) -> list[ValidatedField]:
    """hits: list of RawFieldHit from structurer.py"""
    by_name = {h.field_name: h for h in hits}
    validated: list[ValidatedField] = []

    numeric_cache = {}
    for h in hits:
        numeric_cache[h.field_name] = parse_number(h.value)

    required = REQUIRED_FIELDS.get(doc_type, [])
    for field_name in required:
        hit = by_name.get(field_name)
        if hit is None:
            validated.append(ValidatedField(
                field_name=field_name, value="", numeric_value=None, confidence=0.0,
                source_page=0, source_snippet="",
                notes=[{"rule": "presence", "passed": False, "message": "Field not found in document."}],
                auto_status="pending",
            ))
            continue

        notes = []
        confidence = hit.pattern_specificity

        page_ocr_conf = ocr_confidence_by_page.get(hit.page_number)
        if page_ocr_conf is not None:
            confidence = (confidence + page_ocr_conf) / 2
            notes.append({"rule": "ocr_quality", "passed": page_ocr_conf >= 0.7,
                           "message": f"Source page OCR confidence {page_ocr_conf * 100:.0f}%."})

        if field_name == "Invoice Date":
            valid_date = is_valid_date(hit.value)
            notes.append({"rule": "date_format", "passed": valid_date,
                           "message": "Recognisable date format." if valid_date else "Date format looks unusual."})
            confidence = confidence * (1.0 if valid_date else 0.5)

        numeric_fields = {"Subtotal", "Tax", "Total", "Revenue", "Operating expenses", "Expenses", "Net income", "Assets", "Liabilities"}
        if field_name in numeric_fields:
            parsed = numeric_cache.get(field_name)
            ok = parsed is not None
            notes.append({"rule": "numeric_parse", "passed": ok,
                           "message": "Parsed as a number." if ok else "Could not parse a clean number."})
            if not ok:
                confidence *= 0.4

        validated.append(ValidatedField(
            field_name=field_name, value=hit.value, numeric_value=numeric_cache.get(field_name),
            confidence=round(min(confidence, 0.99), 3), source_page=hit.page_number,
            source_snippet=hit.snippet, notes=notes, auto_status="pending",
        ))

    _cross_check_invoice_math(validated, numeric_cache)
    _cross_check_financials(validated, numeric_cache)

    for v in validated:
        v.auto_status = "auto_accepted" if v.confidence >= ACCEPT_THRESHOLD else "pending"

    return validated


def _cross_check_invoice_math(validated: list[ValidatedField], numeric_cache: dict):
    sub = numeric_cache.get("Subtotal")
    tax = numeric_cache.get("Tax")
    total = numeric_cache.get("Total")
    if sub is None or tax is None or total is None:
        return
    expected = round(sub + tax, 2)
    passed = abs(expected - round(total, 2)) < max(0.01 * total, 1.0)
    message = (f"Subtotal + Tax = {expected:,.2f}, matches stated Total." if passed
               else f"Subtotal + Tax = {expected:,.2f}, but stated Total is {total:,.2f} — mismatch.")
    for v in validated:
        if v.field_name in ("Subtotal", "Tax", "Total"):
            v.notes.append({"rule": "arithmetic_check", "passed": passed, "message": message})
            if not passed:
                v.confidence *= 0.55
            v.confidence = round(min(v.confidence, 0.99), 3)


def _cross_check_financials(validated: list[ValidatedField], numeric_cache: dict):
    revenue = numeric_cache.get("Revenue")
    opex = numeric_cache.get("Operating expenses") or numeric_cache.get("Expenses")
    net_income = numeric_cache.get("Net income")
    if revenue is None or opex is None or net_income is None:
        return
    expected = round(revenue - opex, 2)
    tolerance = max(0.05 * abs(revenue), 5.0)
    passed = abs(expected - round(net_income, 2)) <= tolerance
    message = (f"Revenue - Operating expenses ≈ {expected:,.2f}, consistent with stated Net income."
               if passed else
               f"Revenue - Operating expenses ≈ {expected:,.2f}, but stated Net income is {net_income:,.2f} — check for other line items.")
    for v in validated:
        if v.field_name in ("Revenue", "Operating expenses", "Expenses", "Net income"):
            v.notes.append({"rule": "arithmetic_check", "passed": passed, "message": message})
            if not passed:
                v.confidence *= 0.7
            v.confidence = round(min(v.confidence, 0.99), 3)
