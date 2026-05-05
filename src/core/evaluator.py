import json
import re
from ..models.llm_client import LLMClient
from ..utils.prompt_utils import PromptUtils
from ..utils.log_utils import LogUtils


class Evaluator:
    """Scores user answers via LLM. Parses JSON output with regex fallback."""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def evaluate(self, standard_answer: str, user_answer: str) -> dict:
        prompt = PromptUtils.load(
            "evaluate",
            standard_answer=standard_answer,
            user_answer=user_answer,
        )
        response = self.llm.invoke(prompt)
        try:
            result = self._parse_json(response)
        except (json.JSONDecodeError, ValueError) as e:
            LogUtils.warning(f"Failed to parse evaluation JSON, using fallback: {e}")
            result = self._fallback_parse(response)

        result.setdefault("accuracy", result.get("score", 50))
        result.setdefault("completeness", result.get("score", 50))
        result.setdefault("depth", result.get("score", 50))
        result["rating"] = self._get_rating(result["score"])
        return result

    def _parse_json(self, response: str) -> dict:
        match = re.search(r'\{[\s\S]*\}', response)
        json_str = match.group() if match else response
        return json.loads(json_str)

    def _fallback_parse(self, response: str) -> dict:
        score_match = re.search(r'"score"\s*:\s*(\d+)', response)
        score = int(score_match.group(1)) if score_match else 50
        return {
            "score": score,
            "accuracy": score,
            "completeness": score,
            "depth": score,
            "evaluation_basis": response[:200],
            "explanation": response[:200],
        }

    @staticmethod
    def _get_rating(score: int) -> str:
        if score >= 90:
            return "A级 - 优秀"
        elif score >= 70:
            return "B级 - 良好"
        elif score >= 60:
            return "C级 - 及格"
        return "D级 - 不及格"
