---
title: QA Agent
emoji: 📝
colorFrom: blue
colorTo: green
sdk: streamlit
sdk_version: 1.57.0
python_version: "3.12"
app_file: main.py
pinned: false
---

# Q&A Agent — 智能问答学习助手

基于 Python + LangChain + Streamlit 构建的 AI 学习助手，支持智能选题、自动评分、多维度解析和题库管理。

## 功能概览

- **智能问答** — AI 从题库中选题，用户作答后自动评分（准确性/完整性/深度），并生成详细解析
- **追问系统** — 答题后可无限轮追问，AI 结合标准答案深度解答
- **题库管理** — 支持文件批量导入、对话添加、在线编辑、删除题目
- **语义搜索** — 基于 Chroma 向量数据库的关键词智能搜索
- **历史记录** — 按线程组织的答题历史，支持领域/分数/关键词筛选
- **流式输出** — AI 回复实时逐字显示，交互更流畅
- **Agent 工具** — 自然语言查询学习统计、智能推荐练习方向、语义搜索相关题目

## 技术栈

| 组件 | 技术选型 |
|------|---------|
| 编程语言 | Python 3.10+ |
| Agent 框架 | LangChain (langchain_classic) |
| 大语言模型 | Qwen-Plus (阿里云百炼) |
| Embedding 模型 | Qwen text-embedding-v3 |
| 向量数据库 | Chroma (持久化) |
| Web 界面 | Streamlit 原生多页面 |
| 数据存储 | JSON 文件 |
| 配置管理 | YAML + 环境变量 |

## 项目结构

```
qa-agent/
├── main.py                              # Streamlit 入口 - 问答页面
├── pages/
│   ├── 1_📚_题库管理.py                 # 题库管理页面入口
│   └── 2_📊_历史记录.py                 # 历史记录页面入口
├── config/
│   ├── models.yml                       # 模型配置 (LLM + Embedding)
│   ├── commands.yml                      # 命令注册表
│   ├── storage.yml                       # 存储路径配置
│   ├── search.yml                        # 搜索参数 (top_k, 阈值)
│   └── prompts/                          # 提示词模板
│       ├── qa_system.md                  # 问答系统提示词
│       ├── evaluate.md                   # 评分提示词 (输出 JSON)
│       ├── add_question.md               # 题目整理提示词
│       └── follow_up.md                  # 追问提示词
├── src/
│   ├── config/
│   │   └── config_loader.py              # 配置加载 (YAML + ${ENV_VAR})
│   ├── models/
│   │   ├── model_factory.py              # 模型工厂 (LLM + Embedding)
│   │   ├── llm_client.py                 # 文本模型客户端 (ChatOpenAI)
│   │   └── embedding_client.py           # Embedding 客户端
│   ├── core/
│   │   ├── qa_controller.py              # 问答流程总控 (核心协调器)
│   │   ├── qa_agent.py                   # LangChain Agent 封装
│   │   ├── agent_tools.py                # Agent 工具函数（统计/推荐/搜索）
│   │   ├── question_bank.py              # 题库 CRUD + JSON 持久化
│   │   ├── search_engine.py              # 语义搜索 (Chroma)
│   │   ├── evaluator.py                  # LLM 评分引擎
│   │   ├── history_manager.py            # 历史记录管理 (线程组织)
│   │   └── command_parser.py             # 斜杠命令解析器
│   ├── utils/
│   │   ├── log_utils.py                  # 日志工具 (分级输出)
│   │   ├── path_utils.py                 # 路径工具 (绝对路径)
│   │   ├── file_utils.py                 # 文件读写工具
│   │   └── prompt_utils.py               # 提示词加载 (变量填充)
│   └── ui/
│       ├── qa_page.py                    # 问答页面渲染 (流式聊天)
│       ├── manage_page.py                # 题库管理页面 (三 Tab)
│       ├── history_page.py               # 历史记录页面 (筛选+详情)
│       └── shared_state.py               # 跨页面共享状态
├── tests/                                # 单元测试
├── data/
│   ├── questions.json                    # 题库文件
│   ├── history.json                      # 历史记录文件
│   └── chroma/                           # Chroma 向量库
├── logs/
│   └── app.log                           # 应用日志
├── requirements.txt
├── .env.example
└── README.md
```

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
cd qa-agent

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入阿里云百炼 API Key
# DASHSCOPE_API_KEY=your-api-key-here
```

### 3. 启动应用

```bash
streamlit run main.py
```

浏览器自动打开 `http://localhost:8501`，即可开始使用。

## 命令系统

所有操作通过聊天输入框输入斜杠命令完成：

### 问答命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `/Q` | 进入问答模式，AI 询问意图 | `/Q` |
| `/Q <领域>` | 智能选题：优先出未答过的题 | `/Q Python基础` |
| `/Q <领域> random` | 从领域随机抽 1 题 | `/Q Python基础 random` |
| `/Q <领域> random N` | 从领域随机抽 N 题 | `/Q Python基础 random 3` |
| `/Q <关键词>` | 语义搜索最相关题目 | `/Q 装饰器` |
| `/Q random N` | 从全题库随机 N 题 | `/Q random 5` |

### 题库管理

| 命令 | 说明 | 示例 |
|------|------|------|
| `/list_domains` | 查看所有领域及题目数量 | `/list_domains` |
| `/list_questions <领域>` | 查看领域内所有题目 | `/list_questions Python基础` |
| `/add_file <路径>` | 从 Markdown 文件批量导入 | `/add_file data/import.md` |
| `/add_interactive` | 对话方式添加题目 | `/add_interactive` |
| `/edit <题目ID>` | 编辑题目 | `/edit q001` |
| `/delete <题目ID>` | 删除题目 | `/delete q001` |

### 其他

| 命令 | 说明 |
|------|------|
| `/help` | 显示帮助信息 |
| `/exit` | 退出当前模式（答题/追问），回到空闲状态 |

## 自然语言交互 (Agent Tools)

在空闲状态下，除了斜杠命令，你还可以用自然语言与 AI 对话。AI 会自动调用以下工具查询数据：

| 工具 | 触发方式 | 功能 |
|------|---------|------|
| 学习统计 | "我学得怎么样？" "看看我的学习数据" | 总答题数、平均分、各领域表现、最近趋势 |
| 练习推荐 | "推荐我练什么？" "接下来做什么？" | 分析薄弱领域，智能推荐练习方向 |
| 题目搜索 | "有没有关于装饰器的题？" | 语义搜索相关题目 |
| 领域概览 | "各领域掌握得如何？" "Python有哪些题？" | 领域题目数、已答数、平均分 |

> 这些工具只读，不会修改题库或历史数据。命令系统（`/Q`、`/list_domains` 等）在自然语言模式下同样可用。

## 页面导航

Streamlit 侧边栏提供三个页面：

1. **🏠 问答** — 主要交互页面，聊天式问答
2. **📚 题库管理** — 三个 Tab：查看/编辑/删除、文件导入、对话添加
3. **📊 历史记录** — 筛选和查看答题历史，支持展开详情和追问线程

## 交互流程

```
用户输入 /Q Python基础
    │
    ├── CommandParser 解析：cmd=qa, target=Python基础
    │
    ├── QAController._qa() 处理：
    │   ├── 确认 Python基础 是已存在的领域
    │   ├── _pick_unanswered() 智能选择未答题
    │   └── 返回题目给前端
    │
    └── 题目展示 → 用户输入答案 → 自动评分 → 进入追问模式
```

## 评分体系

| 维度 | 说明 |
|------|------|
| 准确性 (accuracy) | 核心概念是否正确 |
| 完整性 (completeness) | 是否覆盖关键要点 |
| 深度 (depth) | 是否有深入理解和拓展 |

| 分数段 | 等级 |
|--------|------|
| 90-100 | A级 - 优秀 |
| 70-89 | B级 - 良好 |
| 60-69 | C级 - 及格 |
| 0-59 | D级 - 不及格 |

## 题目导入格式

支持 Markdown 文件批量导入，格式如下：

```markdown
## Python基础

问题: 什么是装饰器？
答案: 装饰器是一个函数，用于在不修改原函数代码的情况下添加额外功能。

---

问题: 列表和元组的区别是什么？
答案: 列表可变，元组不可变；列表用方括号，元组用圆括号。

---

## 数据结构

问题: 什么是哈希表？
答案: 哈希表是一种通过哈希函数将键映射到值的数据结构。
```

## 数据存储

### 题库 (`data/questions.json`)

```json
{
  "domains": ["Python基础", "数据结构"],
  "questions": {
    "Python基础": {
      "q001": {
        "id": "q001",
        "question": "什么是装饰器？",
        "answer": "装饰器是一个函数...",
        "created_at": "2026-05-01T10:00:00",
        "updated_at": "2026-05-01T10:00:00"
      }
    }
  },
  "metadata": {
    "version": "1.0",
    "question_count": 1,
    "last_id": 1
  }
}
```

### 历史记录 (`data/history.json`)

```json
{
  "records": [
    {
      "id": "h_20260501T103000_a3f2",
      "type": "answer",
      "parent_id": null,
      "round": 1,
      "domain": "Python基础",
      "question_id": "q001",
      "score": 85,
      "rating": "B级 - 良好",
      "evaluation": {"accuracy": 90, "completeness": 80, "depth": 85},
      "explanation": "理解基本用途，实现机制有盲区"
    },
    {
      "id": "h_20260501T103200_b4e1",
      "type": "follow_up",
      "parent_id": "h_20260501T103000_a3f2",
      "round": 2,
      "response": "闭包是实现装饰器的基础..."
    }
  ]
}
```

## 配置说明

所有配置文件位于 `config/` 目录，支持 `${ENV_VAR}` 环境变量引用：

- **models.yml** — 文本模型和 Embedding 模型的参数配置（provider, model_name, api_key, temperature 等）
- **commands.yml** — 所有斜杠命令的注册、描述和使用说明
- **storage.yml** — 题库、历史、Chroma、日志的存储路径
- **search.yml** — 语义搜索的 top_k（默认 20）、相似度阈值（默认 0.5）、去重阈值（默认 0.9）

## 技术要点

### 架构设计

**混合路由** — 用户输入按类型走不同路径：
- `/Q`、`/list_domains` 等确定性命令 → `CommandParser` 直接解析参数执行函数，快速可靠
- 自然语言对话、追问等开放交互 → `QAAgent` + Agent Tools，灵活智能

**双 Agent 设计** — 两个 `QAAgent` 实例分别服务不同场景：

| Agent | 工具 | 用途 |
|-------|------|------|
| `agent` | 无 | 结构化任务：意图分类（`/Q` 无参）、JSON 格式化（`/add_interactive`） |
| `agent_tools` | 4 个只读工具 | 自由对话：自然语言查询统计/推荐/搜索、追问 |

拆分的原因是：工具启用后 Agent 走工具调用循环，会产生额外的 LLM 推理轮次和消息上下文。结构化任务（如"把这段话整理为 JSON"）不需要工具，用无工具的 Agent 更快、更准确。

### Qwen API 兼容性

项目使用阿里云百炼的 Qwen DashScope API（OpenAI 兼容模式）。虽然接口格式兼容，但 SDK 和模型行为在多处存在差异，以下是踩过的坑和解决方案：

| 问题 | 表现 | 根因 | 方案 |
|------|------|------|------|
| 花括号转义 | `ChatPromptTemplate` 抛出 `KeyError` | Prompt 中的 JSON 示例 `{"score": ...}` 被当作模板变量 | 传入前将 `{` `}` 替换为 `{{` `}}` |
| AgentExecutor 报错 | API 返回 "contents is neither str nor list of str" | LangChain Agent 向 API 发送多模态消息结构 | 无工具时绕过 AgentExecutor，直接组装字符串消息 |
| Embedding 报错 | 同上错误信息 | tiktoken 将文本预处理为整数 token ID 列表 | `check_embedding_ctx_length=False` |
| Agent 不调用工具 | 模型回复文字却不执行工具 | Qwen 不返回 OpenAI function calling 格式的 `tool_calls` | 自建 XML 标记循环：模型输出 `<tool>` `<args>` 标记，代码解析执行 |
| 跨页面数据不同步 | 题库管理页添加的题目，问答页看不到 | Streamlit 多页面各自创建独立实例 | `st.session_state` 做单例缓存，所有页面共享同一个 `QuestionBank` |

> 详细排查过程见 [docs/issues-and-solutions.md](docs/issues-and-solutions.md)

**自定义工具调用循环** — 这是最核心的解决方案。LangChain 提供了三种 Agent 类型，但都对 Qwen 不兼容：
- `create_openai_tools_agent`：把工具定义放进 API 请求的 `tools` 字段，期待模型返回 `tool_calls`。Qwen 返回的是自然语言文本。
- `create_react_agent`：用文本格式 `Thought → Action → Final Answer:` 驱动。Qwen 能正确调用工具，但收到结果后直接输出自然语言回答，不写 `Final Answer:` 前缀，导致解析器一直认为未完成。

最终方案是放弃 LangChain AgentExecutor，在 `QAAgent.invoke()` 中实现了一个简洁的调用循环：

```
用户输入 → LLM 判断是否需要工具
  ├─ 不需要 → 直接返回回答
  └─ 需要 → LLM 输出 <tool>xxx</tool><args>xxx</args>
       → 代码解析执行工具 → 结果反馈给 LLM → LLM 生成最终回答
```

### 状态管理

Streamlit 的 `st.session_state` 承担了两层角色：
1. **跨页面共享** — `QuestionBank` 和 `SearchEngine` 通过 `init_shared()` 存入 session_state，三个 Streamlit 页面共享同一实例，数据变更实时同步
2. **会话状态机** — `mode` 字段（idle → answering → follow_up）驱动交互流程，`current_question`、`current_record_id` 等传递上下文

### 其他优化

- **流式输出** — 无工具模式下 `LLM.stream()` + `st.write_stream()` 实时逐字渲染
- **智能选题** — `/Q <领域>` 从 `HistoryManager.get_answered_ids()` 获取已答题集合，优先从未答题中随机选择
- **Chroma 增量同步** — 启动时 `sync_from_bank()` 对比题库 ID 与索引 ID，增量添加/删除，避免全量重建

## 依赖清单

```
streamlit>=1.28
langchain>=0.3,<0.4
langchain-community>=0.3
langchain-chroma>=0.2
langchain-openai>=0.2
chromadb>=0.5
pyyaml>=6.0
python-dotenv>=1.0
```
## 界面展示
初始界面
<img width="1913" height="570" alt="Snipaste_2026-05-06_18-24-36" src="https://github.com/user-attachments/assets/4ab7a122-1120-4b73-bc9e-cc2079b8c3d9" />

常用指令
<img width="1249" height="294" alt="Snipaste_2026-05-06_18-25-13" src="https://github.com/user-attachments/assets/7941fcb6-c117-4bd6-a7a1-791ffabe0b93" />
<img width="1122" height="304" alt="Snipaste_2026-05-06_18-24-58" src="https://github.com/user-attachments/assets/a3c77c7d-3391-4703-8691-42f9da308c1c" />
<img width="1107" height="362" alt="Snipaste_2026-05-06_18-24-50" src="https://github.com/user-attachments/assets/db31d1ec-681d-4cc1-97a2-8a623c006807" />

工具调用
<img width="1180" height="407" alt="Snipaste_2026-05-06_18-25-19" src="https://github.com/user-attachments/assets/dce12364-42f5-4e36-b63e-d7e754f33786" />
<img width="1232" height="443" alt="Snipaste_2026-05-06_18-25-28" src="https://github.com/user-attachments/assets/ccc42e82-24b5-421e-b107-c73cfefa1b23" />

题库管理
<img width="1022" height="755" alt="Snipaste_2026-05-06_18-29-34" src="https://github.com/user-attachments/assets/e223a535-a894-4d04-9c5e-0a39db6b5393" />

历史记录
<img width="697" height="909" alt="Snipaste_2026-05-06_18-29-05" src="https://github.com/user-attachments/assets/6abff071-543e-4070-bedc-a30adfc205d7" />
<img width="1872" height="902" alt="Snipaste_2026-05-06_18-25-47" src="https://github.com/user-attachments/assets/0d874c96-8a9b-4f1b-8b4d-0848fdcef67a" />

答题模式
<img width="932" height="842" alt="Snipaste_2026-05-06_18-28-22" src="https://github.com/user-attachments/assets/82b35616-4d9e-4b92-b655-166331aa95d8" />

答题追问<img width="977" height="849" alt="Snipaste_2026-05-06_18-28-28" src="https://github.com/user-attachments/assets/d8092a31-eb2d-41b3-8c2f-afac6d74ff09" />




## License

MIT
