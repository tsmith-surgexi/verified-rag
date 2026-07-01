# Copyright © 2026 SurgeXi Business Intelligence, a Teamsmith Enterprises LLC company. All Rights Reserved.
"""Runnable demo: `python -m verified_rag.demo`.

Shows the guarantee from both sides on a toy public-domain corpus:

  * a query the corpus CAN ground  → a cited answer with a verbatim quote and
    full provenance (key, doc, char span, sha256);
  * a query the corpus CANNOT ground → an honest abstention, no invented cite;
  * an ADVERSARIAL synthesizer that tries to smuggle out (a) an invented
    citation key and (b) a one-character-tampered quote → both are dropped by
    the verification gate and the point abstains.

Runs with zero API keys via the deterministic TemplateSynthesizer.
"""

from __future__ import annotations

import os

from .engine import AnswerEngine
from .retrieve import ScoredChunk
from .store import CorpusStore
from .synthesize import Proposal, TemplateSynthesizer
from .verify import Citation

CORPUS_DIR = os.path.join(os.path.dirname(__file__), "corpus")

RULE = "=" * 72


def _print_answer(result) -> None:
    print(f"Q: {result.query}")
    if result.abstained:
        print(f"A: {result.answer}  [ABSTAINED — nothing verifiable]")
    else:
        print(f"A: {result.answer}")
    for c in result.citations:
        span = f"chars {c.start}–{c.end}" if c.start is not None else "whole chunk"
        print(f"   ✔ VERIFIED cite [{c.key}] — {c.title} ({span})")
        print(f"     sha256={c.sha256[:16]}…  quote is verbatim")
    for d in result.dropped:
        print(f"   x DROPPED   [{d.key}] - {d.reason}")
    print()


class AdversarialSynthesizer:
    """A deliberately dishonest synthesizer used to prove the gate holds.

    It claims three citations: one legitimate (verbatim), one with an INVENTED
    key, and one whose quote has been TAMPERED by a single character. Only the
    legitimate one should survive.
    """

    def synthesize(self, query: str, candidates: list[ScoredChunk]) -> Proposal:
        best = candidates[0].chunk
        good_quote = best.text
        tampered = good_quote[:-1] + ("X" if not good_quote.endswith("X") else "Y")
        return Proposal(
            answer=(
                "The corpus clearly states everything, and also see the "
                "Supreme Court's landmark ruling."
            ),
            citations=[
                Citation(key=best.key, quote=good_quote),          # legit
                Citation(key="supreme-court-9000#c1", quote="a fake holding"),  # invented key
                Citation(key=best.key, quote=tampered),            # 1-char tamper
            ],
        )


def main() -> None:
    store = CorpusStore.from_directory(CORPUS_DIR)
    print(RULE)
    print(f"verified-rag demo — corpus: {len(store)} chunks from "
          f"{len({c.doc_id for c in store})} public-domain / sample docs")
    print(RULE, "\n")

    engine = AnswerEngine(store)  # deterministic TemplateSynthesizer by default

    print("① Groundable query — expect a cited answer with a verbatim quote\n")
    _print_answer(engine.answer("What does the Constitution's preamble establish?"))

    print("② Un-groundable query — expect an HONEST abstention, no invented cite\n")
    _print_answer(engine.answer("What is the airspeed velocity of an unladen swallow?"))

    print(RULE)
    print("③ Adversarial synthesizer — it TRIES to emit an invented key and a")
    print("   one-character-tampered quote. The gate must drop both.")
    print(RULE, "\n")
    adv_engine = AnswerEngine(store, synthesizer=AdversarialSynthesizer())
    _print_answer(
        adv_engine.answer("How long do I have to return an unused widget for a refund?")
    )

    print(RULE)
    print("Guarantee: every citation above was verified (real key + verbatim")
    print("quote) before release, or the point abstained. No fabricated citation")
    print("can leave the engine — there is no code path that emits one.")
    print(RULE)


if __name__ == "__main__":
    main()
