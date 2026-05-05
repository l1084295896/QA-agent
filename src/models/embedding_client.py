# 嵌入模型客户端模块 —— 封装 Qwen Embedding 模型，通过 OpenAI 兼容接口调用。
from langchain_openai import OpenAIEmbeddings


class EmbeddingClient:
    """Wraps Qwen embedding model via OpenAI-compatible OpenAIEmbeddings."""

    def __init__(self, config: dict):
        """初始化嵌入模型客户端。

        Qwen Embedding API 兼容 OpenAI Embeddings 协议，可通过 langchain 的
        OpenAIEmbeddings 直接调用。base_url 默认为阿里云 DashScope 兼容接口。

        check_embedding_ctx_length 设为 False 的原因：
        langchain 默认会在调用 embedding 前检查 token 数是否超过模型上下文长度，
        但 Qwen 嵌入模型实际支持的文本长度大于 langchain 内部预置的限制值，
        开启检查会导致正常文本被错误拒绝，因此显式禁用。

        Args:
            config: 包含 model_name, api_key, base_url(可选), dimension(可选) 的字典。
        """
        self._embeddings = OpenAIEmbeddings(
            model=config["model_name"],
            api_key=config["api_key"],
            base_url=config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            dimensions=config.get("dimension", 1024),
            # 禁用嵌入上下文长度检查：Qwen 嵌入模型支持更长的输入，
            # langchain 内置限制可能导致正常文本被错误截断或拒绝。
            check_embedding_ctx_length=False,
        )

    def embed_query(self, text: str) -> list[float]:
        """对单条查询文本进行向量嵌入。

        Args:
            text: 待嵌入的查询文本。

        Returns:
            嵌入向量（浮点数列表）。
        """
        return self._embeddings.embed_query(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """对多条文档文本进行批量向量嵌入。

        Args:
            texts: 待嵌入的文档文本列表。

        Returns:
            嵌入向量列表，每个元素对应一条文本的向量。
        """
        return self._embeddings.embed_documents(texts)

    def get_embeddings(self):
        """获取底层 OpenAIEmbeddings 实例，供需要直接访问的场景使用。"""
        return self._embeddings
