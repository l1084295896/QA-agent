from datetime import datetime
from ..utils.file_utils import FileUtils
from ..utils.log_utils import LogUtils


class QuestionBank:
    """Full CRUD for questions stored in JSON. Auto-generates q### IDs."""

    def __init__(self, storage_path: str = "data/questions.json"):
        self.storage_path = storage_path
        self.data = self._load()

    def _load(self) -> dict:
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
        FileUtils.save_json(self.storage_path, self.data)

    def _next_id(self) -> str:
        self.data["metadata"]["last_id"] += 1
        return f"q{self.data['metadata']['last_id']:03d}"

    def _recount(self) -> None:
        total = sum(len(qs) for qs in self.data["questions"].values())
        self.data["metadata"]["question_count"] = total

    # ---- queries ----

    def get_domains(self) -> list[str]:
        return self.data.get("domains", [])

    def get_question(self, qid: str) -> dict | None:
        for domain, questions in self.data["questions"].items():
            if qid in questions:
                return {**questions[qid], "domain": domain}
        return None

    def get_questions_by_domain(self, domain: str) -> list[dict]:
        if domain not in self.data["questions"]:
            return []
        return [{**q, "domain": domain} for q in self.data["questions"][domain].values()]

    def get_all_questions(self) -> list[dict]:
        result = []
        for domain, qs in self.data["questions"].items():
            for q in qs.values():
                result.append({**q, "domain": domain})
        return result

    # ---- mutations ----

    def add_domain(self, domain: str) -> None:
        if domain not in self.data["domains"]:
            self.data["domains"].append(domain)
        if domain not in self.data["questions"]:
            self.data["questions"][domain] = {}

    def add_question(self, domain: str, question: str, answer: str) -> str:
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
        existing = self.get_question(qid)
        if not existing:
            raise ValueError(f"Question {qid} not found")

        old_domain = existing["domain"]
        new_domain = domain or old_domain

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
        existing = self.get_question(qid)
        if not existing:
            raise ValueError(f"Question {qid} not found")
        domain = existing["domain"]
        del self.data["questions"][domain][qid]
        self._recount()
        self._save()
        LogUtils.info(f"Deleted question {qid}")

    def get_question_count(self) -> int:
        return self.data["metadata"].get("question_count", 0)
