"""基于 LangChain 的通用问答代理，支持工具调用和流式输出双模式。

工具调用使用自定义 XML 标记循环（<tool> / <args>），不依赖 LangChain AgentExecutor，
以兼容 Qwen DashScope API 的工具调用行为。
"""

import json
import re

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool

from ..utils.log_utils import LogUtils


class QAAgent:
    """QA Agent 封装：无工具时纯 LLM 对话，有工具时走自定义调用循环。

    核心职责：
    - 统一非工具模式（纯 LLM 调用）和工具模式（自定义 XML 标记循环）
    - 支持 invoke（一次性返回）和 stream（流式输出）两种调用方式
    """

    def __init__(self, llm, prompt_template: str):
        self.llm = llm
        self.prompt_template = prompt_template
        self._tools: list = []
        self._tool_map: dict[str, object] = {}

    def register_tool(self, func):
        """注册工具函数，会被 LangChain 的 @tool 装饰器包装。"""
        wrapped = tool(func)
        self._tools.append(wrapped)
        self._tool_map[wrapped.name] = wrapped

    def _build_tool_prompt(self) -> str:
        """构建工具描述文本，注入到系统提示词中。"""
        if not self._tools:
            return self.prompt_template

        tool_lines = []
        for t in self._tools:
            # Extract first line of docstring as brief description
            desc = (t.description or "").split("\n")[0]
            # Extract parameter info from function signature
            tool_lines.append(f"  - **{t.name}**: {desc}")

        tools_section = "\n".join(tool_lines)

        return f"""{self.prompt_template}

## 可用工具

你可以调用以下工具来查询数据：

{tools_section}

## 工具调用规则

当用户的问题需要使用工具查询数据时（如询问学习统计、推荐、搜索题目、领域概况），
你必须在回复中**首先**用以下格式调用工具：

<tool>工具名称</tool>
<args>参数（纯文本，不要用JSON。如工具不需要参数则省略此标签）</args>

工具调用后，系统会返回查询结果，你再根据结果给出最终回答。

**示例：**
用户问"我学得怎么样？"，你应该回复：
<tool>get_learning_stats</tool>

用户问"有没有关于装饰器的题目？"，你应该回复：
<tool>find_related_questions</tool>
<args>装饰器</args>

**重要约束：**
- 如果不需要查询数据就能回答（普通聊天），直接回复即可，不要使用 <tool> 标签
- 一次只能调用一个工具
- 不要在 <tool> 标签前后添加任何其他文字
- args 里直接写搜索词/参数文本，不要写成 JSON 格式
- 收到工具返回的数据后，用友好的语气组织回答，不要提及"工具返回"等内部细节"""

    def _try_call_tool(self, response: str) -> str | None:
        """尝试从 LLM 响应中提取并执行工具调用。返回工具执行结果，无调用则返回 None。"""
        tool_m = re.search(r'<tool>\s*(.*?)\s*</tool>', response, re.DOTALL)
        if not tool_m:
            return None
        tool_name = tool_m.group(1).strip()
        if tool_name not in self._tool_map:
            LogUtils.warn(f"Agent requested unknown tool: {tool_name}")
            return f"未知工具: {tool_name}"

        args_m = re.search(r'<args>\s*(.*?)\s*</args>', response, re.DOTALL)
        args_text = args_m.group(1).strip() if args_m else ""

        # 尝试解析 JSON 格式参数，提取实际值
        if args_text:
            try:
                parsed = json.loads(args_text)
                if isinstance(parsed, dict):
                    # 取第一个非空值作为参数
                    args_text = next((v for v in parsed.values() if v), args_text)
                elif isinstance(parsed, str):
                    args_text = parsed
            except (json.JSONDecodeError, StopIteration):
                pass  # 保持原始文本参数

        tool_obj = self._tool_map[tool_name]
        try:
            if args_text:
                result = tool_obj.invoke({"query": args_text})
            else:
                result = tool_obj.invoke({})
        except Exception:
            try:
                if args_text:
                    result = tool_obj.invoke(args_text)
                else:
                    result = tool_obj.invoke("")
            except Exception as e:
                result = f"工具调用失败: {e}"

        LogUtils.info(f"Tool '{tool_name}' called with args='{args_text}' -> {str(result)[:80]}...")
        return str(result)

    def invoke(self, input_text: str, chat_history: list | None = None) -> str:
        """同步调用：无工具时直接 LLM.invoke，有工具时走自定义调用循环。

        Args:
            input_text: 用户输入文本
            chat_history: 历史消息列表

        Returns:
            LLM 或 Agent 的最终输出字符串
        """
        if not self._tools:
            messages = [SystemMessage(content=self.prompt_template)]
            if chat_history:
                messages.extend(chat_history)
            messages.append(HumanMessage(content=input_text))
            response = self.llm.invoke(messages)
            return response.content

        # 工具模式：自定义调用循环
        system_content = self._build_tool_prompt()
        messages = [SystemMessage(content=system_content)]
        if chat_history:
            messages.extend(chat_history)
        messages.append(HumanMessage(content=input_text))

        for iteration in range(3):
            response = self.llm.invoke(messages)
            content = response.content or ""

            # 尝试提取工具调用
            tool_result = self._try_call_tool(content)
            if tool_result is None:
                # 没有工具调用，直接返回回复
                return content

            # 有工具调用：把工具结果反馈给 LLM 生成最终回答
            messages.append(AIMessage(content=content))
            messages.append(HumanMessage(
                content=f"工具返回结果:\n\n{tool_result}\n\n请根据以上数据用友好的语气回答用户。不要提及'工具'或内部细节，直接给出答案。"
            ))

        # 最后一轮：直接返回（不应到达这里，作为兜底）
        final = self.llm.invoke(messages)
        return final.content or "抱歉，处理请求时出现问题，请稍后重试。"

    def stream(self, input_text: str, chat_history: list | None = None):
        """流式调用：无工具时逐块 yield，有工具时降级为同步 invoke。

        Args:
            input_text: 用户输入文本
            chat_history: 历史消息列表

        Yields:
            str: LLM 输出的文本块
        """
        if not self._tools:
            messages = [SystemMessage(content=self.prompt_template)]
            if chat_history:
                messages.extend(chat_history)
            messages.append(HumanMessage(content=input_text))
            for chunk in self.llm.stream(messages):
                if chunk.content:
                    yield chunk.content
        else:
            # 工具模式下不支持流式，降级为一次性返回
            yield self.invoke(input_text, chat_history)
