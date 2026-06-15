<div align="center">

<img src="https://raw.githubusercontent.com/unison-labs-ai/unison-brain/main/assets/brain.svg" alt="Unison Brain" width="180" />

# llama-index-memory-unison

### Long-term agent memory for LlamaIndex — powered by the Unison brain.

**Drop in wherever you'd use `ChatMemoryBuffer`.** Agents get persistent,
knowledge-graph-powered recall across sessions with zero infrastructure changes.

[![CI](https://github.com/unison-labs-ai/llama-index-memory-unison/actions/workflows/ci.yml/badge.svg)](https://github.com/unison-labs-ai/llama-index-memory-unison/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/llama-index-memory-unison)](https://pypi.org/project/llama-index-memory-unison/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Stars](https://img.shields.io/github/stars/unison-labs-ai/llama-index-memory-unison?style=social)](https://github.com/unison-labs-ai/llama-index-memory-unison)

[**Install**](#install) • [**Quick start**](#quick-start) • [**Replacing ChatMemoryBuffer**](#replacing-chatmemorybuffer) • [**How it works**](#how-it-works) • [**For agents**](./AGENTS.md)

</div>

---

> **Reading this as an AI agent?** See [`AGENTS.md`](./AGENTS.md) — install, auth, and `UnisonMemory.from_client(session_id=...)` usage in one place.

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

Set a PyPI token, then run one command:

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-...
python scripts/release.py
```

Or configure `~/.pypirc` instead of the env vars.

The script builds `llama-index-memory-unison`, publishes to PyPI (idempotent — skips if the version is already on PyPI), then tags and pushes `v<version>`.

## Links

- Unison brain: https://unisonlabs.ai
- Docs: https://docs.unisonlabs.ai
- Unison brain repo: https://github.com/unison-labs-ai/unison-brain
- LlamaIndex memory docs: https://docs.llamaindex.ai/en/stable/module_guides/storing/chat_stores/

## Contributing & security

Contributions welcome — see [`CONTRIBUTING.md`](./CONTRIBUTING.md). Found a vulnerability? See [`SECURITY.md`](./SECURITY.md) — please report privately, not via a public issue.

## Part of the Unison Labs constellation

**One brain, every agent.** Every repo below reads from _and writes to_ the same [Unison brain](https://unisonlabs.ai) — no per-tool memory silos.

| Repo | What it does |
|---|---|
| [unison-brain](https://github.com/unison-labs-ai/unison-brain) | CLI · SDK · MCP server — the core |
| [claude-unison](https://github.com/unison-labs-ai/claude-unison) | Memory for Claude Code |
| [cursor-unison](https://github.com/unison-labs-ai/cursor-unison) | Memory for Cursor |
| [codex-unison](https://github.com/unison-labs-ai/codex-unison) | Memory for OpenAI Codex CLI |
| [opencode-unison](https://github.com/unison-labs-ai/opencode-unison) | Memory for OpenCode |
| [openclaw-unison](https://github.com/unison-labs-ai/openclaw-unison) | Memory for OpenClaw |
| [pipecat-unison](https://github.com/unison-labs-ai/pipecat-unison) | Memory for Pipecat voice agents |
| [langchain-unison](https://github.com/unison-labs-ai/langchain-unison) | LangChain memory, history & retriever |
| **[llama-index-memory-unison](https://github.com/unison-labs-ai/llama-index-memory-unison)** | **LlamaIndex memory provider ← you are here** |
| [unison-ai-sdk](https://github.com/unison-labs-ai/unison-ai-sdk) | Vercel AI SDK memory middleware |
| [unison-mastra](https://github.com/unison-labs-ai/unison-mastra) | Mastra agent memory provider |
| [python-sdk](https://github.com/unison-labs-ai/python-sdk) | Python SDK for the brain |
| [install-mcp](https://github.com/unison-labs-ai/install-mcp) | One-command MCP installer |
| [unison-fs](https://github.com/unison-labs-ai/unison-fs) | Mount the brain as a filesystem |
| [backchannel](https://github.com/unison-labs-ai/backchannel) | Async messaging between agents |
| [Unison-evals](https://github.com/unison-labs-ai/Unison-evals) | Open memory benchmark suite |

## License

MIT — see [LICENSE](LICENSE).
