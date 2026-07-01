"""CorpusStore — the authoritative, keyed index of chunks.

This is the single source of truth the verification gate checks against. A
citation key is only "real" if it resolves here; a quote is only "verbatim" if
it appears in the stored chunk this store returns. Nothing downstream is trusted
to have the right text.
"""

from __future__ import annotations

import os
from typing import Dict, Iterable, List, Optional

from .chunk import Chunk, chunk_document


class CorpusStore:
    """In-memory, keyed store of chunks. Keys are unique and authoritative."""

    def __init__(self) -> None:
        self._chunks: Dict[str, Chunk] = {}

    def add(self, chunk: Chunk) -> None:
        if chunk.key in self._chunks:
            raise ValueError(f"duplicate citation key: {chunk.key!r}")
        self._chunks[chunk.key] = chunk

    def add_document(
        self,
        doc_id: str,
        text: str,
        *,
        title: str = "",
        key_prefix: Optional[str] = None,
    ) -> List[Chunk]:
        """Chunk a document and register every chunk. Returns the new chunks."""
        new = chunk_document(doc_id, text, title=title, key_prefix=key_prefix)
        for c in new:
            self.add(c)
        return new

    def get(self, key: str) -> Optional[Chunk]:
        """Resolve a citation key to its stored chunk, or None if it is invented."""
        return self._chunks.get(key)

    def has(self, key: str) -> bool:
        return key in self._chunks

    def all(self) -> List[Chunk]:
        return list(self._chunks.values())

    def __len__(self) -> int:
        return len(self._chunks)

    def __iter__(self) -> Iterable[Chunk]:
        return iter(self._chunks.values())

    @classmethod
    def from_directory(cls, path: str) -> "CorpusStore":
        """Load every ``*.txt`` in ``path`` as a document.

        The first non-empty line is treated as the document *title* (metadata),
        not a citable chunk — so chunk #c1 is the first real paragraph of body
        text. The doc_id (and citation-key prefix) is the filename stem, so keys
        are stable across runs.
        """
        store = cls()
        for name in sorted(os.listdir(path)):
            if not name.endswith(".txt"):
                continue
            doc_id = os.path.splitext(name)[0]
            with open(os.path.join(path, name), "r", encoding="utf-8") as fh:
                raw = fh.read()
            title, body = _split_title(raw)
            store.add_document(doc_id, body, title=title or doc_id)
        return store


def _split_title(text: str) -> tuple[str, str]:
    """Return ``(title, body)`` where title is the first non-empty line and body
    is everything after it. If no title line is found, title is empty and the
    whole text is the body.
    """
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.strip():
            title = line.strip()
            body = "".join(lines[i + 1:])
            return title, body
    return "", text
