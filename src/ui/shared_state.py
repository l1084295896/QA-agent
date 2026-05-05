"""跨 Streamlit 页面共享状态初始化 — 确保 bank/search/LLM/embedding/config 只创建一次."""
import streamlit as st

from ..utils.path_utils import PathUtils
from ..utils.log_utils import LogUtils
from ..config.config_loader import ConfigLoader
from ..models.model_factory import ModelFactory
from ..core.question_bank import QuestionBank
from ..core.search_engine import SearchEngine


def init_shared():
    """初始化全局共享实例（bank, search, LLM, embedding, config），每个 session 仅执行一次.

    使用 st.session_state 作为单例容器：首次调用时创建所有组件并存入 session_state，
    后续调用直接返回已缓存的实例，避免重复初始化带来的开销和不一致.
    """
    if "shared_bank" not in st.session_state:
        # ---- 基础初始化：路径、日志、配置 ----
        PathUtils.set_project_root(".")
        LogUtils.setup()
        config = ConfigLoader()

        # ---- 模型工厂：创建 LLM 和 Embedding 实例 ----
        factory = ModelFactory(config)
        llm = factory.create_llm()
        emb = factory.create_embedding()

        # ---- 题库：从 JSON 文件加载 ----
        storage_path = config.get("storage", "storage", "question_bank") or "data/questions.json"
        bank = QuestionBank(storage_path)

        # ---- 检索引擎：基于 Chroma 向量数据库 + Embedding ----
        sc = config.load("search").get("search", {})
        search = SearchEngine(
            emb,
            chroma_path=config.get("storage", "storage", "chroma_db") or "data/chroma",
            top_k=sc.get("top_k", 20),
            similarity_threshold=sc.get("similarity_threshold", 0.5),
            dedup_threshold=sc.get("dedup_threshold", 0.9),
        )
        # 将题库中的现有题目同步到向量索引
        search.sync_from_bank(bank.get_all_questions())

        # ---- 存入 st.session_state 作为全局共享单例 ----
        st.session_state.shared_bank = bank
        st.session_state.shared_search = search
        st.session_state.shared_llm = llm
        st.session_state.shared_emb = emb
        st.session_state.shared_config = config

    return (
        st.session_state.shared_bank,
        st.session_state.shared_search,
        st.session_state.shared_llm,
        st.session_state.shared_emb,
        st.session_state.shared_config,
    )
