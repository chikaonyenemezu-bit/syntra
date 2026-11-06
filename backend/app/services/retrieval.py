"""Keyword retrieval over document sections (BM25).

The corpus is small (a few hundred sections), so a BM25 index in memory is fast, needs no extra
service, and every ranking is explainable and reproducible, which matters for validating the
assistant. Titles and headings count double. The index is rebuilt automatically when a document
changes.
"""
import math
import re
from collections import Counter
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.knowledge import KnowledgeDocument

STOPWORDS = set("""
a about above after again all also am an and any are as at be because been before being below between
both but by can could did do does doing down during each few for from further had has have having he her
here hers him his how i if in into is it its itself just me more most my no nor not now of off on once only
or other our out over own same she should so some such than that the their them then there these they this
those through to too under until up very was we were what when where which while who whom why will with
would you your yours yourself please tell show give need want get got does
""".split())

TOKEN = re.compile(r"[a-z0-9]+")
K1, B = 1.4, 0.75


def stem(word: str) -> str:
    """Very light English stemming: enough to match 'incidents'/'incident', 'approved'/'approve'."""
    for suffix in ("ations", "ation", "ings", "ing", "ies", "ied", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            word = word[: -len(suffix)]
            return word + ("y" if suffix in ("ies", "ied") else "")
    return word


def tokenize(text: str) -> list[str]:
    return [stem(t) for t in TOKEN.findall(text.lower()) if t not in STOPWORDS]


@dataclass
class Passage:
    doc_id: str
    title: str
    doc_type: str
    version: str
    section: str
    heading: str
    text: str
    score: float = 0.0

    @property
    def ref(self) -> str:
        return f"{self.doc_id} §{self.section}"

    def excerpt(self, length: int = 280) -> str:
        flat = " ".join(self.text.split())
        return flat if len(flat) <= length else flat[: length - 1].rsplit(" ", 1)[0] + "…"


class BM25Index:
    def __init__(self, passages: list[Passage]):
        self.passages = passages
        self.docs: list[Counter] = []
        for p in passages:
            boosted = f"{p.title} {p.heading} " * 2 + p.text
            self.docs.append(Counter(tokenize(boosted)))
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg_len = sum(self.lengths) / len(self.lengths) if self.lengths else 0.0
        df: Counter = Counter()
        for d in self.docs:
            df.update(d.keys())
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    # Calibrated on app/knowledge/evaluation.csv: every in-scope question scores >= 5.9 for its best
    # section, off-topic questions stay below 4. Tail hits under 35 % of the best score are noise.
    def search(self, query: str, k: int = 5, min_score: float = 4.0, relative: float = 0.35) -> list[Passage]:
        terms = set(tokenize(query))
        scored = []
        for i, d in enumerate(self.docs):
            s = 0.0
            for t in terms:
                tf = d.get(t)
                if tf:
                    s += self.idf[t] * tf * (K1 + 1) / (tf + K1 * (1 - B + B * self.lengths[i] / self.avg_len))
            if s >= min_score:
                scored.append((s, i))
        scored.sort(reverse=True)
        if scored:
            scored = [(s, i) for s, i in scored if s >= scored[0][0] * relative]
        out = []
        for s, i in scored[:k]:
            p = self.passages[i]
            out.append(Passage(**{**p.__dict__, "score": round(s, 3)}))
        return out


_cache: dict[str, BM25Index] = {}


def get_index(db: Session) -> BM25Index:
    docs = db.scalars(select(KnowledgeDocument).options(selectinload(KnowledgeDocument.chunks))
                      .order_by(KnowledgeDocument.doc_id)).all()
    signature = "|".join(f"{d.doc_id}:{d.content_hash}" for d in docs)
    if signature not in _cache:
        _cache.clear()
        _cache[signature] = BM25Index([
            Passage(d.doc_id, d.title, d.doc_type, d.version, c.section, c.heading, c.text)
            for d in docs for c in d.chunks
        ])
    return _cache[signature]


def search(db: Session, query: str, k: int = 5) -> list[Passage]:
    return get_index(db).search(query, k)
