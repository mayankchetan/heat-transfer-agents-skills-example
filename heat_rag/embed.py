"""RAG stage 3 — turn text into embedding vectors via the LiteLLM proxy.

The proxy speaks the OpenAI API, so we use the official `openai` client and just
point its base_url at https://litellm.nlr.gov. Every string in / every vector out.
"""
from __future__ import annotations

import base64

import numpy as np
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import EMBED_BATCH, EMBED_MODEL, LITELLM_BASE_URL, LITELLM_KEY


def _client() -> OpenAI:
    if not LITELLM_KEY:
        raise RuntimeError("LITELLM_KEY is missing — add it to the .env file.")
    return OpenAI(api_key=LITELLM_KEY, base_url=LITELLM_BASE_URL)


def _decode(embedding) -> list[float]:
    """A LiteLLM/OpenAI response can be a float list or a base64 string.

    We handle both so the pipeline works regardless of encoding_format.
    """
    if isinstance(embedding, str):
        raw = base64.b64decode(embedding)
        return np.frombuffer(raw, dtype=np.float32).astype(float).tolist()
    return list(embedding)


@retry(stop=stop_after_attempt(5), wait=wait_exponential(min=1, max=30))
def _embed_batch(client: OpenAI, texts: list[str]) -> list[list[float]]:
    resp = client.embeddings.create(
        input=texts, model=EMBED_MODEL, encoding_format="float"
    )
    return [_decode(item.embedding) for item in resp.data]


def embed_texts(texts: list[str], batch: int = EMBED_BATCH) -> list[list[float]]:
    """Embed a list of texts, one batch of requests at a time."""
    client = _client()
    vectors: list[list[float]] = []
    for i in range(0, len(texts), batch):
        vectors.extend(_embed_batch(client, texts[i : i + batch]))
    return vectors
