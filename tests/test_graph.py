"""测试：Agent 状态机编排器。"""
from __future__ import annotations

import pytest

from src.agent.graph import AgentGraph


def _node_fn(state):
    state.final_report = (state.final_report or "") + "N"
    return None


def _fail_once(state):
    state.stage = 99
    return None


def test_graph_simple_chain():
    g = AgentGraph()
    g.add_node("a", _node_fn)
    g.add_node("b", _node_fn)
    g.set_entry("a")
    g.add_edge("a", "b")
    g.add_edge("b", "")
    from src.models import AnalysisState
    state = AnalysisState()
    g.run(state)
    assert state.final_report == "NN"
    assert g.execution_trace == ["a", "b"]


def test_graph_conditional_route():
    from src.models import AnalysisState

    def route_fn(state):
        return "pass" if state.critic_feedback.get("pass") else "retry"

    g = AgentGraph()
    g.add_node("start", _node_fn)
    g.add_node("retry", _node_fn)
    g.add_node("pass", _node_fn)
    g.set_entry("start")
    g.add_edge("start", route=route_fn)
    g.add_edge("retry", "")
    g.add_edge("pass", "")

    # pass 分支
    s1 = AnalysisState()
    s1.critic_feedback = {"pass": True}
    g.run(s1)
    assert g.execution_trace == ["start", "pass"]

    # retry 分支
    g2 = AgentGraph()
    g2.add_node("start", _node_fn)
    g2.add_node("retry", _node_fn)
    g2.add_node("pass", _node_fn)
    g2.set_entry("start")
    g2.add_edge("start", route=route_fn)
    g2.add_edge("retry", "")
    g2.add_edge("pass", "")
    s2 = AnalysisState()
    s2.critic_feedback = {"pass": False}
    g2.run(s2)
    assert g2.execution_trace == ["start", "retry"]


def test_graph_guard_prevents_infinite_loop():
    from src.models import AnalysisState
    g = AgentGraph()
    g.add_node("loop", _node_fn)
    g.set_entry("loop")
    g.add_edge("loop", "loop")  # 自循环
    state = AnalysisState()
    g.run(state)
    # 不会死循环
    assert len(g.execution_trace) <= 20


def test_graph_parallel_group():
    from src.models import AnalysisState

    calls = []

    def n1(state):
        calls.append("n1")
        return None

    def n2(state):
        calls.append("n2")
        return None

    g = AgentGraph()
    g.add_node("a", n1, parallel_with=["b"])
    g.add_node("b", n2)
    g.add_edge("a", "")
    state = AnalysisState()
    g.run(state)
    assert sorted(calls) == ["n1", "n2"]
