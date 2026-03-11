# Stargate Parking Reservation System

A multi-agent RAG (Retrieval-Augmented Generation) system that combines LangGraph orchestration, LlamaIndex vector search, and PostgreSQL to handle parking information queries and spot reservations through natural language. The system classifies user intent and routes queries to specialized tools — SQL database lookups, policy document search, or a reservation workflow with human-in-the-loop approval.

## Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Configure environment
cp .env.example .env
# Edit .env with your GOOGLE_API_KEY and other settings

# 3. Start databases
docker compose up -d

# 4. Run all services (in separate terminals)
npx -y @modelcontextprotocol/server-filesystem    your/path/to/customer_data  # MCP file server
uvicorn src.api.main:app --reload --port 8000                  # Admin API
streamlit run src/ui/streamlit_app.py                          # User UI (localhost:8501)
streamlit run src/ui/admin_app.py --server.port 8502           # Admin UI (localhost:8502)
```

| Service | URL | Description |
|---------|-----|-------------|
| User UI | http://localhost:8501 | Chat interface for parking queries & reservations |
| Admin UI | http://localhost:8502 | Approve/reject pending reservations |
| Admin API | http://localhost:8000/docs | REST API with Swagger documentation |
| MCP Server | — | File operations for reservation logging |

## Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup](#setup)
- [Usage](#usage)
- [REST API](#rest-api)
- [Streamlit UI](#streamlit-ui)
- [Workflow Details](#workflow-details)
- [Tools](#tools)
- [Agents](#agents)
- [Security](#security)

## Architecture

The system is built as a LangGraph `StateGraph` with 7 nodes and 3 conditional routers. User queries enter the graph, get answered by a supervisor agent, then are classified as either informational (routed to `END`) or reservation requests (routed through a human-approval loop).

```
User Query
    │
    ▼
┌──────────┐
│ assistant│ ── Supervisor agent answers using SQL + RAG tools
└────┬─────┘       and appends <<<RESERVATION:{...}>>> or <<<INFO>>> tag
     │
     ▼
┌────────────────┐
│ classify_intent│ ── Reads reservation_details from state
└────┬───────────┘
     │
     ├── [info query] ──────────────────────────────────────► END
     │
     ▼
┌────────────────┐
│ human_approval │ ── interrupt() pauses graph
└────┬───────────┘       Collects: customer name, car number, approve/deny
     │
     ├── [denied] ──► denial ──► END
     │
     ▼
┌─────────────┐
│ reservation │ ── Finds available spot (if needed), executes SQL UPDATE
└────┬────────┘
     │
     ├── [failed] ──► denial ──► END
     │
     ▼
┌────────────────┐
│ file_recording │ ── Appends record to approved_reservations.txt via MCP
└────┬───────────┘
     │
     ▼
┌─────────────────────────┐
│ succesfull_reservation  │ ── Formats confirmation message
└────┬────────────────────┘
     │
     ▼
    END
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Orchestration | [LangGraph](https://github.com/langchain-ai/langgraph) — stateful graph with checkpointing and interrupts |
| LLM | [Google Gemini](https://ai.google.dev/) (via `langchain-google-genai`) |
| Agent framework | [LangChain](https://github.com/langchain-ai/langchain) `create_agent` |
| Admin API | [FastAPI](https://fastapi.tiangolo.com/) with Pydantic validation |
| User UI | [Streamlit](https://streamlit.io/) chat interface |
| Vector search (RAG) | [LlamaIndex](https://github.com/run-llama/llama_index) with sentence window parsing |
| Vector store | [MongoDB Atlas](https://www.mongodb.com/atlas) (cosine similarity index) |
| Relational DB | PostgreSQL with parameterized SQL via SQLAlchemy |
| File operations | [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol) filesystem server |
| Embeddings | Google `gemini-embedding-001` |
| Package manager | [uv](https://github.com/astral-sh/uv) |
| Python | 3.11+ |

## Project Structure

```
parking-reservation/
├── pyproject.toml                          # Dependencies (uv/hatchling)
├── .env.example                            # Environment variable template
├── notebooks/
│   └── research.ipynb                      # Original prototype notebook
└── src/
    ├── main.py                             # Entry point — interactive chat + example flow
    ├── agents/
    │   └── supervisor_agent.py             # Supervisor agent (Gemini + 5 tools)
    ├── api/
    │   ├── main.py                         # FastAPI app — Admin approval API
    │   ├── models/
    │   │   └── schemas.py                  # Pydantic models (ReservationRequest, etc.)
    │   ├── routers/
    │   │   └── reservations.py             # REST endpoints for reservation management
    │   └── services/
    │       └── reservation_service.py      # Business logic + file-based storage
    ├── ui/
    │   ├── streamlit_app.py                # Streamlit chat UI for users
    │   └── admin_app.py                    # Streamlit admin panel for approvals
    ├── prompts/
    │   ├── supervisor_prompt.py            # Supervisor system prompt with classification rules
    │   └── file_writer_prompt.py           # File agent system prompt
    ├── tools/
    │   ├── sql_reader_tool.py              # 4 read-only SQL tools (availability, pricing, details, find)
    │   ├── parking_reservation_tool.py     # reserve_parking_space — validated SQL UPDATE
    │   ├── rag_tool.py                     # search_parking_policies — LlamaIndex vector search
    │   └── file_writer_tools.py            # MCP-based append_reservation + read_reservations
    ├── workflow/
    │   ├── nodes.py                        # ParkingState, 7 graph nodes, 3 router functions
    │   └── workflow.py                     # StateGraph assembly + compile
    ├── sql/
    │   ├── parking_lots.sql                # Schema + 100-row seed data
    │   └── user_creating.sql               # reader / parking_writer DB roles
    ├── data/
    │   └── parking_policy.txt              # Policy document (598 lines, RAG source)
    └── customer_data/
        ├── approved_reservations.txt       # Reservation log (written by MCP file agent)
        └── pending_reservations.json       # Pending reservations queue (API storage)
```

## Setup

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd parking-reservation
uv sync
source .venv/bin/activate
```

### 2. Configure environment variables

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

| Variable | Purpose | Example |
|----------|---------|---------|
| `GOOGLE_API_KEY` | Gemini API key | `Your-Gemini-API-Key` |
| `LLM_MODEL` | Gemini model for generation | `gemini-3-flash-preview` |
| `EMBEDDING_MODEL` | Gemini model for embeddings | `gemini-embedding-001` |
| `READER_CONNECTION_STRING` | PostgreSQL URI (read-only user) | `postgresql://reader:pass@localhost:5432/rag_db` |
| `WRITER_CONNECTION_STRING` | PostgreSQL URI (writer user) | `postgresql://parking_writer:pass@localhost:5432/rag_db` |
| `SCHEMA` | PostgreSQL schema name | `parking` |
| `MONGODB_URI` | MongoDB Atlas connection string | `mongodb://localhost:53888/?directConnection=true` |
| `ALLOWED_DIR` | MCP filesystem restriction path | `customer_data/` |
| `LANGSMITH_API_KEY` | LangSmith tracing key (optional) | — |
| `LANGSMITH_TRACING` | Enable LangSmith tracing | `true` |
| `LANGSMITH_PROJECT` | LangSmith project name | `parking-reservation` |

### 3. Set up databases with Docker (Recommended)

The easiest way to run PostgreSQL and MongoDB is using Docker Compose. This automatically sets up both databases with the correct schema and seed data.

#### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed and running
- [Docker Compose](https://docs.docker.com/compose/install/) (included with Docker Desktop)

#### Start the containers

```bash
# Start both PostgreSQL and MongoDB containers
docker compose up -d

# Verify containers are running
docker compose ps

# View logs (optional)
docker compose logs -f
```

This will:
- Start **PostgreSQL 16** on port `5432` with:
  - Database `rag_db` created automatically
  - Schema and 100 parking spots seeded from `src/sql/parking_lots.sql`
  - `reader` and `parking_writer` users created from `src/sql/user_creating.sql`
- Start **MongoDB Atlas Local** on port `27017` with vector search support

#### Environment variables for Docker

Update your `.env` file with these connection strings:

```bash
# PostgreSQL (Docker)
READER_CONNECTION_STRING=postgresql://reader:password@localhost:5432/rag_db
WRITER_CONNECTION_STRING=postgresql://parking_writer:password@localhost:5432/rag_db

# MongoDB (Docker)
MONGODB_URI=mongodb://localhost:27017/?directConnection=true
```

#### Useful Docker commands

```bash
# Stop containers (preserves data)
docker compose stop

# Start stopped containers
docker compose start

# Stop and remove containers (preserves volume data)
docker compose down

# Stop and remove containers AND delete all data
docker compose down -v

# Restart with fresh data
docker compose down -v && docker compose up -d

# Connect to PostgreSQL CLI
docker exec -it parking-postgres psql -U admin -d rag_db

# Connect to MongoDB shell
docker exec -it parking-mongodb mongosh
```

#### Database layout

| Parking Type | Spot IDs | Price/hr | Count |
|-------------|----------|----------|-------|
| Premium | 1 - 15 | $6.00 | 15 |
| Standard | 16 - 65 | $4.00 | 50 |
| Rooftop | 66 - 85 | $3.00 | 20 |
| Oversized | 86 - 95 | $7.00 | 10 |
| Motorcycle | 96 - 100 | $2.00 | 5 |

The `reader` user has SELECT-only access. The `parking_writer` user can SELECT and UPDATE `space_availability`, `reservation_start`, and `reservation_end` columns only.

---

### 4. Alternative: Manual database setup

<details>
<summary>Click to expand manual setup instructions (without Docker)</summary>

#### Set up PostgreSQL manually

Create the database, schema, seed data, and restricted users:

```bash
# Create database (if not exists)
createdb rag_db

# Create schema and insert 100 parking spots
psql -U admin -d rag_db -f src/sql/parking_lots.sql

# Create reader and parking_writer roles
psql -U admin -d rag_db -f src/sql/user_creating.sql
```


On first run, the system automatically:
1. Reads `src/data/parking_policy.txt`
2. Parses it with a sentence window parser (window size: 3)
3. Generates embeddings via Gemini
4. Creates a `parking_policy` collection in the `parking_db` database
5. Creates a cosine similarity vector search index

### 5. Install MCP filesystem server

The file recording tool uses the MCP filesystem server via `npx`:

```bash
npx -y @modelcontextprotocol/server-filesystem `path/to/customer_data`
```

No separate installation is needed — `npx` downloads it on first use.

## Usage

### Interactive chat session (recommended)

```bash
python -m src.main
```

This starts a multi-turn conversation session where you can:
- Ask informational questions ("How many Premium spots are available?")
- Query parking policies ("What's the refund policy?")
- Make reservations ("Reserve a Premium spot from 2025-06-01 to 2025-06-02")

The system handles the human-in-the-loop flow inline — when a reservation is detected, it prompts for your name, car number, and confirmation.

### Example flow (scripted demo)

```bash
python -m src.main --example
```

Runs a pre-scripted 3-step reservation flow: availability check, reservation request, and approval with customer info.

### Programmatic usage

```python
from src.workflow.workflow import parking_graph
from langchain_core.messages import HumanMessage
from langgraph.types import Command
import uuid

# Each conversation session needs a unique thread_id
config = {"configurable": {"thread_id": str(uuid.uuid4())}}

# Step 1: Ask a question or request a reservation
result = await parking_graph.ainvoke(
    {"messages": [HumanMessage(content="Reserve a Premium spot from 2025-06-01 to 2025-06-02")]},
    config=config,
)

# Step 2: Check for interrupt (reservation detected)
graph_state = parking_graph.get_state(config)
for task in graph_state.tasks:
    if hasattr(task, "interrupts") and task.interrupts:
        print(task.interrupts[0].value)  # Shows reservation details

# Step 3: Resume with approval + customer info
result = await parking_graph.ainvoke(
    Command(resume={
        "decision": "approve",
        "customer_name": "John Doe",
        "car_number": "ABC-1234",
    }),
    config=config,
)

print(result["final_response"])
```

### Example queries

| Type | Query |
|------|-------|
| Availability | "How many Premium spots are available?" |
| Pricing | "What's the price for Rooftop parking?" |
| Spot details | "What's the status of spot #42?" |
| Policy | "What are the operating hours?" |
| Policy | "What's the refund policy?" |
| Reservation | "Reserve a Premium spot from 2025-06-01 to 2025-06-02" |

## REST API

The system includes a FastAPI-based Admin API for managing parking reservations. This provides a web interface for administrators to review and approve/reject reservation requests.

### Start the API server

```bash
uvicorn src.api.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive documentation is at `/docs` (Swagger UI) or `/redoc`.

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/reservations/request` | Create a new pending reservation |
| `GET` | `/reservations/pending` | List all pending reservations |
| `GET` | `/reservations/all` | List all reservations (any status) |
| `POST` | `/reservations/{id}/approve` | Approve a pending reservation |
| `POST` | `/reservations/{id}/reject` | Reject a pending reservation |
| `GET` | `/reservations/{id}/status` | Check reservation status |

### Request/Response models

**ReservationRequest** (POST `/reservations/request`):
```json
{
  "parking_id": 1,
  "parking_type": "Premium",
  "start_time": "2025-06-01T09:00:00",
  "end_time": "2025-06-02T09:00:00",
  "customer_name": "John Doe",
  "car_number": "ABC-1234",
  "total_price": 144.00
}
```

**ReservationResponse**:
```json
{
  "id": "uuid",
  "parking_id": 1,
  "parking_type": "Premium",
  "start_time": "2025-06-01T09:00:00",
  "end_time": "2025-06-02T09:00:00",
  "total_price": 144.00,
  "customer_name": "John Doe",
  "car_number": "ABC-1234",
  "status": "pending",
  "created_at": "2025-05-15T10:30:00",
  "updated_at": "2025-05-15T10:30:00",
  "admin_notes": null
}
```

**ApprovalRequest** (optional body for approve/reject):
```json
{
  "admin_notes": "Approved by admin"
}
```

### Workflow integration

When a reservation is approved via the API:
1. The `reserve_parking_space` tool is called to update the PostgreSQL database
2. The reservation is appended to `approved_reservations.txt`
3. The status changes from `pending` to `approved`

Pending reservations are stored in `customer_data/pending_reservations.json` with file locking for concurrent access safety.

## Streamlit UI

Two web interfaces for users and administrators to interact with the parking reservation system.

### Start the applications

```bash
# User interface (port 8501)
streamlit run src/ui/streamlit_app.py

# Admin interface (port 8502)
streamlit run src/ui/admin_app.py --server.port 8502
```

| Interface | URL | Purpose |
|-----------|-----|---------|
| User UI | `http://localhost:8501` | Chat, queries, reservation requests |
| Admin UI | `http://localhost:8502` | Review, approve/reject reservations |

### User UI Features

- **Chat interface**: Natural language queries about parking availability, pricing, and policies
- **Reservation flow**: When a reservation is detected, a form collects customer information
- **API integration**: Reservations are submitted to the Admin API for approval
- **Status checker**: Sidebar widget to check reservation status by ID

### Admin UI Features

- **Pending approvals tab**: View all pending reservations with approve/reject buttons
- **History tab**: View all reservations with filtering (by status) and sorting
- **Statistics sidebar**: Real-time counts of pending, approved, and rejected reservations
- **Admin notes**: Add optional notes when approving or rejecting

### Complete workflow

1. **User** opens User UI → asks "Reserve a Premium spot from 2025-06-01 to 2025-06-02"
2. **User** fills customer info form → submits → receives pending reservation ID
3. **Admin** opens Admin UI → sees pending reservation in "Pending Approvals" tab
4. **Admin** reviews details → clicks "Approve" (or "Reject" with notes)
5. **User** checks status in sidebar → sees "APPROVED" status

### Running all components

```bash
# Terminal 1: Databases
docker compose up -d

# Terminal 2: Admin API
uvicorn src.api.main:app --reload --port 8000

# Terminal 3: User UI
streamlit run src/ui/streamlit_app.py

# Terminal 4: Admin UI
streamlit run src/ui/admin_app.py --server.port 8502
```

### Environment variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `API_BASE_URL` | Admin API URL for reservation submissions | `http://localhost:8000` |

## Workflow Details

### Graph state (`ParkingState`)

Defined in [nodes.py](src/workflow/nodes.py), extends LangGraph's `MessagesState`:

| Field | Type | Purpose |
|-------|------|---------|
| `messages` | `list` | Conversation history (uses `add_messages` reducer) |
| `reservation_details` | `str` | JSON string with parsed reservation info, or `""` |
| `approval` | `str` | `"approved"` / `"denied"` / `""` |
| `customer_name` | `str` | Customer's full name (collected at interrupt) |
| `car_number` | `str` | Customer's car/license plate number |
| `reservation_success` | `bool` | Whether the SQL UPDATE succeeded |
| `final_response` | `str` | Text returned to the user |

### Nodes

| Node | Function | Description |
|------|----------|-------------|
| `assistant` | [nodes.py:52](src/workflow/nodes.py#L52) `assistant_node` | Invokes supervisor agent, parses `<<<RESERVATION:...>>>` or `<<<INFO>>>` tags from its response |
| `classify_intent` | [nodes.py:94](src/workflow/nodes.py#L94) `classify_intent_node` | Passthrough — classification is already done in `assistant_node` via tag parsing |
| `human_approval` | [nodes.py:107](src/workflow/nodes.py#L107) `human_approval_node` | Calls `interrupt()` to pause the graph; expects a dict with `decision`, `customer_name`, `car_number` |
| `reservation` | [nodes.py:161](src/workflow/nodes.py#L161) `reservation_node` | Finds available spot if no `parking_id` specified, then calls `reserve_parking_space` tool |
| `file_recording` | [nodes.py:203](src/workflow/nodes.py#L203) `file_recording_node` | Async — appends reservation to `approved_reservations.txt` via MCP filesystem server |
| `succesfull_reservation` | [nodes.py:229](src/workflow/nodes.py#L229) `succesfull_reservation_node` | Formats confirmation with all details (customer, spot, dates, price) |
| `denial` | [nodes.py:262](src/workflow/nodes.py#L262) `denial_node` | Returns cancellation message |

### Routers

| Router | After Node | Condition | Routes To |
|--------|------------|-----------|-----------|
| `route_after_classification` | `classify_intent` | `reservation_details` is non-empty | `human_approval` or `END` |
| `route_after_approval` | `human_approval` | `approval == "approved"` | `reservation` or `denial` |
| `route_after_reservation` | `reservation` | `reservation_success == True` | `file_recording` or `denial` |

### Graph compilation

The graph is compiled with `InMemorySaver` as the checkpointer in [workflow.py](src/workflow/workflow.py#L38), which enables:
- Multi-turn conversations within a session (same `thread_id`)
- `interrupt()` / `Command(resume=...)` for human-in-the-loop

## Tools

### SQL reader tools — [sql_reader_tool.py](src/tools/sql_reader_tool.py)

Four read-only tools backed by SQLAlchemy with parameterized queries against the `READER_CONNECTION_STRING`:

| Tool | Purpose | Input |
|------|---------|-------|
| `check_availability` | Count available spots, optionally by type | `parking_type` (optional) |
| `get_pricing` | Get price per hour by type | `parking_type` (optional) |
| `get_spot_details` | Full details for a specific spot | `parking_id` (int) |
| `find_available_spot` | Find one available spot of a given type | `parking_type` (required) |

### Reservation tool — [parking_reservation_tool.py](src/tools/parking_reservation_tool.py)

`reserve_parking_space` — Accepts a JSON string with `parking_type`, `parking_id`, `start_time`, and `end_time`. Validates all inputs (type membership, positive ID, ISO 8601 timestamps, end > start), verifies the spot exists and is available, then executes a SQL `UPDATE` via the `WRITER_CONNECTION_STRING`. Returns a confirmation string containing "confirmed" on success.

### RAG tool — [rag_tool.py](src/tools/rag_tool.py)

`search_parking_policies` — LlamaIndex-powered vector search over the 598-line parking policy document. Uses:
- **Sentence window parsing** (window size: 3) for context-aware chunking
- **MongoDB Atlas** as the vector store with cosine similarity
- **MetadataReplacementPostProcessor** to return surrounding context
- **Lazy initialization** — the index is built on first query

### MCP file tools — [file_writer_tools.py](src/tools/file_writer_tools.py)

Two async tools that use `MultiServerMCPClient` with the `@modelcontextprotocol/server-filesystem` MCP server:

| Tool | Purpose |
|------|---------|
| `append_reservation` | Read existing file, append new reservation line, write back |
| `read_reservations` | Read and return all approved reservations |

File format: `Name | Car Number | Parking #ID (Type) | Period | Approved: Timestamp`

The MCP server is restricted to the `ALLOWED_DIR` directory.

## Agents

### Supervisor agent — [supervisor_agent.py](src/agents/supervisor_agent.py)

Created with `langchain.agents.create_agent` using the Gemini model. This is the main query-answering agent that has access to all 5 read-side tools:

- `check_availability`
- `get_pricing`
- `get_spot_details`
- `find_available_spot`
- `search_parking_policies`

The supervisor prompt ([supervisor_prompt.py](src/prompts/supervisor_prompt.py)) includes:
- Tool routing table mapping query types to the appropriate tool
- Instructions to append `<<<RESERVATION:{...}>>>` or `<<<INFO>>>` tags after its natural language response
- Security rules to reject prompt injection attempts

Each invocation of the supervisor uses a unique `thread_id` (`f"supervisor-{uuid4()}"`) to prevent context leakage between turns.

## Security

### Database access control

Two PostgreSQL roles enforce least-privilege access:

- **`reader`** — SELECT-only on the `parking` schema. Cannot modify any data.
- **`parking_writer`** — SELECT on all tables + UPDATE restricted to three columns: `space_availability`, `reservation_start`, `reservation_end`. Cannot CREATE, ALTER, or DROP.

See [user_creating.sql](src/sql/user_creating.sql) for the full role definitions.

### SQL injection prevention

All SQL queries in the reader and writer tools use **parameterized queries** via SQLAlchemy's `text()` with bound parameters (`:ptype`, `:id`, `:start`, `:end`). No string interpolation is used for user-supplied values.

### Input validation (reservation tool)

The `reserve_parking_space` tool validates:
- `parking_id` is a positive integer
- `parking_type` is one of the 5 valid types
- Timestamps are valid ISO 8601
- `end_time` is after `start_time`
- The spot exists, matches the requested type, and is currently available

### Supervisor prompt hardening

The supervisor prompt instructs the agent to treat "ignore instructions" and "admin override" messages as attacks and refuse to comply.

### File system restriction

The MCP filesystem server is restricted to the `ALLOWED_DIR` directory, preventing access to files outside the designated customer data folder.

### Separation of concerns

The file agent prompt ([file_writer_prompt.py](src/prompts/file_writer_prompt.py)) explicitly defines boundaries — the file agent cannot approve reservations, query the database, or search policies.
