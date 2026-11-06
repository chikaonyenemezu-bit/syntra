"""Validation rules for incoming recall records.

Each rule is a user requirement (validation/URS.md, URS-INT-03). A record that fails any rule is
rejected with every reason that applies, so the data owner can see all problems at once.
"""
import re
from dataclasses import dataclass, field
from datetime import date, datetime

REQUIRED = ["recall_number", "classification", "status", "product_type",
            "product_description", "reason_for_recall", "recalling_firm", "report_date"]
CLASSIFICATIONS = {"Class I", "Class II", "Class III"}
STATUSES = {"Ongoing", "Completed", "Terminated", "Pending"}
RECALL_NUMBER = re.compile(r"^[A-Z]-\d{3,5}-\d{4}$")
DATE_FIELDS = ["recall_initiation_date", "report_date", "termination_date"]
OPTIONAL_TEXT = ["event_id", "city", "state", "country", "distribution_pattern",
                 "code_info", "product_quantity", "voluntary_mandated"]


@dataclass
class ValidationResult:
    record: dict | None              # normalised record when valid
    reasons: list[str] = field(default_factory=list)
    key: str = ""

    @property
    def valid(self) -> bool:
        return not self.reasons


def _text(value) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    value = " ".join(value.split())
    return value or None


def _date(value: str | None) -> date | None:
    """openFDA dates are YYYYMMDD strings."""
    if value is None:
        return None
    return datetime.strptime(value, "%Y%m%d").date()


def validate_recall(raw: dict, *, today: date | None = None, position: int = 0) -> ValidationResult:
    today = today or date.today()
    reasons: list[str] = []
    if not isinstance(raw, dict):
        return ValidationResult(None, ["Record is not a JSON object"], f"#{position}")

    rec = {k: _text(raw.get(k)) for k in REQUIRED + OPTIONAL_TEXT + DATE_FIELDS}
    key = (rec["recall_number"] or f"#{position}")[:64]

    for name in REQUIRED:
        if rec[name] is None:
            reasons.append(f"Missing required field '{name}'")

    if rec["recall_number"] and not RECALL_NUMBER.match(rec["recall_number"]):
        reasons.append(f"Recall number '{rec['recall_number']}' does not match format X-NNNN-YYYY")
    if rec["classification"] and rec["classification"] not in CLASSIFICATIONS:
        reasons.append(f"Unknown classification '{rec['classification']}' (expected Class I, II or III)")
    if rec["status"] and rec["status"] not in STATUSES:
        reasons.append(f"Unknown status '{rec['status']}'")
    if rec["product_type"] and rec["product_type"] != "Drugs":
        reasons.append(f"Product type '{rec['product_type']}' is not 'Drugs'")

    dates: dict[str, date | None] = {}
    for name in DATE_FIELDS:
        try:
            dates[name] = _date(rec[name])
        except ValueError:
            dates[name] = None
            reasons.append(f"Invalid date in '{name}': '{rec[name]}' (expected YYYYMMDD)")
        if dates[name] and dates[name] > today:
            reasons.append(f"Date in '{name}' ({dates[name]:%Y-%m-%d}) is in the future")

    start, end = dates["recall_initiation_date"], dates["termination_date"]
    if start and end and end < start:
        reasons.append(f"Termination date {end:%Y-%m-%d} is before initiation date {start:%Y-%m-%d}")

    if reasons:
        return ValidationResult(None, reasons, key)
    return ValidationResult({**rec, **dates}, [], key)
