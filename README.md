# Stackme

**Your context brain for every AI.**

Stackme is a free, open-source memory layer for AI. It stores what matters about you, retrieves relevant context before every query, and injects it into any AI — ChatGPT, Claude, Copilot, Gemini, Ollama, anyone.

No server. No subscription. No data leaves your machine.

---

## Install

```bash
pip install stackme
```

## Quick Start

```python
from stackme import Context

ctx = Context()

# Add facts about yourself
ctx.add_fact("I run a fintech B2B SaaS, launched March 2024")
ctx.add_fact("Q3 goal: 10K paying customers")
ctx.add_fact("Users are 25-40, income $50-100K")

# Ask any AI — Stackme retrieves your context first
context = ctx.get_relevant("What pricing should we use?")
# → "I run a fintech B2B SaaS... | Q3 goal: 10K customers..."

# Your AI gets the full picture every time.
```

## How It Works

```
You: "What pricing should we use?"

Stackme retrieves:
  - I run a fintech B2B SaaS
  - Q3 goal: 10K paying customers
  - Users: 25-40, $50-100K income

Enriched prompt sent to ChatGPT:
  "Context: I run a fintech B2B SaaS...
   Q3 goal: 10K customers...
   User: What pricing should we use?"

ChatGPT responds with full context awareness.
```

## Architecture

```
~/.stackme/
├── memory.sqlite     ← all memories, encrypted
├── vectors.faiss      ← semantic index
└── facts.graph       ← structured knowledge graph
```

- **Session Memory** — current conversation, in-process
- **Short-Term Memory** — last 24h, SQLite
- **Long-Term Memory** — permanent, SQLite + vector search
- **Knowledge Graph** — structured facts, extracted from your prompts

## Chrome Extension

The Stackme Chrome Extension intercepts your prompts on ChatGPT, Claude, and Copilot — injects your context automatically.

Install: [Chrome Web Store] (coming soon)

## Why Stackme?

| | Without Stackme | With Stackme |
|---|---|---|
| First query | AI knows nothing about you | AI knows your full context |
| Repeat queries | Start from zero every time | Context compounds automatically |
| Team context | Siloed in each conversation | Shared memory across team |
| Your data | Lost after the session | Stored permanently, locally |

## Supported AI Platforms

- ChatGPT (chat.openai.com)
- Claude (claude.ai)
- Copilot (copilot.microsoft.com)
- Gemini (gemini.google.com)
- Ollama (local)
- Any AI via API

## Privacy

Everything stays on your machine. Your memories are yours. We never see, store, or transmit your data. No account required.

## License

Apache 2.0 — free for commercial and personal use.

---

Built by [Stack AI](https://stack-ai.me) · [GitHub](https://github.com/my-ai-stack/stackme) · [HuggingFace](https://huggingface.co/my-ai-stack/stackme)
