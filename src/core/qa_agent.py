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
        # Escape curly braces so ChatPromptTemplate treats JSON examples as literal text
        escaped_system = self.prompt_template.replace("{", "{{").replace("}", "}}")
        prompt = ChatPromptTemplate.from_messages([
            ("system", escaped_system),
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
        if not self._tools:
            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [SystemMessage(content=self.prompt_template)]
            if chat_history:
                messages.extend(chat_history)
            messages.append(HumanMessage(content=input_text))
            response = self.llm.invoke(messages)
            return response.content

        if self._executor is None:
            self._build()
        result = self._executor.invoke({
            "input": input_text,
            "chat_history": chat_history or [],
        })
        return result.get("output", "")

    def stream(self, input_text: str, chat_history: list | None = None):
        if not self._tools:
            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [SystemMessage(content=self.prompt_template)]
            if chat_history:
                messages.extend(chat_history)
            messages.append(HumanMessage(content=input_text))
            for chunk in self.llm.stream(messages):
                if chunk.content:
                    yield chunk.content
        else:
            yield self.invoke(input_text, chat_history)
