from langchain_classic.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool

from ..utils.log_utils import LogUtils


class QAAgent:
    """LangChain Agent wrapping tool-calling for open-ended interactions."""

    def __init__(self, llm, prompt_template: str):
        self.llm = llm
        self.prompt_template = prompt_template
        self._tools: list = []
        self._executor: AgentExecutor | None = None

    def register_tool(self, func):
        self._tools.append(tool(func))

    def _build(self) -> None:
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.prompt_template),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        agent = create_openai_tools_agent(self.llm, self._tools, prompt)
        self._executor = AgentExecutor(
            agent=agent, tools=self._tools, verbose=False,
            handle_parsing_errors=True, max_iterations=5,
        )

    def invoke(self, input_text: str, chat_history: list | None = None) -> str:
        if self._executor is None:
            self._build()
        result = self._executor.invoke({
            "input": input_text,
            "chat_history": chat_history or [],
        })
        return result.get("output", "")
