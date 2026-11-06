import copy
import json
from datetime import date

import pytest

from app.integrations.openfda import FIXTURES
from app.services.data_validator import validate_recall

TODAY = date(2026, 11, 6)
SAMPLE = json.loads((FIXTURES / "fda_sample.json").read_text())["results"]


def good() -> dict:
    return copy.deepcopy(SAMPLE[0])


def test_every_sample_record_is_valid():
    for rec in SAMPLE:
        result = validate_recall(rec, today=TODAY)
        assert result.valid, (rec["recall_number"], result.reasons)


def test_valid_record_is_normalised():
    raw = good()
    raw["recalling_firm"] = "  Northbridge   Pharmaceuticals Inc. "
    r = validate_recall(raw, today=TODAY)
    assert r.record["recalling_firm"] == "Northbridge Pharmaceuticals Inc."
    assert r.record["report_date"] == date(2026, 10, 3)
    assert r.record["termination_date"] is None


@pytest.mark.parametrize("change,expected", [
    ({"classification": None}, "Missing required field 'classification'"),
    ({"reason_for_recall": "   "}, "Missing required field 'reason_for_recall'"),
    ({"classification": "Class IV"}, "Unknown classification 'Class IV'"),
    ({"status": "Archived"}, "Unknown status 'Archived'"),
    ({"product_type": "Devices"}, "Product type 'Devices' is not 'Drugs'"),
    ({"recall_number": "RECALL-77"}, "does not match format"),
    ({"report_date": "2026-10-31"}, "Invalid date in 'report_date'"),
    ({"report_date": "20991231"}, "is in the future"),
    ({"recall_initiation_date": "20261020", "termination_date": "20261001"}, "before initiation date"),
])
def test_rule_rejects_with_reason(change, expected):
    raw = good()
    for k, v in change.items():
        if v is None:
            raw.pop(k)
        else:
            raw[k] = v
    r = validate_recall(raw, today=TODAY)
    assert not r.valid
    assert any(expected in reason for reason in r.reasons), r.reasons


def test_all_reasons_reported_at_once():
    raw = good()
    raw.update(classification="Class IV", status="Archived", report_date="bad")
    assert len(validate_recall(raw, today=TODAY).reasons) == 3


def test_missing_recall_number_uses_position_as_key():
    raw = good()
    raw.pop("recall_number")
    assert validate_recall(raw, today=TODAY, position=7).key == "#7"
