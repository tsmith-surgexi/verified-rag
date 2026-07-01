# Copyright © 2026 SurgeXi Business Intelligence, a Teamsmith Enterprises LLC company. All Rights Reserved.
"""Tests for chunking, content-addressing, and the store."""

from verified_rag.chunk import Chunk, chunk_document, sha256_text
from verified_rag.store import CorpusStore


def test_sha256_is_stable_and_text_derived():
    text = "the exact bytes matter"
    assert sha256_text(text) == sha256_text(text)
    assert sha256_text(text) != sha256_text(text + "!")


def test_chunk_sha_is_authoritative_even_if_supplied_wrong():
    # A caller cannot forge the content address; it is recomputed from text.
    c = Chunk(key="k#c1", doc_id="k", text="hello", start=0, end=5, sha256="deadbeef")
    assert c.sha256 == sha256_text("hello")
    assert c.sha256 != "deadbeef"


def test_chunk_offsets_map_back_to_source():
    doc = "First paragraph here.\n\nSecond paragraph here."
    chunks = chunk_document("doc", doc)
    assert len(chunks) == 2
    for c in chunks:
        assert doc[c.start : c.end] == c.text  # offsets are exact


def test_keys_are_stable_and_unique():
    doc = "Para one.\n\nPara two.\n\nPara three."
    chunks = chunk_document("mydoc", doc)
    keys = [c.key for c in chunks]
    assert keys == ["mydoc#c1", "mydoc#c2", "mydoc#c3"]
    assert len(set(keys)) == len(keys)


def test_store_rejects_duplicate_keys():
    store = CorpusStore()
    store.add(Chunk(key="dup#c1", doc_id="dup", text="a", start=0, end=1))
    try:
        store.add(Chunk(key="dup#c1", doc_id="dup", text="b", start=0, end=1))
    except ValueError as exc:
        assert "duplicate" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError on duplicate key")


def test_from_directory_loads_corpus_and_strips_title(store):
    assert len(store) > 0
    # Titles were treated as metadata, not chunk #c1 body.
    con = store.get("us-constitution#c1")
    assert con is not None
    assert con.text.startswith("We the People")
    assert "public domain" not in con.text  # that line was the title
    assert con.title.startswith("United States Constitution")
