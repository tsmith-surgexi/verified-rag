<!-- Copyright © 2026 SurgeXi Business Intelligence, a Teamsmith Enterprises LLC company. All Rights Reserved. -->
# ADR 0003 — Abstain over fabricate; exact-substring matching

- **Status:** Accepted
- **Context:** When the corpus does not support a point, a system must choose
  between two behaviors: emit a plausible answer anyway (risking a fabricated or
  unbacked citation), or decline. Most RAG systems have a single output shape —
  an answer — which pushes them toward the first, unsafe choice. Separately, the
  verbatim check must decide how strict "verbatim" is.
- **Decision:** Make **abstention a first-class outcome**. When no claimed
  citation survives verification, `AnswerEngine` returns `abstained=True`, the
  text `"Not supported by the corpus."`, and **zero** citations — never a
  best-effort guess with an unverified cite. For the quote check, use **exact
  substring matching** against the stored chunk's exact text: safety over recall.
- **Consequences:**
  - ➕ The system's honest "I don't know" is structural, not a rare fallback, so
    it never papers over a gap with an invented citation.
  - ➕ Exact matching cannot be tricked by near-miss paraphrases; a one-character
    edit is rejected.
  - ➖ A quote that differs only in whitespace or straight-vs-curly quotes is
    rejected even though a human would call it the same. Accepted trade-off:
    biased toward safety.
  - ➖ Normalization (e.g. collapsing whitespace) would raise recall but must
    never silently widen into "close enough." If added, it belongs behind an
    explicit, **audited allowlist** of transformations — a deliberate future ADR,
    not an ad-hoc loosening of this one.
- **Alternatives considered:** always answer with a confidence score (still emits
  unbacked cites); fuzzy quote matching by default (erodes the guarantee the repo
  exists to provide).
