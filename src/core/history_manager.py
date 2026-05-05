"""答题历史持久化管理，支持回答记录和追问记录的存储、检索与线程聚合。"""

import random
import string
from datetime import datetime
from ..utils.file_utils import FileUtils
from ..utils.log_utils import LogUtils


class HistoryManager:
    """历史管理器：records 列表的增删查 + JSON 文件持久化。

    数据结构：{"records": [{id, type, parent_id, round, timestamp, ...}]}。
    支持两种记录类型：
    - "answer"：用户首次作答记录，包含评分和评估详情
    - "follow_up"：追问记录，通过 parent_id 关联到原始答案
    """

    def __init__(self, storage_path: str = "data/history.json"):
        """初始化历史管理器，从 JSON 文件加载记录。

        Args:
            storage_path: history.json 文件路径
        """
        self.storage_path = storage_path
        self.data = self._load()

    def _load(self) -> dict:
        """加载历史 JSON 文件，若 records 字段缺失则返回空结构。"""
        data = FileUtils.load_json(self.storage_path)
        if "records" not in data:
            return {"records": []}
        return data

    def _save(self) -> None:
        """将 records 列表写回 JSON 文件。"""
        FileUtils.save_json(self.storage_path, self.data)

    @staticmethod
    def _gen_id() -> str:
        """生成唯一记录 ID：格式为 h_YYYYMMDDTHHMMSS_4位随机字符。"""
        ts = datetime.now().strftime("%Y%m%dT%H%M%S")
        rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        return f"h_{ts}_{rand}"

    def add_answer_record(
        self, domain: str, question_id: str, question: str,
        user_input: str, score: int, rating: str,
        evaluation: dict, standard_answer: str, explanation: str,
    ) -> str:
        """添加一条作答记录（type="answer"）。

        Args:
            domain: 所属领域
            question_id: 题目 ID
            question: 问题文本
            user_input: 用户答案
            score: 评分（0-100）
            rating: 等级标签（A/B/C/D）
            evaluation: 子维度评分字典（accuracy, completeness, depth）
            standard_answer: 标准答案
            explanation: LLM 给出的解释

        Returns:
            新生成的记录 ID
        """
        record = {
            "id": self._gen_id(),
            "type": "answer",
            "parent_id": None,
            "round": 1,
            "timestamp": datetime.now().isoformat(),
            "domain": domain,
            "question_id": question_id,
            "question": question,
            "user_input": user_input,
            "score": score,
            "rating": rating,
            "evaluation": {
                "accuracy": evaluation.get("accuracy", 0),
                "completeness": evaluation.get("completeness", 0),
                "depth": evaluation.get("depth", 0),
            },
            "standard_answer": standard_answer,
            "explanation": explanation,
        }
        self.data["records"].append(record)
        self._save()
        LogUtils.info(f"Added answer record {record['id']}")
        return record["id"]

    def add_follow_up_record(
        self, parent_id: str, domain: str, question_id: str,
        question: str, user_input: str, response: str, round_num: int,
    ) -> str:
        """添加一条追问记录（type="follow_up"），通过 parent_id 关联到主回答。

        Args:
            parent_id: 父记录 ID（指向关联的 answer 记录）
            domain: 所属领域
            question_id: 题目 ID
            question: 追问问题文本
            user_input: 用户输入
            response: LLM 的回复
            round_num: 当前对话轮次

        Returns:
            新生成的记录 ID
        """
        record = {
            "id": self._gen_id(),
            "type": "follow_up",
            "parent_id": parent_id,
            "round": round_num,
            "timestamp": datetime.now().isoformat(),
            "domain": domain,
            "question_id": question_id,
            "question": question,
            "user_input": user_input,
            "response": response,
        }
        self.data["records"].append(record)
        self._save()
        return record["id"]

    def get_records(
        self, domain: str = None, min_score: int = None,
        max_score: int = None, keyword: str = None,
    ) -> list[dict]:
        """按条件筛选历史记录，按时间倒序返回。

        Args:
            domain: 可选，按领域筛选
            min_score: 可选，最低分
            max_score: 可选，最高分
            keyword: 可选，在问题和用户输入中搜索关键词

        Returns:
            匹配的记录列表，按 timestamp 降序
        """
        records = self.data["records"]
        if domain:
            records = [r for r in records if r.get("domain") == domain]
        if min_score is not None:
            records = [r for r in records if r.get("score", 0) >= min_score]
        if max_score is not None:
            records = [r for r in records if r.get("score", 100) <= max_score]
        if keyword:
            kw = keyword.lower()
            records = [
                r for r in records
                if kw in r.get("question", "").lower() or kw in r.get("user_input", "").lower()
            ]
        return sorted(records, key=lambda r: r["timestamp"], reverse=True)

    def get_thread(self, record_id: str) -> list[dict]:
        """获取以某条记录为根的完整对话线程（包含自身和所有子追问）。

        Args:
            record_id: 根记录 ID

        Returns:
            按时间升序排列的记录列表
        """
        thread = [
            r for r in self.data["records"]
            if r["id"] == record_id or r.get("parent_id") == record_id
        ]
        return sorted(thread, key=lambda r: r["timestamp"])

    def get_answered_ids(self) -> set[str]:
        """获取所有已作答的题目 ID 集合，用于 _pick_unanswered 逻辑。

        仅统计 type="answer" 的记录，忽略追问记录。
        """
        return {r["question_id"] for r in self.data["records"] if r.get("type") == "answer"}
