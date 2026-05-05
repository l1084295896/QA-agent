"""Home page — Q&A chat interface."""
import streamlit as st

from ..utils.log_utils import LogUtils
from ..utils.path_utils import PathUtils
from ..config.config_loader import ConfigLoader
from ..models.model_factory import ModelFactory
from ..core.question_bank import QuestionBank
from ..core.search_engine import SearchEngine
from ..core.evaluator import Evaluator
from ..core.history_manager import HistoryManager
from ..core.command_parser import CommandParser
from ..core.qa_agent import QAAgent
from ..core.qa_controller import QAController
from ..utils.prompt_utils import PromptUtils


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
    PathUtils.set_project_root(".")
    LogUtils.setup()

    config = ConfigLoader()
    factory = ModelFactory(config)
    llm_client = factory.create_llm()
    emb_client = factory.create_embedding()

    bank = QuestionBank(config.get("storage", "storage", "question_bank") or "data/questions.json")
    search_cfg = config.load("search").get("search", {})

    search = SearchEngine(
        emb_client,
        chroma_path=config.get("storage", "storage", "chroma_db") or "data/chroma",
        top_k=search_cfg.get("top_k", 20),
        similarity_threshold=search_cfg.get("similarity_threshold", 0.5),
        dedup_threshold=search_cfg.get("dedup_threshold", 0.9),
    )
    # Sync Chroma on startup
    all_qs = bank.get_all_questions()
    search.sync_from_bank(all_qs)

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

    # Add user message
    state["messages"].append({"role": "human", "content": user_input})

    # Process
    try:
        result = ctrl.process_input(user_input, state)
    except Exception as e:
        LogUtils.error(f"Controller error: {e}")
        result = {"type": "error", "message": "系统内部错误，请稍后重试"}

    # Format response
    if result["type"] == "error":
        content = f"❌ {result['message']}"
    elif result["type"] == "question":
        content = result["message"]
    else:
        content = result["message"]

    state["messages"].append({"role": "assistant", "content": content})
    st.rerun()
