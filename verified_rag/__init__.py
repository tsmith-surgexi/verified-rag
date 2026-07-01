"""verified-rag — a retrieval-augmented answer engine that structurally cannot
fabricate a citation.

Every citation that leaves the system is verified against the corpus: the cited
key must resolve to a real stored chunk, and any quoted span must be a verbatim
substring of that chunk's exact text (re-checked against its sha256). A citation
that fails verification is *dropped* and the point *abstains* — the engine
returns a real citation with a verbatim quote, or an honest "not supported by
the corpus." It has no code path that emits an unverified citation.
"""

from .chunk import Chunk, sha256_text
from .store import CorpusStore
from .retrieve import Retriever
from .verify import Citation, VerificationResult, verify_citation
from .engine import VerifiedAnswer, AnswerEngine

__all__ = [
    "Chunk",
    "sha256_text",
    "CorpusStore",
    "Retriever",
    "Citation",
    "VerificationResult",
    "verify_citation",
    "VerifiedAnswer",
    "AnswerEngine",
]

__version__ = "0.1.0"
