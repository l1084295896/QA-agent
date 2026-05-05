from langchain_openai import OpenAIEmbeddings


class EmbeddingClient:
    """Wraps Qwen embedding model via OpenAI-compatible OpenAIEmbeddings."""

    def __init__(self, config: dict):
        self._embeddings = OpenAIEmbeddings(
            model=config["model_name"],
            api_key=config["api_key"],
            base_url=config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            dimensions=config.get("dimension", 1024),
            check_embedding_ctx_length=False,
        )

    def embed_query(self, text: str) -> list[float]:
        return self._embeddings.embed_query(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embeddings.embed_documents(texts)

    def get_embeddings(self):
        return self._embeddings
