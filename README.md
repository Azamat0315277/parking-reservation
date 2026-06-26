# 🅿️ Stargate Parking Reservation System

An AI parking assistant. Ask about availability, pricing, and policies in plain
English, or make a reservation — an LLM agent answers questions, looks up live
data, and routes reservation requests through human approval.

It's built on a **LangGraph** agent (running on **Ollama** `gemma4:31b-cloud`) with
SQL tools over PostgreSQL, document search (RAG) over MongoDB, a FastAPI approval
service, and Streamlit web UIs.

---

## What you can do

- **Ask questions** — "How many Standard spots are available?", "What's the price for Premium parking?", "What's the EV charging policy?"
- **Make a reservation** — "Reserve a Premium spot from 2025-06-01 to 2025-06-02". The request is captured and sent for admin approval.
- **Approve/reject** reservations as an admin, via the API or the Admin UI.

---

## Prerequisites

Install these first:

| Tool | Why | Install |
|------|-----|---------|
| **[uv](https://docs.astral.sh/uv/)** | Python deps + runner (manages Python 3.11 for you) | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **[Docker](https://docs.docker.com/get-docker/)** | Runs PostgreSQL + MongoDB | Docker Desktop |
| **[Node.js 18+](https://nodejs.org/)** | Runs the MCP file server (via `npx`) for saving approved reservations | nodejs.org |
| **[Ollama](https://ollama.com/download)** | Serves the LLM | ollama.com |
| **GNU Make** | Runs the project commands | Preinstalled on macOS/Linux |

### One-time Ollama setup

The model `gemma4:31b-cloud` runs on **Ollama Cloud** (proxied through your local
Ollama). You need a free Ollama account, then:

```bash
ollama signin                 # authenticate your machine (opens the browser)
ollama pull gemma4:31b-cloud  # register the cloud model
```

> You also need a **Google API key** for embeddings (the document search uses
> Google `gemini-embedding-001`). Get one free at
> [aistudio.google.com/apikey](https://aistudio.google.com/apikey).

---

## Quick Start

```bash
# 1. Clone and enter the project
git clone <repo-url> && cd parking-reservation

# 2. First run — creates .env, then stops so you can add your key
make setup
#    → edit .env and set GOOGLE_API_KEY=...

# 3. Run setup again — installs deps, starts databases, builds the search index
make setup

# 4. Start the app
make start
```

`make start` launches three services and prints their URLs:

| Service | URL | What it's for |
|---------|-----|---------------|
| **User UI** | http://localhost:8501 | Chat + make reservations |
| **Admin UI** | http://localhost:8502 | Approve/reject reservations |
| **Admin API** | http://localhost:8000/docs | REST API (Swagger docs) |

Press **Ctrl-C** to stop them all.

Prefer the terminal? Run the chat assistant directly:

```bash
make chat
```

---

## Make commands

Run `make help` to see everything. The ones you'll use most:

| Command | What it does |
|---------|--------------|
| `make setup` | One-time end-to-end setup: deps, databases, RAG index |
| `make start` | Run the Admin API + User UI + Admin UI together |
| `make chat` | Run the interactive CLI chat assistant |
| `make test` | Run the test suite |
| `make db-up` / `make db-down` | Start / stop the databases |
| `make db-reset` | Wipe and re-seed the databases from scratch |
| `make api` / `make user-ui` / `make admin-ui` | Run a single service |
| `make ollama-check` | Verify Ollama is running and the model is available |
| `make clean` | Remove caches and test artifacts |

You can override ports, e.g. `make start API_PORT=9000`.

---

## How it works

```
                         ┌──────────────────────────────────────┐
   "Reserve a Premium    │            LangGraph workflow         │
    spot tomorrow"       │                                      │
        │                │   ┌────────────┐   classify intent   │
   User UI / CLI ───────▶│   │ Supervisor │──────────┐          │
                         │   │   agent    │          ▼          │
                         │   │ (gemma4)   │   question? ──▶ answer
                         │   └─────┬──────┘          │          │
                         │         │ 5 tools         ▼          │
                         │         │           reservation?     │
                         │         ▼                 │          │
                         │   ┌───────────┐           ▼          │
                         │   │ SQL (PG)  │     human approval ──▶│──▶ Admin API / UI
                         │   │ RAG (Mongo)│          │          │       │ approve
                         │   └───────────┘           ▼          │       ▼
                         │                    reserve (SQL)      │   write to file
                         └──────────────────────────────────────┘    (MCP server)
```

1. The **supervisor agent** (LangGraph + Ollama) reads your message and decides whether to answer a question or start a reservation, using five tools:
   - `check_availability`, `get_pricing`, `get_spot_details`, `find_available_spot` — live SQL queries against PostgreSQL.
   - `search_parking_policies` — document search (RAG) over the policy doc, using LlamaIndex + MongoDB vector search + Ollama for the answer.
2. **Questions** are answered directly.
3. **Reservation requests** are classified, then sent to **human approval**. In the default API mode, the request becomes a *pending reservation* that an admin approves or rejects via the Admin API / UI.
4. On approval, the spot is reserved (SQL update) and recorded to `src/customer_data/approved_reservations.txt` via the **MCP filesystem server**.

The LLM split: **Ollama `gemma4:31b-cloud`** handles all text generation; **Google `gemini-embedding-001`** handles embeddings for document search.

---

## Configuration

`make setup` copies [.env.example](.env.example) to `.env`. The only value you must
set is `GOOGLE_API_KEY` — everything else defaults to the bundled Docker stack.

| Variable | Purpose | Default |
|----------|---------|---------|
| `GOOGLE_API_KEY` | **Required.** Google key for embeddings | *(you set this)* |
| `LLM_MODEL` | Ollama model for generation | `gemma4:31b-cloud` |
| `OLLAMA_BASE_URL` | Ollama endpoint (local daemon proxies the cloud model) | `http://localhost:11434` |
| `OLLAMA_API_KEY` | Only for direct cloud access; blank for local daemon | *(blank)* |
| `EMBEDDING_MODEL` | Google embedding model | `gemini-embedding-001` |
| `READER_CONNECTION_STRING` | PostgreSQL read-only user | matches docker-compose |
| `WRITER_CONNECTION_STRING` | PostgreSQL writer user | matches docker-compose |
| `MONGODB_URI` | MongoDB connection | matches docker-compose |
| `ALLOWED_DIR` | Where approved reservations are written | `src/customer_data` |
| `USE_API_APPROVAL` | `true` = approve via API/UI, `false` = approve in CLI | `true` |
| `LANGSMITH_TRACING` | Enable LangSmith tracing (optional) | `false` |

---

## REST API

Start it with `make api` (or it's included in `make start`). Interactive docs at
**http://localhost:8000/docs**.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/reservations/request` | Submit a pending reservation |
| `GET` | `/reservations/pending` | List pending reservations |
| `GET` | `/reservations/all` | List all reservations |
| `POST` | `/reservations/{id}/approve` | Approve a reservation |
| `POST` | `/reservations/{id}/reject` | Reject a reservation |
| `GET` | `/reservations/{id}/status` | Check a reservation's status |

---

## Project structure

```
src/
├── main.py                  # CLI chat entry point
├── agents/                  # Supervisor agent (Ollama + 5 tools)
├── workflow/                # LangGraph state machine (nodes + graph)
├── tools/                   # SQL, RAG, reservation, and MCP file tools
├── prompts/                 # Supervisor system prompt
├── guardrails/              # PII filtering
├── api/                     # FastAPI admin approval service
├── ui/                      # Streamlit user + admin apps
├── evaluation/              # RAGAS evaluation pipeline
├── llm_config.py            # Shared Ollama config (base URL + auth)
├── data/                    # Parking policy document (RAG source)
└── sql/                     # Schema + seed data (100 parking spots)

scripts/build_rag_index.py   # Builds & warms the vector index (used by make setup)
docker-compose.yml           # PostgreSQL + MongoDB
Makefile                     # All project commands
```

---

## Testing

```bash
make test
```

The suite (264 tests) runs fully offline with mocks — no databases, API keys, or
Ollama needed. For coverage: `uv run --env-file .env pytest tests/ --cov=src`.

---

## RAG evaluation

Measure retrieval quality (Context Precision / Recall) with RAGAS:

```bash
uv run --env-file .env python -m src.evaluation.cli                 # full run
uv run --env-file .env python -m src.evaluation.cli --questions 5   # first 5 questions
uv run --env-file .env python -m src.evaluation.cli --output report.json
```

Requires the databases up (`make db-up`) and a populated RAG index (`make rag-index`).

---

## Troubleshooting

**`make setup` stops after creating `.env`** — that's expected on the first run. Set
`GOOGLE_API_KEY` in `.env`, then run `make setup` again.

**`Ollama not reachable` / `Model not found`** — start the Ollama app, then:
```bash
ollama signin
ollama pull gemma4:31b-cloud
```
Cloud models need you to stay signed in. A `401`/auth error at runtime means run `ollama signin` again.

**RAG answers are empty on the very first query** — the MongoDB vector index builds
asynchronously and isn't live for a few seconds. `make setup` warms it for you; if you
skipped that, run `make rag-index`.

**Database password / connection errors** — your `.env` must match the Docker stack.
The cleanest fix is a fresh start: `make db-reset` re-seeds Postgres and MongoDB with
the credentials from `.env.example`. (The seed script creates the `reader` /
`parking_writer` roles with password `password` — keep your `.env` aligned with it.)

**Reservation approval doesn't save to file** — saving uses the MCP filesystem server,
launched on demand via `npx`. Make sure **Node.js** is installed and `ALLOWED_DIR`
points to a real directory (default `src/customer_data`).

---

## Tech stack

| Component | Technology |
|-----------|------------|
| LLM (generation) | [Ollama](https://ollama.com/) `gemma4:31b-cloud` |
| Embeddings | Google `gemini-embedding-001` |
| Orchestration | [LangGraph](https://github.com/langchain-ai/langgraph) (stateful graph + human-in-the-loop) |
| Agent | [LangChain](https://github.com/langchain-ai/langchain) `create_agent` |
| RAG | [LlamaIndex](https://github.com/run-llama/llama_index) + MongoDB vector search |
| Databases | PostgreSQL (spots) + MongoDB Atlas Local (vectors) |
| API | [FastAPI](https://fastapi.tiangolo.com/) |
| UI | [Streamlit](https://streamlit.io/) |
| File ops | [MCP](https://modelcontextprotocol.io/) filesystem server |
| Evaluation | [RAGAS](https://docs.ragas.io/) |
| Tooling | [uv](https://github.com/astral-sh/uv), Docker, Make |
