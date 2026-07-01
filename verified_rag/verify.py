# Copyright © 2026 SurgeXi Business Intelligence, a Teamsmith Enterprises LLC company. All Rights Reserved.
"""The verification gate — the whole point of this repo.

A citation is a claim: "this key backs this quote." The gate treats every such
claim as untrusted until proven against the authoritative corpus:

  1. **Key resolution.** The cited key must resolve to a real stored chunk. An
     invented key (a hallucinated citation) resolves to nothing → REJECT.
  2. **Verbatim span.** Any quoted text must be a *verbatim substring* of that
     chunk's exact text. The check re-hashes the stored chunk (content address)
     and confirms the quote is a real, unmodified span → tamper of even one
     character fails.

Only a citation that passes both checks is allowed out. Everything else is
dropped and the corresponding point abstains. There is no path in this module
that returns ``ok=True`` for an unverifiable citation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .chunk import sha256_text
from .store import CorpusStore


@dataclass(frozen=True)
class Citation:
    """A *claimed* citation, prior to verification.

    ``quote`` is optional: a citation may point at a whole chunk (key only) or
    assert a specific verbatim span (key + quote). Either way the key must be
    real; if a quote is present it must be verbatim.
    """

    key: str
    quote: Optional[str] = None


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    reason: str
    key: str
    quote: Optional[str] = None
    # Provenance, populated only when ok=True — never for a rejected citation.
    doc_id: Optional[str] = None
    title: Optional[str] = None
    start: Optional[int] = None
    end: Optional[int] = None
    sha256: Optional[str] = None


def verify_citation(citation: Citation, store: CorpusStore) -> VerificationResult:
    """Verify one claimed citation against the corpus. Fail-closed."""
    chunk = store.get(citation.key)

    # (a) Key resolution — an invented key backs nothing.
    if chunk is None:
        return VerificationResult(
            ok=False,
            reason=f"unknown citation key {citation.key!r} — not in corpus",
            key=citation.key,
            quote=citation.quote,
        )

    # Re-hash the stored chunk: never trust a cached/derived hash at verify time.
    recomputed = sha256_text(chunk.text)
    if recomputed != chunk.sha256:  # pragma: no cover - store keeps these equal
        return VerificationResult(
            ok=False,
            reason=f"stored chunk {citation.key!r} failed integrity check",
            key=citation.key,
            quote=citation.quote,
        )

    # (b) Verbatim span — if a quote is claimed it must be a real substring.
    if citation.quote is not None:
        quote = citation.quote
        if not quote.strip():
            return VerificationResult(
                ok=False,
                reason="empty quote is not a verifiable span",
                key=citation.key,
                quote=quote,
            )
        if quote not in chunk.text:
            return VerificationResult(
                ok=False,
                reason=(
                    f"quoted text is not a verbatim substring of {citation.key!r} "
                    "(altered, paraphrased, or invented)"
                ),
                key=citation.key,
                quote=quote,
            )

    return VerificationResult(
        ok=True,
        reason="verified: key resolves and quote is verbatim",
        key=citation.key,
        quote=citation.quote,
        doc_id=chunk.doc_id,
        title=chunk.title,
        start=chunk.start,
        end=chunk.end,
        sha256=chunk.sha256,
    )
