"""RAG stage 5 — retrieval. Given a question, find the most relevant chunks and
present them with page + equation citations grounded in the book.

This is a *retrieval* RAG: it returns the exact passages and their citations. It
does not paraphrase with an LLM, so every line you read comes straight from the
textbook — nothing is invented.
"""
from __future__ import annotations

from dataclasses import dataclass

from .embed import embed_texts
from .store import get_collection


@dataclass
class Hit:
    text: str
    pdf_page: int
    printed_page: int
    equations: str
    book: str
    score: float  # cosine similarity in [-1, 1]; higher = more relevant

    def citation(self) -> str:
        cite = f"{self.book}, p. {self.printed_page} (PDF p. {self.pdf_page})"
        if self.equations:
            cite += f", eq. {self.equations}"
        return cite


def search(question: str, k: int = 5) -> list[Hit]:
    """Embed the question and return the top-k closest textbook chunks."""
    query_vec = embed_texts([question])[0]
    collection = get_collection()
    res = collection.query(
        query_embeddings=[query_vec],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    hits: list[Hit] = []
    for doc, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        hits.append(
            Hit(
                text=doc,
                pdf_page=int(meta["pdf_page"]),
                printed_page=int(meta["printed_page"]),
                equations=str(meta.get("equations", "")),
                book=str(meta.get("book", "")),
                score=1.0 - float(dist),  # Chroma returns cosine distance
            )
        )
    return hits


def format_hits(question: str, hits: list[Hit]) -> str:
    """Render retrieval results as a readable, citation-first answer."""
    lines = [f"Q: {question}", ""]
    if not hits:
        lines.append("No relevant passages found. Did you run `ingest` first?")
        return "\n".join(lines)
    for rank, hit in enumerate(hits, start=1):
        snippet = " ".join(hit.text.split())
        if len(snippet) > 600:
            snippet = snippet[:600] + " ..."
        lines.append(f"[{rank}] score={hit.score:.3f}  {hit.citation()}")
        lines.append(f"    {snippet}")
        lines.append("")
    return "\n".join(lines)
