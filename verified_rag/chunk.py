# Copyright © 2026 SurgeXi Business Intelligence, a Teamsmith Enterprises LLC company. All Rights Reserved.
"""Chunk model + chunking + content-addressed hashing.

A chunk is the unit of citation. Each one carries a stable citation *key*, its
*exact* text, the character offsets of that text inside its source document, and
a sha256 of the text. The hash is what makes verification cheap and tamper-
evident: verifying a quote later never trusts a copy — it re-hashes the stored
text and confirms the quote is a real substring of it.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import List


def sha256_text(text: str) -> str:
    """Content address for a chunk's exact text. Stable and tamper-evident."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Chunk:
    """An immutable, content-addressed unit of citable text.

    Attributes:
        key:        Stable, human-readable citation key, e.g. "us-constitution#c1".
        doc_id:     Identifier of the source document.
        text:       The chunk's *exact* text. Verification quotes must be
                    verbatim substrings of this.
        start:      Character offset of ``text`` within the source document.
        end:        End character offset (exclusive) within the source document.
        sha256:     sha256 of ``text``; recomputed on verification.
        title:      Human-friendly source title for display/provenance.
    """

    key: str
    doc_id: str
    text: str
    start: int
    end: int
    sha256: str = field(default="")
    title: str = ""

    def __post_init__(self) -> None:
        # Content address is derived, never supplied — keep it authoritative.
        object.__setattr__(self, "sha256", sha256_text(self.text))

    def contains_verbatim(self, quote: str) -> bool:
        """True iff ``quote`` is a verbatim substring of this chunk's text."""
        return quote in self.text


# Paragraph boundary: one or more blank lines.
_PARA_SPLIT = re.compile(r"\n\s*\n")


def chunk_document(
    doc_id: str,
    text: str,
    *,
    title: str = "",
    key_prefix: str | None = None,
) -> List[Chunk]:
    """Split a document into paragraph chunks with stable keys + char offsets.

    Structure-aware on purpose: splitting on paragraph boundaries keeps each
    chunk coherent, and preserving char offsets means every chunk can be traced
    back to an exact span of the original document.
    """
    prefix = key_prefix or doc_id
    chunks: List[Chunk] = []
    cursor = 0
    index = 0

    for raw in _PARA_SPLIT.split(text):
        para = raw.strip()
        if not para:
            # Still advance the cursor past the skipped span so offsets stay true.
            cursor = text.find(raw, cursor) + len(raw)
            continue

        start = text.find(para, cursor)
        if start == -1:  # pragma: no cover - defensive; strip() shouldn't lose it
            start = cursor
        end = start + len(para)
        cursor = end

        index += 1
        chunks.append(
            Chunk(
                key=f"{prefix}#c{index}",
                doc_id=doc_id,
                text=para,
                start=start,
                end=end,
                title=title,
            )
        )

    return chunks
