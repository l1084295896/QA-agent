"""历史记录页面 — 筛选、查看详情、显示追问线程（History records page）."""
import streamlit as st

from ..utils.path_utils import PathUtils
from ..utils.log_utils import LogUtils
from ..config.config_loader import ConfigLoader
from ..core.history_manager import HistoryManager


def _get_history():
    """懒加载 HistoryManager 单例，存入 st.session_state 以跨 rerun 复用."""
    if "history_mgr" not in st.session_state:
        PathUtils.set_project_root(".")
        LogUtils.setup()
        config = ConfigLoader()
        st.session_state.history_mgr = HistoryManager(
            config.get("storage", "storage", "history") or "data/history.json")
    return st.session_state.history_mgr


def render():
    """渲染历史记录页面."""
    st.set_page_config(page_title="历史记录", page_icon="📊")
    st.title("📊 历史记录")

    hm: HistoryManager = _get_history()

    # ---- 筛选栏：领域 / 分数段 / 关键词 ----
    col1, col2, col3 = st.columns(3)
    with col1:
        records = hm.get_records()
        domains = sorted(set(r.get("domain", "") for r in records if r.get("type") == "answer"))
        domain_filter = st.selectbox("领域", ["全部"] + domains)
    with col2:
        score_range = st.selectbox("分数段", ["全部", "A级 (90-100)", "B级 (70-89)", "C级 (60-69)", "D级 (0-59)"])
    with col3:
        keyword = st.text_input("关键词搜索")

    # 解析分数段为 min/max
    min_s, max_s = None, None
    if score_range != "全部":
        if "A" in score_range: min_s, max_s = 90, 100
        elif "B" in score_range: min_s, max_s = 70, 89
        elif "C" in score_range: min_s, max_s = 60, 69
        elif "D" in score_range: min_s, max_s = 0, 59

    # 应用筛选条件查询历史记录
    filtered = hm.get_records(
        domain=domain_filter if domain_filter != "全部" else None,
        min_score=min_s, max_score=max_s,
        keyword=keyword if keyword else None,
    )

    # 主列表仅展示 answer 类型的记录
    answer_records = [r for r in filtered if r.get("type") == "answer"]

    if not answer_records:
        st.info("暂无符合条件的记录")
        return

    st.markdown(f"共 {len(answer_records)} 条记录")

    # ---- 逐条渲染记录详情 ----
    for r in answer_records:
        with st.expander(
            f"{r['timestamp'][:16]}  |  {r.get('domain', '')}  |  {r.get('score', '?')}分  |  {r.get('rating', '')}"
        ):
            st.markdown(f"**题目:** {r.get('question', '')}")
            st.markdown(f"**你的回答:** {r.get('user_input', '')}")
            st.markdown(f"**标准答案:** {r.get('standard_answer', '')}")

            ev = r.get("evaluation", {})
            st.markdown(f"**评分:** {r.get('score', '?')}/100 ({r.get('rating', '')})")
            st.markdown(f"- 准确性: {ev.get('accuracy', 'N/A')}")
            st.markdown(f"- 完整性: {ev.get('completeness', 'N/A')}")
            st.markdown(f"- 深度: {ev.get('depth', 'N/A')}")
            st.markdown(f"**解释:** {r.get('explanation', '')}")

            # ---- 追问线程：展示与该题目关联的追问记录 ----
            thread = hm.get_thread(r["id"])
            follow_ups = [t for t in thread if t.get("type") == "follow_up"]
            if follow_ups:
                st.markdown("---")
                st.markdown("**💬 追问记录:**")
                for fu in sorted(follow_ups, key=lambda x: x.get("round", 0)):
                    st.markdown(f"*Q{fu.get('round', '?')}:* {fu.get('user_input', '')}")
                    st.markdown(f"*A{fu.get('round', '?')}:* {fu.get('response', '')}")
