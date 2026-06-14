# llama-index-memory-unison

![CI](https://github.com/unison-labs-ai/llama-index-memory-unison/actions/workflows/ci.yml/badge.svg)

**LlamaIndex memory provider backed by the [Unison brain](https://unisonlabs.ai) — persistent, knowledge-graph-powered agent memory.** Drop it in wherever you'd use `ChatMemoryBuffer` to give your agents long-term recall across sessions.

Powered by the Unison brain.

## Install

```bash
pip install llama-index-memory-unison
```

## Quick start

```python
import os
from llama_index.memory.unison import UnisonMemory
from llama_index.core.agent import ReActAgent
from llama_index.llms.openai import OpenAI

# Build Unison memory for this user/session
memory = UnisonMemory.from_client(
    session_id="user-123",          # stable per-user or per-thread ID
    api_key="usk_live_...",         # or set UNISON_TOKEN env var
    # api_url="https://brain.unisonlabs.ai",  # default
    # search_k=5,                             # hits per recall
)

# Pass it to any LlamaIndex agent or chat engine
llm = OpenAI(model="gpt-4o", api_key=os.environ["OPENAI_API_KEY"])
agent = ReActAgent.from_tools([], llm=llm, memory=memory, verbose=True)

# Subsequent calls automatically recall relevant long-term context
response = agent.chat("What did we discuss last week about Alice?")
print(response)
```

### Replacing `ChatMemoryBuffer`

```python
# Before
from llama_index.core.memory import ChatMemoryBuffer
memory = ChatMemoryBuffer.from_defaults(token_limit=3000)

# After — drop-in replacement with long-term recall
from llama_index.memory.unison import UnisonMemory
memory = UnisonMemory.from_client(session_id="user-123", api_key="usk_live_...")
```

### Using environment variables

```bash
export UNISON_TOKEN="usk_live_..."
export UNISON_API_URL="https://brain.unisonlabs.ai"  # optional, this is the default
```

```python
from llama_index.memory.unison import UnisonMemory

# Reads UNISON_TOKEN and UNISON_API_URL automatically
memory = UnisonMemory.from_defaults(session_id="user-123")
```

## Environment variables

| Variable | Description | Default |
|---|---|---|
| `UNISON_TOKEN` | Unison API token (`usk_live_...`) | Required |
| `UNISON_API_URL` | Unison brain base URL | `https://brain.unisonlabs.ai` |

## How it works

| LlamaIndex call | What `UnisonMemory` does |
|---|---|
| `put(message)` | Appends to a local in-session buffer **and** POSTs the turn to `POST /v1/brain/ingest`. Ingestion is async on the Unison side — entity resolution and fact extraction happen server-side. |
| `get(input=query)` | Fetches `GET /v1/brain/context?q=<query>` and, if the brain has relevant hits (`weakEvidence=false`), prepends a `SYSTEM` message containing the recalled `contextMd` block ahead of the local buffer. |
| `get_all()` | Returns the raw local buffer only (no recall). |
| `set(messages)` | Replaces the local buffer. Server memory is **not** modified. |
| `reset()` | Clears the local buffer. Server memory is **not** deleted. |

Network errors are caught and logged; they never crash the agent.

## Releasing

This package uses **PyPI Trusted Publishing** (no API token required in CI).

Before the first release, configure a Trusted Publisher on PyPI:

1. Go to your PyPI project page → Publishing → Add a new publisher.
2. Set: Publisher = GitHub, Owner = `unison-labs-ai`, Repository = `llama-index-memory-unison`, Workflow = `release.yml`.

Then tag a release:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The `release.yml` workflow builds the wheel + sdist and publishes to PyPI automatically.

**Fallback:** if you prefer a token, set a `PYPI_API_TOKEN` repository secret and update `release.yml` to pass `password: ${{ secrets.PYPI_API_TOKEN }}` to the publish action.

## Links

- Unison brain: https://unisonlabs.ai
- Docs: https://docs.unisonlabs.ai
- Unison brain repo: https://github.com/unison-labs-ai/unison-brain
- LlamaIndex memory docs: https://docs.llamaindex.ai/en/stable/module_guides/storing/chat_stores/

## License

MIT — see [LICENSE](LICENSE).
