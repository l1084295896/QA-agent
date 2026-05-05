# 模型工厂模块 —— 统一的 LLM / Embedding 客户端创建入口。
from ..config.config_loader import ConfigLoader
from .llm_client import LLMClient
from .embedding_client import EmbeddingClient


class ModelFactory:
    """Single entry point for creating LLM and Embedding clients."""

    def __init__(self, config_loader: ConfigLoader | None = None):
        """初始化模型工厂。

        Args:
            config_loader: 可选的配置加载器，不传则自动创建默认实例。
        """
        self._config = config_loader or ConfigLoader()

    def create_llm(self) -> LLMClient:
        """创建大语言模型客户端。

        从 models.yml 的 text_model 配置段读取参数并初始化 LLMClient。

        Returns:
            配置好的 LLMClient 实例。
        """
        cfg = self._config.get("models", "text_model")
        return LLMClient(cfg)

    def create_embedding(self) -> EmbeddingClient:
        """创建嵌入模型客户端。

        从 models.yml 的 embedding_model 配置段读取参数并初始化 EmbeddingClient。

        Returns:
            配置好的 EmbeddingClient 实例。
        """
        cfg = self._config.get("models", "embedding_model")
        return EmbeddingClient(cfg)
