"""RAG stage 4 — the vector database (Chroma).

A vector database stores each chunk's embedding and, on a query, returns the
chunks whose vectors are closest to the query vector. We use cosine distance,
the standard choice for text embeddings. Chroma persists to disk under data/chroma.
"""
from __future__ import annotations

import chromadb
from chromadb.config import Settings

from .config import CHROMA_DIR, COLLECTION


def get_collection():
    """Open (or create) the persistent Chroma collection for the textbook."""
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    # hnsw:space=cosine tells Chroma to rank neighbours by cosine distance.
    return client.get_or_create_collection(
        name=COLLECTION, metadata={"hnsw:space": "cosine"}
    )


def reset_collection() -> None:
    """Delete the collection so a fresh ingest starts from an empty index."""
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass  # collection did not exist yet
