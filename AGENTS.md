# AGENTS.md

Guidance for AI agents. This file covers two jobs — jump to yours:

- **Use llama-index-memory-unison** — you're an agent helping someone wire Unison memory into a LlamaIndex project
- **Contribute to this repo** — you're changing this integration's code

Follows the [AGENTS.md](https://agents.md/) convention. Human contributors: see [`CONTRIBUTING.md`](./CONTRIBUTING.md).

---

## Use llama-index-memory-unison

### What it does

`llama-index-memory-unison` is a drop-in replacement for LlamaIndex's `ChatMemoryBuffer`
that gives your agents persistent, knowledge-graph-powered long-term memory backed by
the [Unison brain](https://unisonlabs.ai).

| LlamaIndex call | What `UnisonMemory` does |
|---|---|
| `put(message)` | Appends to the local in-session buffer **and** POSTs the turn to the Unison brain for async ingestion (entity resolution + fact extraction happen server-side) |
| `get(input=query)` | Calls the brain's context endpoint and, when relevant hits exist, prepends a `SYSTEM` recall block ahead of the local buffer |
| `get_all()` | Returns the raw local buffer only — no recall |
| `set(messages)` | Replaces the local buffer; server memory is **not** modified |
| `reset()` | Clears the local buffer; server memory is **not** deleted |

Network errors are caught and logged — they never crash the agent.

### Install

```bash
pip install llama-index-memory-unison
```

### Authenticate

Set the `UNISON_TOKEN` environment variable before running your agent:

```bash
export UNISON_TOKEN="usk_live_..."
export UNISON_API_URL="https://brain.unisonlabs.ai"   # optional — this is the default
```

**Provision a token (headless / CI):**

```bash
curl -X POST https://brain.unisonlabs.ai/v1/auth/provision \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com"}'
# Returns: {"apiKey":"usk_live_...","workspaceId":"..."}
export UNISON_TOKEN="usk_live_..."
```

### Usage — drop-in for `ChatMemoryBuffer`

```python
# Before
from llama_index.core.memory import ChatMemoryBuffer
memory = ChatMemoryBuffer.from_defaults(token_limit=3000)

# After — long-term recall across sessions, same interface
from llama_index.memory.unison import UnisonMemory
memory = UnisonMemory.from_client(session_id="user-123", api_key="usk_live_...")
```

Pass `memory` to any LlamaIndex agent or chat engine as normal:

```python
from llama_index.core.agent import ReActAgent
from llama_index.llms.openai import OpenAI

llm = OpenAI(model="gpt-4o")
agent = ReActAgent.from_tools([], llm=llm, memory=memory, verbose=True)

response = agent.chat("What did we discuss last week about the architecture?")
print(response)
```

Using environment variables (reads `UNISON_TOKEN` and `UNISON_API_URL` automatically):

```python
from llama_index.memory.unison import UnisonMemory

memory = UnisonMemory.from_defaults(session_id="user-123")
```

### Environment variables

| Variable | Description | Default |
|---|---|---|
| `UNISON_TOKEN` | Unison API token (`usk_live_...`) | Required |
| `UNISON_API_URL` | Unison brain base URL | `https://brain.unisonlabs.ai` |

---

## Contributing to this repo

Single-package Python project. Source in `src/llama_index/memory/unison/`, tests in `tests/`.

### Build, test

```bash
pip install -e ".[dev]"   # or: pip install -e . pytest httpx llama-index-core
pytest -q
```

CI runs `pytest -q`. All tests must pass before merging.

### Key conventions

- Keep the dependency footprint minimal — `llama-index-core` and `httpx` are the only runtime deps.
- `UnisonMemory` must be tolerant: if the brain is unreachable or `UNISON_TOKEN` is missing, log a warning and degrade gracefully — never raise in `get()` or `put()`.
- The client enforces nothing. The Unison backend is the only security boundary. Do not add client-side scope checks or path allow-lists.
- No comments unless the logic is genuinely non-obvious. Good names explain themselves.

### PRs

One logical change per PR. Add or update a test for every new behavior. Run `pytest -q` before pushing. Security issues: see [`SECURITY.md`](./SECURITY.md).
