"""测试：模块注册表（三模块差异化配置）。"""
from __future__ import annotations

from src.agent.orchestrator import Orchestrator
from src.modules.registry import get_module_config, list_modules


def test_module_registry_has_four_modules():
    modules = list_modules()
    assert "competitor" in modules
    assert "market" in modules
    assert "user" in modules
    assert "industry" in modules


def test_module_differentiation():
    m_comp = get_module_config("competitor")
    m_market = get_module_config("market")
    m_user = get_module_config("user")
    m_industry = get_module_config("industry")

    # 三模块 Agent 角色 / 章节 / 主题色各不相同
    names = {m.name for m in [m_comp, m_market, m_user, m_industry]}
    assert len(names) == 4
    colors = {m.theme_color for m in [m_comp, m_market, m_user, m_industry]}
    assert len(colors) == 4
    section_sets = {tuple(m.sections) for m in [m_comp, m_market, m_user, m_industry]}
    assert len(section_sets) == 4
    agent_names = {tuple(a.name for a in m.agents) for m in [m_comp, m_market, m_user, m_industry]}
    assert len(agent_names) == 4


def test_orchestrator_runs_all_modules():
    requests = {
        "competitor": "分析一下 AI 笔记应用的竞品",
        "market": "研究一下中国低空经济市场",
        "user": "分析 Notion 的用户反馈",
        "industry": "梳理 AI 应用行业报告",
    }
    for module, req in requests.items():
        orch = Orchestrator(module=module)
        state = orch.run(req)
        assert len(state.report_sections) >= 3, f"{module} 报告章节不足"
        assert state.final_report, f"{module} 报告为空"
