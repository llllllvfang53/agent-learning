"""一键运行 Demo：无需 API Key，快速体验完整流程。

用法：
    python -m src.agent.demo_agent
    python -m src.agent.demo_agent --module market
"""
from __future__ import annotations

import argparse
import sys

from src.agent.orchestrator import Orchestrator
from src.modules.registry import list_modules

DEMO_REQUESTS = {
    "competitor": "分析一下 AI 笔记应用的竞品",
    "market": "研究一下中国低空经济市场",
    "user": "分析 Notion 的用户反馈与痛点",
    "industry": "梳理 AI 应用行业报告",
}


def run_demo(module: str = "competitor", verbose: bool = True) -> None:
    request = DEMO_REQUESTS[module]
    print("=" * 66)
    print(f"  竞品分析 Agent Demo | 模块：{module} | 需求：{request}")
    print("  运行模式：mock（内置示例数据，无需 API Key）")
    print("=" * 66)

    def progress(msg: dict) -> None:
        name = msg.get("module_name", "Agent")
        pct = msg.get("percent")
        text = msg.get("message", "")
        pct_str = f"[{pct:>3}%]" if pct is not None else "[...]"
        if verbose:
            print(f"  {pct_str} {name} | {text}")

    orch = Orchestrator(module=module, on_progress=progress)
    state = orch.run(request)

    print("\n" + "─" * 66)
    print("✔ 报告生成完成，前 1200 字预览：")
    print("─" * 66)
    print(state.final_report[:1200])
    print("…" if len(state.final_report) > 1200 else "")
    print("\n统计：")
    print(f"  - 信源数量：{len(state.sources)}")
    print(f"  - 报告章节：{len(state.report_sections)}")
    print(f"  - Critic 评分：{state.critic_feedback.get('scores', {})}")
    print(f"  - Agent 执行轨迹：{' -> '.join(orch.graph.execution_trace)}")

    # 演示对话修改报告
    print("\n" + "─" * 66)
    print("演示：对话修改报告")
    print("─" * 66)
    inst = "在策略建议章节补充针对中小团队的具体落地方案"
    print(f"用户指令：{inst}")
    state = orch.modify_report(state, inst)
    print(f"修改结果：目标章节「{state.target_section}」，报告已重建（{len(state.final_report)} 字）")


def main() -> None:
    parser = argparse.ArgumentParser(description="竞品分析 Agent Demo")
    parser.add_argument("--module", default="competitor", choices=list_modules())
    parser.add_argument("--quiet", action="store_true", help="关闭进度输出")
    args = parser.parse_args()
    run_demo(args.module, verbose=not args.quiet)


if __name__ == "__main__":
    main()
