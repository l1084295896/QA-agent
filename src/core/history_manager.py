import random
import string
from datetime import datetime
from ..utils.file_utils import FileUtils
from ..utils.log_utils import LogUtils


class HistoryManager:
    """CRUD for history.json. Supports threaded follow-up records."""

    def __init__(self, storage_path: str = "data/history.json"):
        self.storage_path = storage_path
        self.data = self._load()

    def _load(self) -> dict:
        data = FileUtils.load_json(self.storage_path)
        if "records" not in data:
            return {"records": []}
        return data

    def _save(self) -> None:
        FileUtils.save_json(self.storage_path, self.data)

    @staticmethod
    def _gen_id() -> str:
        ts = datetime.now().strftime("%Y%m%dT%H%M%S")
        rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        return f"h_{ts}_{rand}"

    def add_answer_record(
        self, domain: str, question_id: str, question: str,
        user_input: str, score: int, rating: str,
        evaluation: dict, standard_answer: str, explanation: str,
    ) -> str:
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
        thread = [
            r for r in self.data["records"]
            if r["id"] == record_id or r.get("parent_id") == record_id
        ]
        return sorted(thread, key=lambda r: r["timestamp"])

    def get_answered_ids(self) -> set[str]:
        return {r["question_id"] for r in self.data["records"] if r.get("type") == "answer"}
