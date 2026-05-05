from langchain_openai import ChatOpenAI


class LLMClient:
    """Wraps Qwen text model via OpenAI-compatible ChatOpenAI."""

    def __init__(self, config: dict):
        self._llm = ChatOpenAI(
            model=config["model_name"],
            api_key=config["api_key"],
            base_url=config["base_url"],
            temperature=config.get("temperature", 0.1),
        )

    def invoke(self, prompt: str) -> str:
        response = self._llm.invoke(prompt)
        return response.content

    def stream(self, prompt: str):
        for chunk in self._llm.stream(prompt):
            if chunk.content:
                yield chunk.content

    def get_llm(self):
        return self._llm
