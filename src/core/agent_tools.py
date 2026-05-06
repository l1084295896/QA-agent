"""Agent 工具工厂：创建供 LangChain Agent 调用的只读查询工具。

所有工具通过闭包捕获 QuestionBank / SearchEngine / HistoryManager 实例，
以普通函数返回，由 QAAgent.register_tool() 用 @tool 装饰器包装。
"""

from ..utils.log_utils import LogUtils


def create_tools(bank, search, history):
    """创建 Agent 工具函数列表，每个函数通过闭包持有数据源引用。

    Args:
        bank: QuestionBank 实例
        search: SearchEngine 实例
        history: HistoryManager 实例

    Returns:
        4 个可注册的工具函数列表
    """

    def get_learning_stats() -> str:
        """获取用户学习统计概览：总答题数、平均分、各领域表现、最近趋势。"""
        records = history.get_records()
        answer_records = [r for r in records if r.get("type") == "answer"]

        if not answer_records:
            return "暂无学习记录。输入 /Q 开始练习吧！"

        total = len(answer_records)
        avg_score = sum(r.get("score", 0) for r in answer_records) / total

        # 按领域统计
        domain_stats: dict[str, dict] = {}
        for r in answer_records:
            d = r.get("domain", "未知")
            if d not in domain_stats:
                domain_stats[d] = {"count": 0, "total_score": 0, "scores": []}
            domain_stats[d]["count"] += 1
            domain_stats[d]["total_score"] += r.get("score", 0)
            domain_stats[d]["scores"].append(r.get("score", 0))

        lines = [
            f"## 学习统计\n",
            f"总答题数: {total} 题 | 平均分: {avg_score:.1f}/100\n",
            f"### 各领域表现\n",
            "| 领域 | 答题数 | 平均分 | 最高 | 最低 |",
            "|------|--------|--------|------|------|",
        ]
        for domain, ds in sorted(domain_stats.items(), key=lambda x: sum(x[1]["scores"]) / len(x[1]["scores"])):
            scores = ds["scores"]
            lines.append(
                f"| {domain} | {ds['count']} | {sum(scores)/len(scores):.1f} | {max(scores)} | {min(scores)} |"
            )

        # 最近趋势：取最近 10 条倒序后还原为时间升序
        recent = sorted(answer_records, key=lambda r: r["timestamp"])[-10:]
        if len(recent) >= 2:
            recent_scores = [r.get("score", 0) for r in recent]
            trend = "上升" if recent_scores[-1] > recent_scores[0] else "下降" if recent_scores[-1] < recent_scores[0] else "持平"
            lines.append(f"\n最近 {len(recent)} 题趋势: {trend}（{recent_scores[0]} → {recent_scores[-1]}）")

        LogUtils.info(f"Agent tool: get_learning_stats returned {total} records")
        return "\n".join(lines)

    def recommend_practice() -> str:
        """基于历史数据推荐下一步练习方向，优先薄弱领域和未练习领域。"""
        domains = bank.get_domains()
        if not domains:
            return "题库暂无题目，请先通过 /add_file 或 /add_interactive 添加题目。"

        answer_records = [r for r in history.get_records() if r.get("type") == "answer"]
        answered_ids = history.get_answered_ids()

        # 计算每个领域的答题数和平均分
        domain_perf: dict[str, dict] = {}
        for d in domains:
            domain_perf[d] = {"total": len(bank.get_questions_by_domain(d)), "answered": 0, "total_score": 0, "unanswered": 0}

        for r in answer_records:
            d = r.get("domain", "")
            if d in domain_perf:
                domain_perf[d]["answered"] += 1
                domain_perf[d]["total_score"] += r.get("score", 0)

        # 统计未答题数
        for d in domains:
            qs = bank.get_questions_by_domain(d)
            domain_perf[d]["unanswered"] = sum(1 for q in qs if q["id"] not in answered_ids)

        lines = ["## 练习推荐\n"]

        # 策略1：有未练习的领域 → 推荐
        untouched = [d for d in domains if domain_perf[d]["answered"] == 0]
        if untouched:
            lines.append(f"🎯 你尚未练习过: {', '.join(untouched)}，建议从这里开始！\n")

        # 策略2：薄弱领域（均分 < 60）
        weak = [
            d for d in domains
            if domain_perf[d]["answered"] > 0 and domain_perf[d]["total_score"] / domain_perf[d]["answered"] < 60
        ]
        if weak:
            lines.append(f"📉 薄弱领域（均分<60）: {', '.join(weak)}，建议加强练习。\n")

        # 策略3：有未答题的领域
        has_unanswered = [(d, domain_perf[d]["unanswered"]) for d in domains if domain_perf[d]["unanswered"] > 0]
        if has_unanswered:
            lines.append("📋 以下领域还有未做的题目：")
            for d, n in has_unanswered:
                lines.append(f"  - {d}: {n} 题未答")
            lines.append("")

        # 策略4：全做完了
        if not untouched and not weak and not has_unanswered:
            all_scores = [r.get("score", 0) for r in answer_records]
            avg = sum(all_scores) / len(all_scores) if all_scores else 0
            lines.append(f"🎉 所有题目已完成！平均分 {avg:.1f}/100。")
            if avg < 80:
                lines.append("建议回顾低分题目，加深理解。")

        LogUtils.info("Agent tool: recommend_practice called")
        return "\n".join(lines)

    def find_related_questions(query: str) -> str:
        """根据关键词或主题语义搜索相关题目。

        Args:
            query: 搜索关键词或主题描述
        """
        if not query.strip():
            return "请提供搜索关键词或主题描述。"

        results = search.search(query, k=5)
        if not results:
            return f"未找到与「{query}」相关的题目。试试换个关键词？"

        lines = [f"## 搜索「{query}」的相关题目\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. [{r['domain']}] {r['question'][:120]}（相似度: {r['similarity']:.0%}）")

        LogUtils.info(f"Agent tool: find_related_questions('{query}') -> {len(results)} results")
        return "\n".join(lines)

    def get_domain_summary(domain: str = "") -> str:
        """获取领域概览：题目数、已答数、平均分。不指定领域则返回全部领域摘要。

        Args:
            domain: 领域名称，留空则返回全部领域
        """
        answer_records = [r for r in history.get_records() if r.get("type") == "answer"]
        answered_ids = history.get_answered_ids()

        # 按领域统计作答情况
        answered_count: dict[str, int] = {}
        answered_scores: dict[str, list] = {}
        for r in answer_records:
            d = r.get("domain", "")
            answered_count[d] = answered_count.get(d, 0) + 1
            if d not in answered_scores:
                answered_scores[d] = []
            answered_scores[d].append(r.get("score", 0))

        if domain:
            domains = [domain] if domain in bank.get_domains() else []
            if not domains:
                return f"领域「{domain}」不存在。可用领域: {', '.join(bank.get_domains()) or '无'}"
        else:
            domains = bank.get_domains()

        if not domains:
            return "题库暂无题目。"

        lines = [f"## 领域概览\n" if not domain else f"## {domain} 领域详情\n"]
        lines.append("| 领域 | 总题数 | 已答数 | 平均分 |")
        lines.append("|------|--------|--------|--------|")

        for d in domains:
            total = len(bank.get_questions_by_domain(d))
            answered = answered_count.get(d, 0)
            scores = answered_scores.get(d, [])
            avg = f"{sum(scores)/len(scores):.1f}" if scores else "-"
            lines.append(f"| {d} | {total} | {answered} | {avg} |")

        LogUtils.info(f"Agent tool: get_domain_summary('{domain}') -> {len(domains)} domains")
        return "\n".join(lines)

    return [get_learning_stats, recommend_practice, find_related_questions, get_domain_summary]
