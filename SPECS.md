# Q&A Agent 项目设计文档

**日期:** 2026-05-05
**版本:** v2.1 (Agent Tools 已实现)

---

## 1. 项目概述

### 1.1 项目目标
使用 Python + LangChain 构建一个基于 Agent 智能体的问答评分系统，支持：
- 从题库中智能选题并答题
- 模型自动评分并生成解析
- 多途径管理题目（文件导入 / 对话添加 / 编辑 / 删除）
- Streamlit Web 界面，侧边栏选项卡导航
- CLI 命令为主要交互方式（通过聊天输入框输入斜杠命令）

### 1.2 核心场景
个人学习助手，用于检验和巩固知识掌握程度。

---

## 2. 技术栈

| 组件 | 选择 | 说明 |
|------|------|------|
| 编程语言 | Python 3.10+ | |
| Agent 框架 | LangChain >=0.3,<0.4 | + langchain-community, langchain-chroma |
| 大模型 - 文本 | Qwen (阿里云百炼) | qwen-plus |
| 大模型 - Embedding | Qwen Embedding (阿里云百炼) | text-embedding-v3 |
| 向量数据库 | Chroma | 持久化存储 |
| Web 框架 | Streamlit | 原生多页面 |
| 题库存储 | JSON | 轻量直观 |
| 历史记录 | JSON | 固定路径存储 |
| 配置管理 | YAML | 多配置文件，支持环境变量引用 |
| 日志 | 自定义 Logger | 分级输出、文件记录 |
| 环境变量 | .env + python-dotenv | API Key 等敏感信息 |

---

## 3. 架构设计

### 3.1 整体架构：混合模式

```
用户输入 (Streamlit 聊天框)
        │
        ▼
  CommandParser.parse(input)
        │
        ├── 匹配到显式命令 ──► 直接函数调用执行
        │    (/Q domain, /list_domains 等确定性操作)
        │
        └── 未匹配命令 ──► QAAgent (LangChain Agent + Tools)
             (/Q 无参数、追问、/add_interactive 等开放交互)
```

**原则：**
- 确定性操作（指定领域选题、列表、导入文件等）→ **CommandParser + 普通函数**，快速稳定
- 开放交互（意图理解、追问、对话添加）→ **LangChain Agent + Tools**，灵活智能

### 3.2 Agent Tools

Agent 工具分为两类：

**A. 确定性工具（已通过 CommandParser + 状态机实现）**

| Tool | 用途 | 调用场景 |
|------|------|----------|
| `select_question_by_domain` | 从指定领域选题 | `/Q domain` |
| `search_questions` | 语义搜索题目 | `/Q keyword` |
| `evaluate_answer` | 评分并生成解析 | 用户提交答案后 |
| `add_question_tool` | LLM 整理题目格式 | `/add_interactive` |
| `handle_follow_up` | 基于标准答案回答追问 | 答题后的追问 |

**B. 对话增强工具（Agent 自主调用，自然语言触发）**

| Tool | 参数 | 功能 | 实现文件 |
|------|------|------|----------|
| `get_learning_stats` | 无 | 总答题数、平均分、各领域表现、最近趋势 | `agent_tools.py` |
| `recommend_practice` | 无 | 分析薄弱+未练习领域，智能推荐 | `agent_tools.py` |
| `find_related_questions` | `query: str` | 语义搜索 top 5 相关题目 | `agent_tools.py` |
| `get_domain_summary` | `domain: str` (可选) | 领域题目数、已答数、均分 | `agent_tools.py` |

**架构说明：** 采用双 Agent 设计 — `agent`（无工具）处理结构化任务（意图分类、JSON 格式化），`agent_tools`（带工具）处理自由对话和追问，通过 `QAController` 按场景路由。

---

## 4. 目录结构

```
qa-agent/
├── config/                         # 配置文件
│   ├── models.yml                  # 模型配置
│   ├── commands.yml                # 命令注册
│   ├── storage.yml                 # 存储路径
│   ├── search.yml                  # 搜索参数
│   └── prompts/                    # 提示词模板
│       ├── qa_system.md            # 问答系统提示词
│       ├── evaluate.md             # 评分提示词（输出 JSON）
│       ├── add_question.md         # 添加题目提示词
│       └── follow_up.md            # 追问提示词
├── data/                           # 数据文件
│   ├── questions.json              # 题库
│   ├── history.json                # 历史记录
│   └── chroma/                     # Chroma 向量库持久化目录
├── logs/                           # 日志
│   └── app.log
├── src/                            # 源代码
│   ├── __init__.py
│   ├── config/                     # 配置模块
│   │   ├── __init__.py
│   │   └── config_loader.py        # 统一配置加载（YAML + 环境变量）
│   ├── models/                     # 模型工厂
│   │   ├── __init__.py
│   │   ├── model_factory.py        # 统一模型创建入口
│   │   ├── llm_client.py           # 文本模型客户端
│   │   └── embedding_client.py     # Embedding 模型客户端
│   ├── utils/                      # 工具函数
│   │   ├── __init__.py
│   │   ├── log_utils.py            # 日志工具（分级输出 + 文件记录）
│   │   ├── path_utils.py           # 路径工具（绝对路径、目录确保）
│   │   ├── file_utils.py           # 文件加载/保存
│   │   └── prompt_utils.py         # 提示词加载与变量填充
│   ├── core/                       # 核心业务逻辑
│   │   ├── __init__.py
│   │   ├── question_bank.py        # 题库 CRUD
│   │   ├── search_engine.py        # 语义搜索（Chroma + Embedding）
│   │   ├── evaluator.py            # 评分引擎
│   │   ├── history_manager.py      # 历史记录管理
│   │   ├── command_parser.py       # 命令解析器
│   │   ├── qa_agent.py             # LangChain Agent（Tools 定义）
│   │   ├── agent_tools.py           # Agent 工具函数（统计/推荐/搜索）
│   │   └── qa_controller.py        # 问答流程总控
│   └── ui/                         # Streamlit 页面渲染（薄封装）
│       ├── __init__.py
│       ├── qa_page.py              # 问答页面渲染
│       ├── manage_page.py          # 题库管理页面渲染
│       └── history_page.py         # 历史记录页面渲染
├── pages/                          # Streamlit 原生多页面
│   ├── 1_📚_题库管理.py            # 薄入口：from src.ui.manage_page import render
│   └── 2_📊_历史记录.py            # 薄入口：from src.ui.history_page import render
├── main.py                         # Streamlit 入口（首页：问答页面）
├── tests/
├── requirements.txt
├── .env.example
└── README.md
```

---

## 5. 数据结构

### 5.1 题库文件 (`data/questions.json`)

```json
{
  "domains": ["langchain基础", "python基础", "项目中遇到的问题"],
  "questions": {
    "langchain基础": {
      "q001": {
        "id": "q001",
        "question": "什么是LangChain的Chain？",
        "answer": "Chain是LangChain中的核心概念，它将多个组件串联起来形成完整的处理流程。",
        "created_at": "2026-05-01T10:00:00",
        "updated_at": "2026-05-01T10:00:00"
      }
    }
  },
  "metadata": {
    "created_at": "2026-05-01",
    "version": "1.0",
    "question_count": 1,
    "last_id": 1
  }
}
```

**说明：**
- ID 格式：`q{自增序号}`（如 q001），由 `metadata.last_id` 追踪
- 题目包含 `created_at` / `updated_at` 时间戳
- 题库只存 `question` + `answer`，解析由模型实时生成

### 5.2 历史记录文件 (`data/history.json`)

```json
{
  "records": [
    {
      "id": "h_{timestamp}_{random4}",
      "type": "answer",
      "parent_id": null,
      "round": 1,
      "timestamp": "2026-05-01T10:30:00",
      "domain": "python基础",
      "question_id": "q003",
      "question": "什么是装饰器？",
      "user_input": "装饰器是用来给函数添加额外功能的...",
      "score": 85,
      "rating": "B级 - 良好",
      "evaluation": {
        "accuracy": 90,
        "completeness": 80,
        "depth": 85
      },
      "standard_answer": "装饰器是一个函数，用于包装另一个函数...",
      "explanation": "用户的回答表明理解装饰器基本用途，但在实现机制上有所欠缺。"
    },
    {
      "id": "h_{timestamp}_{random4}",
      "type": "follow_up",
      "parent_id": "h_{timestamp}_{random4}",
      "round": 2,
      "timestamp": "2026-05-01T10:32:00",
      "domain": "python基础",
      "question_id": "q003",
      "question": "那闭包和装饰器有什么关系？",
      "user_input": "那闭包和装饰器有什么关系？",
      "response": "闭包是实现装饰器的基础..."
    }
  ]
}
```

**说明：**
- ID 格式：`h_{timestamp}_{random4}`（如 `h_20260501T103000_a3f2`）
- `type`: `"answer"` | `"follow_up"` — 区分答题记录与追问记录
- `parent_id`: 追问时指向原始答题记录，方便历史页面按线程展示
- `round`: 对话轮次
- `follow_up` 类型不包含 `score`/`evaluation`，但有 `response` 字段

---

## 6. 配置文件

### 6.1 模型配置 (`config/models.yml`)

```yaml
text_model:
  provider: qwen
  model_name: qwen-plus
  api_key: ${DASHSCOPE_API_KEY}
  base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
  temperature: 0.1

embedding_model:
  provider: qwen
  model_name: text-embedding-v3
  api_key: ${DASHSCOPE_API_KEY}
  dimension: 1024
```

### 6.2 命令配置 (`config/commands.yml`)

```yaml
commands:
  qa:
    trigger: /Q
    description: 开启问答模式
    usage: |
      /Q                        - Agent 询问意图
      /Q <领域名>               - 从该领域出题
      /Q <领域名> random        - 从该领域随机 1 题
      /Q <领域名> random N      - 从该领域随机 N 题
      /Q <关键词>               - 语义搜索最相关 1 题
      /Q <关键词> random N      - 语义搜索 Top-K，随机 N 题
      /Q random N               - 从全题库随机 N 题
  list_domains:
    trigger: /list_domains
    description: 查看所有领域
  list_questions:
    trigger: /list_questions
    description: 查看某领域所有题目
    usage: /list_questions <领域名>
  add_file:
    trigger: /add_file
    description: 从 Markdown 文件导入题目
    usage: /add_file <文件路径>
  add_interactive:
    trigger: /add_interactive
    description: 通过对话添加题目（LLM 整理 → 用户确认）
  edit:
    trigger: /edit
    description: 编辑题目
    usage: /edit <题目ID>
  delete:
    trigger: /delete
    description: 删除题目
    usage: /delete <题目ID>
  help:
    trigger: /help
    description: 显示帮助信息
  exit:
    trigger: /exit
    description: 退出当前模式
```

### 6.3 存储配置 (`config/storage.yml`)

```yaml
storage:
  question_bank: data/questions.json
  history: data/history.json
  chroma_db: data/chroma
  temp_dir: data/temp
  log_dir: logs
  log_file: logs/app.log
```

### 6.4 搜索配置 (`config/search.yml`)

```yaml
search:
  top_k: 20                    # 语义搜索返回 Top-K 条结果
  similarity_threshold: 0.5    # 最低相似度阈值，低于此值视为无结果
  dedup_threshold: 0.9         # 题目去重相似度阈值
```

---

## 7. 命令系统

### 7.1 命令解析流程

```
输入文本 → CommandParser.parse(text)
              │
              ├── 识别 trigger（/Q, /list_domains, ...）
              ├── 提取参数（领域名、关键词、random N、文件路径等）
              ├── 校验参数合法性
              └── 返回 (command, params) 元组
```

### 7.2 命令详解

#### `/Q` — 问答命令

| 用法 | 行为 |
|------|------|
| `/Q` | 进入 Agent 对话模式，询问用户意图 |
| `/Q <领域名>` | 优先出该领域未答过的题，答完则从头循环 |
| `/Q <领域名> random` | 从该领域随机选 1 题 |
| `/Q <领域名> random N` | 从该领域随机选 N 题 |
| `/Q <关键词>` | 语义搜索，取最相关 1 题 |
| `/Q <关键词> random N` | 语义搜索 Top-K（K 从 search.yml 读取），随机选 N 题 |
| `/Q random N` | 从全题库随机选 N 题 |

**优先级判断：**
1. 检查第一个参数是否为已存在的领域名 → 按领域选题
2. 否则 → 语义搜索

#### `/list_domains` — 列出领域
显示所有领域及每个领域的题目数量。

#### `/list_questions <领域名>` — 列出题目
显示该领域所有题目 ID 和问题摘要。

#### `/add_file <路径>` — 文件导入
1. 读取文件，用正则解析 Markdown（`## 领域` + `问题:` + `答案:` + `---` 分隔）
2. LLM 仅在格式不标准时兜底
3. 检查去重（embedding 相似度 > 0.9 则提示）
4. 展示预览，用户确认后批量导入

#### `/add_interactive` — 对话添加
1. 用户描述题目内容
2. LLM 整理为标准格式（领域、问题、答案）
3. 展示预览
4. 检查去重
5. 用户确认后入库

#### `/edit <题目ID>` — 编辑题目
1. 查找题目，显示当前内容
2. 用户输入修改内容
3. 更新 `questions.json` + Chroma 索引

#### `/delete <题目ID>` — 删除题目
1. 查找题目，显示内容
2. 用户确认
3. 从 `questions.json` 删除 + Chroma 索引同步删除

#### `/help` — 帮助
显示所有可用命令及用法。

#### `/exit` — 退出
退出当前模式（答题模式 / 追问模式），回到 idle 状态。

---

## 8. 提示词设计

### 8.1 评分提示词 (`config/prompts/evaluate.md`)

输出 JSON 格式，确保可靠解析：

```markdown
你是一个评分专家。请根据标准答案对用户回答进行评分。

标准答案: {standard_answer}
用户回答: {user_answer}

从以下三个维度评判：
- accuracy: 核心概念是否正确
- completeness: 是否覆盖要点
- depth: 是否有深入理解

请严格输出以下 JSON 格式（不要输出其他内容）：
{
  "score": <0-100 整数>,
  "accuracy": <0-100 整数>,
  "completeness": <0-100 整数>,
  "depth": <0-100 整数>,
  "evaluation_basis": "<评分依据>",
  "explanation": "<推断与解释>"
}
```

### 8.2 问答系统提示词 (`config/prompts/qa_system.md`)

```markdown
你是一个学习助手。你的职责是：
1. 帮助用户选择题目进行练习
2. 对用户的回答进行评分
3. 提供详细的反馈和改进建议
4. 回答用户的追问，优先参考标准答案

请保持友好、鼓励的语气。
```

### 8.3 添加题目提示词 (`config/prompts/add_question.md`)

```markdown
你是一个题目整理专家。请将用户输入整理为以下标准 JSON 格式：

{
  "domain": "<领域名，优先从已有领域选择，必要时新建>",
  "question": "<整理后的问题>",
  "answer": "<整理后的标准答案>"
}

已有领域: {existing_domains}
```

### 8.4 追问提示词 (`config/prompts/follow_up.md`)

```markdown
你是一个学习助手。用户刚回答了一道题目，现在有追问。请参考标准答案回答用户的问题。

题目: {question}
标准答案: {standard_answer}
用户回答: {user_answer}
评分: {score}/100

用户追问: {follow_up_question}

请基于标准答案的内容，清晰、准确地回答用户的追问。
```

---

## 9. 评分标准

### 9.1 评分维度

| 维度 | 说明 | 权重 |
|------|------|------|
| 准确性 (accuracy) | 核心概念是否正确 | 均衡 |
| 完整性 (completeness) | 是否覆盖要点 | 均衡 |
| 深度 (depth) | 是否有深入理解 | 均衡 |

### 9.2 综合评分等级

| 分数段 | 等级 |
|--------|------|
| 90-100 | A级 - 优秀 |
| 70-89 | B级 - 良好 |
| 60-69 | C级 - 及格 |
| 0-59 | D级 - 不及格 |

### 9.3 追问功能
- 答题后自动进入追问模式
- 不限轮次，在题目上下文中自由对话
- 追问记录保存到 history（type="follow_up", parent_id 指向原始答题记录）
- `/exit` 退出追问模式

---

## 10. 题库管理功能

题库管理页面（侧边栏选项卡 `📚 题库管理`）提供：

### 10.1 功能列表

| 功能 | 实现方式 |
|------|----------|
| 查看题库 | 按领域分组展示，显示题目列表 |
| 文件导入 | 拖拽/选择 .md/.txt 文件，规则解析 + LLM 兜底 |
| 对话添加 | 聊天框输入描述，LLM 整理后确认 |
| 编辑题目 | 选择题目 → 编辑表单 → 确认更新 |
| 删除题目 | 选择题目 → 确认弹窗 → 删除 |

### 10.2 文件导入格式

```markdown
## langchain基础

问题: 什么是LangChain的Chain？
答案: Chain是LangChain中的核心概念...

---

问题: LangChain支持哪些类型的组件？
答案: 支持LLM、Prompt、Memory等组件...

---

## python基础

问题: 什么是装饰器？
答案: 装饰器是一个函数...
```

**解析策略：**
1. 正则提取 `## 领域名`、`问题:`、`答案:`、`---` 分隔符
2. 格式不标准时，将原始文本交给 LLM 解析
3. 解析结果预览 → 用户确认 → 批量导入

### 10.3 题目去重
- 添加/导入时，计算新题目的 embedding 向量
- 在 Chroma 中搜索最相似题目
- 若相似度 ≥ `search.dedup_threshold`（默认 0.9），提示用户确认是否仍要添加

---

## 11. 页面设计

### 11.1 侧边栏导航
Streamlit 原生多页面，侧边栏自动显示：
- **🏠 问答** — 主页，`main.py`
- **📚 题库管理** — `pages/1_📚_题库管理.py`
- **📊 历史记录** — `pages/2_📊_历史记录.py`

### 11.2 问答页面 (`main.py` / `src/ui/qa_page.py`)

```
┌──────────────────────────────────────────────────────────┐
│  Q&A 学习助手                                             │
├──────────────────────────────────────────────────────────┤
│  聊天区域:                                                │
│  ┌──────────────────────────────────────────────────────┐│
│  │ 助手: 欢迎使用 Q&A 学习助手！输入 /help 查看命令。    ││
│  │                                                      ││
│  │ 用户: /Q python基础                                  ││
│  │                                                      ││
│  │ 助手: 📝 题目: 什么是装饰器？                        ││
│  │      请在此输入你的回答...                            ││
│  │                                                      ││
│  │ 用户: 装饰器是用来给函数添加额外功能的...             ││
│  │                                                      ││
│  │ 助手: 📊 评分: 85/100 (B级 - 良好)                   ││
│  │      - 准确性: 90 ✓                                  ││
│  │      - 完整性: 80 ⚠                                  ││
│  │      - 深度: 85 ✓                                    ││
│  │      📖 标准答案: 装饰器是一个函数...                ││
│  │      💡 解释: 理解基本用途，实现机制有盲区            ││
│  │                                                      ││
│  │ 用户: 那闭包和装饰器有什么关系？                      ││
│  │                                                      ││
│  │ 助手: 闭包是实现装饰器的基础...                       ││
│  └──────────────────────────────────────────────────────┘│
│  ┌──────────────────────────────────────────────────────┐│
│  │ [聊天输入框]                              [发送]     ││
│  └──────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────┘
```

**交互说明：**
- 所有操作通过聊天输入框输入命令完成
- 没有独立的按钮，命令驱动一切
- 支持斜杠命令和自然语言输入
- 聊天历史在当前会话中保留（`st.session_state.messages`）

### 11.3 题库管理页面 (`pages/1_📚_题库管理.py`)

```
┌──────────────────────────────────────────────────────────┐
│  题库管理                                                 │
├──────────────────────────────────────────────────────────┤
│  [Tab: 查看题库] [Tab: 文件导入] [Tab: 对话添加]          │
├──────────────────────────────────────────────────────────┤
│  查看题库:                                                │
│  ┌──────────────────────────────────────────────────────┐│
│  │ 📁 python基础 (3 题)                                 ││
│  │   q001  什么是装饰器？        [编辑] [删除]          ││
│  │   q002  列表和元组的区别？    [编辑] [删除]          ││
│  │   q003  GIL 是什么？          [编辑] [删除]          ││
│  │                                                      ││
│  │ 📁 langchain基础 (2 题)                              ││
│  │   q004  什么是 Chain？        [编辑] [删除]          ││
│  │   q005  Memory 的作用？       [编辑] [删除]          ││
│  └──────────────────────────────────────────────────────┘│
│                                                          │
│  文件导入:                                                │
│  ┌──────────────────────────────────────────────────────┐│
│  │ [拖拽上传区域] 支持 .md, .txt                        ││
│  │ [预览解析结果]                                       ││
│  │ [确认导入]                                           ││
│  └──────────────────────────────────────────────────────┘│
│                                                          │
│  对话添加:                                                │
│  ┌──────────────────────────────────────────────────────┐│
│  │ 描述你想添加的题目:                                  ││
│  │ [文本输入]                    [提交给模型整理]       ││
│  │ ───────────────────────────                          ││
│  │ 模型整理预览:                                        ││
│  │ 领域: python基础                                     ││
│  │ 问题: 什么是装饰器？                                 ││
│  │ 答案: 装饰器是一个用于包装函数的函数...              ││
│  │ [确认添加] [修改] [取消]                             ││
│  └──────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────┘
```

### 11.4 历史记录页面 (`pages/2_📊_历史记录.py`)

```
┌──────────────────────────────────────────────────────────┐
│  历史记录                                                 │
├──────────────────────────────────────────────────────────┤
│  筛选: [领域 ▼] [分数段 ▼] [时间范围] [搜索关键词]       │
├──────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐│
│  │ 2026-05-01 10:30  python基础  85分 B级-良好          ││
│  │   📝 什么是装饰器？                                  ││
│  │   💬 2 条追问                                       ││
│  │   [展开详情]                                         ││
│  ├──────────────────────────────────────────────────────┤│
│  │ 2026-05-01 09:15  langchain基础  70分 B级-良好       ││
│  │   📝 什么是 Chain？                                  ││
│  │   [展开详情]                                         ││
│  └──────────────────────────────────────────────────────┘│
│                                                          │
│  展开详情:                                                │
│  ┌──────────────────────────────────────────────────────┐│
│  │ 题目: 什么是装饰器？                                 ││
│  │ 你的回答: 装饰器是用来添加功能的...                   ││
│  │ 标准答案: 装饰器是一个用于包装函数的函数...          ││
│  │ 评分: 85/100 (准确性:90 完整性:80 深度:85)           ││
│  │ 解释: 理解基本用途，实现机制有盲区                    ││
│  │ ───────── 追问线程 ─────────                         ││
│  │ Q: 那闭包和装饰器有什么关系？                        ││
│  │ A: 闭包是实现装饰器的基础...                         ││
│  └──────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────┘
```

---

## 12. 异常处理策略

| 场景 | 处理方式 |
|------|----------|
| API 调用失败 / 超时 | 友好提示"模型服务暂时不可用，请稍后重试" |
| 题库为空 | 提示"题库暂无题目，请先通过 /add_file 或 /add_interactive 添加" |
| 语义搜索无结果 | 提示"未找到相关题目，请尝试其他关键词" |
| 领域不存在 | 提示"领域 'XXX' 不存在，可用 /list_domains 查看已有领域" |
| 文件不存在 / 格式错误 | 提示具体错误原因，引导修正 |
| 重复题目 | 提示"检测到相似题目 qXXX（相似度 XX%），是否仍要添加？" |
| 非法命令 | 提示"未知命令，输入 /help 查看可用命令" |
| 网络异常 | 友好提示，不暴露技术细节 |

**原则：所有异常统一通过 Streamlit 的 `st.warning` / `st.error` / `st.info` 友好展示，不崩溃。**

---

## 13. Chroma 向量库同步策略

- **启动时：** 读取 `questions.json`，检查 Chroma 索引是否存在及一致，不一致则全量重建
- **运行时：** 增量同步
  - 添加题目 → `questions.json` 写入 + Chroma 同步添加
  - 编辑题目 → `questions.json` 更新 + Chroma 删除旧向量 + 添加新向量
  - 删除题目 → `questions.json` 删除 + Chroma 同步删除
- 用题目 ID 作为 Chroma 的 document ID，确保可追踪

---

## 14. 模块职责

| 模块 | 路径 | 职责 |
|------|------|------|
| ConfigLoader | `src/config/config_loader.py` | 加载 YAML 配置，解析 `${ENV_VAR}` 环境变量引用 |
| ModelFactory | `src/models/model_factory.py` | 统一创建 LLM / Embedding 模型实例 |
| LogUtils | `src/utils/log_utils.py` | 自定义日志，分级输出 + 文件记录 |
| PathUtils | `src/utils/path_utils.py` | 绝对路径转换，目录自动创建 |
| FileUtils | `src/utils/file_utils.py` | JSON 文件读写，Markdown 文件读取 |
| PromptUtils | `src/utils/prompt_utils.py` | 加载 Markdown 提示词，填充变量 |
| QuestionBank | `src/core/question_bank.py` | 题库 CRUD（增删改查），文件持久化 |
| SearchEngine | `src/core/search_engine.py` | Chroma 管理，语义搜索，去重检测 |
| Evaluator | `src/core/evaluator.py` | 调用 LLM 评分，解析 JSON 结果 |
| HistoryManager | `src/core/history_manager.py` | 历史记录增删查，按线程组织 |
| CommandParser | `src/core/command_parser.py` | 解析斜杠命令，提取参数，校验 |
| QAAgent | `src/core/qa_agent.py` | LangChain Agent 定义，Tools 注册机制 |
| AgentTools | `src/core/agent_tools.py` | Agent 工具工厂（统计/推荐/搜索/概览） |
| QAController | `src/core/qa_controller.py` | 流程总控，协调各模块，双 Agent 路由 |

---

## 15. Streamlit 会话状态设计

```python
st.session_state = {
    "mode": "idle",           # "idle" | "answering" | "follow_up" | "adding_question"
    "messages": [],           # 聊天消息历史
    "current_question": None, # 当前题目 {id, question, answer, domain}
    "current_record_id": None,# 当前答题记录 ID（用于追问的 parent_id）
    "current_round": 0,       # 当前对话轮次
    "pending_question": None, # 待确认的题目（/add_interactive 流程中）
}
```

---

## 16. 依赖清单 (`requirements.txt`)

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

---

## 17. 待实现清单

- [ ] 配置模块：YAML 加载 + 环境变量解析
- [ ] 模型工厂：LLM + Embedding 客户端
- [ ] 工具函数：日志、路径、文件、提示词
- [ ] 题库管理：CRUD + JSON 持久化
- [ ] 语义搜索：Chroma 管理 + 索引同步
- [ ] 评分引擎：LLM 评分 + JSON 解析
- [ ] 历史记录：增删查 + 线程组织
- [ ] 命令解析器：斜杠命令识别 + 参数提取
- [x] QA Agent：LangChain Agent + Tools
- [ ] QA 控制器：流程编排 + 模式管理
- [ ] 问答页面：Streamlit 聊天界面
- [ ] 题库管理页面：Tab 切换 + 查看/编辑/删除/导入/添加
- [ ] 历史记录页面：筛选 + 详情展开 + 追问线程
- [ ] 异常处理：统一友好提示
- [ ] 测试：核心模块单元测试
