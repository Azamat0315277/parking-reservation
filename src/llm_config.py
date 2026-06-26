"""Shared Ollama configuration for the chat/generation LLM.

The generation LLM runs on Ollama (`gemma4:31b-cloud`). A `:cloud` model is a
proxy stub: the local daemon at OLLAMA_BASE_URL forwards inference to
https://ollama.com using the credentials from `ollama signin`, so no API key is
needed for the local-daemon path. For headless/direct access, set
OLLAMA_BASE_URL=https://ollama.com and OLLAMA_API_KEY=<key>; the key is then sent
as a Bearer header.

Embeddings deliberately stay on Google (gemini-embedding-001) — see rag_tool.py.
"""

import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


def ollama_headers() -> dict:
    """Bearer auth header for Ollama Cloud when OLLAMA_API_KEY is set.

    Empty against a signed-in local daemon (it proxies :cloud models itself).
    LlamaIndex `Ollama` takes this via its `headers=` field; LangChain
    `ChatOllama` takes it via `client_kwargs={"headers": ...}`.
    """
    key = os.getenv("OLLAMA_API_KEY")
    return {"Authorization": f"Bearer {key}"} if key else {}
