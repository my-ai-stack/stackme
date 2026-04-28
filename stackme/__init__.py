"""
Stackme — The context layer for every AI.
Your memory brain, stored locally, works with any AI.
"""

__version__ = "0.1.0"
__author__ = "Stack AI"
__license__ = "Apache 2.0"

from .context import Context
from .embeddings import (
    EmbeddingProvider,
    SimpleEmbeddingProvider,
    SentenceTransformerEmbeddingProvider,
    OpenAIEmbeddingProvider,
    create_embedding_provider,
    get_default_provider,
)

# LangChain integration
from .integrations.langchain import (
    StackmeMemory,
    StackmeMessageHistory,
    StackmeRetrieverMemory,
    get_session_history,
    create_stackme_memory,
)

# Server
from .server import run_server

__all__ = [
    "Context",
    # Embedding providers
    "EmbeddingProvider",
    "SimpleEmbeddingProvider",
    "SentenceTransformerEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "create_embedding_provider",
    "get_default_provider",
    # LangChain integration
    "StackmeMemory",
    "StackmeMessageHistory",
    "StackmeRetrieverMemory",
    "get_session_history",
    "create_stackme_memory",
    # Server
    "run_server",
]
