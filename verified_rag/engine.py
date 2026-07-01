"""AnswerEngine — retrieve → synthesize → *verify every citation* → answer.

The engine wires the pieces together and enforces the guarantee at the seam:
a citation reaches the caller only after :func:`verify_citation` returns ok. Any
citation that fails is dropped. If a synthesizer's answer had no verifiable
support, the engine abstains instead of emitting an unbacked claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .retrieve import Retriever
from .store import CorpusStore
from .synthesize import Synthesizer, default_synthesizer
from .verify import VerificationResult, verify_citation

ABSTENTION = "Not supported by the corpus."


@dataclass
class VerifiedAnswer:
    """The engine's output. ``abstained`` answers carry zero citations."""

    query: str
    answer: str
    abstained: bool
    citations: List[VerificationResult] = field(default_factory=list)
    dropped: List[VerificationResult] = field(default_factory=list)

    @property
    def is_grounded(self) -> bool:
        return bool(self.citations) and not self.abstained


class AnswerEngine:
    def __init__(
        self,
        store: CorpusStore,
        retriever: Optional[Retriever] = None,
        synthesizer: Optional[Synthesizer] = None,
        top_k: int = 5,
    ) -> None:
        self.store = store
        self.retriever = retriever or Retriever(store)
        self.synthesizer = synthesizer or default_synthesizer()
        self.top_k = top_k

    def answer(self, query: str) -> VerifiedAnswer:
        candidates = self.retriever.retrieve(query, top_k=self.top_k)
        proposal = self.synthesizer.synthesize(query, candidates)

        verified: List[VerificationResult] = []
        dropped: List[VerificationResult] = []
        for citation in proposal.citations:
            result = verify_citation(citation, self.store)
            (verified if result.ok else dropped).append(result)

        # Abstain when nothing survived verification. A synthesizer answer that
        # depended on dropped citations must not be emitted as if it were backed.
        if not verified:
            return VerifiedAnswer(
                query=query,
                answer=ABSTENTION,
                abstained=True,
                citations=[],
                dropped=dropped,
            )

        return VerifiedAnswer(
            query=query,
            answer=proposal.answer,
            abstained=False,
            citations=verified,
            dropped=dropped,
        )
