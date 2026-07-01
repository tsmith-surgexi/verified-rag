# Copyright © 2026 SurgeXi Business Intelligence, a Teamsmith Enterprises LLC company. All Rights Reserved.
"""Tests for the verification gate — the core guarantee.

These prove, at the unit level, the three ways a citation can be dishonest and
that each is rejected: invented key, tampered quote, empty quote. And that an
honest citation passes with full provenance.
"""

from verified_rag.verify import Citation, verify_citation


def _first_chunk(store):
    return store.all()[0]


def test_real_key_and_verbatim_quote_passes(store):
    chunk = _first_chunk(store)
    quote = chunk.text[: max(10, len(chunk.text) // 2)]  # a real span
    result = verify_citation(Citation(key=chunk.key, quote=quote), store)

    assert result.ok
    assert result.key == chunk.key
    # Provenance is only populated on success.
    assert result.doc_id == chunk.doc_id
    assert result.sha256 == chunk.sha256
    assert result.start is not None and result.end is not None


def test_key_only_citation_passes_when_key_is_real(store):
    chunk = _first_chunk(store)
    result = verify_citation(Citation(key=chunk.key), store)  # no quote claimed
    assert result.ok


def test_invented_key_is_rejected(store):
    result = verify_citation(
        Citation(key="totally-made-up#c99", quote="anything"), store
    )
    assert not result.ok
    assert "unknown citation key" in result.reason
    # A rejected citation carries no provenance to leak.
    assert result.doc_id is None
    assert result.sha256 is None


def test_one_char_tampered_quote_is_rejected(store):
    chunk = _first_chunk(store)
    tampered = chunk.text[:-1] + "Z"  # change exactly one character
    assert tampered != chunk.text
    result = verify_citation(Citation(key=chunk.key, quote=tampered), store)
    assert not result.ok
    assert "verbatim" in result.reason


def test_paraphrased_quote_is_rejected(store):
    chunk = _first_chunk(store)
    paraphrase = "This is a paraphrase that does not appear verbatim anywhere."
    assert paraphrase not in chunk.text
    result = verify_citation(Citation(key=chunk.key, quote=paraphrase), store)
    assert not result.ok


def test_empty_quote_is_rejected(store):
    chunk = _first_chunk(store)
    result = verify_citation(Citation(key=chunk.key, quote="   "), store)
    assert not result.ok
    assert "empty quote" in result.reason


def test_real_key_but_quote_from_a_different_chunk_is_rejected(store):
    """A verbatim quote that belongs to chunk B does not validate a cite to A."""
    chunks = store.all()
    a, b = chunks[0], chunks[1]
    assert b.text not in a.text
    result = verify_citation(Citation(key=a.key, quote=b.text), store)
    assert not result.ok
