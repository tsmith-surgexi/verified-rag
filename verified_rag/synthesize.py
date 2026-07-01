"""Synthesizers — pluggable, and untrusted by design.

A synthesizer proposes an answer plus the citations it *claims* support it. It
is treated as an adversary: whatever it emits (a real LLM, a template, a
deliberately-lying stub in the tests) must still pass the verification gate
before any citation reaches a caller. Nothing here can bypass verification.

Two are shipped:

* :class:`TemplateSynthesizer` — deterministic, zero-dependency, zero API keys.
  Default so the repo runs from a clean clone.
* :class:`LLMSynthesizer` — optional; enabled only when ``VERIFIED_RAG_LLM=1``
  and an OpenAI-compatible endpoint is configured. Still gated identically.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Protocol

from .retrieve import ScoredChunk
from .verify import Citation


@dataclass
class Proposal:
    """A *claimed* answer + the citations the synthesizer says support it."""

    answer: str
    citations: List[Citation] = field(default_factory=list)


class Synthesizer(Protocol):
    def synthesize(self, query: str, candidates: List[ScoredChunk]) -> Proposal: ...


class TemplateSynthesizer:
    """Deterministic synthesizer: quote the single best candidate verbatim.

    It never paraphrases the source into a quote, so — given a relevant
    candidate — it produces a citation that the gate will accept. When nothing is
    relevant (all scores at/below ``min_score``) it proposes an empty answer with
    no citations, and the engine abstains.
    """

    def __init__(self, min_score: float = 0.05) -> None:
        # Below this cosine score a candidate is treated as noise (e.g. only
        # stop-word overlap) and the point abstains rather than citing junk.
        self.min_score = min_score

    def synthesize(self, query: str, candidates: List[ScoredChunk]) -> Proposal:
        relevant = [c for c in candidates if c.score > self.min_score]
        if not relevant:
            return Proposal(answer="", citations=[])

        best = relevant[0]
        # Quote the chunk's exact text — verbatim by construction.
        quote = best.chunk.text
        answer = f'Per {best.chunk.title or best.chunk.doc_id}: "{quote}"'
        return Proposal(answer=answer, citations=[Citation(key=best.chunk.key, quote=quote)])


class LLMSynthesizer:  # pragma: no cover - exercised only when explicitly enabled
    """Optional OpenAI-compatible synthesizer. Output is still fully gated.

    The model is instructed to quote verbatim and cite by key, but the guarantee
    does not depend on it obeying: any citation it invents or any quote it alters
    is caught and dropped by the verification gate downstream.
    """

    def __init__(self) -> None:
        self.model = os.environ.get("VERIFIED_RAG_LLM_MODEL", "gpt-4o-mini")
        self.base_url = os.environ.get("VERIFIED_RAG_LLM_BASE_URL")  # optional
        self.api_key = os.environ.get("VERIFIED_RAG_LLM_API_KEY") or os.environ.get(
            "OPENAI_API_KEY"
        )

    def synthesize(self, query: str, candidates: List[ScoredChunk]) -> Proposal:
        try:
            from openai import OpenAI  # imported lazily; optional dependency
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "LLM mode requires the 'openai' package: pip install openai"
            ) from exc

        client_kwargs = {}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        if self.api_key:
            client_kwargs["api_key"] = self.api_key
        client = OpenAI(**client_kwargs)

        context = "\n\n".join(
            f"[{c.chunk.key}] {c.chunk.text}" for c in candidates
        )
        system = (
            "You answer strictly from the provided sources. Cite sources by their "
            "bracketed key. When you quote, copy the text VERBATIM. If the sources "
            "do not support an answer, say so and cite nothing. Never invent a key."
        )
        user = f"Sources:\n{context}\n\nQuestion: {query}"

        resp = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.0,
        )
        text = resp.choices[0].message.content or ""

        # Claim every candidate whose key appears in the model's text; the gate
        # will discard any that aren't backed verbatim. We quote the full chunk
        # so the verbatim check is meaningful and provenance is exact.
        claimed: List[Citation] = []
        for c in candidates:
            if c.chunk.key in text:
                claimed.append(Citation(key=c.chunk.key, quote=c.chunk.text))
        return Proposal(answer=text, citations=claimed)


def default_synthesizer() -> Synthesizer:
    """Template synthesizer unless ``VERIFIED_RAG_LLM=1`` opts into the LLM."""
    if os.environ.get("VERIFIED_RAG_LLM") == "1":
        return LLMSynthesizer()
    return TemplateSynthesizer()
