"""命令行交互入口。

支持：
- 一句话需求 -> 完整报告（默认 mock 模式，无需 API Key）
- 对话修改报告：分析完成后可继续输入修改指令
- --module 指定研究模块（competitor / market / user / industry）
"""
from __future__ import annotations

import argparse
import sys
from typing import List

from src.agent.orchestrator import Orchestrator
from src.modules.registry import list_modules


def _print_progress(msg: dict) -> None:
    name = msg.get("module_name", "Agent")
    stage = msg.get("stage", "")
    pct = msg.get("percent")
    text = msg.get("message", "")
    pct_str = f" [{pct}%]" if pct is not None else ""
    print(f"\r  {name} {pct_str} {text}", end="", flush=True)


def run_cli(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="竞品分析 Agent - 命令行版")
    parser.add_argument("request", nargs="?", help="一句话分析需求（缺省则进入交互模式）")
    parser.add_argument("--module", default="competitor", choices=list_modules(), help="研究模块")
    parser.add_argument("--no-modify", action="store_true", help="生成后不进入对话修改")
    args = parser.parse_args(argv)

    print("=" * 60)
    print(" 竞品分析 Agent（多 Agent 协同研究平台）")
    print("=" * 60)

    if args.request:
        request = args.request
    else:
        request = input("请输入分析需求（如：分析一下 AI 笔记应用的竞品）> ").strip()
        if not request:
            request = "分析一下 AI 笔记应用的竞品"

    orch = Orchestrator(module=args.module, on_progress=_print_progress)
    print(f"\n▶ 开始 {orch.module_cfg.name}（{orch.module_cfg.tagline}）")
    state = orch.run(request)
    print()

    # 输出报告
    print("\n" + "─" * 60)
    print(state.final_report)
    print("─" * 60)
    print(f"\n✔ 信源 {len(state.sources)} 条 | 章节 {len(state.report_sections)} 个 | "
          f"Critic 评分 {state.critic_feedback.get('scores', {})}")

    # 对话修改报告
    if not args.no_modify:
        print("\n（支持对话修改报告，输入指令修改，直接回车退出）")
        while True:
            instruction = input("修改指令 > ").strip()
            if not instruction:
                break
            state = orch.modify_report(state, instruction)
            print("  ✔ 已修改。报告更新如下：")
            print(state.final_report)
            print("-" * 60)
    return 0


def main() -> None:
    sys.exit(run_cli())


if __name__ == "__main__":
    main()
