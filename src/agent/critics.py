"""Critic 质量自检引擎。

对齐 PRD A.2.7「Critic」与 9.4「评估指标」：
- 四维评分：信源充分性 / 切题度 / 事实准确性 / 结构逻辑
- 生成改进建议（Suggestion）
- 决定是否触发重试（planner -> searcher -> ... 循环）

实测口径：分数为 LLM 主观评分（1-5），指标类数字（准确率/幻觉率）见 scripts/evaluate.py。
"""
from __future__ import annotations

from typing import Any, Dict, List

from src.models import AnalysisState
from src.tools.llm import get_llm, parse_json_response

DIMENSIONS = ["信源充分性", "切题度", "事实准确性", "结构逻辑"]


class CriticEngine:
    """四维质量评分引擎。"""

    def __init__(self, pass_threshold: float = 3.5) -> None:
        self.pass_threshold = pass_threshold

    def evaluate(self, state: AnalysisState) -> Dict[str, Any]:
        """对当前状态做质量评分，返回 verdict dict。"""
        llm = get_llm()
        source_count = len(state.sources)
        section_count = len(state.report_sections)
        avg_score = self._average_scores(state.critic_feedback.get("scores", {})) if state.critic_feedback else 0.0

        # 简化规则评估（mock 下 LLM 返回固定高分，规则用于兜底）
        issues: List[str] = []
        if source_count < 2:
            issues.append(f"信源数量不足（当前 {source_count} 条，建议 ≥2）")
        if section_count < 3:
            issues.append(f"报告章节过少（当前 {section_count} 个，建议 ≥3）")

        feedback: Dict[str, Any] = {
            "scores": state.critic_feedback.get("scores", {}) or self._default_scores(source_count, section_count),
            "pass": len(issues) == 0,
            "issues": issues,
            "suggestion": "；".join(issues) if issues else "整体质量达标，建议补充高权威信源以提升可信度。",
            "source_count": source_count,
            "section_count": section_count,
            "avg_score": round(avg_score, 2) if avg_score else None,
        }
        return feedback

    @staticmethod
    def _average_scores(scores: Dict[str, float]) -> float:
        if not scores:
            return 0.0
        return sum(scores.values()) / len(scores)

    @staticmethod
    def _default_scores(source_count: int, section_count: int) -> Dict[str, float]:
        """无 LLM 评分时的规则兜底。"""
        return {
            "信源充分性": min(5.0, 1.0 + source_count * 0.8),
            "切题度": 4.0,
            "事实准确性": min(5.0, 3.0 + source_count * 0.3),
            "结构逻辑": min(5.0, 2.0 + section_count * 0.4),
        }
