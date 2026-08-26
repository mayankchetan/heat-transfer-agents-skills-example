"""RAG stage 2 — split each page into small overlapping chunks.

Why chunk? Embedding models turn a piece of text into one vector. A whole page
is too coarse (the vector blurs many ideas together), so we cut each page into
~1200-character windows with a little overlap so ideas that straddle a boundary
are still captured. Each chunk keeps its page number for citation.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import CHUNK_CHARS, CHUNK_OVERLAP
from .extract import Page, find_equations


@dataclass
class Chunk:
    id: str
    text: str
    pdf_page: int
    printed_page: int
    equations: list[str]


def _windows(text: str, size: int, overlap: int) -> list[str]:
    """Sliding character window that snaps the cut point to a nearby space."""
    if len(text) <= size:
        return [text]
    out: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        # Snap the end to the last whitespace so we do not slice mid-word.
        if end < len(text):
            space = text.rfind(" ", start + size - overlap, end)
            if space != -1:
                end = space
        out.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [w for w in out if w]


def chunk_pages(pages: list[Page]) -> list[Chunk]:
    """Turn Page objects into citation-tagged Chunk objects."""
    chunks: list[Chunk] = []
    for page in pages:
        for idx, window in enumerate(_windows(page.text, CHUNK_CHARS, CHUNK_OVERLAP)):
            equations = find_equations(window)
            chunks.append(
                Chunk(
                    id=f"p{page.pdf_page}-c{idx}",
                    text=window,
                    pdf_page=page.pdf_page,
                    printed_page=page.printed_page,
                    equations=equations,
                )
            )
    return chunks
