"""题库管理页面 — 查看、导入、添加、编辑、删除题目（Question bank management page）."""
import streamlit as st

from ..utils.file_utils import FileUtils
from ..utils.prompt_utils import PromptUtils
from ..core.qa_agent import QAAgent
from .shared_state import init_shared
import json
import re
import time


def _get_bank_search_llm():
    """从 shared_state 获取题库、检索引擎、LLM 客户端三个共享实例."""
    bank, search, llm, _, _ = init_shared()
    return bank, search, llm


def _parse_md(content: str) -> list[dict]:
    """解析 Markdown 题目文件，按 --- 分块，提取领域(##标题)、问题和答案."""
    questions = []
    current_domain = "默认"
    # 以 --- 分隔符将文件切分为题目块
    for block in re.split(r'\n---+\n', content):
        block = block.strip()
        if not block:
            continue
        # 检测 ## 标题作为领域名
        dm = re.match(r'^##\s+(.+)', block)
        if dm:
            current_domain = dm.group(1).strip()
            continue
        # 提取问题和答案行
        qm = re.search(r'问题[:：]\s*(.+)', block)
        am = re.search(r'答案[:：]\s*(.+)', block)
        if qm and am:
            questions.append({"domain": current_domain, "question": qm.group(1).strip(), "answer": am.group(1).strip()})
    return questions


def render():
    """渲染题库管理页面，包含三个子页签."""
    st.set_page_config(page_title="题库管理", page_icon="📚")
    st.title("📚 题库管理")

    # 获取共享实例
    bank, search, llm = _get_bank_search_llm()

    tab1, tab2, tab3 = st.tabs(["查看题库", "文件导入", "对话添加"])

    # ================================================================
    # Tab 1: 查看/编辑/删除题目
    # ================================================================
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
                        # 编辑按钮：设置 st.session_state 标志，展开编辑表单
                        if st.button("✏️ 编辑", key=f"edit_btn_{q['id']}"):
                            st.session_state[f"edit_{q['id']}"] = True
                    with col3:
                        # 删除按钮：同时从搜索引擎索引和题库中移除
                        if st.button("🗑 删除", key=f"del_btn_{q['id']}"):
                            search.remove_from_index(q["id"])
                            bank.delete_question(q["id"])
                            st.rerun()

                    # 编辑表单：通过 st.session_state[f"edit_{q['id']}"] 控制显隐
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

    # ================================================================
    # Tab 2: 文件批量导入
    # ================================================================
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
                        # 重复检测：利用搜索引擎的语义相似度
                        dup = search.check_duplicate(item["question"])
                        if dup:
                            st.warning(f"跳过重复: {item['question'][:40]} (相似于 {dup['id']})")
                            continue
                        qid = bank.add_question(item["domain"], item["question"], item["answer"])
                        search.add_to_index(qid, item["question"], item["domain"])
                    st.success("导入完成")
                    st.rerun()

    # ================================================================
    # Tab 3: 通过自然语言描述让模型自动整理并添加题目
    # ================================================================
    with tab3:
        st.markdown("描述你想添加的题目，模型会自动整理格式")
        desc = st.text_area("题目描述", placeholder="例如：在Python基础领域，添加一道关于装饰器的题目，答案是…")
        if st.button("🤖 提交给模型整理"):
            if desc.strip():
                domains_str = ", ".join(bank.get_domains()) or "无"
                prompt = PromptUtils.load("add_question", existing_domains=domains_str)
                agent = QAAgent(llm.get_llm(), prompt)
                # 调用 LLM 从自然语言描述中提取结构化题目
                response = agent.invoke(f"{prompt}\n\n用户输入: {desc}")
                m = re.search(r'\{[\s\S]*\}', response)
                if m:
                    item = json.loads(m.group())
                else:
                    item = {"domain": "默认", "question": response, "answer": ""}
                # 暂存到 st.session_state，等待用户确认
                st.session_state["pending_item"] = item
                st.markdown("### 模型整理预览")
                st.markdown(f"**领域:** {item.get('domain')}")
                st.markdown(f"**问题:** {item.get('question')}")
                st.markdown(f"**答案:** {item.get('answer')}")

                dup = search.check_duplicate(item["question"])
                if dup:
                    st.warning(f"⚠ 检测到相似题目 {dup['id']}（相似度 {dup['similarity']:.0%}）")

        # 确认/取消按钮：仅当有暂存题目时显示
        if st.session_state.get("pending_item"):
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ 确认添加"):
                    item = st.session_state["pending_item"]
                    qid = bank.add_question(item["domain"], item["question"], item["answer"])
                    search.add_to_index(qid, item["question"], item["domain"])
                    # 清空暂存
                    st.session_state["pending_item"] = None
                    st.success(f"已添加 {qid}")
                    st.rerun()
            with c2:
                if st.button("取消"):
                    st.session_state["pending_item"] = None
                    st.rerun()
