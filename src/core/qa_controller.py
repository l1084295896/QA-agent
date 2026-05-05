import json
import random
import re

from ..utils.log_utils import LogUtils
from ..utils.file_utils import FileUtils
from ..utils.prompt_utils import PromptUtils
from .command_parser import CommandParser
from .question_bank import QuestionBank
from .search_engine import SearchEngine
from .evaluator import Evaluator
from .history_manager import HistoryManager
from .qa_agent import QAAgent


class QAController:
    """Routes all user input: commands → direct handlers; free text → Agent/mode handlers."""

    def __init__(
        self, command_parser: CommandParser, question_bank: QuestionBank,
        search_engine: SearchEngine, evaluator: Evaluator,
        history_manager: HistoryManager, qa_agent: QAAgent,
    ):
        self.cp = command_parser
        self.bank = question_bank
        self.search = search_engine
        self.evaluator = evaluator
        self.history = history_manager
        self.agent = qa_agent

    def process_input(self, text: str, state: dict) -> dict:
        cmd_name, params = self.cp.parse(text)
        try:
            if cmd_name:
                return self._dispatch(cmd_name, params, state)
            return self._free_text(text, state)
        except Exception:
            import traceback
            LogUtils.error(f"Controller error:\n{traceback.format_exc()}")
            return {"type": "error", "message": "系统内部错误，请稍后重试"}

    # ---- command dispatch ----

    def _dispatch(self, cmd: str, params: dict, state: dict) -> dict:
        handlers = {
            "qa": self._qa, "list_domains": self._list_domains,
            "list_questions": self._list_questions, "add_file": self._add_file,
            "add_interactive": self._add_interactive, "edit": self._edit,
            "delete": self._delete, "help": self._help, "exit": self._exit,
        }
        h = handlers.get(cmd)
        if h:
            return h(params, state)
        return {"type": "error", "message": f"未知命令: /{cmd}"}

    def _qa(self, p: dict, state: dict) -> dict:
        mode = p.get("mode")
        target = p.get("target")
        n = p.get("random_count")

        if mode == "ask_intent":
            msg = self.agent.invoke("用户想开始问答，请询问他想练习哪个领域或搜索什么关键词。")
            return {"type": "message", "message": msg}

        domains = self.bank.get_domains()

        # domain match
        if target and target in domains:
            qs = self.bank.get_questions_by_domain(target)
            if not qs:
                return {"type": "error", "message": f"领域 '{target}' 暂无题目"}
            if n:
                selected = random.sample(qs, min(n, len(qs)))
                prefix = f"🎲 从 '{target}' 随机抽题"
            else:
                q = self._pick_unanswered(qs)
                selected = [q]
                prefix = f"📝 领域: {target}"
        elif target:
            # semantic search
            results = self.search.search(target)
            if not results:
                return {"type": "error", "message": f"未找到与 '{target}' 相关的题目"}
            pool = results[:self.search.top_k]
            if n:
                ids = random.sample([r["id"] for r in pool], min(n, len(pool)))
            else:
                ids = [pool[0]["id"]]
            selected = [self.bank.get_question(qid) for qid in ids]
            prefix = f"🔍 搜索 '{target}'"
        else:
            # random from all
            all_qs = self.bank.get_all_questions()
            if not all_qs:
                return {"type": "error", "message": "题库暂无题目，请先通过 /add_file 或 /add_interactive 添加"}
            selected = random.sample(all_qs, min(n or 1, len(all_qs)))
            prefix = "🎲 随机选题"

        q = selected[0]
        if q is None:
            return {"type": "error", "message": "选题异常，题目数据不完整，请检查题库一致性"}
        state["mode"] = "answering"
        state["current_question"] = q
        state["current_round"] = 1
        return {
            "type": "question",
            "question": q,
            "message": f"{prefix}:\n\n📝 **题目** (领域: {q['domain']}, ID: {q['id']}):\n\n{q['question']}\n\n请在此输入你的回答…",
        }

    def _list_domains(self, p: dict, state: dict) -> dict:
        ds = self.bank.get_domains()
        if not ds:
            return {"type": "message", "message": "暂无领域，请先添加题目"}
        lines = ["📁 **已有领域:**"]
        for d in ds:
            n = len(self.bank.get_questions_by_domain(d))
            lines.append(f"  - {d} ({n} 题)")
        return {"type": "message", "message": "\n".join(lines)}

    def _list_questions(self, p: dict, state: dict) -> dict:
        domain = p.get("domain")
        if not domain:
            return {"type": "error", "message": "用法: /list_questions <领域名>"}
        qs = self.bank.get_questions_by_domain(domain)
        if not qs:
            return {"type": "message", "message": f"领域 '{domain}' 暂无题目"}
        lines = [f"📁 **{domain}** ({len(qs)} 题):"]
        for q in qs:
            lines.append(f"  - {q['id']}: {q['question'][:60]}")
        return {"type": "message", "message": "\n".join(lines)}

    def _add_file(self, p: dict, state: dict) -> dict:
        path = p.get("file_path")
        if not path:
            return {"type": "error", "message": "用法: /add_file <文件路径>"}
        if not FileUtils.file_exists(path):
            return {"type": "error", "message": f"文件不存在: {path}"}

        content = FileUtils.read_text(path)
        parsed = self._parse_md(content)
        if not parsed:
            return {"type": "error", "message": "未能从文件中解析出题目，请检查格式（## 领域 + 问题: + 答案: + --- 分隔）"}

        dupes = []
        for item in parsed:
            d = self.search.check_duplicate(item["question"])
            if d:
                dupes.append((item, d))

        state["mode"] = "confirm_add"
        state["pending_add"] = parsed
        lines = [f"📄 解析到 {len(parsed)} 道题目:"]
        for item in parsed:
            lines.append(f"  - [{item['domain']}] {item['question'][:50]}")
        if dupes:
            lines.append(f"\n⚠ 检测到 {len(dupes)} 道相似题目")
        lines.append("\n输入 **确认** 导入全部，**取消** 放弃")
        return {"type": "message", "message": "\n".join(lines)}

    def _add_interactive(self, p: dict, state: dict) -> dict:
        state["mode"] = "adding_question"
        state["pending_add"] = None
        return {"type": "message", "message": "📝 请描述你想添加的题目（问题和答案），我会整理成标准格式"}

    def _edit(self, p: dict, state: dict) -> dict:
        qid = p.get("question_id")
        if not qid:
            return {"type": "error", "message": "用法: /edit <题目ID>"}
        q = self.bank.get_question(qid)
        if not q:
            return {"type": "error", "message": f"题目 {qid} 不存在"}
        state["mode"] = "editing"
        state["edit_target"] = qid
        return {"type": "message", "message": f"📝 编辑 {qid}:\n\n领域: {q['domain']}\n问题: {q['question']}\n答案: {q['answer']}\n\n请发送修改后的内容（格式: 领域: xxx, 问题: xxx, 答案: xxx）或 /exit 取消"}

    def _delete(self, p: dict, state: dict) -> dict:
        qid = p.get("question_id")
        if not qid:
            return {"type": "error", "message": "用法: /delete <题目ID>"}
        q = self.bank.get_question(qid)
        if not q:
            return {"type": "error", "message": f"题目 {qid} 不存在"}
        state["mode"] = "confirm_delete"
        state["delete_target"] = qid
        return {"type": "message", "message": f"⚠ 确认删除 {qid}?\n领域: {q['domain']}\n问题: {q['question']}\n\n输入 **确认** 删除，**取消** 放弃"}

    def _help(self, p: dict, state: dict) -> dict:
        cmds = self.cp.get_command_list()
        lines = ["📖 **可用命令:**\n"]
        for c in cmds:
            lines.append(f"**{c['trigger']}** — {c['description']}")
            if c.get("usage"):
                lines.append(f"  `{c['usage']}`")
        return {"type": "message", "message": "\n".join(lines)}

    def _exit(self, p: dict, state: dict) -> dict:
        for k in ("mode", "current_question", "current_record_id", "current_round",
                   "pending_add", "edit_target", "delete_target"):
            state.pop(k, None)
        state["mode"] = "idle"
        state["current_round"] = 0
        return {"type": "message", "message": "已退出当前模式，输入 /Q 开始新的问答"}

    # ---- free-text handlers ----

    def _free_text(self, text: str, state: dict) -> dict:
        mode = state.get("mode", "idle")
        if mode == "answering":
            return self._evaluate(text, state)
        elif mode == "follow_up":
            return self._follow_up(text, state)
        elif mode == "confirm_add":
            return self._confirm_add(text, state)
        elif mode == "adding_question":
            return self._handle_adding(text, state)
        elif mode == "confirm_delete":
            return self._confirm_delete(text, state)
        elif mode == "editing":
            return self._handle_editing(text, state)
        else:
            msg = self.agent.invoke(text)
            return {"type": "message", "message": msg}

    def _evaluate(self, user_answer: str, state: dict) -> dict:
        q = state.get("current_question")
        if not q:
            state["mode"] = "idle"
            return {"type": "error", "message": "没有当前题目，请用 /Q 开始"}

        try:
            result = self.evaluator.evaluate(q["answer"], user_answer)
        except Exception as e:
            LogUtils.error(f"Evaluation error: {e}")
            return {"type": "error", "message": "评分服务暂时不可用，请稍后重试"}

        rid = self.history.add_answer_record(
            domain=q["domain"], question_id=q["id"], question=q["question"],
            user_input=user_answer, score=result["score"], rating=result["rating"],
            evaluation={
                "accuracy": result.get("accuracy", 0),
                "completeness": result.get("completeness", 0),
                "depth": result.get("depth", 0),
            },
            standard_answer=q["answer"],
            explanation=result.get("explanation", ""),
        )
        state["mode"] = "follow_up"
        state["current_record_id"] = rid
        state["current_round"] = 1

        msg = (
            f"📊 **评分: {result['score']}/100 ({result['rating']})**\n\n"
            f"- 准确性: {result.get('accuracy', 'N/A')}\n"
            f"- 完整性: {result.get('completeness', 'N/A')}\n"
            f"- 深度: {result.get('depth', 'N/A')}\n\n"
            f"📖 **标准答案:**\n{q['answer']}\n\n"
            f"💡 **解释:**\n{result.get('explanation', '')}\n\n"
            f"有疑问可继续追问，/exit 退出，/Q 开始新题"
        )
        return {"type": "message", "message": msg}

    def _follow_up(self, text: str, state: dict) -> dict:
        q = state.get("current_question", {})
        prompt = PromptUtils.load(
            "follow_up",
            question=q.get("question", ""),
            standard_answer=q.get("answer", ""),
            follow_up_question=text,
        )
        response = self.agent.invoke(prompt)
        self.history.add_follow_up_record(
            parent_id=state.get("current_record_id", ""),
            domain=q.get("domain", ""), question_id=q.get("id", ""),
            question=text, user_input=text, response=response,
            round_num=state.get("current_round", 1) + 1,
        )
        state["current_round"] = state.get("current_round", 1) + 1
        return {"type": "message", "message": response}

    def _confirm_add(self, text: str, state: dict) -> dict:
        t = text.strip().lower()
        if t in ("确认", "yes", "y"):
            items = state.get("pending_add", [])
            for item in items:
                qid = self.bank.add_question(item["domain"], item["question"], item["answer"])
                self.search.add_to_index(qid, item["question"], item["domain"])
            state["mode"] = "idle"
            state["pending_add"] = None
            return {"type": "message", "message": f"✅ 已导入 {len(items)} 道题目"}
        elif t in ("取消", "cancel", "no", "n"):
            state["mode"] = "idle"
            state["pending_add"] = None
            return {"type": "message", "message": "已取消导入"}
        return {"type": "message", "message": "请输入 **确认** 或 **取消**"}

    def _handle_adding(self, text: str, state: dict) -> dict:
        t = text.strip().lower()
        if t in ("取消", "cancel"):
            state["mode"] = "idle"
            return {"type": "message", "message": "已取消"}
        if t in ("确认", "yes", "y"):
            pending = state.get("pending_add")
            if pending:
                item = pending[0] if isinstance(pending, list) else pending
                dup = self.search.check_duplicate(item["question"])
                if dup:
                    return {"type": "message", "message": f"⚠ 检测到相似题目 {dup['id']}（相似度 {dup['similarity']:.0%}），仍要添加请输入 **强制确认**"}
                qid = self.bank.add_question(item["domain"], item["question"], item["answer"])
                self.search.add_to_index(qid, item["question"], item["domain"])
                state["mode"] = "idle"
                state["pending_add"] = None
                return {"type": "message", "message": f"✅ 已添加题目 {qid}"}
            return {"type": "message", "message": "没有待添加的题目"}
        if t in ("强制确认",):
            pending = state.get("pending_add")
            if pending:
                item = pending[0] if isinstance(pending, list) else pending
                qid = self.bank.add_question(item["domain"], item["question"], item["answer"])
                self.search.add_to_index(qid, item["question"], item["domain"])
                state["mode"] = "idle"
                state["pending_add"] = None
                return {"type": "message", "message": f"✅ 已强制添加题目 {qid}"}

        # User described a question → LLM formats it
        domains = ", ".join(self.bank.get_domains()) or "无"
        prompt = PromptUtils.load("add_question", existing_domains=domains)
        response = self.agent.invoke(f"{prompt}\n\n用户输入: {text}")
        item = self._parse_json_response(response)
        state["pending_add"] = [item]
        return {"type": "message", "message": f"模型整理结果:\n\n领域: {item.get('domain')}\n问题: {item.get('question')}\n答案: {item.get('answer')}\n\n输入 **确认** 添加，**取消** 放弃"}

    def _confirm_delete(self, text: str, state: dict) -> dict:
        t = text.strip().lower()
        if t in ("确认", "yes", "y"):
            qid = state.get("delete_target")
            self.search.remove_from_index(qid)
            self.bank.delete_question(qid)
            state["mode"] = "idle"
            state["delete_target"] = None
            return {"type": "message", "message": f"✅ 已删除 {qid}"}
        elif t in ("取消", "cancel", "no", "n"):
            state["mode"] = "idle"
            state["delete_target"] = None
            return {"type": "message", "message": "已取消删除"}
        return {"type": "message", "message": "请输入 **确认** 或 **取消**"}

    def _handle_editing(self, text: str, state: dict) -> dict:
        t = text.strip().lower()
        if t in ("取消", "cancel"):
            state["mode"] = "idle"
            return {"type": "message", "message": "已取消编辑"}
        qid = state.get("edit_target")
        try:
            item = self._parse_edit_input(text)
        except Exception:
            return {"type": "error", "message": "格式错误，请使用：领域: xxx, 问题: xxx, 答案: xxx"}

        old = self.bank.get_question(qid)
        self.bank.update_question(
            qid,
            question=item.get("question"),
            answer=item.get("answer"),
            domain=item.get("domain"),
        )
        updated = self.bank.get_question(qid)
        self.search.update_index(qid, updated["question"], updated["domain"])
        state["mode"] = "idle"
        state["edit_target"] = None
        return {"type": "message", "message": f"✅ 已更新 {qid}"}

    # ---- helpers ----

    def _pick_unanswered(self, qs: list[dict]) -> dict:
        """Pick an unanswered question from the domain, or the least-recently-answered."""
        answered_ids = self.history.get_answered_ids()
        unanswered = [q for q in qs if q["id"] not in answered_ids]
        if unanswered:
            if len(unanswered) > 1:
                return random.choice(unanswered)
            return unanswered[0]
        return qs[0]

    @staticmethod
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
                questions.append({
                    "domain": current_domain,
                    "question": qm.group(1).strip(),
                    "answer": am.group(1).strip(),
                })
        return questions

    @staticmethod
    def _parse_json_response(response: str) -> dict:
        m = re.search(r'\{[\s\S]*\}', response)
        if m:
            return json.loads(m.group())
        return {"domain": "默认", "question": response, "answer": ""}

    @staticmethod
    def _parse_edit_input(text: str) -> dict:
        result = {}
        for part in re.split(r'[,，]\s*', text):
            for key in ("领域", "问题", "答案"):
                m = re.match(rf'{key}[:：]\s*(.+)', part.strip())
                if m:
                    result["domain" if key == "领域" else "question" if key == "问题" else "answer"] = m.group(1).strip()
        return result
