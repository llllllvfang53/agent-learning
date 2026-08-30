"""示例：一句话需求 -> 完整报告。

用法：
    python examples/run_analysis.py "分析一下 AI 笔记应用的竞品"
    python examples/run_analysis.py --module market "研究中国低空经济市场"
"""
from __future__ import annotations

import argparse
import sys

from src.agent.orchestrator import Orchestrator
from src.modules.registry import list_modules


def main() -> None:
    parser = argparse.ArgumentParser(description="竞品分析 Agent 示例")
    parser.add_argument("request", nargs="?", default="分析一下 AI 笔记应用的竞品")
    parser.add_argument("--module", default="competitor", choices=list_modules())
    parser.add_argument("--save", default="report.md", help="报告保存路径")
    args = parser.parse_args()

    def progress(msg: dict) -> None:
        pct = msg.get("percent")
        pct_str = f"[{pct:>3}%]" if pct is not None else "[...]"
        print(f"  {pct_str} {msg.get('module_name')} | {msg.get('message')}")

    orch = Orchestrator(module=args.module, on_progress=progress)
    print(f"▶ 模块：{orch.module_cfg.name} | 需求：{args.request}")
    state = orch.run(args.request)

    with open(args.save, "w", encoding="utf-8") as f:
        f.write(state.final_report)
    print(f"\n✔ 报告已保存到 {args.save}")
    print(f"  信源 {len(state.sources)} 条 | 章节 {len(state.report_sections)} 个")
    print(f"  Agent 执行轨迹：{' -> '.join(orch.graph.execution_trace)}")


if __name__ == "__main__":
    main()
