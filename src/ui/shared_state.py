"""Shared state initialization across Streamlit pages."""
import streamlit as st

from ..utils.path_utils import PathUtils
from ..utils.log_utils import LogUtils
from ..config.config_loader import ConfigLoader
from ..models.model_factory import ModelFactory
from ..core.question_bank import QuestionBank
from ..core.search_engine import SearchEngine


def init_shared():
    """Initialize shared bank, search, LLM, embedding, config once per session."""
    if "shared_bank" not in st.session_state:
        PathUtils.set_project_root(".")
        LogUtils.setup()
        config = ConfigLoader()
        factory = ModelFactory(config)
        llm = factory.create_llm()
        emb = factory.create_embedding()

        storage_path = config.get("storage", "storage", "question_bank") or "data/questions.json"
        bank = QuestionBank(storage_path)

        sc = config.load("search").get("search", {})
        search = SearchEngine(
            emb,
            chroma_path=config.get("storage", "storage", "chroma_db") or "data/chroma",
            top_k=sc.get("top_k", 20),
            similarity_threshold=sc.get("similarity_threshold", 0.5),
            dedup_threshold=sc.get("dedup_threshold", 0.9),
        )
        search.sync_from_bank(bank.get_all_questions())

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
