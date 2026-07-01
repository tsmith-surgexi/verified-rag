<!-- Copyright © 2026 SurgeXi Business Intelligence, a Teamsmith Enterprises LLC company. All Rights Reserved. -->
# ADR 0002 — Content-addressed chunks (sha256) for verbatim verification

- **Status:** Accepted
- **Context:** The verification gate must confirm that a quoted span is real
  text from a specific stored chunk — not a paraphrase, not a one-character
  edit, and not text borrowed from a *different* chunk. It also must not trust a
  cached or supplied hash, because a corrupted or swapped store would then be
  able to validate a bad quote.
- **Decision:** Give every chunk a stable citation **key**, its **exact text**,
  the **character offsets** of that text in the source document, and a
  **sha256** of the text. The hash is derived from the text and cannot be
  supplied by a caller (`Chunk.__post_init__` recomputes it). Verification
  re-hashes the stored chunk at check time (integrity), then confirms the quote
  is a verbatim substring of that exact text.
- **Consequences:**
  - ➕ Tamper-evident: altering stored text changes its hash and is caught before
    a citation is released.
  - ➕ Stable, durable provenance: the hash is a content address for a passage —
    useful for audit logs ("this is the exact text we cited"), caching, and
    dedup.
  - ➕ Offsets let downstream UIs highlight the exact source span.
  - ➖ Exact bytes matter: whitespace/encoding differences produce a different
    hash. Correct for a *verbatim* guarantee; normalization is handled
    separately and audibly (ADR 0003).
- **Alternatives considered:** store text only, compare strings (loses the
  integrity check and durable address); fuzzy/embedding similarity for the quote
  (defeats the point — "verbatim" must mean verbatim).
