# ADR 0001 — Verify citations, don't trust the model

- **Status:** Accepted
- **Context:** LLMs fabricate citations — inventing source keys and
  "quoting" text that the real source never contained (*Mata v. Avianca*, 2023).
  RAG improves recall but does not stop this: a model with the right passages in
  context can still cite a key it was never given, or reword a real quote.
  Prompting, bigger models, and temperature 0 lower the *rate* but give **no
  guarantee** — unacceptable where one fabricated cite is a serious incident.
- **Decision:** Move the trust boundary out of the model. Treat the synthesizer
  (LLM or template) as **untrusted**: it may *propose* an answer and citations,
  but it has **no authority to release** a citation. Every claimed citation
  passes through a verification gate that checks it against an authoritative
  corpus store before release. A citation that fails is dropped; if none survive,
  the engine abstains.
- **Consequences:**
  - ➕ Fabrication becomes structurally impossible at the seam, not merely rare —
    the guarantee holds regardless of which model or retriever is plugged in.
  - ➕ The property is testable: a lying synthesizer is a valid unit-test double,
    and the suite proves its fabrications are dropped.
  - ➖ Requires an authoritative, keyed store and a per-citation check on every
    answer. Cheap relative to generation, and the whole point.
- **Alternatives considered:** prompt engineering ("only use the sources") —
  reduces rate, no guarantee; fine-tuning for honesty — same; post-hoc human
  review — doesn't scale and still trusts the model to surface its own cites.
