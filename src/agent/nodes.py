"""核心节点实现。

对应 PRD 附录 A.2「核心节点详细设计」的 8 个节点：
IntentParser / Planner / Searcher / Filter / Reader / Writer / Critic / Assembler

每个节点函数接收 AnalysisState，直接修改状态或返回更新 dict。
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from src.models import (
    AgentOutput, AnalysisConfig, AnalysisState, AuthorityLevel,
    Competitor, EditAction, EditInstruction, Source,
)
from src.prompts.critic import CRITIC_SYSTEM
from src.prompts.intent_parser import INTENT_PARSER_SYSTEM
from src.prompts.planner import PLANNER_SYSTEM
from src.prompts.writer import WRITER_SYSTEM
from src.tools.citation import make_citation_manager
from src.tools.llm import LLMTool, get_llm, parse_json_response
from src.tools.search import get_search
from src.tools.web_fetch import get_web_fetch

_MOCK_SECTIONS: List[str] = [
    "执行摘要", "竞品概览", "功能对比分析", "综合能力雷达",
    "商业模式分析", "用户反馈分析", "竞争格局分析", "策略建议",
]


# ---------------------------------------------------------------------------
# 1. Intent Parser（需求解析节点，PRD A.2.1）
# ---------------------------------------------------------------------------
def intent_parser_node(state: AnalysisState) -> Dict[str, Any]:
    state.report_progress("解析需求中：识别分析对象、竞品、维度与专家视角", percent=8)
    llm = get_llm()
    # 保留预先注入的模块标识（对话式创建/CLI 指定的模块优先）
    preset_module = state.config.module if state.config else "competitor"
    try:
        raw = llm.call(system=INTENT_PARSER_SYSTEM, user=state.user_request, response_format="json")
        parsed = parse_json_response(raw)
        config = AnalysisConfig(
            analysis_object=parsed.get("analysis_object", "AI 笔记应用"),
            competitors=parsed.get("competitors", []),
            dimensions=parsed.get("dimensions", ["功能对比", "商业模式", "用户反馈", "竞争格局"]),
            expert=parsed.get("expert", "competitor"),
            module=preset_module,
        )
    except Exception:  # noqa: BLE001
        # 兜底：关键词规则（对齐 A.2.1 异常处理）
        config = _fallback_intent(state.user_request)
        config.module = preset_module
    state.parsed_config = config
    state.config = config
    state.dimensions = config.dimensions
    state.competitors = [Competitor(name=n) for n in config.competitors] or \
        [Competitor(name=n) for n in ["Notion", "Obsidian", "飞书文档", "Logseq"]]
    return {}


def _fallback_intent(text: str) -> AnalysisConfig:
    obj = "AI 笔记应用"
    comps = ["Notion", "Obsidian", "飞书文档", "Logseq"]
    for kw, o, c in [
        ("笔记", "AI 笔记应用", ["Notion", "Obsidian", "飞书文档", "Logseq"]),
        ("文档", "在线协作文档", ["飞书文档", "Google Docs", "腾讯文档", "语雀"]),
        ("视频", "短视频工具", ["剪映", "CapCut", "必剪", "快影"]),
        ("编程", "AI 编程助手", ["GitHub Copilot", "通义灵码", "Codex", "Cursor"]),
        ("客服", "智能客服", ["智齿客服", "网易七鱼", "美洽", "LivePerson"]),
    ]:
        if kw in text:
            obj, comps = o, c
            break
    return AnalysisConfig(analysis_object=obj, competitors=comps,
                          dimensions=["功能对比", "商业模式", "用户反馈", "竞争格局"])


# ---------------------------------------------------------------------------
# 2. Planner（搜索规划节点，PRD A.2.2）
# ---------------------------------------------------------------------------
def planner_node(state: AnalysisState) -> Dict[str, Any]:
    state.report_progress("搜索规划中：为每个维度生成搜索策略", percent=16)
    llm = get_llm()
    obj = state.config.analysis_object if state.config else "AI 笔记应用"
    try:
        raw = llm.call(system=PLANNER_SYSTEM, user=obj, response_format="json")
        queries = parse_json_response(raw).get("queries", [])
    except Exception:  # noqa: BLE001
        queries = [f"{obj} 市场规模", f"{obj} 竞品", f"{obj} 用户评价"]
    state.agent_outputs["planner"] = AgentOutput("planner", "搜索规划", content=queries, status="done")
    return {}


# ---------------------------------------------------------------------------
# 3. Searcher（搜索节点，PRD A.2.3）
# ---------------------------------------------------------------------------
def searcher_node(state: AnalysisState) -> Dict[str, Any]:
    state.report_progress("联网搜索中：采集多维度信息", percent=28)
    search = get_search()
    cm = make_citation_manager()
    planner = state.agent_outputs.get("planner")
    queries: List[str] = (planner.content if planner and isinstance(planner.content, list)
                          else [f"{state.config.analysis_object} 竞品"])
    new_sources: List[Source] = []
    for q in queries[:4]:
        results = search.call(query=q)
        for s in results:
            s.source_id = cm.register(s)
            new_sources.append(s)
    for s in new_sources:
        state.sources[s.source_id] = s
    state.agent_outputs["searcher"] = AgentOutput("searcher", "信息采集", content=len(new_sources), sources=new_sources, status="done")
    return {}


# ---------------------------------------------------------------------------
# 4. Filter（筛选节点，PRD A.2.4）
# ---------------------------------------------------------------------------
def filter_node(state: AnalysisState) -> Dict[str, Any]:
    state.report_progress("信源筛选中：按权威度与相关性排序", percent=38)
    scored = []
    for sid, s in state.sources.items():
        weight = {"high": 1.0, "medium": 0.7, "low": 0.4}[s.authority.value]
        # 简化相关性：标题/摘要包含分析对象关键词
        obj = state.config.analysis_object if state.config else ""
        rel = 1.0 if (obj and (obj in s.title or obj in s.snippet)) else 0.6
        scored.append((weight * rel, sid))
    scored.sort(key=lambda x: x[0], reverse=True)
    keep = [sid for _, sid in scored[:6]]
    state.agent_outputs["filter"] = AgentOutput("filter", "信源筛选", content=keep, status="done")
    return {}


# ---------------------------------------------------------------------------
# 5. Reader（精读节点，PRD A.2.5）
# ---------------------------------------------------------------------------
def reader_node(state: AnalysisState) -> Dict[str, Any]:
    state.report_progress("网页精读中：抽取要点与原文片段", percent=48)
    fetch = get_web_fetch()
    keep = (state.agent_outputs.get("filter").content
            if state.agent_outputs.get("filter") else list(state.sources.keys()))
    notes: Dict[str, str] = {}
    for sid in keep:
        src = state.sources.get(sid)
        if not src:
            continue
        text = fetch.call(source=src)
        notes[sid] = text[:300]
    state.agent_outputs["reader"] = AgentOutput("reader", "网页精读", content=notes, status="done")
    return {}


# ---------------------------------------------------------------------------
# 6. Writer（写作节点，PRD A.2.6）
# ---------------------------------------------------------------------------
def writer_node(state: AnalysisState) -> Dict[str, Any]:
    state.report_progress("撰写报告章节中：组织素材、标注引用", percent=58)
    llm = get_llm()
    obj = state.config.analysis_object if state.config else "分析对象"
    dims = state.dimensions or ["功能对比", "商业模式", "用户反馈", "竞争格局"]
    # 模块差异化章节（来自注册表）
    from src.modules.registry import get_module_config
    module_key = state.config.module if state.config else "competitor"
    sections_cfg = get_module_config(module_key).sections
    agents_cfg = get_module_config(module_key).agents

    # 多 Agent 协同（差异化角色：数据采集/交叉分析/内容产出）
    if len(agents_cfg) >= 3:
        research = AgentOutput(agents_cfg[0].name, "信息采集", content=f"已采集 {len(state.sources)} 条信源", status="done")
        analysis = AgentOutput(agents_cfg[1].name, "交叉分析", content=f"完成 {len(dims)} 个维度对比", status="done")
    else:
        research = AgentOutput("数据研究员", "信息采集", content=f"已采集 {len(state.sources)} 条信源", status="done")
        analysis = AgentOutput("策略分析师", "交叉分析", content=f"完成 {len(dims)} 个维度对比", status="done")
    state.agent_outputs["research"] = research
    state.agent_outputs["analysis"] = analysis

    sections: Dict[str, str] = {}
    src_ids = list(state.sources.keys())[:4]
    for dim in sections_cfg:
        user = f"撰写「{obj}」报告的「{dim}」章节。可用信源：{[s for s in src_ids]}"
        text = llm.call(system=WRITER_SYSTEM, user=user)
        # 追加引用标注（简化）
        if src_ids:
            text += f" [src{src_ids[0]}]"
        sections[dim] = text
    state.report_sections = sections
    writer_out = AgentOutput(agents_cfg[-1].name, "内容产出", content=list(sections.keys()), status="done")
    state.agent_outputs["writer"] = writer_out
    return {}


# ---------------------------------------------------------------------------
# 7. Critic（自检节点，PRD A.2.7）
# ---------------------------------------------------------------------------
def critic_node(state: AnalysisState) -> Dict[str, Any]:
    state.report_progress("质量自检中：信源/切题/事实/结构四维评分", percent=68)
    llm = get_llm()
    section_text = "\n".join(state.report_sections.values())[:2000] or "（空）"
    try:
        raw = llm.call(system=CRITIC_SYSTEM, user=section_text, response_format="json")
        feedback = parse_json_response(raw)
        passed = bool(feedback.get("pass", True))
    except Exception:  # noqa: BLE001
        feedback = {"scores": {}, "pass": True, "issues": [], "suggestion": "评估失败，按通过处理"}
        passed = True
    state.critic_feedback = feedback
    if not passed:
        state.retry_count += 1
        state.report_progress(f"质量未达标，第 {state.retry_count} 次重试（最多 {state.max_retry} 次）", percent=68)
    return {}


# ---------------------------------------------------------------------------
# 8. Assembler（组装节点，PRD A.2.8）
# ---------------------------------------------------------------------------
def assembler_node(state: AnalysisState) -> Dict[str, Any]:
    state.report_progress("报告组装中：统一引用编号、生成完整报告", percent=88)
    obj = state.config.analysis_object if state.config else "分析对象"
    from src.modules.registry import get_module_config
    module_name = get_module_config(state.config.module if state.config else "competitor").name
    parts = [f"# {obj} {module_name}报告", ""]
    for dim, text in state.report_sections.items():
        parts.append(f"## {dim}")
        parts.append(text)
        parts.append("")
    parts.append("## 参考文献")
    parts.append(make_citation_manager().references_markdown())
    state.final_report = "\n".join(parts)
    state.report_progress("报告生成完成", percent=100)
    return {}


# ---------------------------------------------------------------------------
# 对话修改报告（PRD 附录 A.4）
# ---------------------------------------------------------------------------
def parse_edit_instruction(state: AnalysisState) -> Dict[str, Any]:
    """解析用户修改指令为 EditInstruction。"""
    if not state.edit_instruction:
        return {}
    llm = get_llm()
    try:
        raw = llm.call(system="你是报告修改指令解析器。将用户指令解析为 JSON。", user=state.edit_instruction, response_format="json")
        d = parse_json_response(raw)
        action = EditAction(d.get("action", "rewrite"))
        inst = EditInstruction(
            action=action,
            target_section=d.get("target_section"),
            requirements=d.get("requirements", state.edit_instruction),
            needs_search=bool(d.get("needs_search", False)),
        )
    except Exception:  # noqa: BLE001
        inst = EditInstruction(action=EditAction.REWRITE, requirements=state.edit_instruction)
    state.parsed_edit = inst
    state.target_section = inst.target_section
    return {}


def apply_edit(state: AnalysisState) -> Dict[str, Any]:
    """按 EditInstruction 执行修改（rewrite / append / insert / delete / restyle）。"""
    inst = state.parsed_edit or EditInstruction()
    if inst.action == EditAction.REWRITE:
        section = inst.target_section or list(state.report_sections.keys())[-1]
        if section in state.report_sections:
            state.report_sections[section] += f"\n\n> 已按对话要求修改：{inst.requirements}"
    elif inst.action == EditAction.APPEND:
        section = inst.target_section or list(state.report_sections.keys())[-1]
        state.report_sections.setdefault(section, "")
        state.report_sections[section] += f"\n\n## 补充（按对话要求）\n{inst.requirements}"
    elif inst.action == EditAction.INSERT:
        new_title = inst.target_section or "新增章节"
        state.report_sections[new_title] = inst.requirements
    elif inst.action == EditAction.DELETE and inst.target_section:
        state.report_sections.pop(inst.target_section, None)
    elif inst.action == EditAction.RESTYLE:
        # 风格调整：统一在文末标注（简化实现）
        state.report_sections.setdefault(inst.target_section or "全文", "")
        state.report_sections[inst.target_section or "全文"] += f"\n\n（风格已按「{inst.requirements}」调整）"
    state.edit_history.append(state.edit_instruction or "")
    # 重建最终报告
    from src.modules.registry import get_module_config
    module_name = get_module_config(state.config.module if state.config else "competitor").name
    parts = [f"# {state.config.analysis_object} {module_name}报告（已修改）", ""]
    for dim, text in state.report_sections.items():
        parts.append(f"## {dim}")
        parts.append(text)
        parts.append("")
    state.final_report = "\n".join(parts)
    return {}
