"""Optional RAG stage 6 — generative, cite-only answer.

Retrieval (search.py) returns raw passages. This module goes one step further:
it feeds those passages to a chat model through the LiteLLM proxy with a strict
instruction to answer ONLY from the excerpts and to cite each one. This keeps the
answer grounded — the model may summarise, but it cannot introduce equations or
page numbers that are not in the retrieved text.
"""
from __future__ import annotations

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import CHAT_MODEL, LITELLM_BASE_URL, LITELLM_KEY
from .search import Hit, search

_SYSTEM = (
    "You are a heat-transfer teaching assistant. Answer the question using ONLY "
    "the numbered textbook excerpts provided. Every equation, boundary condition, "
    "or correlation you state must cite the excerpt it came from using its [n] "
    "tag. If the excerpts do not contain the answer, say so plainly. Do not use "
    "outside knowledge, and never invent page numbers or equations."
)


def _context(hits: list[Hit]) -> str:
    """Render retrieved passages as numbered, citation-tagged blocks."""
    blocks = []
    for i, hit in enumerate(hits, start=1):
        blocks.append(f"[{i}] {hit.citation()}\n{hit.text.strip()}")
    return "\n\n".join(blocks)


@retry(stop=stop_after_attempt(4), wait=wait_exponential(min=1, max=20))
def _complete(client: OpenAI, messages: list[dict]) -> str:
    resp = client.chat.completions.create(model=CHAT_MODEL, messages=messages)
    return resp.choices[0].message.content or ""


def answer(question: str, k: int = 6) -> tuple[str, list[Hit]]:
    """Retrieve, then compose a grounded answer. Returns (answer_text, hits)."""
    hits = search(question, k=k)
    if not hits:
        return (
            "No relevant passages were found in the textbook. Try different "
            "search terms, or run `ingest` if the index is empty.",
            hits,
        )
    if not LITELLM_KEY:
        raise RuntimeError("LITELLM_KEY is missing — add it to the .env file.")
    client = OpenAI(api_key=LITELLM_KEY, base_url=LITELLM_BASE_URL)
    messages = [
        {"role": "system", "content": _SYSTEM},
        {
            "role": "user",
            "content": f"Question: {question}\n\nExcerpts:\n{_context(hits)}",
        },
    ]
    return _complete(client, messages), hits


def format_answer(text: str, hits: list[Hit]) -> str:
    """Append a Sources list mapping [n] tags to their full citations."""
    lines = [text.strip()]
    if hits:
        lines.append("")
        lines.append("Sources:")
        for i, hit in enumerate(hits, start=1):
            lines.append(f"  [{i}] {hit.citation()}")
    return "\n".join(lines)
