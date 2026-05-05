"""题目持久化管理，基于 JSON 文件提供完整的 CRUD 操作，自动生成 q### 格式的 ID。"""

from datetime import datetime
from ..utils.file_utils import FileUtils
from ..utils.log_utils import LogUtils


class QuestionBank:
    """题库管理：增删改查 + JSON 文件持久化。

    数据结构：{"domains": [...], "questions": {domain: {qid: {...}}}, "metadata": {...}}。
    每个题目返回时自动附加 domain 字段，方便上层使用。
    """

    def __init__(self, storage_path: str = "data/questions.json"):
        """初始化题库，从 JSON 文件加载数据。

        Args:
            storage_path: 题目 JSON 文件的存储路径
        """
        self.storage_path = storage_path
        self.data = self._load()

    def _load(self) -> dict:
        """加载 JSON 文件，若文件不存在或格式不合法则返回默认空结构。"""
        data = FileUtils.load_json(self.storage_path)
        if not data or "questions" not in data:
            return {
                "domains": [],
                "questions": {},
                "metadata": {
                    "created_at": datetime.now().isoformat()[:10],
                    "version": "1.0",
                    "question_count": 0,
                    "last_id": 0,
                },
            }
        return data

    def _save(self) -> None:
        """将当前数据写回 JSON 文件。"""
        FileUtils.save_json(self.storage_path, self.data)

    def _next_id(self) -> str:
        """自增 last_id 并生成 q### 格式的新 ID（如 q001, q042）。"""
        self.data["metadata"]["last_id"] += 1
        return f"q{self.data['metadata']['last_id']:03d}"

    def _recount(self) -> None:
        """遍历所有领域重新统计题目总数，更新 metadata.question_count。"""
        total = sum(len(qs) for qs in self.data["questions"].values())
        self.data["metadata"]["question_count"] = total

    # ---- queries ----

    def get_domains(self) -> list[str]:
        """获取所有领域名称列表。"""
        return self.data.get("domains", [])

    def get_question(self, qid: str) -> dict | None:
        """根据 ID 查找题目，返回包含 domain 字段的完整题目信息。

        Args:
            qid: 题目 ID（如 "q001"）

        Returns:
            包含 id, question, answer, domain 等字段的字典；未找到返回 None
        """
        for domain, questions in self.data["questions"].items():
            if qid in questions:
                return {**questions[qid], "domain": domain}
        return None

    def get_questions_by_domain(self, domain: str) -> list[dict]:
        """获取指定领域下的所有题目列表。

        Args:
            domain: 领域名称

        Returns:
            题目字典列表，每个题目自动附加 domain 字段
        """
        if domain not in self.data["questions"]:
            return []
        return [{**q, "domain": domain} for q in self.data["questions"][domain].values()]

    def get_all_questions(self) -> list[dict]:
        """获取题库中所有题目，每个题目附带其所属领域。"""
        result = []
        for domain, qs in self.data["questions"].items():
            for q in qs.values():
                result.append({**q, "domain": domain})
        return result

    # ---- mutations ----

    def add_domain(self, domain: str) -> None:
        """添加领域（幂等：已存在则跳过）。

        Args:
            domain: 领域名称
        """
        if domain not in self.data["domains"]:
            self.data["domains"].append(domain)
        if domain not in self.data["questions"]:
            self.data["questions"][domain] = {}

    def add_question(self, domain: str, question: str, answer: str) -> str:
        """添加新题目：自动创建领域、分配 ID、保存并返回新 ID。

        Args:
            domain: 所属领域
            question: 问题文本
            answer: 标准答案

        Returns:
            新生成的题目 ID（如 "q007"）
        """
        self.add_domain(domain)
        qid = self._next_id()
        now = datetime.now().isoformat()
        self.data["questions"][domain][qid] = {
            "id": qid,
            "question": question,
            "answer": answer,
            "created_at": now,
            "updated_at": now,
        }
        self._recount()
        self._save()
        LogUtils.info(f"Added question {qid} to domain '{domain}'")
        return qid

    def update_question(self, qid: str, question: str = None, answer: str = None, domain: str = None) -> None:
        """更新题目：支持修改问题、答案和领域（可跨领域迁移）。

        Args:
            qid: 题目 ID
            question: 新问题文本（None 表示不修改）
            answer: 新答案文本（None 表示不修改）
            domain: 新领域（None 表示不修改）

        Raises:
            ValueError: 题目 ID 不存在
        """
        existing = self.get_question(qid)
        if not existing:
            raise ValueError(f"Question {qid} not found")

        old_domain = existing["domain"]
        new_domain = domain or old_domain

        # 跨领域迁移：从旧领域删除，在新领域插入
        if new_domain != old_domain:
            del self.data["questions"][old_domain][qid]
            self.add_domain(new_domain)
            self.data["questions"][new_domain][qid] = existing

        target = self.data["questions"][new_domain][qid]
        if question is not None:
            target["question"] = question
        if answer is not None:
            target["answer"] = answer
        target["updated_at"] = datetime.now().isoformat()
        self._save()
        LogUtils.info(f"Updated question {qid}")

    def delete_question(self, qid: str) -> None:
        """删除题目及其在索引中的记录。

        Args:
            qid: 题目 ID

        Raises:
            ValueError: 题目 ID 不存在
        """
        existing = self.get_question(qid)
        if not existing:
            raise ValueError(f"Question {qid} not found")
        domain = existing["domain"]
        del self.data["questions"][domain][qid]
        self._recount()
        self._save()
        LogUtils.info(f"Deleted question {qid}")

    def get_question_count(self) -> int:
        """返回题库当前题目总数。"""
        return self.data["metadata"].get("question_count", 0)
