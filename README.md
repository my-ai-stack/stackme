---
title: Stackme
emoji: 🧠
colorFrom: purple
colorTo: blue
sdk: gradio
sdk_version: 6.13.0
app_file: app.py
pinned: false
description: The context layer for every AI. Your memory brain, stored locally. 100% free, 100% local, works with ChatGPT, Claude, Copilot and any AI.
tags:
- memory
- context
- llm
- agentic
- rag
- tool-calling
- local-ai
- open-source
license: apache-2.0
---

# 🧠 Stackme

**The context layer for every AI.**

Stackme is a free, open-source memory layer for AI. It stores what matters about you, retrieves relevant context before every query, and injects it into any AI — ChatGPT, Claude, Copilot, Gemini, Ollama, anyone.

**No server. No subscription. No data leaves your machine.**

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

# Your AI gets the full picture every time.
```

## How It Works

```
You: "What pricing should we use?"

Stackme retrieves:
  - I run a fintech B2B SaaS
  - Q3 goal: 10K paying customers
  - Users: 25-40, $50-100K income

Enriched prompt → ChatGPT / Claude / any AI
```

## Architecture

```
~/.stackme/
├── memory.sqlite     ← all memories
├── vectors.faiss     ← semantic index
└── facts.graph       ← structured knowledge graph
```

## Chrome Extension

The Stackme Chrome Extension intercepts your prompts on ChatGPT, Claude, and Copilot — injects your context automatically.

## Privacy

Everything stays on your machine. Your memories are yours. We never see, store, or transmit your data.

## License

Apache 2.0 — free for commercial and personal use.

---

Built by [Stack AI](https://stack-ai.me) · [GitHub](https://github.com/my-ai-stack/stackme)
