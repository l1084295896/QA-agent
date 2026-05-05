# LLM 客户端模块 —— 封装 Qwen 大语言模型，通过 OpenAI 兼容接口调用。
from langchain_openai import ChatOpenAI


class LLMClient:
    """Wraps Qwen text model via OpenAI-compatible ChatOpenAI."""

    def __init__(self, config: dict):
        """初始化 LLM 客户端。

        Qwen API 兼容 OpenAI 协议，因此可直接使用 langchain 的 ChatOpenAI 封装。
        需要配置 model_name、api_key、base_url 三个必要参数。

        Args:
            config: 包含 model_name, api_key, base_url, temperature(可选) 的字典。
        """
        self._llm = ChatOpenAI(
            model=config["model_name"],
            api_key=config["api_key"],
            base_url=config["base_url"],
            temperature=config.get("temperature", 0.1),
        )

    def invoke(self, prompt: str) -> str:
        """同步调用 LLM，返回完整响应文本。

        Args:
            prompt: 输入的提示词字符串。

        Returns:
            LLM 返回的完整文本内容。
        """
        response = self._llm.invoke(prompt)
        return response.content

    def stream(self, prompt: str):
        """流式调用 LLM，逐块返回响应文本。

        Args:
            prompt: 输入的提示词字符串。

        Yields:
            每个包含内容的 chunk 字符串。
        """
        for chunk in self._llm.stream(prompt):
            if chunk.content:
                yield chunk.content

    def get_llm(self):
        """获取底层 ChatOpenAI 实例，供需要直接访问的场景使用。"""
        return self._llm
