# Copyright © 2026 SurgeXi Business Intelligence, a Teamsmith Enterprises LLC company. All Rights Reserved.
"""End-to-end tests: the engine never lets a fabricated citation out.

The decisive test uses a deliberately dishonest synthesizer that emits an
invented key and a one-character-tampered quote alongside one legitimate cite.
The engine must release only the legitimate cite and drop the rest.
"""

from typing import List

from verified_rag.engine import ABSTENTION, AnswerEngine
from verified_rag.retrieve import ScoredChunk
from verified_rag.synthesize import Proposal, TemplateSynthesizer
from verified_rag.verify import Citation


class LyingSynthesizer:
    """Emits: one legit cite, one invented key, one tampered quote."""

    def synthesize(self, query: str, candidates: List[ScoredChunk]) -> Proposal:
        best = candidates[0].chunk
        tampered = best.text[:-1] + "Z"
        return Proposal(
            answer="Confident nonsense.",
            citations=[
                Citation(key=best.key, quote=best.text),            # legit
                Citation(key="fabricated-court#c1", quote="fake"),  # invented key
                Citation(key=best.key, quote=tampered),             # tampered quote
            ],
        )


class AllFabricationSynthesizer:
    """Every citation it emits is fabricated — engine must abstain entirely."""

    def synthesize(self, query: str, candidates: List[ScoredChunk]) -> Proposal:
        return Proposal(
            answer="It definitely says so, trust me.",
            citations=[
                Citation(key="ghost#c1", quote="never existed"),
                Citation(key="phantom#c2", quote="also invented"),
            ],
        )


def test_grounded_query_returns_verbatim_cite(store):
    engine = AnswerEngine(store, synthesizer=TemplateSynthesizer())
    result = engine.answer("What does the preamble establish about justice?")

    assert result.is_grounded
    assert not result.abstained
    assert len(result.citations) == 1
    cite = result.citations[0]
    assert cite.ok
    # The quote the engine released is verbatim in the stored chunk.
    chunk = store.get(cite.key)
    assert cite.quote in chunk.text


def test_ungroundable_query_abstains_without_inventing(store):
    engine = AnswerEngine(store, synthesizer=TemplateSynthesizer())
    result = engine.answer("Explain quantum chromodynamics gluon confinement.")

    assert result.abstained
    assert result.answer == ABSTENTION
    assert result.citations == []  # nothing invented to fill the gap


def test_lying_synthesizer_only_the_real_cite_survives(store):
    engine = AnswerEngine(store, synthesizer=LyingSynthesizer())
    result = engine.answer("How long do I have to return a widget for a refund?")

    # Exactly one verified cite; the invented key and tampered quote are dropped.
    assert len(result.citations) == 1
    assert result.citations[0].ok
    assert len(result.dropped) == 2

    dropped_reasons = " ".join(d.reason for d in result.dropped)
    assert "unknown citation key" in dropped_reasons
    assert "verbatim" in dropped_reasons

    # No fabricated key ever appears among released citations.
    released_keys = {c.key for c in result.citations}
    assert "fabricated-court#c1" not in released_keys


def test_engine_abstains_when_all_citations_are_fabricated(store):
    engine = AnswerEngine(store, synthesizer=AllFabricationSynthesizer())
    result = engine.answer("anything at all")

    assert result.abstained
    assert result.answer == ABSTENTION
    assert result.citations == []
    # The fabricated claims were caught and recorded as dropped, not emitted.
    assert len(result.dropped) == 2
    assert all(not d.ok for d in result.dropped)


def test_released_citations_are_all_verified(store):
    """Invariant: every citation the engine returns has ok=True."""
    engine = AnswerEngine(store, synthesizer=LyingSynthesizer())
    result = engine.answer("return an unused widget refund")
    assert all(c.ok for c in result.citations)
