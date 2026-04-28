---
license: apache-2.0
library_name: stackme
tags:
- memory
- context
- llm
- rag
- agentic
- local-ai
- open-source
---

# 🧠 Stackme

**The context layer for every AI.**

Stackme is a free, open-source memory layer for AI. It stores what matters about you, retrieves relevant context before every query, and injects it into any AI — ChatGPT, Claude, Copilot, Gemini, Ollama, or any AI via API.

**No server. No subscription. No data leaves your machine.**

---

## Install

```bash
pip install stackme
```

Or install from source:

```bash
pip install git+https://github.com/my-ai-stack/stackme
```

---

## Quick Start

```python
from stackme import Context

ctx = Context()

# Add facts about yourself
ctx.add_fact("I run a fintech B2B SaaS, launched March 2024")
ctx.add_fact("Q3 goal: 10K paying customers")
ctx.add_fact("Users are 25-40, income $50-100K")

# Add a user message — facts are auto-extracted
ctx.add_user_message("I'm building a B2B SaaS, targeting fintech companies")

# Ask any AI — Stackme retrieves your context first
context = ctx.get_relevant("What pricing should we use?")
# → "## Facts\n- I run a fintech B2B SaaS...\n- Q3 goal: 10K paying customers..."

# Your AI gets the full picture every time.
print(context)
```

---

## How It Works

```
You: "What pricing should we use?"

Stackme retrieves:
  - I run a fintech B2B SaaS
  - Q3 goal: 10K paying customers
  - Users are 25-40, income $50-100K

Enriched prompt → ChatGPT / Claude / any AI
```

---

## Architecture

```
~/.stackme/
├── memory.sqlite     ← all memories
├── vectors.faiss     ← semantic index
└── facts.graph       ← structured knowledge graph
```

- **Session Memory** — current conversation, in-process
- **Short-Term Memory** — last 24h, SQLite
- **Long-Term Memory** — permanent, SQLite + vector search
- **Knowledge Graph** — structured facts, extracted from your prompts

---

## CLI

```bash
# Add facts
stackme add-fact "I run a fintech startup"
stackme add "I'm building a B2B SaaS"   # also auto-extracts facts

# Retrieve context
stackme get "what pricing?"

# Search all memories
stackme search "fintech"

# List all facts
stackme facts

# Knowledge graph
stackme graph

# Session history
stackme history --last 10

# Export all data
stackme export

# Stats
stackme count
```

---

## API Reference

### `Context`

Main class. All data stored locally in `~/.stackme/`.

```python
ctx = Context(user_id="default")  # multi-user support
```

### Adding Memories

```python
ctx.add_fact("I run a fintech startup")       # structured fact
ctx.add_prompt("User asked about pricing")    # user prompt
ctx.add_context("AI responded with...")      # AI response
ctx.add_user_message("I'm building a B2B SaaS")  # both + auto-extract
ctx.add_ai_message("Here's my recommendation...")
```

### Retrieving

```python
ctx.get_relevant("pricing strategy?", top_k=5)  # → formatted string
ctx.search("fintech", top_k=10)                  # → list of strings
ctx.get_facts()                                   # → all facts
ctx.get_graph(subject="User")                     # → GraphFact list
```

### Session

```python
ctx.get_session_history(last_n=20)  # in-memory conversation
ctx.clear_session()                # wipe session only
```

### Utilities

```python
ctx.export()      # full JSON backup
ctx.count()       # total items
ctx.clear_all()   # ⚠️ wipe everything
```

---

## Privacy

Everything stays on your machine. Your memories are yours. We never see, store, or transmit your data. No account required.

---

## License

Apache 2.0 — free for commercial and personal use.

---

Built by [Stack AI](https://stack-ai.me) · [GitHub](https://github.com/my-ai-stack/stackme) · [HuggingFace](https://huggingface.co/my-ai-stack/stackme)
