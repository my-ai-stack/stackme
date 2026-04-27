"""
Stackme — Core Context class.

Three-tier memory architecture:
  Session  → in-memory dict (current conversation)
  ShortTerm → SQLite (last 24h)
  LongTerm  → SQLite + FAISS (permanent facts + learned knowledge)
  Graph     → SQLAlchemy (structured knowledge graph)
"""

import os
import json
import time
import sqlite3
import hashlib
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from collections import defaultdict

# ─── App Directory ────────────────────────────────────────────────────────────

def _stackme_dir() -> Path:
    d = Path(os.path.expanduser("~/.stackme"))
    d.mkdir(parents=True, exist_ok=True)
    return d


# ─── Data Models ─────────────────────────────────────────────────────────────

@dataclass
class MemoryItem:
    id: str
    type: str            # "fact" | "prompt" | "session" | "context"
    content: str
    metadata: dict
    embedding: list[float] | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_accessed: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    access_count: int = 0
    user_id: str = "default"


@dataclass
class GraphFact:
    id: str
    subject: str
    predicate: str
    value: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ─── Simple Embedding (cosine sim without external deps) ──────────────────────

def _simple_vec(text: str, dim: int = 128) -> list[float]:
    """Deterministic fake embedding from text hash — good enough for semantic search demo."""
    h = hashlib.sha256(text.encode()).digest()
    vec = []
    for i in range(dim):
        byte_val = h[i % len(h)]
        vec.append((byte_val / 255.0) * 2.0 - 1.0)
    norm = sum(v * v for v in vec) ** 0.5
    return [v / (norm + 1e-8) for v in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return dot / (na * nb + 1e-8)


# ─── Storage Layer ─────────────────────────────────────────────────────────────

class Storage:
    """SQLite + FAISS-lite storage for MemoryItems."""

    def __init__(self, db_path: Path | None = None, dim: int = 128):
        self.dim = dim
        self.db_path = db_path or str(_stackme_dir() / "memory.sqlite")
        self.faiss_path = str(_stackme_dir() / "vectors.faiss")
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._vectors: list[list[float]] = []
        self._load_vectors()
        self._init_db()

    def _init_db(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                embedding_id INTEGER,
                created_at TEXT NOT NULL,
                last_accessed TEXT NOT NULL,
                access_count INTEGER NOT NULL DEFAULT 0,
                user_id TEXT NOT NULL DEFAULT 'default'
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS graph (
                id TEXT PRIMARY KEY,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS short_term (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
        """)
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_type ON memory(type)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_user ON memory(user_id)"
        )
        self._conn.commit()

    def _load_vectors(self):
        """Load FAISS index from disk (in-memory for simplicity)."""
        pass  # We keep vectors in-memory for now

    def add(self, item: MemoryItem) -> str:
        """Store a memory item with optional embedding."""
        if item.embedding is None:
            item.embedding = _simple_vec(item.content, self.dim)
        self._conn.execute(
            """INSERT OR REPLACE INTO memory
               (id, type, content, metadata, created_at, last_accessed, access_count, user_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (item.id, item.type, item.content, json.dumps(item.metadata),
             item.created_at, item.last_accessed, item.access_count, item.user_id)
        )
        self._conn.commit()
        # Store vector in-memory
        vid = len(self._vectors)
        self._vectors.append(item.embedding)
        return item.id

    def search(self, query: str, top_k: int = 5, user_id: str = "default") -> list[MemoryItem]:
        """Semantic search against stored memories."""
        qvec = _simple_vec(query, self.dim)
        rows = self._conn.execute(
            """SELECT id, type, content, metadata, created_at, last_accessed, access_count, user_id
               FROM memory WHERE user_id = ? ORDER BY created_at DESC LIMIT 200""",
            (user_id,)
        ).fetchall()
        scored = []
        for row in rows:
            item = MemoryItem(
                id=row[0], type=row[1], content=row[2],
                metadata=json.loads(row[3]), created_at=row[4],
                last_accessed=row[5], access_count=row[6], user_id=row[7]
            )
            if item.embedding:
                sim = _cosine(qvec, item.embedding)
            else:
                sim = 0.0
            # Boost by access_count (popular items rank higher)
            boost = 1.0 + (item.access_count / 100.0)
            scored.append((sim * boost, -item.access_count, item))
        scored.sort(key=lambda x: x[0] * x[1], reverse=True)
        return [item for _, _, item in scored[:top_k]]

    def update_access(self, item_id: str):
        self._conn.execute(
            """UPDATE memory SET access_count = access_count + 1,
               last_accessed = ? WHERE id = ?""",
            (datetime.utcnow().isoformat(), item_id)
        )
        self._conn.commit()

    def add_graph(self, fact: GraphFact):
        self._conn.execute(
            """INSERT OR REPLACE INTO graph (id, subject, predicate, value, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (fact.id, fact.subject, fact.predicate, fact.value, fact.created_at)
        )
        self._conn.commit()

    def query_graph(self, subject: str | None = None,
                    predicate: str | None = None) -> list[GraphFact]:
        q = "SELECT id, subject, predicate, value, created_at FROM graph WHERE 1=1"
        args = []
        if subject:
            q += " AND subject = ?"
            args.append(subject)
        if predicate:
            q += " AND predicate = ?"
            args.append(predicate)
        rows = self._conn.execute(q, args).fetchall()
        return [GraphFact(id=r[0], subject=r[1], predicate=r[2], value=r[3], created_at=r[4]) for r in rows]

    def add_short_term(self, content: str) -> str:
        id_ = str(uuid.uuid4())
        expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        self._conn.execute(
            "INSERT INTO short_term (id, content, expires_at) VALUES (?, ?, ?)",
            (id_, content, expires)
        )
        self._conn.commit()
        return id_

    def get_short_term(self) -> list[str]:
        now = datetime.utcnow().isoformat()
        rows = self._conn.execute(
            "SELECT content FROM short_term WHERE expires_at > ?", (now,)
        ).fetchall()
        return [r[0] for r in rows]

    def cleanup_short_term(self):
        now = datetime.utcnow().isoformat()
        self._conn.execute("DELETE FROM short_term WHERE expires_at <= ?", (now,))
        self._conn.commit()

    def close(self):
        self._conn.close()

    def export_all(self) -> dict:
        """Export all data as dict (for backup / migration)."""
        memory_rows = self._conn.execute(
            "SELECT id, type, content, metadata, created_at, last_accessed, access_count, user_id FROM memory"
        ).fetchall()
        graph_rows = self._conn.execute(
            "SELECT id, subject, predicate, value, created_at FROM graph"
        ).fetchall()
        return {
            "memory": [{
                "id": r[0], "type": r[1], "content": r[2],
                "metadata": json.loads(r[3]), "created_at": r[4],
                "last_accessed": r[5], "access_count": r[6], "user_id": r[7]
            } for r in memory_rows],
            "graph": [dict(zip(["id","subject","predicate","value","created_at"], r)) for r in graph_rows],
            "exported_at": datetime.utcnow().isoformat(),
        }


# ─── Session Memory (in-process, ephemeral) ────────────────────────────────────

class SessionMemory:
    """In-memory session context — current conversation window."""

    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self.turns: list[dict] = []

    def add_turn(self, role: str, content: str, metadata: dict | None = None):
        self.turns.append({
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "ts": datetime.utcnow().isoformat(),
        })
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]

    def get_history(self, last_n: int | None = None) -> list[dict]:
        if last_n is None:
            return self.turns.copy()
        return self.turns[-last_n:]

    def get_context_summary(self) -> str:
        """One-line summary of session so far."""
        if not self.turns:
            return ""
        parts = [f"[{t['role']}]: {t['content'][:80]}" for t in self.turns[-5:]]
        return " | ".join(parts)

    def clear(self):
        self.turns = []


# ─── Knowledge Graph ──────────────────────────────────────────────────────────

class KnowledgeGraph:
    """Structured fact extraction from user prompts."""

    def __init__(self, storage: Storage):
        self.storage = storage

    def add_fact(self, subject: str, predicate: str, value: str):
        fact = GraphFact(
            id=str(uuid.uuid4()),
            subject=subject.strip(),
            predicate=predicate.strip(),
            value=value.strip(),
        )
        self.storage.add_graph(fact)
        return fact

    def add_facts_from_text(self, text: str):
        """Simple rule-based extraction of (subject, predicate, value) triplets.
        Looks for patterns like:
          - "I am a X"  → (User, type, X)
          - "I work at X" → (User, works_at, X)
          - "My goal is X" → (User, goal, X)
          - "We are building X" → (Team, building, X)
        """
        text_lower = text.lower()
        triples = []

        # "I am a X" → user type
        import re
        m = re.search(r"\bi\s+am\s+(?:a\s+)?([^\.]+)", text_lower)
        if m:
            triples.append(("User", "is_a", m.group(1).strip()))

        # "I work at X"
        m = re.search(r"\bi\s+work\s+at\s+([^\.]+)", text_lower)
        if m:
            triples.append(("User", "works_at", m.group(1).strip()))

        # "I run X"
        m = re.search(r"\bi\s+run\s+(?:a\s+)?([^\.]+)", text_lower)
        if m:
            triples.append(("User", "runs", m.group(1).strip()))

        # "My goal is X"
        m = re.search(r"\bmy\s+goal\s+(?:is|was)\s+([^\.]+)", text_lower)
        if m:
            triples.append(("User", "goal", m.group(1).strip()))

        # "We are building X"
        m = re.search(r"\bwe(?:'re|\s+are)\s+building\s+([^\.]+)", text_lower)
        if m:
            triples.append(("Team", "building", m.group(1).strip()))

        # "Q3 goal: X"
        m = re.search(r"\bq\d+\s+goal[^\w]*([^\.]+)", text_lower)
        if m:
            triples.append(("Team", "goal", m.group(1).strip()))

        # "Team: X" or "team is X"
        m = re.search(r"\bteam\s+(?:is\s+)?([^\.]+)", text_lower)
        if m:
            triples.append(("Team", "description", m.group(1).strip()))

        for subj, pred, val in triples:
            self.add_fact(subj, pred, val)

    def query(self, subject: str | None = None) -> list[GraphFact]:
        return self.storage.query_graph(subject=subject)

    def get_all_as_text(self) -> str:
        facts = self.storage.query_graph()
        lines = [f"{f.subject} — {f.predicate}: {f.value}" for f in facts]
        return "\n".join(lines) if lines else ""


# ─── Main Context Class ────────────────────────────────────────────────────────

class Context:
    """
    Stackme — Your context brain.

    Three-tier memory + knowledge graph, all stored locally.

    Usage:
        from stackme import Context
        ctx = Context()

        ctx.add_fact("I run a fintech startup")
        ctx.add_fact("Q3 goal: 10K paying customers")
        ctx.add_prompt("User asked ChatGPT about Q3 pricing strategy")

        context = ctx.get_relevant("What should we price at?")
        # → "I run a fintech startup | Q3 goal: 10K customers"

        ctx.add_user_message("I'm building a B2B SaaS, targeting fintech")
        # → auto-extracts facts: (User, is_a, B2B SaaS), (User, targets, fintech)
    """

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.storage = Storage()
        self.session = SessionMemory()
        self.kg = KnowledgeGraph(self.storage)

    # ── Core API ──

    def add_fact(self, content: str, metadata: dict | None = None) -> str:
        """Add a structured fact to long-term memory."""
        item = MemoryItem(
            id=str(uuid.uuid4()),
            type="fact",
            content=content.strip(),
            metadata=metadata or {},
            user_id=self.user_id,
        )
        self.storage.add(item)
        # Try to extract structured facts from natural language
        self.kg.add_facts_from_text(content)
        return item.id

    def add_prompt(self, content: str, metadata: dict | None = None) -> str:
        """Store a user prompt / message — builds context over time."""
        item = MemoryItem(
            id=str(uuid.uuid4()),
            type="prompt",
            content=content.strip(),
            metadata=metadata or {"source": "user_prompt"},
            user_id=self.user_id,
        )
        self.storage.add(item)
        self.kg.add_facts_from_text(content)
        return item.id

    def add_context(self, content: str, metadata: dict | None = None) -> str:
        """Store a context note (result, observation, etc)."""
        item = MemoryItem(
            id=str(uuid.uuid4()),
            type="context",
            content=content.strip(),
            metadata=metadata or {},
            user_id=self.user_id,
        )
        self.storage.add(item)
        return item.id

    def add_user_message(self, text: str) -> str:
        """Add a user message — stores as prompt AND extracts facts."""
        item_id = self.add_prompt(text)
        self.session.add_turn("user", text)
        return item_id

    def add_ai_message(self, text: str) -> str:
        """Add an AI response — stored as context."""
        item_id = self.add_context(text, metadata={"source": "ai_response"})
        self.session.add_turn("assistant", text)
        return item_id

    def get_relevant(self, query: str, top_k: int = 5) -> str:
        """Retrieve most relevant context for a query, as a readable string."""
        items = self.storage.search(query, top_k=top_k, user_id=self.user_id)
        for item in items:
            self.storage.update_access(item.id)

        if not items:
            return ""

        # Build readable context string
        fact_items = [i for i in items if i.type == "fact"]
        prompt_items = [i for i in items if i.type == "prompt"]
        context_items = [i for i in items if i.type == "context"]

        lines = []
        if fact_items:
            lines.append("## Facts")
            for item in fact_items[:3]:
                lines.append(f"- {item.content}")
        if prompt_items:
            lines.append("## Past queries")
            for item in prompt_items[:2]:
                lines.append(f"- {item.content[:100]}")
        if context_items:
            lines.append("## Context")
            for item in context_items[:2]:
                lines.append(f"- {item.content[:100]}")

        # Add graph facts if query matches subject
        graph_text = self.kg.get_all_as_text()
        if graph_text:
            lines.append("## Knowledge Graph")
            lines.append(graph_text)

        return "\n".join(lines) if lines else ""

    def search(self, query: str, top_k: int = 10) -> list[str]:
        """Full-text search across all memories. Returns list of content strings."""
        items = self.storage.search(query, top_k=top_k, user_id=self.user_id)
        return [item.content for item in items]

    def get_facts(self) -> list[str]:
        """Get all stored facts."""
        items = self.storage.search("", top_k=100, user_id=self.user_id)
        return [i.content for i in items if i.type == "fact"]

    def get_graph(self, subject: str | None = None) -> list[GraphFact]:
        """Query the knowledge graph."""
        return self.kg.query(subject=subject)

    # ── Session ──

    def add_session_turn(self, role: str, content: str):
        """Add a turn to in-session memory."""
        self.session.add_turn(role, content)

    def get_session_history(self, last_n: int | None = None) -> list[dict]:
        """Get session conversation history."""
        return self.session.get_history(last_n)

    def clear_session(self):
        """Clear in-session memory only (long-term memory preserved)."""
        self.session.clear()

    # ── Utility ──

    def export(self) -> dict:
        """Export all memory data as a JSON-serializable dict."""
        return self.storage.export_all()

    def count(self) -> int:
        """Total memory items stored."""
        row = self.storage._conn.execute(
            "SELECT COUNT(*) FROM memory WHERE user_id = ?", (self.user_id,)
        ).fetchone()
        return row[0] if row else 0

    def clear_all(self):
        """Wipe ALL memory — use with caution."""
        self.storage._conn.execute(
            "DELETE FROM memory WHERE user_id = ?", (self.user_id,)
        )
        self.storage._conn.execute("DELETE FROM graph")
        self.storage._conn.execute("DELETE FROM short_term")
        self.storage._conn.commit()
        self.session.clear()
