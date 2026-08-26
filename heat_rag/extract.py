"""RAG stage 1 — extract text from the PDF, one page at a time.

We keep the page number with every piece of text so that later, when we answer a
question, we can point back to the exact page and equation in the book.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pymupdf  # the PDF text-extraction library (formerly imported as `fitz`)

from .config import PDF_PATH

# The book numbers equations as (chapter.number), e.g. (6.7) or (5.13a). Two
# reliable signals distinguish a real equation label from an ordinary decimal in
# parentheses like (0.17): the label sits at the end of a line (right-aligned
# numbering), or it is explicitly referenced as "Eq. (6.7)".
_EOL_EQ_RE = re.compile(r"(?m)\((\d{1,2}\.\d{1,2}[a-z]?)\)\s*$")
_INLINE_EQ_RE = re.compile(
    r"(?:Eqs?\.?|Eqn\.?|[Ee]quations?)\s*\((\d{1,2}\.\d{1,2}[a-z]?)\)"
)


def _eq_sort_key(label: str):
    chapter, rest = label.split(".", 1)
    digits = re.match(r"\d+", rest).group()
    return (int(chapter), int(digits), rest[len(digits):])


def find_equations(text: str) -> list[str]:
    """Return the equation labels (e.g. '6.7') referenced in a piece of text."""
    labels = set(_EOL_EQ_RE.findall(text)) | set(_INLINE_EQ_RE.findall(text))
    return sorted(labels, key=_eq_sort_key)


@dataclass
class Page:
    pdf_page: int          # 1-based index of the page inside the PDF file
    printed_page: int      # best-effort page number printed on the page itself
    text: str
    equations: list[str] = field(default_factory=list)


def _guess_printed_page(text: str, pdf_page: int) -> int:
    """The printed page number is usually a standalone integer in the margins.

    We scan the first and last few lines for a bare number. If we cannot find
    one (title pages, figures) we fall back to the PDF page index.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for cand in lines[:3] + lines[-3:]:
        if re.fullmatch(r"\d{1,3}", cand):
            return int(cand)
    return pdf_page


def extract_pages(pdf_path=PDF_PATH) -> list[Page]:
    """Return one Page per non-empty page of the PDF."""
    pages: list[Page] = []
    with pymupdf.open(pdf_path) as doc:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if not text:
                continue  # skip blank pages / pure figure pages with no text
            equations = find_equations(text)
            pages.append(
                Page(
                    pdf_page=i,
                    printed_page=_guess_printed_page(text, i),
                    text=text,
                    equations=equations,
                )
            )
    return pages
