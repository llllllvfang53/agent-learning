"""多 Agent 编排器（Orchestrator）。

对齐 PRD 第 6 章「Agent 架构」与附录 A.3「多 Agent 并行机制」：
- 数据研究员：采集信息
- 策略分析师：交叉对比
- 报告撰写师：内容产出
- Critic：质量自检

编排器统一调度上述 Agent，支持并行执行与进度回调。
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from src.agent.critics import CriticEngine
from src.agent.graph import AgentGraph, build_competitor_graph
from src.agent.nodes import (
    apply_edit, assembler_node, critic_node, filter_node, intent_parser_node,
    parse_edit_instruction, planner_node, reader_node, searcher_node, writer_node,
)
from src.models import AgentOutput, AnalysisConfig, AnalysisState
from src.modules.registry import MODULE_REGISTRY, get_module_config
from src.tools.base import safe_call


class Orchestrator:
    """竞品分析 Agent 编排器。"""

    def __init__(self, module: str = "competitor", on_progress: Optional[Callable[[dict], None]] = None) -> None:
        self.module = module
        self.module_cfg = get_module_config(module)
        self.on_progress = on_progress or (lambda m: None)
        self.critic = CriticEngine()
        self.graph: Optional[AgentGraph] = None

    # ------------------------------------------------------------------
    # 入口
    # ------------------------------------------------------------------
    def run(self, user_request: str) -> AnalysisState:
        """一句话需求 -> 完整报告（含多 Agent 协同 + Critic 自检闭环）。"""
        state = AnalysisState(
            user_request=user_request,
            on_progress=self._progress,
            total_stages=8,
        )
        state.report_progress(f"启动{self.module_cfg.name}Agent，开始解析需求…", percent=0)

        # 1) 构建状态机图（按模块差异化）；预置模块标识（对话式创建/CLI 指定的模块优先于 intent 默认值）
        self.graph = self.module_cfg.build_graph()
        state.config = AnalysisConfig(module=self.module)

        # 2) 执行状态机
        self.graph.run(state, on_node=self._on_node)

        # 3) 质量门禁（CRITIC 终检）
        state.report_progress("Critic 终检中：校验信源充分性与整体质量", percent=92)
        verdict = self.critic.evaluate(state)
        state.critic_feedback = verdict
        if verdict.get("pass") is False:
            state.report_progress(f"终检未达标，已记录改进建议（重试 {state.retry_count}/{state.max_retry}）", percent=94)

        state.report_progress("分析完成", percent=100)
        return state

    def modify_report(self, state: AnalysisState, instruction: str) -> AnalysisState:
        """对话修改报告（PRD 附录 A.4）：解析指令 -> 应用修改 -> 重建报告。"""
        state.edit_instruction = instruction
        parse_edit_instruction(state)
        apply_edit(state)
        state.report_progress("报告已按对话要求修改", percent=100)
        return state

    # ------------------------------------------------------------------
    # 回调
    # ------------------------------------------------------------------
    def _progress(self, msg: dict) -> None:
        msg["module"] = self.module
        msg["module_name"] = self.module_cfg.name
        self.on_progress(msg)

    def _on_node(self, node: str, state: AnalysisState) -> None:
        self._progress({"stage": state.stage, "node": node, "message": f"执行节点：{node}"})


def run_analysis(user_request: str, module: str = "competitor",
                 on_progress: Optional[Callable[[dict], None]] = None) -> AnalysisState:
    """便捷入口：一句话需求 -> 报告。"""
    orch = Orchestrator(module=module, on_progress=on_progress)
    return orch.run(user_request)
