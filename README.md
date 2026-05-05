# Q&A Agent

基于 LangChain Agent 的智能问答评分系统，使用 CLI 命令驱动，Streamlit Web 界面。

## 快速开始

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置 API Key：
```bash
cp .env.example .env
# 编辑 .env，填入你的 DASHSCOPE_API_KEY
```

3. 运行：
```bash
streamlit run main.py
```

## 命令列表

| 命令 | 说明 |
|------|------|
| `/Q` | 开始问答 |
| `/Q <领域>` | 从领域出题 |
| `/Q <领域> random N` | 随机 N 题 |
| `/Q <关键词>` | 语义搜索 |
| `/list_domains` | 列出领域 |
| `/list_questions <领域>` | 列出题目 |
| `/add_file <路径>` | 文件导入 |
| `/add_interactive` | 对话添加 |
| `/edit <ID>` | 编辑题目 |
| `/delete <ID>` | 删除题目 |
| `/help` | 帮助 |
| `/exit` | 退出模式 |

## 项目结构

```
qa-agent/
├── config/           # YAML 配置 + 提示词模板
├── data/             # 题库 + 历史 + 向量库
├── src/              # 源代码
│   ├── config/       # 配置加载
│   ├── models/       # 模型工厂
│   ├── utils/        # 工具函数
│   ├── core/         # 核心业务
│   └── ui/           # Streamlit 渲染
├── pages/            # Streamlit 多页面
└── main.py           # 入口
```
