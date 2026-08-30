"""测试：核心节点（意图解析 / 搜索 / 写作 / Critic / 组装）。"""
from __future__ import annotations

from src.agent.nodes import (
    assembler_node, critic_node, filter_node, intent_parser_node,
    parse_edit_instruction, apply_edit, planner_node, reader_node,
    searcher_node, writer_node,
)
from src.models import AnalysisConfig, AnalysisState, EditAction


def _make_state(request: str = "分析一下 AI 笔记应用的竞品") -> AnalysisState:
    state = AnalysisState(user_request=request)
    intent_parser_node(state)
    return state


def test_intent_parser_sets_config():
    state = _make_state()
    assert state.parsed_config is not None
    assert state.parsed_config.analysis_object != ""


def test_intent_parser_fallback_rule():
    state = _make_state("分析一下短视频剪辑工具的竞品")
    assert "视频" in state.parsed_config.analysis_object or "短视频" in state.parsed_config.analysis_object


def test_full_pipeline_nodes():
    state = _make_state()
    planner_node(state)
    searcher_node(state)
    filter_node(state)
    reader_node(state)
    writer_node(state)
    critic_node(state)
    assembler_node(state)
    assert len(state.sources) > 0
    assert len(state.report_sections) >= 3
    assert "# " in state.final_report  # 报告已组装
    assert "参考文献" in state.final_report
    assert state.critic_feedback != {}


def test_edit_rewrite_and_insert():
    state = _make_state()
    writer_node(state)
    before_keys = set(state.report_sections.keys())

    # INSERT 新章节
    state.edit_instruction = "新增一个「出海机会分析」章节"
    parse_edit_instruction(state)
    apply_edit(state)
    assert "出海机会分析" in state.report_sections

    # DELETE 章节
    state.edit_instruction = "删除「综合能力雷达」章节"
    parse_edit_instruction(state)
    apply_edit(state)
    assert "综合能力雷达" not in state.report_sections

    # REWRITE
    state.edit_instruction = "重写执行摘要"
    parse_edit_instruction(state)
    apply_edit(state)
    assert len(state.edit_history) == 3
