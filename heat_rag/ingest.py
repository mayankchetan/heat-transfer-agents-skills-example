"""RAG ingestion — run the whole pipeline once to build the index.

    PDF  ->  pages  ->  chunks  ->  embeddings  ->  Chroma vector DB

Run this once (and again whenever you change chunking). It prints counts at each
stage so you can watch the pipeline work.
"""
from __future__ import annotations

from .chunk import chunk_pages
from .config import BOOK_TITLE, EMBED_MODEL
from .embed import embed_texts
from .extract import extract_pages
from .store import get_collection, reset_collection


def ingest(reset: bool = True) -> int:
    """Build the vector index from the textbook. Returns the chunk count."""
    if reset:
        reset_collection()

    print("1/4  Extracting text from the PDF ...")
    pages = extract_pages()
    print(f"     -> {len(pages)} pages with text")

    print("2/4  Splitting pages into chunks ...")
    chunks = chunk_pages(pages)
    print(f"     -> {len(chunks)} chunks")

    print(f"3/4  Embedding chunks with {EMBED_MODEL} (via LiteLLM) ...")
    vectors = embed_texts([c.text for c in chunks])
    print(f"     -> {len(vectors)} vectors of dim {len(vectors[0])}")

    print("4/4  Writing to the Chroma vector DB ...")
    collection = get_collection()
    # Chroma metadata values must be scalars, so equations is a comma string.
    metadatas = [
        {
            "pdf_page": c.pdf_page,
            "printed_page": c.printed_page,
            "equations": ", ".join(c.equations),
            "book": BOOK_TITLE,
        }
        for c in chunks
    ]
    # Add in batches to keep each write small.
    step = 512
    for i in range(0, len(chunks), step):
        sl = slice(i, i + step)
        collection.add(
            ids=[c.id for c in chunks[sl]],
            documents=[c.text for c in chunks[sl]],
            embeddings=vectors[sl],
            metadatas=metadatas[sl],
        )
    print(f"Done. Indexed {len(chunks)} chunks into collection '{collection.name}'.")
    return len(chunks)
