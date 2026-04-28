"""
Embedding providers for stackme.

Supports multiple backends:
- simple: Hash-based pseudo-embeddings (fallback, no dependencies)
- sentence-transformers: all-MiniLM-L6-v2 (default, requires sentence-transformers)
- openai: text-embedding-3-small (requires openai package + API key)
"""

import os
import hashlib
from abc import ABC, abstractmethod
from typing import Optional

# Type alias for embedding vectors
EmbeddingVector = list[float]


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the provider."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimensionality of the embedding vectors."""
        pass

    @abstractmethod
    def encode(self, text: str) -> EmbeddingVector:
        """Encode a single text into an embedding vector."""
        pass

    def encode_batch(self, texts: list[str]) -> list[EmbeddingVector]:
        """Encode a batch of texts. Default implementation calls encode() for each."""
        return [self.encode(text) for text in texts]

    def is_available(self) -> bool:
        """Check if the provider is available (dependencies installed, etc.)."""
        return True


class SimpleEmbeddingProvider(EmbeddingProvider):
    """
    Simple hash-based embeddings for demos.

    Uses SHA-256 hash of text to generate deterministic pseudo-random vectors.
    Not suitable for real semantic search, but works without external dependencies.
    """

    def __init__(self, dimension: int = 128):
        self._dimension = dimension

    @property
    def name(self) -> str:
        return "simple"

    @property
    def dimension(self) -> int:
        return self._dimension

    def encode(self, text: str) -> EmbeddingVector:
        """Generate deterministic embedding from text hash."""
        h = hashlib.sha256(text.encode()).digest()
        vec = []
        for i in range(self._dimension):
            byte_val = h[i % len(h)]
            vec.append((byte_val / 255.0) * 2.0 - 1.0)
        # Normalize the vector
        norm = sum(v * v for v in vec) ** 0.5
        return [v / (norm + 1e-8) for v in vec]


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """
    Sentence-transformers provider using all-MiniLM-L6-v2.

    Requires: pip install sentence-transformers
    Produces 384-dimensional embeddings.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model_name = model_name
        self._model = None
        self._load_model()

    def _load_model(self):
        """Lazy load the sentence-transformers model."""
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
        except ImportError:
            raise ImportError(
                "sentence-transformers is not installed. "
                "Install it with: pip install sentence-transformers"
            )

    @property
    def name(self) -> str:
        return f"sentence-transformers:{self._model_name}"

    @property
    def dimension(self) -> int:
        return 384  # all-MiniLM-L6-v2 produces 384-dimensional vectors

    def is_available(self) -> bool:
        return self._model is not None

    def encode(self, text: str) -> EmbeddingVector:
        if self._model is None:
            raise RuntimeError("SentenceTransformer model not loaded")
        # Encode returns a 2D array, we need the first row
        result = self._model.encode(text, convert_to_numpy=True)
        return result.tolist()

    def encode_batch(self, texts: list[str]) -> list[EmbeddingVector]:
        if self._model is None:
            raise RuntimeError("SentenceTransformer model not loaded")
        results = self._model.encode(texts, convert_to_numpy=True)
        return [row.tolist() for row in results]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI text-embedding-3-small provider.

    Requires: pip install openai
    Environment variables:
        OPENAI_API_KEY: Your OpenAI API key

    Produces 1536-dimensional embeddings.
    """

    def __init__(self, model: str = "text-embedding-3-small", api_key: Optional[str] = None):
        self._model = model
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._client = None
        if self._api_key:
            self._load_client()

    def _load_client(self):
        """Lazy load the OpenAI client."""
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key)
        except ImportError:
            raise ImportError(
                "openai is not installed. "
                "Install it with: pip install openai"
            )

    @property
    def name(self) -> str:
        return f"openai:{self._model}"

    @property
    def dimension(self) -> int:
        return 1536  # text-embedding-3-small produces 1536-dimensional vectors

    def is_available(self) -> bool:
        return self._client is not None

    def encode(self, text: str) -> EmbeddingVector:
        if self._client is None:
            raise RuntimeError(
                "OpenAI client not initialized. "
                "Set OPENAI_API_KEY environment variable or pass api_key to constructor."
            )
        response = self._client.embeddings.create(
            model=self._model,
            input=text
        )
        return response.data[0].embedding


def create_embedding_provider(
    provider: str = "sentence-transformers",
    **kwargs
) -> EmbeddingProvider:
    """
    Factory function to create an embedding provider.

    Args:
        provider: Provider name - "simple", "sentence-transformers", or "openai"
        **kwargs: Additional arguments passed to the provider constructor

    Returns:
        An EmbeddingProvider instance

    Raises:
        ValueError: If provider name is unknown
        ImportError: If provider dependencies are not installed
    """
    provider = provider.lower().strip()

    if provider == "simple":
        dimension = kwargs.get("dimension", 128)
        return SimpleEmbeddingProvider(dimension=dimension)

    elif provider == "sentence-transformers":
        model_name = kwargs.get("model_name", "all-MiniLM-L6-v2")
        try:
            return SentenceTransformerEmbeddingProvider(model_name=model_name)
        except ImportError as e:
            # Re-raise with more helpful message
            raise ImportError(
                f"{e.message} "
                "For sentence-transformers support, run: pip install sentence-transformers"
            )

    elif provider == "openai":
        api_key = kwargs.get("api_key")
        model = kwargs.get("model", "text-embedding-3-small")
        try:
            return OpenAIEmbeddingProvider(model=model, api_key=api_key)
        except ImportError as e:
            raise ImportError(
                f"{e.message} "
                "For OpenAI embeddings, run: pip install openai"
            )

    else:
        raise ValueError(
            f"Unknown embedding provider: {provider}. "
            "Valid options: 'simple', 'sentence-transformers', 'openai'"
        )


def get_default_provider() -> EmbeddingProvider:
    """
    Get the default embedding provider.

    Tries sentence-transformers first, falls back to simple if not available.
    """
    try:
        return SentenceTransformerEmbeddingProvider()
    except ImportError:
        return SimpleEmbeddingProvider()