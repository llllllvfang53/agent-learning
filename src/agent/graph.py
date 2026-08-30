"""轻量 Agent 状态机编排器。

对标 LangGraph 的核心语义，用纯标准库实现一个可运行的图执行引擎：
- 节点（Node）：可调用对象，输入 state 输出 state
- 边（Edge）：显式连线 或 条件路由（回调函数决定下一节点）
- 支持循环（Critic 重试）与并发（多 Agent 并行，通过线程池）

本实现刻意保持依赖为零，便于面试讲解"状态机如何工作"；
若需生产级能力（检查点、持久化、流式），可无缝替换为 langgraph。
"""
from __future__ import annotations

import inspect
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


# 节点：接收 state，返回 (new_state, updates) 或直接修改 state 并返回 None
NodeFn = Callable[["AnalysisState"], Optional[Dict[str, Any]]]
# 条件路由：接收 state，返回下一节点名
RouteFn = Callable[["AnalysisState"], str]


@dataclass
class NodeSpec:
    """节点定义。"""

    name: str
    fn: NodeFn
    description: str = ""
    parallel_with: List[str] = field(default_factory=list)  # 并行节点名列表


@dataclass
class EdgeSpec:
    """边定义：source -> target（或 source -> 条件路由）。"""

    source: str
    target: str = ""
    route: Optional[RouteFn] = None
    when: Optional[Callable[["AnalysisState"], bool]] = None  # 条件门


class AgentGraph:
    """可执行的 Agent 状态机图。"""

    def __init__(self) -> None:
        self.nodes: Dict[str, NodeSpec] = {}
        self.edges: List[EdgeSpec] = []
        self.entry: str = ""
        self.terminal: str = "END"
        self.execution_trace: List[str] = []

    # ------------------------------------------------------------------
    # 构建 API
    # ------------------------------------------------------------------
    def add_node(self, name: str, fn: NodeFn, description: str = "", parallel_with: Optional[List[str]] = None) -> "AgentGraph":
        self.nodes[name] = NodeSpec(name=name, fn=fn, description=description, parallel_with=parallel_with or [])
        if not self.entry:
            self.entry = name
        return self

    def add_edge(self, source: str, target: str = "", route: Optional[RouteFn] = None) -> "AgentGraph":
        self.edges.append(EdgeSpec(source=source, target=target, route=route))
        return self

    def set_entry(self, name: str) -> "AgentGraph":
        self.entry = name
        return self

    # ------------------------------------------------------------------
    # 执行
    # ------------------------------------------------------------------
    def run(self, state: "AnalysisState", on_node: Optional[Callable[[str, "AnalysisState"], None]] = None) -> "AnalysisState":
        """从 entry 开始执行，直到没有出边或到达 terminal。"""
        current = self.entry
        guard = 0
        max_steps = len(self.nodes) * 10 + 10

        while current and current != self.terminal:
            if guard >= max_steps:
                state.report_progress("流程异常：超过最大执行步数，终止")
                break
            guard += 1

            spec = self.nodes.get(current)
            if spec is None:
                break

            if on_node:
                on_node(current, state)
            self.execution_trace.append(current)
            state.stage = len(self.execution_trace)

            # 并行执行本节点 + 其并行伙伴
            self._execute_node_group(current, state)

            # 路由到下一节点
            next_node = self._route(current, state)
            if next_node is None:
                break
            current = next_node

        return state

    def _execute_node_group(self, name: str, state: "AnalysisState") -> None:
        """执行一个节点及其并行伙伴（线程池并发）。"""
        spec = self.nodes[name]
        targets = [name] + [p for p in spec.parallel_with if p in self.nodes and p != name]
        if len(targets) == 1:
            self._run_single(name, state)
            return
        with ThreadPoolExecutor(max_workers=len(targets)) as pool:
            futures = {pool.submit(self._run_single, t, state): t for t in targets}
            for fut in as_completed(futures):
                fut.result()  # 触发异常传播

    def _run_single(self, name: str, state: "AnalysisState") -> None:
        """执行单个节点，处理状态更新。"""
        spec = self.nodes[name]
        result = spec.fn(state)
        if result:
            for k, v in result.items():
                if hasattr(state, k):
                    setattr(state, k, v)

    def _route(self, source: str, state: "AnalysisState") -> Optional[str]:
        """根据边与条件路由决定下一节点。"""
        for edge in self.edges:
            if edge.source != source:
                continue
            if edge.when is not None and not edge.when(state):
                continue
            if edge.route is not None:
                return edge.route(state)
            if edge.target:
                return edge.target
        return None


def build_competitor_graph(**kwargs: Any) -> AgentGraph:
    """组装竞品分析 Agent 的状态机图（节点在 nodes.py 中定义）。"""
    from src.agent.nodes import (
        assembler_node, critic_node, filter_node, intent_parser_node,
        planner_node, reader_node, searcher_node, writer_node,
    )
    g = AgentGraph()
    g.add_node("intent_parser", intent_parser_node, "解析一句话需求")
    g.add_node("planner", planner_node, "搜索规划")
    g.add_node("searcher", searcher_node, "联网搜索")
    g.add_node("filter", filter_node, "筛选高价值信源")
    g.add_node("reader", reader_node, "网页精读")
    g.add_node("writer", writer_node, "撰写报告章节")
    g.add_node("critic", critic_node, "质量自检")
    g.add_node("assembler", assembler_node, "组装全文")
    g.set_entry("intent_parser")
    g.add_edge("intent_parser", "planner")
    g.add_edge("planner", "searcher")
    g.add_edge("searcher", "filter")
    g.add_edge("filter", "reader")
    g.add_edge("reader", "writer")
    g.add_edge("writer", "critic")
    # Critic 不通过则回 planner 重试，超过 max_retry 则强制进入 assembler
    g.add_edge("critic", route=lambda s: "planner" if (s.critic_feedback.get("pass") is False and s.retry_count < s.max_retry) else "assembler")
    g.add_edge("assembler", "")
    return g
