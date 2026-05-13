"""首页 — 问答聊天界面（Home page — Q&A chat interface）."""
import streamlit as st

from ..utils.log_utils import LogUtils
from ..core.evaluator import Evaluator
from ..core.history_manager import HistoryManager
from ..core.command_parser import CommandParser
from ..core.qa_agent import QAAgent
from ..core.qa_controller import QAController
from ..utils.prompt_utils import PromptUtils
from .shared_state import init_shared


def _init_session() -> dict:
    """初始化本页面的 session_state 变量，包括模式、消息列表、当前题目等."""
    defaults = {
        "mode": "idle",              # 当前模式: idle / questioning / following_up
        "messages": [],               # 对话消息历史
        "current_question": None,     # 当前正在回答的题目
        "current_record_id": None,    # 当前答题记录 ID
        "current_round": 0,           # 当前追问轮次
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    return st.session_state


def _build_controller():
    """组装 QAController：获取共享实例，注入各依赖组件，构建双 agent 并返回."""
    # 从 shared_state 获取全局共享的 bank、search、LLM、embedding、config
    bank, search, llm_client, emb_client, config = init_shared()

    evaluator = Evaluator(llm_client)
    history = HistoryManager(config.get("storage", "storage", "history") or "data/history.json")
    cp = CommandParser(config.load("commands"))

    system_prompt = PromptUtils.load("qa_system")
    llm = llm_client.get_llm()

    # 无工具 Agent：用于结构化任务（意图分类、JSON 格式化）
    agent = QAAgent(llm, system_prompt)

    # 带工具 Agent：用于自由对话和追问
    from ..core.agent_tools import create_tools
    agent_tools = QAAgent(llm, system_prompt)
    for func in create_tools(bank, search, history):
        agent_tools.register_tool(func)

    return QAController(cp, bank, search, evaluator, history, agent, agent_tools=agent_tools)


def render():
    """渲染首页问答聊天界面."""
    st.set_page_config(page_title="Q&A 学习助手", page_icon="📝")
    state = _init_session()

    # 只初始化一次 controller，存入 st.session_state 避免重复创建
    if "controller" not in st.session_state:
        try:
            st.session_state.controller = _build_controller()
        except Exception as e:
            import traceback
            st.error(f"初始化失败: {e}")
            with st.expander("错误详情"):
                st.code(traceback.format_exc())
            return

    ctrl: QAController = st.session_state.controller

    # ---- 渲染历史对话消息 ----
    for msg in state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ---- 用户输入框 ----
    user_input = st.chat_input("输入命令或回答…（/help 查看帮助）")
    if not user_input:
        return

    # 立即显示用户消息
    with st.chat_message("human"):
        st.markdown(user_input)

    # ---- 流式处理用户输入 ----
    # ctrl.process_input 返回 dict，若含 _stream 字段则为流式输出
    with st.chat_message("assistant"):
        with st.spinner("AI 思考中…"):
            try:
                result = ctrl.process_input(user_input, state, stream=True)
            except Exception as e:
                LogUtils.error(f"Controller error: {e}")
                result = {"type": "error", "message": "系统内部错误，请稍后重试"}

        # 根据返回类型渲染不同内容
        if "_stream" in result:
            # 流式输出：使用 st.write_stream 逐 token 渲染
            response = st.write_stream(result["_stream"])
        elif result["type"] == "error":
            response = f"❌ {result['message']}"
            st.error(result["message"])
        elif result["type"] == "question":
            response = result["message"]
            st.markdown(response)
        else:
            response = result.get("message", "")
            if response:
                st.markdown(response)

    # 将本轮对话追加到消息历史，供下次渲染时展示
    state["messages"].append({"role": "human", "content": user_input})
    state["messages"].append({"role": "assistant", "content": response})
