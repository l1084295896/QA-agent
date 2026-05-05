"""使用 LLM 对用户答案进行评分，支持 JSON 解析和正则 fallback 两种提取策略。"""

import json
import re
from ..models.llm_client import LLMClient
from ..utils.prompt_utils import PromptUtils
from ..utils.log_utils import LogUtils


class Evaluator:
    """评分器：通过 LLM 对比标准答案与用户答案，输出评分和解释。

    核心功能：
    - 调用 LLM 生成 JSON 格式的评分结果（score, accuracy, completeness, depth, explanation）
    - 主解析路径：正则提取 JSON 块后 json.loads
    - 降级路径：当 LLM 输出格式不规范时，用正则提取 score 字段作为 fallback
    - 自动补齐缺失字段（accuracy/completeness/depth 默认取 score 值）
    """

    def __init__(self, llm_client: LLMClient):
        """初始化评分器。

        Args:
            llm_client: LLM 客户端，需支持 invoke(prompt) -> str
        """
        self.llm = llm_client

    def evaluate(self, standard_answer: str, user_answer: str) -> dict:
        """对比标准答案和用户答案，返回评分字典。

        Args:
            standard_answer: 标准答案文本
            user_answer: 用户提交的答案文本

        Returns:
            包含 score, accuracy, completeness, depth, rating, explanation 的字典
        """
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

        # 补齐可能缺失的子维度评分，默认使用总分兜底
        result.setdefault("accuracy", result.get("score", 50))
        result.setdefault("completeness", result.get("score", 50))
        result.setdefault("depth", result.get("score", 50))
        result["rating"] = self._get_rating(result["score"])
        return result

    def _parse_json(self, response: str) -> dict:
        """从 LLM 返回文本中提取最外层 JSON 对象并解析。

        使用正则 \{[\s\S]*\} 进行贪婪匹配，提取第一个完整的 JSON 块。
        即使 LLM 在 JSON 前后附加了说明文字，也能正确提取。
        """
        match = re.search(r'\{[\s\S]*\}', response)
        json_str = match.group() if match else response
        return json.loads(json_str)

    def _fallback_parse(self, response: str) -> dict:
        """JSON 解析失败时的降级策略：用正则直接提取 "score" 字段的数值。

        仅能提取总分，无法恢复完整的 evaluation 细节，explanation 截取前 200 字符。
        """
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
        """根据分数返回等级标签。

        Args:
            score: 0-100 的整数评分

        Returns:
            A/B/C/D 四级中文等级字符串
        """
        if score >= 90:
            return "A级 - 优秀"
        elif score >= 70:
            return "B级 - 良好"
        elif score >= 60:
            return "C级 - 及格"
        return "D级 - 不及格"
