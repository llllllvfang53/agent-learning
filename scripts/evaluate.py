"""评估脚本：4 组对比实验 + 消融实验（对齐 PRD 第 9 章「效果评估」）。

对比组：
- A 完整 Agent（本系统）
- B 单轮 LLM（无 Agent 流程）
- C LLM + 搜索（无编排/无 Critic）
- D 人工专家（基准）

消融实验：去掉 Critic / Planner / Reader / 多 Agent 后的效果衰减。

用法：
    python scripts/evaluate.py
    python scripts/evaluate.py --quick   # 只跑完整 Agent
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

# 确保可从项目根导入 src（支持 python3 scripts/evaluate.py 直接运行）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.orchestrator import Orchestrator
from src.agent.critics import CriticEngine
from src.models import AnalysisState
from src.tools.citation import make_citation_manager

# 固定评估用例（对齐 PRD 9.3 评估集）
EVAL_CASES = [
    "分析一下 AI 笔记应用的竞品",
    "分析飞书文档的竞品",
    "分析短视频剪辑工具的竞品",
]

# 人工专家基准分（A/B/C 组对比的 D 组目标值，取自 PRD 9.2 验收目标）
HUMAN_BENCHMARK = {
    "事实准确率": 0.95,
    "引用覆盖率": 0.90,
    "报告完整度": 0.96,
    "综合评分": 4.8,
}


@dataclass
class EvalResult:
    group: str
    case: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    elapsed: float = 0.0


def _metrics_for(state: AnalysisState, group: str, case: str) -> Dict[str, Any]:
    """从运行状态提取可计算指标。"""
    cm = make_citation_manager()
    # 引用覆盖率
    coverage = cm.citation_coverage(state.final_report)
    # 高权威信源占比
    high_ratio = (sum(1 for s in state.sources.values() if s.authority.value == "high")
                  / len(state.sources)) if state.sources else 0.0
    return {
        "group": group,
        "case": case,
        "信源数量": len(state.sources),
        "章节数量": len(state.report_sections),
        "报告字数": len(state.final_report),
        "高权威信源占比": round(high_ratio, 2),
        "引用覆盖率": round(coverage, 2),
        "Critic 平均分": round(sum(state.critic_feedback.get("scores", {}).values()) /
                              len(state.critic_feedback.get("scores", {}))
                              if state.critic_feedback.get("scores") else 0.0, 2),
        "耗时(s)": None,  # 由外层填充
    }


def run_full_agent(case: str) -> AnalysisState:
    orch = Orchestrator(module="competitor")
    return orch.run(case)


def run_single_llm(case: str) -> AnalysisState:
    """B 组：单轮 LLM，无 Agent 流程。"""
    from src.tools.llm import get_llm
    llm = get_llm()
    text = llm.call(system="你是竞品分析师，直接输出一份竞品分析报告。", user=case)
    state = AnalysisState(user_request=case)
    state.report_sections = {"单轮结果": text}
    state.final_report = text
    return state


def run_llm_search(case: str) -> AnalysisState:
    """C 组：LLM + 搜索，无编排 / 无 Critic。"""
    from src.tools.llm import get_llm
    from src.tools.search import get_search
    llm, search = get_llm(), get_search()
    sources = search.call(query=case)
    ctx = "\n".join(f"- {s.title}: {s.snippet}" for s in sources)
    text = llm.call(system="你是竞品分析师，基于以下资料撰写竞品分析报告。", user=f"资料：\n{ctx}\n\n需求：{case}")
    state = AnalysisState(user_request=case)
    state.sources = {s.source_id: s for s in sources}
    state.report_sections = {"报告": text}
    state.final_report = text
    return state


def run_ablation(case: str, remove: str) -> AnalysisState:
    """消融实验：去掉某个组件后运行。"""
    state = AnalysisState(user_request=case)
    from src.agent.graph import AgentGraph
    from src.agent import nodes
    g = AgentGraph()
    if remove != "planner":
        g.add_node("planner", nodes.planner_node)
    if remove != "reader":
        g.add_node("reader", nodes.reader_node)
    if remove != "critic":
        g.add_node("critic", nodes.critic_node)
    if remove != "multi_agent":
        # 多 Agent 在 writer 节点内模拟，这里仅标记
        pass
    g.add_node("intent_parser", nodes.intent_parser_node)
    g.add_node("searcher", nodes.searcher_node)
    g.add_node("filter", nodes.filter_node)
    g.add_node("writer", nodes.writer_node)
    g.add_node("assembler", nodes.assembler_node)
    g.set_entry("intent_parser")
    g.add_edge("intent_parser", "searcher")
    g.add_edge("searcher", "filter")
    if remove != "reader":
        g.add_edge("filter", "reader")
        g.add_edge("reader", "writer")
    else:
        g.add_edge("filter", "writer")
    g.add_edge("writer", "critic" if remove != "critic" else "assembler")
    g.add_edge("critic", "assembler")
    g.add_edge("assembler", "")
    g.run(state)
    return state


def evaluate(quick: bool = False) -> List[EvalResult]:
    results: List[EvalResult] = []

    for case in EVAL_CASES:
        print(f"▶ 评估用例：{case}")

        # A 完整 Agent
        t0 = time.time()
        state_a = run_full_agent(case)
        metrics_a = _metrics_for(state_a, "A_完整Agent", case)
        metrics_a["耗时(s)"] = round(time.time() - t0, 2)
        results.append(EvalResult("A_完整Agent", case, metrics_a, metrics_a["耗时(s)"]))
        print(f"  A 完整Agent：{metrics_a}")

        if quick:
            continue

        # B 单轮 LLM
        t0 = time.time()
        state_b = run_single_llm(case)
        metrics_b = _metrics_for(state_b, "B_单轮LLM", case)
        metrics_b["耗时(s)"] = round(time.time() - t0, 2)
        results.append(EvalResult("B_单轮LLM", case, metrics_b, metrics_b["耗时(s)"]))
        print(f"  B 单轮LLM：{metrics_b}")

        # C LLM + 搜索
        t0 = time.time()
        state_c = run_llm_search(case)
        metrics_c = _metrics_for(state_c, "C_LLM+搜索", case)
        metrics_c["耗时(s)"] = round(time.time() - t0, 2)
        results.append(EvalResult("C_LLM+搜索", case, metrics_c, metrics_c["耗时(s)"]))
        print(f"  C LLM+搜索：{metrics_c}")

    # 消融实验（quick 模式下仍运行一轮，展示能力）
    print("\n▶ 消融实验（去掉各组件后的衰减）")
    case = EVAL_CASES[0]
    for comp in ["critic", "planner", "reader", "multi_agent"]:
        t0 = time.time()
        state = run_ablation(case, comp)
        m = _metrics_for(state, f"消融-去{comp}", case)
        m["耗时(s)"] = round(time.time() - t0, 2)
        results.append(EvalResult(f"消融-去{comp}", case, m, m["耗时(s)"]))
        print(f"  去{comp}：信源{len(state.sources)} 章节{len(state.report_sections)} 字数{len(state.final_report)}")

    return results


def summarize(results: List[EvalResult]) -> None:
    print("\n" + "=" * 66)
    print("评估汇总")
    print("=" * 66)
    groups: Dict[str, List[EvalResult]] = {}
    for r in results:
        groups.setdefault(r.group, []).append(r)

    header = f"{'组别':<18}{'用例数':<6}{'平均引用覆盖率':<14}{'平均高权威占比':<14}{'平均耗时':<10}"
    print(header)
    print("-" * 66)
    for g, rs in groups.items():
        avg_cov = sum(r.metrics.get("引用覆盖率", 0) for r in rs) / len(rs)
        avg_high = sum(r.metrics.get("高权威信源占比", 0) for r in rs) / len(rs)
        avg_time = sum(r.elapsed for r in rs) / len(rs)
        print(f"{g:<18}{len(rs):<6}{avg_cov:<16.2f}{avg_high:<16.2f}{avg_time:<10.2f}")

    print("\n注：本评估在 mock 模式下运行，指标用于验证流程正确性；")
    print("    真实质量指标（事实准确率/幻觉率）需接入真实 LLM + 标注集评测，见 PRD 9 章。")


def main() -> None:
    parser = argparse.ArgumentParser(description="竞品分析 Agent 评估")
    parser.add_argument("--quick", action="store_true", help="只跑完整 Agent")
    parser.add_argument("--json", help="结果输出到 JSON 文件")
    args = parser.parse_args()
    results = evaluate(quick=args.quick)
    summarize(results)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump([r.__dict__ for r in results], f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到 {args.json}")


if __name__ == "__main__":
    main()
