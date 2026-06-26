"""Build and warm the RAG vector index.

The first policy query embeds the parking policy document (Google embeddings) and
creates the MongoDB Atlas vector search index. That index builds asynchronously,
so the *very first* query often returns an empty result before it goes live. This
script runs warm-up queries with retries so the app is ready before anyone uses it.

Run via `make rag-index` (needs the databases up and GOOGLE_API_KEY / Ollama set).
"""

import sys
import time

from src.tools.rag_tool import search_parking_policies

WARMUP_QUESTION = "What are the parking operating hours?"
MAX_ATTEMPTS = 8
WAIT_SECONDS = 8


def main() -> int:
    print("Building and warming the RAG vector index...")
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            answer = str(search_parking_policies.invoke(WARMUP_QUESTION)).strip()
        except Exception as exc:  # noqa: BLE001 - surface any setup error clearly
            print(f"  attempt {attempt}: error: {exc}")
            answer = ""

        if answer and answer != "Empty Response":
            print(f"\nRAG index is ready (warmed on attempt {attempt}).")
            return 0

        print(f"  attempt {attempt}: index not queryable yet, waiting {WAIT_SECONDS}s...")
        time.sleep(WAIT_SECONDS)

    print(
        "\nRAG index did not become queryable. Check that:\n"
        "  - MongoDB is running (make db-up)\n"
        "  - GOOGLE_API_KEY is set in .env (used for embeddings)\n"
        "  - Ollama is running and signed in",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
