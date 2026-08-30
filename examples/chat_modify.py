"""示例：对话修改报告闭环。

演示：分析完成后，用自然语言修改报告（PRD 附录 A.4）。
"""
from __future__ import annotations

from src.agent.orchestrator import Orchestrator


def main() -> None:
    orch = Orchestrator(module="competitor")
    print("▶ 步骤 1：生成报告")
    state = orch.run("分析一下飞书文档的竞品")
    print(f"  生成完成：{len(state.report_sections)} 个章节，{len(state.final_report)} 字")

    # 场景 1：局部重写
    print("\n▶ 步骤 2：对话修改（REWRITE）")
    print('  指令："策略建议章节补充针对中小团队的落地方案"')
    state = orch.modify_report(state, "策略建议章节补充针对中小团队的落地方案")
    print(f"  目标章节：{state.target_section}")
    print("  修改后的策略建议章节尾部：")
    print("  " + state.report_sections["策略建议"].split("\n")[-2:][0][:80] + "…")

    # 场景 2：新增章节
    print("\n▶ 步骤 3：对话修改（INSERT）")
    print('  指令："新增一个「出海机会分析」章节"')
    state = orch.modify_report(state, "新增一个「出海机会分析」章节")
    print(f"  当前章节列表：{list(state.report_sections.keys())}")

    # 场景 3：删除章节
    print("\n▶ 步骤 4：对话修改（DELETE）")
    print('  指令："删除「综合能力雷达」章节"')
    state = orch.modify_report(state, "删除「综合能力雷达」章节")
    print(f"  当前章节列表：{list(state.report_sections.keys())}")

    print("\n✔ 对话修改报告闭环演示完成")
    print(f"  修改历史：{len(state.edit_history)} 条")


if __name__ == "__main__":
    main()
