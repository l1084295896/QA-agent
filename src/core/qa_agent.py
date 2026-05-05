"""基于 LangChain AgentExecutor 的通用问答代理，支持工具调用和流式输出双模式。"""

from langchain_classic.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool

from ..utils.log_utils import LogUtils


class QAAgent:
    """LangChain Agent 封装：无工具时直接用 LLM 对话，有工具时走 AgentExecutor 的 ReAct 循环。

    核心职责：
    - 统一非工具模式（纯 LLM 调用）和工具模式（Agent 多轮推理）
    - 支持 invoke（一次性返回）和 stream（流式输出）两种调用方式
    """

    def __init__(self, llm, prompt_template: str):
        """初始化 Agent。

        Args:
            llm: LangChain 兼容的 LLM 实例（如 ChatOpenAI）
            prompt_template: 系统提示词模板，可包含 {placeholder} 用于替换
        """
        self.llm = llm
        self.prompt_template = prompt_template
        self._tools: list = []
        self._executor: AgentExecutor | None = None

    def register_tool(self, func):
        """注册工具函数，会被 LangChain 的 @tool 装饰器包装。"""
        self._tools.append(tool(func))

    def _build(self) -> None:
        """构建 AgentExecutor：将 prompt 中的花括号转义后注入 ChatPromptTemplate。

        ChatPromptTemplate 会把 {var} 当作变量占位符。为避免 prompt 模板中的 JSON
        示例花括号被误解析，需要将 { 替换为 {{，} 替换为 }}。
        MessagesPlaceholder 用来在消息序列中插入 chat_history 和 agent_scratchpad
        （二者不是字符串变量，必须用占位符对象而非 {var} 模板语法）。
        """
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
        """同步调用：无工具时直接 LLM.invoke，有工具时走 AgentExecutor。

        Args:
            input_text: 用户输入文本
            chat_history: 历史消息列表（LangChain Message 对象），可为空

        Returns:
            LLM 或 Agent 的最终输出字符串
        """
        # 无工具注册 → 纯 LLM 对话模式，不构建 Agent
        if not self._tools:
            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [SystemMessage(content=self.prompt_template)]
            if chat_history:
                messages.extend(chat_history)
            messages.append(HumanMessage(content=input_text))
            response = self.llm.invoke(messages)
            return response.content

        # 有工具注册 → 延迟构建 AgentExecutor（首次调用时构建）
        if self._executor is None:
            self._build()
        result = self._executor.invoke({
            "input": input_text,
            "chat_history": chat_history or [],
        })
        return result.get("output", "")

    def stream(self, input_text: str, chat_history: list | None = None):
        """流式调用：无工具时逐块 yield LLM 输出，有工具时降级为同步 invoke。

        Args:
            input_text: 用户输入文本
            chat_history: 历史消息列表

        Yields:
            str: LLM 输出的文本块
        """
        # 无工具 → 流式模式：LLM.stream 返回迭代器，逐块产出
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
            # 有工具时暂不支持真正的流式，降级为一次性返回
            yield self.invoke(input_text, chat_history)
