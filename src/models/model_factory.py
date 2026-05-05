from ..config.config_loader import ConfigLoader
from .llm_client import LLMClient
from .embedding_client import EmbeddingClient


class ModelFactory:
    """Single entry point for creating LLM and Embedding clients."""

    def __init__(self, config_loader: ConfigLoader | None = None):
        self._config = config_loader or ConfigLoader()

    def create_llm(self) -> LLMClient:
        cfg = self._config.get("models", "text_model")
        return LLMClient(cfg)

    def create_embedding(self) -> EmbeddingClient:
        cfg = self._config.get("models", "embedding_model")
        return EmbeddingClient(cfg)
