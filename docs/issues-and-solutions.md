# QA Agent 项目技术问题与解决方案

## 一、背景

用 Python + LangChain + Streamlit 构建一个 AI 学习助手，LLM 用的是阿里云百炼的 Qwen-Plus，向量模型用的是 Qwen text-embedding-v3。项目跑通后踩了不少兼容性坑，以下是几个最值得记录的。

---

## 二、ChatPromptTemplate 花括号转义

### 现象

评分提示词里有一个 JSON 输出示例：

```json
{
  "score": <0-100>,
  "accuracy": <0-100>
}
```

LangChain 的 `ChatPromptTemplate` 会把 `{` `}` 当作变量占位符去解析，`{score}`、`{accuracy}` 这些被它误认为是需要填充的模板变量，直接抛异常。

### 原因

`ChatPromptTemplate.from_messages()` 底层用 Python 的 `string.format()` 语法处理 `{variable}` 占位符。任何不在变量列表里的花括号都会被当成非法语法。

### 方案

在传给 `ChatPromptTemplate` 之前，把系统提示词中的所有 `{` 替换为 `{{`，`}` 替换为 `}}`。`format()` 会把 `{{` 渲染为字面量 `{`。

```python
escaped_system = self.prompt_template.replace("{", "{{").replace("}", "}}")
```

---

## 三、AgentExecutor 无工具模式导致 Qwen API 报错

### 现象

Agent 没注册任何工具时，调用 `AgentExecutor.invoke()` 直接报错。错误来自 Qwen API：

> contents is neither str nor list of str

### 原因

LangChain 的 `create_openai_tools_agent` 内部会把工具定义注入到 API 请求的 `tools` 字段中。即使工具列表为空，AgentExecutor 的 ReAct 循环也会向 API 发送结构化的多模态消息（包含 `tool_calls`、`function_call` 等字段），而 Qwen DashScope 的兼容端点只接受纯字符串消息。

### 方案

在 `invoke()` 开头加了一个分支判断：如果 `_tools` 为空，不走 AgentExecutor，直接用 `SystemMessage + HumanMessage` 手动组装消息发给 LLM。

```python
if not self._tools:
    messages = [SystemMessage(content=self.prompt_template)]
    messages.append(HumanMessage(content=input_text))
    response = self.llm.invoke(messages)
    return response.content
```

这是后来"双 Agent" 设计的前身——无工具 Agent 处理结构化任务，有工具 Agent 处理自由对话。

---

## 四、Qwen Embedding API 拒绝 tiktoken Token ID

### 现象

调用 Embedding 模型时报错：

> contents is neither str nor list of str

### 原因

LangChain OpenAI SDK 的 `OpenAIEmbeddings` 默认开启了 `check_embedding_ctx_length=True`，这会让 tiktoken 把文本预先分词为整数 token ID 列表再发送给 API。OpenAI 的 API 接受这种格式，但 Qwen 的 Embedding API 只接受原始字符串。

### 方案

创建 `OpenAIEmbeddings` 实例时显式传入 `check_embedding_ctx_length=False`，让文本以原始字符串形式发送。

```python
OpenAIEmbeddings(
    model=config["model_name"],
    check_embedding_ctx_length=False,
    ...
)
```

**教训：** 用兼容 API 时，SDK 的默认优化很可能不兼容。遇到奇怪错误时先检查 SDK 发了什么格式的请求。

---

## 五、Streamlit 跨页面数据不同步

### 现象

在「题库管理」页面添加或删除了题目，回到「问答」页面后看不到变化。甚至两个页面显示的题目列表不一致，必须重启应用才能同步。

### 原因

Streamlit 的每个页面是独立的 Python 模块，各自创建自己的 `QuestionBank` 和 `SearchEngine` 实例。两个页面从同一个 JSON 文件读取数据，但修改只发生在其中一个实例——另一个页面没有办法知道数据变了。用 `st.rerun()` 也只是刷新当前页面。

### 方案

把 `QuestionBank` 和 `SearchEngine` 的创建逻辑抽到一个 `init_shared()` 函数中，用 `st.session_state` 做单例缓存。所有页面调用同一个函数，获取的始终是同一批实例。题目变更后搜索引擎索引也同步更新。

```python
def init_shared():
    if "shared_bank" not in st.session_state:
        st.session_state.shared_bank = QuestionBank(...)
        st.session_state.shared_search = SearchEngine(...)
    return st.session_state.shared_bank, st.session_state.shared_search, ...
```

**教训：** Streamlit 的 session_state 是跨页面的共享内存，但凡多个页面操作同一份数据，就一定要用它来做单例。

---

## 六、LangChain Agent 工具调用与 Qwen API 的兼容性问题（核心）

这是项目中最复杂的一个问题，经历了三次迭代才最终解决。

### 初始期望

我希望用户在空闲状态下用自然语言提问（如"我学得怎么样？"），Agent 能自动调用工具（如 `get_learning_stats`）查询数据并回答。LangChain 提供了几种 Agent 类型，我以为选一个能用就行。

### 第一次尝试：create_openai_tools_agent

基于 OpenAI 原生 function calling 机制的 Agent。原理是 LangChain 把工具定义序列化后放进 API 请求的 `tools` 字段，模型在响应中返回 `tool_calls` 数组，AgentExecutor 解析后执行工具。

**结果：** 用户问"我学得怎么样？"，模型回复 "让我帮你查看一下当前的学习情况" 就结束了，没有调用工具。

排查发现 Qwen DashScope 的 OpenAI 兼容端点虽然能接收 `tools` 参数，但模型不一定会返回 `tool_calls`——它更倾向于输出自然语言文本。AgentExecutor 收到纯文本后，因为没有检测到 `tool_calls`，就直接把它当作最终输出返回了。

**关键认知：** "API 接口兼容" ≠ "行为兼容"。兼容端点只是接受请求格式，不代表模型真的会按 function calling 的协议响应。

### 第二次尝试：create_react_agent

ReAct（Reasoning + Acting）是一种纯文本的 Agent 模式，不依赖 API 级别的 function calling。它在提示词中告诉模型用固定格式输出：

```
Thought: 我需要做什么
Action: get_learning_stats
Action Input: ...
Observation: <工具返回结果>
Thought: 我现在有足够的数据了
Final Answer: 你的学习情况是...
```

**结果：** 模型确实正确地输出了 `Thought` 和 `Action`，工具也被成功调用。但工具结果返回后，模型直接输出了一大段自然语言回答——没有 `Final Answer:` 前缀。AgentExecutor 的解析器找不到 `Final Answer:`，就认为回答还没完成，把相同的消息再发给 LLM，LLM 又走了一遍同样的流程……如此循环 5 次直到 `max_iterations` 耗尽，返回 "Agent stopped due to iteration limit"。

**关键认知：** ReAct 对输出格式的要求太严格了。Qwen 是一个偏向对话的模型，它的自然行为是直接输出友好文本，而不是严格遵循 `Final Answer:` 标注。这就像让一个习惯写信的人突然用军队的公文格式——他知道内容要写什么，但格式总是不对。

### 第三次尝试：自定义 XML 标记循环

既然模型在"工具识别"上没问题（它知道该调用什么工具），问题只出在"输出格式"上，那不如自己实现一个更宽松的调用循环。

**设计：** 不用任何 LangChain Agent 类型，写一个简单的两步流程：

1. 把工具列表和调用规则直接写进系统提示词，用简单的 XML 标记让模型表示工具意图：
   ```
   <tool>get_learning_stats</tool>
   <args>装饰器</args>
   ```

2. `invoke()` 里用正则提取 `<tool>` 和 `<args>`，执行工具，把结果拼回对话上下文，再让模型生成最终回答。

3. 不需要工具时，模型照常输出自然语言，代码检测不到 `<tool>` 标记就直接返回。

```python
def invoke(self, input_text, chat_history=None):
    # 构建带工具描述的系统提示词
    messages = [SystemMessage(content=self._build_tool_prompt())]
    messages.append(HumanMessage(content=input_text))

    for iteration in range(3):
        response = self.llm.invoke(messages)
        content = response.content

        tool_result = self._try_call_tool(content)
        if tool_result is None:
            return content  # 无工具调用，直接返回

        # 有工具调用，结果反馈给模型
        messages.append(AIMessage(content=content))
        messages.append(HumanMessage(
            content=f"工具返回结果:\n\n{tool_result}\n\n请根据以上数据回答用户。"
        ))
```

这个方案的核心思想是：**不要把格式约束强加在输出端，而是把识别负担放在输入端。** 让模型用最自然的方式表达意图（XML 标签），由代码来解析和执行。

**结果：** 全部 4 个工具（学习统计、练习推荐、题目搜索、领域概览）都能被正确调用并返回结果，不需要工具的普通聊天也不受影响。

---

## 七、总结

这个项目虽然不大，但它碰到的兼容性问题很有代表性。核心原因可以归结为一句话：

**Qwen 的 DashScope API 提供了 OpenAI 兼容接口，但 SDK 层的许多默认行为（tiktoken 分词、function calling、结构化消息格式）是专门为 OpenAI 设计的，用在 Qwen 上会以各种意料之外的方式失败。**

具体表现为三类问题：

| 类型 | 例子 | 修复思路 |
|------|------|---------|
| SDK 默认行为不兼容 | tiktoken 预处理 token ID | 关闭默认优化选项 |
| API 消息格式不兼容 | AgentExecutor 发送结构化消息 | 手动组装纯字符串消息 |
| 模型行为模式不匹配 | 不输出 `tool_calls` / `Final Answer:` | 用宽松的标记格式 + 自定义解析 |

实践下来最大的感受是：做 LLM 应用，真正花时间的往往不是核心业务逻辑，而是让模型和框架的"社交礼仪"对上号。
