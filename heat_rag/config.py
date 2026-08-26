"""Central configuration for the heat-transfer RAG system.

Everything the pipeline needs to know (where the book is, how to chunk it, which
embedding model to call) lives here so the other modules stay small and readable.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root = the folder that contains this package. We load the .env that
# sits next to it so LITELLM_KEY becomes available via os.getenv.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# --- Source document --------------------------------------------------------
PDF_PATH = PROJECT_ROOT / "data" / "AHTTv600.pdf"
BOOK_TITLE = "A Heat Transfer Textbook, 6th ed. (Lienhard & Lienhard, 2024)"

# --- Vector store (Chroma persists to disk here) ----------------------------
CHROMA_DIR = PROJECT_ROOT / "data" / "chroma"
COLLECTION = "ahtt"

# --- Chunking ---------------------------------------------------------------
# Chunks never cross a page boundary, so every chunk maps to exactly one page
# for clean citations. Within a page we use a sliding character window.
CHUNK_CHARS = 1200
CHUNK_OVERLAP = 200

# --- Embeddings via the LiteLLM proxy (OpenAI-compatible API) ---------------
LITELLM_BASE_URL = os.getenv("LITELLM_BASE_URL", "https://litellm.nlr.gov")
LITELLM_KEY = os.getenv("LITELLM_KEY")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
EMBED_BATCH = 64  # how many texts to send per embedding request

# Chat model for the optional generative, cite-only answer layer.
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-5-mini")
