"""Sources of drug recall records.

- OpenFDASource: the live openFDA drug enforcement API (https://open.fda.gov/apis/drug/enforcement/)
- FixtureSource: a JSON file in openFDA format, for demos and tests without network access
"""
import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Protocol

import httpx

from app.config import settings

FIXTURES = Path(__file__).parent / "fixtures"


class SourceError(Exception):
    """The source could not be read (network error, HTTP error, invalid response)."""


class RecallSource(Protocol):
    name: str      # live | sample | sample_with_errors
    detail: str    # URL or file name, recorded on the ingestion job

    def fetch(self) -> list[dict]: ...


@dataclass
class OpenFDASource:
    lookback_days: int = settings.fda_lookback_days
    max_records: int = settings.fda_max_records
    page_size: int = settings.fda_page_size
    base_url: str = settings.fda_api_url
    api_key: str = settings.fda_api_key
    timeout: float = settings.fda_timeout_seconds
    today: date | None = None
    transport: httpx.BaseTransport | None = None  # injectable for tests

    name = "live"

    @property
    def detail(self) -> str:
        return f"{self.base_url} (report_date last {self.lookback_days} days)"

    def _url(self, skip: int, limit: int) -> str:
        end = self.today or date.today()
        start = end - timedelta(days=self.lookback_days)
        url = (f"{self.base_url}?search=report_date:[{start:%Y%m%d}+TO+{end:%Y%m%d}]"
               f"&sort=report_date:desc&limit={limit}&skip={skip}")
        if self.api_key:
            url += f"&api_key={self.api_key}"
        return url

    def fetch(self) -> list[dict]:
        results: list[dict] = []
        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport,
                              headers={"User-Agent": "Syntra/0.2 (portfolio project)"}) as client:
                while len(results) < self.max_records:
                    limit = min(self.page_size, self.max_records - len(results))
                    resp = client.get(self._url(len(results), limit))
                    if resp.status_code == 404:
                        break  # openFDA answers 404 "No matches found" for an empty result
                    if resp.status_code != 200:
                        raise SourceError(f"openFDA returned HTTP {resp.status_code}: {resp.text[:200]}")
                    body = resp.json()
                    page = body.get("results")
                    if not isinstance(page, list):
                        raise SourceError("openFDA response has no 'results' list")
                    results.extend(page)
                    total = body.get("meta", {}).get("results", {}).get("total", 0)
                    if len(page) < limit or len(results) >= total:
                        break
        except httpx.HTTPError as e:
            raise SourceError(f"Could not reach openFDA: {e.__class__.__name__}: {e}") from e
        except ValueError as e:
            raise SourceError(f"openFDA returned invalid JSON: {e}") from e
        return results


@dataclass
class FixtureSource:
    name: str
    file: Path

    @property
    def detail(self) -> str:
        return f"fixture: {self.file.name}"

    def fetch(self) -> list[dict]:
        try:
            return json.loads(self.file.read_text(encoding="utf-8"))["results"]
        except (OSError, ValueError, KeyError) as e:
            raise SourceError(f"Could not read fixture {self.file.name}: {e}") from e


def get_source(name: str) -> RecallSource:
    if name == "live":
        return OpenFDASource()
    if name == "sample":
        return FixtureSource("sample", FIXTURES / "fda_sample.json")
    if name == "sample_with_errors":
        return FixtureSource("sample_with_errors", FIXTURES / "fda_sample_with_errors.json")
    raise ValueError(f"Unknown source '{name}'")
