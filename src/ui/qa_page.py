"""Home page — Q&A chat interface."""
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
    defaults = {
        "mode": "idle",
        "messages": [],
        "current_question": None,
        "current_record_id": None,
        "current_round": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    return st.session_state


def _build_controller():
    bank, search, llm_client, emb_client, config = init_shared()

    evaluator = Evaluator(llm_client)
    history = HistoryManager(config.get("storage", "storage", "history") or "data/history.json")
    cp = CommandParser(config.load("commands"))

    system_prompt = PromptUtils.load("qa_system")
    agent = QAAgent(llm_client.get_llm(), system_prompt)

    return QAController(cp, bank, search, evaluator, history, agent)


def render():
    st.set_page_config(page_title="Q&A 学习助手", page_icon="📝")
    state = _init_session()

    # Build controller once
    if "controller" not in st.session_state:
        try:
            st.session_state.controller = _build_controller()
        except Exception as e:
            st.error(f"初始化失败: {e}")
            return

    ctrl: QAController = st.session_state.controller

    # Display chat history
    for msg in state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    user_input = st.chat_input("输入命令或回答…（/help 查看帮助）")
    if not user_input:
        return

    # Display user message immediately
    with st.chat_message("human"):
        st.markdown(user_input)

    # Process with streaming
    with st.chat_message("assistant"):
        with st.spinner("AI 思考中…"):
            try:
                result = ctrl.process_input(user_input, state, stream=True)
            except Exception as e:
                LogUtils.error(f"Controller error: {e}")
                result = {"type": "error", "message": "系统内部错误，请稍后重试"}

        if "_stream" in result:
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

    # Save to history for display on next interaction
    state["messages"].append({"role": "human", "content": user_input})
    state["messages"].append({"role": "assistant", "content": response})
