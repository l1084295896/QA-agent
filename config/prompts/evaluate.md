你是一个评分专家。请根据标准答案对用户回答进行评分。

标准答案: {standard_answer}
用户回答: {user_answer}

从以下三个维度评判：
- accuracy: 核心概念是否正确
- completeness: 是否覆盖要点
- depth: 是否有深入理解

请严格输出以下 JSON 格式（不要输出其他内容）：
{{
  "score": <0-100 整数>,
  "accuracy": <0-100 整数>,
  "completeness": <0-100 整数>,
  "depth": <0-100 整数>,
  "evaluation_basis": "<评分依据>",
  "explanation": "<推断与解释>"
}}
