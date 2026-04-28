"""
Stackme REST API Server.

A FastAPI-based REST server that exposes stackme memory functionality
as HTTP endpoints, allowing any application to use stackme as a service.

Usage:
    stackme server --port 8000

Or run directly:
    python -m stackme.server --port 8000
"""

import argparse
import uuid
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import Context


# ─── Pydantic Models ────────────────────────────────────────────────────────────

class FactRequest(BaseModel):
    """Request model for adding a fact."""
    content: str = Field(..., description="The fact content to store")
    metadata: Optional[dict] = Field(default=None, description="Optional metadata")
    user_id: str = Field(default="default", description="User identifier")


class MessageRequest(BaseModel):
    """Request model for adding a user message."""
    content: str = Field(..., description="The message content")
    user_id: str = Field(default="default", description="User identifier")


class ContextRequest(BaseModel):
    """Request model for adding context."""
    content: str = Field(..., description="The context content")
    metadata: Optional[dict] = Field(default=None, description="Optional metadata")
    user_id: str = Field(default="default", description="User identifier")


class SessionTurnRequest(BaseModel):
    """Request model for adding a session turn."""
    role: str = Field(..., description="Role (user or assistant)")
    content: str = Field(..., description="Message content")
    user_id: str = Field(default="default", description="User identifier")


class SearchRequest(BaseModel):
    """Request model for searching memories."""
    query: str = Field(..., description="Search query")
    top_k: int = Field(default=5, description="Number of results")
    user_id: str = Field(default="default", description="User identifier")


# ─── Context Storage (per user) ────────────────────────────────────────────────

# Global storage for Context instances per user
_user_contexts: dict[str, Context] = {}


def get_context(user_id: str = "default") -> Context:
    """Get or create a Context instance for a user."""
    if user_id not in _user_contexts:
        _user_contexts[user_id] = Context(user_id=user_id)
    return _user_contexts[user_id]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup: nothing to do
    yield
    # Shutdown: clean up contexts
    _user_contexts.clear()


# ─── FastAPI App ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Stackme API",
    description="REST API for stackme memory layer. Add, search, and manage AI context memories.",
    version="0.1.0",
    lifespan=lifespan,
)


# ─── Health Endpoint ────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "stackme"}


# ─── Memory Endpoints ───────────────────────────────────────────────────────────

@app.post("/memory/facts")
async def add_fact(request: FactRequest):
    """
    Add a fact to long-term memory.

    Example:
        curl -X POST http://localhost:8000/memory/facts \\
             -H "Content-Type: application/json" \\
             -d '{"content": "I run a fintech startup", "user_id": "alice"}'
    """
    ctx = get_context(request.user_id)
    metadata = request.metadata or {}
    fact_id = ctx.add_fact(request.content, metadata=metadata)
    return {"id": fact_id, "status": "added", "content": request.content}


@app.post("/memory/messages")
async def add_message(request: MessageRequest):
    """
    Add a user message (auto-extracts facts).

    Example:
        curl -X POST http://localhost:8000/memory/messages \\
             -H "Content-Type: application/json" \\
             -d '{"content": "I'm building a B2B SaaS for fintech", "user_id": "alice"}'
    """
    ctx = get_context(request.user_id)
    message_id = ctx.add_user_message(request.content)
    return {"id": message_id, "status": "added", "content": request.content}


@app.post("/memory/context")
async def add_context(request: ContextRequest):
    """
    Add context (result, observation, etc).

    Example:
        curl -X POST http://localhost:8000/memory/context \\
             -H "Content-Type: application/json" \\
             -d '{"content": "User asked about pricing strategy", "user_id": "alice"}'
    """
    ctx = get_context(request.user_id)
    metadata = request.metadata or {}
    context_id = ctx.add_context(request.content, metadata=metadata)
    return {"id": context_id, "status": "added", "content": request.content}


@app.get("/memory/search")
async def search_memories(
    q: str = Query(..., description="Search query"),
    top_k: int = Query(5, ge=1, le=100, description="Number of results"),
    user_id: str = Query("default", description="User identifier"),
):
    """
    Search memories semantically.

    Example:
        curl "http://localhost:8000/memory/search?q=fintech&top_k=5&user_id=alice"
    """
    ctx = get_context(user_id)
    results = ctx.search(q, top_k=top_k)
    return {
        "query": q,
        "top_k": top_k,
        "results": results,
        "count": len(results),
    }


@app.get("/memory/facts")
async def get_facts(user_id: str = Query("default", description="User identifier")):
    """
    Get all stored facts.

    Example:
        curl "http://localhost:8000/memory/facts?user_id=alice"
    """
    ctx = get_context(user_id)
    facts = ctx.get_facts()
    return {"facts": facts, "count": len(facts)}


@app.get("/memory/graph")
async def get_graph(
    subject: Optional[str] = Query(None, description="Filter by subject"),
    user_id: str = Query("default", description="User identifier"),
):
    """
    Get knowledge graph facts.

    Example:
        curl "http://localhost:8000/memory/graph?user_id=alice"
        curl "http://localhost:8000/memory/graph?subject=User&user_id=alice"
    """
    ctx = get_context(user_id)
    facts = ctx.get_graph(subject=subject)
    return {
        "facts": [
            {
                "id": f.id,
                "subject": f.subject,
                "predicate": f.predicate,
                "value": f.value,
                "created_at": f.created_at,
            }
            for f in facts
        ],
        "count": len(facts),
    }


# ─── Session Endpoints ──────────────────────────────────────────────────────────

@app.get("/session/history")
async def get_session_history(
    last_n: Optional[int] = Query(None, ge=1, description="Get last N turns"),
    user_id: str = Query("default", description="User identifier"),
):
    """
    Get session conversation history.

    Example:
        curl "http://localhost:8000/session/history?user_id=alice"
        curl "http://localhost:8000/session/history?last_n=5&user_id=alice"
    """
    ctx = get_context(user_id)
    history = ctx.get_session_history(last_n=last_n)
    return {"history": history, "count": len(history)}


@app.post("/session/turn")
async def add_session_turn(request: SessionTurnRequest):
    """
    Add a turn to session history.

    Example:
        curl -X POST http://localhost:8000/session/turn \\
             -H "Content-Type: application/json" \\
             -d '{"role": "user", "content": "Hello", "user_id": "alice"}'
    """
    ctx = get_context(request.user_id)
    if request.role not in ("user", "assistant"):
        raise HTTPException(status_code=400, detail="role must be 'user' or 'assistant'")
    ctx.add_session_turn(request.role, request.content)
    return {"status": "added", "role": request.role, "content": request.content}


@app.delete("/session")
async def clear_session(user_id: str = Query("default", description="User identifier")):
    """
    Clear session memory (long-term memory preserved).

    Example:
        curl -X DELETE "http://localhost:8000/session?user_id=alice"
    """
    ctx = get_context(user_id)
    ctx.clear_session()
    return {"status": "cleared", "user_id": user_id}


# ─── Utility Endpoints ─────────────────────────────────────────────────────────

@app.get("/export")
async def export_data(user_id: str = Query("default", description="User identifier")):
    """
    Export all memory data as JSON.

    Example:
        curl "http://localhost:8000/export?user_id=alice"
    """
    ctx = get_context(user_id)
    data = ctx.export()
    return data


@app.get("/count")
async def get_count(user_id: str = Query("default", description="User identifier")):
    """
    Get total memory count.

    Example:
        curl "http://localhost:8000/count?user_id=alice"
    """
    ctx = get_context(user_id)
    count = ctx.count()
    return {"count": count, "user_id": user_id}


@app.delete("/all")
async def clear_all(user_id: str = Query("default", description="User identifier")):
    """
    Clear ALL memory (irreversible).

    Example:
        curl -X DELETE "http://localhost:8000/all?user_id=alice"
    """
    ctx = get_context(user_id)
    ctx.clear_all()
    return {"status": "cleared_all", "user_id": user_id}


# ─── Main Entry Point ──────────────────────────────────────────────────────────

def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Run the FastAPI server."""
    import uvicorn
    uvicorn.run(
        "stackme.server:app",
        host=host,
        port=port,
        reload=reload,
    )


def main():
    """CLI entry point for the server."""
    parser = argparse.ArgumentParser(
        prog="stackme server",
        description="Start the Stackme REST API server",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload (for development)",
    )
    args = parser.parse_args()

    print(f"Starting Stackme server on http://{args.host}:{args.port}")
    print("API docs available at http://{args.host}:{args.port}/docs")
    run_server(host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()