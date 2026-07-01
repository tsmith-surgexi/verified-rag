"""Retriever — light-dependency TF-IDF cosine retrieval.

Retrieval is deliberately simple and self-contained (pure-Python TF-IDF, no
model download, no vector DB) so the repo runs from a clean clone with zero
setup. Retrieval only *proposes* candidate chunks; it has no authority to make a
citation trustworthy. That job belongs to the verification gate. Swap this class
for embeddings/BM25/a vector store without touching the guarantee.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .chunk import Chunk
from .store import CorpusStore

_TOKEN = re.compile(r"[a-z0-9]+")

# A small stop-word list. Dropping high-frequency function words keeps cosine
# similarity driven by content terms — so an off-topic query scores ~0 and the
# engine can honestly abstain instead of citing a chunk it merely shares "the"
# and "of" with.
_STOPWORDS = frozenset(
    """a an and are as at be by do does for from how i in is it its of on or that
    the their they this to was what when where which who will with you your""".split()
)


def _tokenize(text: str) -> List[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOPWORDS]


@dataclass
class ScoredChunk:
    chunk: Chunk
    score: float


class Retriever:
    """TF-IDF cosine-similarity retriever over a :class:`CorpusStore`."""

    def __init__(self, store: CorpusStore) -> None:
        self.store = store
        self._chunks: List[Chunk] = store.all()
        self._doc_freq: Counter = Counter()
        self._vectors: List[Dict[str, float]] = []
        self._build()

    def _build(self) -> None:
        tokenized = [_tokenize(c.text) for c in self._chunks]
        for toks in tokenized:
            for term in set(toks):
                self._doc_freq[term] += 1

        n_docs = max(len(self._chunks), 1)
        for toks in tokenized:
            tf = Counter(toks)
            length = max(len(toks), 1)
            vec: Dict[str, float] = {}
            for term, count in tf.items():
                idf = math.log((1 + n_docs) / (1 + self._doc_freq[term])) + 1.0
                vec[term] = (count / length) * idf
            self._vectors.append(vec)

    def _query_vector(self, query: str) -> Dict[str, float]:
        toks = _tokenize(query)
        tf = Counter(toks)
        length = max(len(toks), 1)
        n_docs = max(len(self._chunks), 1)
        vec: Dict[str, float] = {}
        for term, count in tf.items():
            idf = math.log((1 + n_docs) / (1 + self._doc_freq.get(term, 0))) + 1.0
            vec[term] = (count / length) * idf
        return vec

    @staticmethod
    def _cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
        if not a or not b:
            return 0.0
        common = set(a) & set(b)
        dot = sum(a[t] * b[t] for t in common)
        na = math.sqrt(sum(v * v for v in a.values()))
        nb = math.sqrt(sum(v * v for v in b.values()))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    def retrieve(self, query: str, top_k: int = 5) -> List[ScoredChunk]:
        """Return the top-k candidate chunks by cosine similarity (desc)."""
        qvec = self._query_vector(query)
        scored: List[Tuple[float, Chunk]] = []
        for chunk, vec in zip(self._chunks, self._vectors):
            scored.append((self._cosine(qvec, vec), chunk))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [ScoredChunk(chunk=c, score=s) for s, c in scored[:top_k]]
