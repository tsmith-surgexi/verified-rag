import os

import pytest

from verified_rag.store import CorpusStore

CORPUS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "verified_rag", "corpus"
)


@pytest.fixture()
def store() -> CorpusStore:
    return CorpusStore.from_directory(CORPUS_DIR)
