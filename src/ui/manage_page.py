"""Question bank management page — view, import, add, edit, delete."""
import streamlit as st

from ..utils.file_utils import FileUtils
from ..utils.prompt_utils import PromptUtils
from ..core.qa_agent import QAAgent
from .shared_state import init_shared
import json
import re
import time


def _get_bank_search_llm():
    bank, search, llm, _, _ = init_shared()
    return bank, search, llm


def _parse_md(content: str) -> list[dict]:
    questions = []
    current_domain = "默认"
    for block in re.split(r'\n---+\n', content):
        block = block.strip()
        if not block:
            continue
        dm = re.match(r'^##\s+(.+)', block)
        if dm:
            current_domain = dm.group(1).strip()
            continue
        qm = re.search(r'问题[:：]\s*(.+)', block)
        am = re.search(r'答案[:：]\s*(.+)', block)
        if qm and am:
            questions.append({"domain": current_domain, "question": qm.group(1).strip(), "answer": am.group(1).strip()})
    return questions


def render():
    st.set_page_config(page_title="题库管理", page_icon="📚")
    st.title("📚 题库管理")

    bank, search, llm = _get_bank_search_llm()

    tab1, tab2, tab3 = st.tabs(["查看题库", "文件导入", "对话添加"])

    # ---- Tab 1: View/Edit/Delete ----
    with tab1:
        domains = bank.get_domains()
        if not domains:
            st.info("暂无题目，请通过文件导入或对话添加")
        for domain in domains:
            qs = bank.get_questions_by_domain(domain)
            with st.expander(f"📁 {domain} ({len(qs)} 题)", expanded=False):
                for q in qs:
                    col1, col2, col3 = st.columns([6, 1, 1])
                    with col1:
                        st.markdown(f"**{q['id']}**: {q['question'][:80]}")
                    with col2:
                        if st.button("✏️ 编辑", key=f"edit_btn_{q['id']}"):
                            st.session_state[f"edit_{q['id']}"] = True
                    with col3:
                        if st.button("🗑 删除", key=f"del_btn_{q['id']}"):
                            search.remove_from_index(q["id"])
                            bank.delete_question(q["id"])
                            st.rerun()

                    if st.session_state.get(f"edit_{q['id']}"):
                        with st.form(f"edit_form_{q['id']}"):
                            new_domain = st.text_input("领域", value=q["domain"])
                            new_q = st.text_area("问题", value=q["question"])
                            new_a = st.text_area("答案", value=q["answer"])
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.form_submit_button("💾 保存"):
                                    bank.update_question(q["id"], question=new_q, answer=new_a, domain=new_domain)
                                    updated = bank.get_question(q["id"])
                                    search.update_index(q["id"], updated["question"], updated["domain"])
                                    st.session_state[f"edit_{q['id']}"] = False
                                    st.rerun()
                            with c2:
                                if st.form_submit_button("取消"):
                                    st.session_state[f"edit_{q['id']}"] = False
                                    st.rerun()

    # ---- Tab 2: File Import ----
    with tab2:
        uploaded = st.file_uploader("上传题目文件 (.md, .txt)", type=["md", "txt"])
        if uploaded:
            content = uploaded.read().decode("utf-8")
            parsed = _parse_md(content)
            if not parsed:
                st.error("未能解析出题目，请检查格式")
            else:
                st.success(f"解析到 {len(parsed)} 道题目")
                st.markdown("### 预览")
                for item in parsed:
                    st.markdown(f"- **[{item['domain']}]** {item['question'][:60]}")
                if st.button("✅ 确认导入", key="confirm_file_import"):
                    for item in parsed:
                        dup = search.check_duplicate(item["question"])
                        if dup:
                            st.warning(f"跳过重复: {item['question'][:40]} (相似于 {dup['id']})")
                            continue
                        qid = bank.add_question(item["domain"], item["question"], item["answer"])
                        search.add_to_index(qid, item["question"], item["domain"])
                    st.success("导入完成")
                    st.rerun()

    # ---- Tab 3: Interactive Add ----
    with tab3:
        st.markdown("描述你想添加的题目，模型会自动整理格式")
        desc = st.text_area("题目描述", placeholder="例如：在Python基础领域，添加一道关于装饰器的题目，答案是…")
        if st.button("🤖 提交给模型整理"):
            if desc.strip():
                domains_str = ", ".join(bank.get_domains()) or "无"
                prompt = PromptUtils.load("add_question", existing_domains=domains_str)
                agent = QAAgent(llm.get_llm(), prompt)
                response = agent.invoke(f"{prompt}\n\n用户输入: {desc}")
                m = re.search(r'\{[\s\S]*\}', response)
                if m:
                    item = json.loads(m.group())
                else:
                    item = {"domain": "默认", "question": response, "answer": ""}
                st.session_state["pending_item"] = item
                st.markdown("### 模型整理预览")
                st.markdown(f"**领域:** {item.get('domain')}")
                st.markdown(f"**问题:** {item.get('question')}")
                st.markdown(f"**答案:** {item.get('answer')}")

                dup = search.check_duplicate(item["question"])
                if dup:
                    st.warning(f"⚠ 检测到相似题目 {dup['id']}（相似度 {dup['similarity']:.0%}）")

        if st.session_state.get("pending_item"):
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ 确认添加"):
                    item = st.session_state["pending_item"]
                    qid = bank.add_question(item["domain"], item["question"], item["answer"])
                    search.add_to_index(qid, item["question"], item["domain"])
                    st.session_state["pending_item"] = None
                    st.success(f"已添加 {qid}")
                    st.rerun()
            with c2:
                if st.button("取消"):
                    st.session_state["pending_item"] = None
                    st.rerun()
