"""模块注册表：市场研究 / 用户洞察 / 行业报告 差异化配置。

设计思路（对齐 PRD 6.6「共性抽象 + 场景定制」）：
- 复用同一套 Agent 状态机与 Orchestrator
- 通过配置驱动差异化：Agent 角色 / 阶段管线 / 报告章节 / 可视化组件 / 主题色
- 新增模块 = 在 registry 里加一条配置，无需改编排器
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from src.agent.graph import AgentGraph


@dataclass
class AgentRole:
    """模块内的 Agent 角色定义。"""

    name: str                 # 展示名
    duty: str                 # 职责
    emoji: str = "🤖"


@dataclass
class ModuleConfig:
    """一个研究模块的完整配置。"""

    key: str                        # competitor / market / user / industry
    name: str                       # 展示名
    theme_color: str                # 主题色（对齐 UI）
    tagline: str                    # 一句话定位
    agents: List[AgentRole]         # 差异化 Agent 角色
    stages: List[str]               # 差异化阶段管线
    sections: List[str]             # 差异化报告章节
    build_graph: Optional[Callable[[], AgentGraph]] = None


def _default_build_graph() -> AgentGraph:
    from src.agent.graph import build_competitor_graph
    return build_competitor_graph()


# ---------------------------------------------------------------------------
# 三个研究模块的差异化定义
# ---------------------------------------------------------------------------
MODULE_REGISTRY: Dict[str, ModuleConfig] = {
    "competitor": ModuleConfig(
        key="competitor",
        name="竞品分析",
        theme_color="#3B82F6",
        tagline="多维度横评，输出差异化竞争策略",
        agents=[
            AgentRole("数据研究员", "采集竞品产品、定价、市场数据", "🔍"),
            AgentRole("策略分析师", "多维度交叉对比与机会判断", "📊"),
            AgentRole("报告撰写师", "组织素材产出结构化报告", "✍️"),
        ],
        stages=["需求解析", "信息采集", "维度对比", "策略输出"],
        sections=["执行摘要", "竞品概览", "功能对比分析", "综合能力雷达",
                  "商业模式分析", "用户反馈分析", "竞争格局分析", "策略建议"],
        build_graph=_default_build_graph,
    ),
    "market": ModuleConfig(
        key="market",
        name="市场研究",
        theme_color="#7C3AED",
        tagline="TAM/SAM/SOM 建模，量化赛道机会（对标 SimilarWeb / Sensor Tower）",
        agents=[
            AgentRole("市场数据员", "聚合市场规模、增速、渗透率数据", "📈"),
            AgentRole("建模分析师", "TAM/SAM/SOM 建模与增长预测", "🧮"),
            AgentRole("赛道评估师", "竞争密度、机会评分与进入建议", "🎯"),
        ],
        stages=["市场数据采集", "TAM/SAM/SOM 建模", "增长预测", "机会评估"],
        sections=["市场概览", "TAM/SAM/SOM 测算", "增长趋势预测", "竞争密度与CR4",
                  "市场细分拆解", "定价与盈利模型", "政策与风险", "机会评分与建议"],
        build_graph=_default_build_graph,
    ),
    "user": ModuleConfig(
        key="user",
        name="用户洞察",
        theme_color="#EC4899",
        tagline="多渠道用户声音聚合，深挖痛点与机会（对标 Zeli / Kraftful）",
        agents=[
            AgentRole("声音采集员", "聚合 38+ 平台用户评价与反馈", "📣"),
            AgentRole("情感分析员", "情感极性识别与主题聚类", "💬"),
            AgentRole("洞察研究员", "痛点矩阵、画像分群与流失归因", "🧠"),
        ],
        stages=["VOC 聚合", "情感分析", "痛点识别", "洞察输出"],
        sections=["VOC 总览", "情感极性分析", "痛点优先级矩阵", "热门需求 Top5",
                  "用户画像分群", "满意度驱动因子", "流失归因分析", "产品机会洞察"],
        build_graph=_default_build_graph,
    ),
    "industry": ModuleConfig(
        key="industry",
        name="行业研究",
        theme_color="#10B981",
        tagline="多机构研报交叉验证，还原产业全貌（对标 GPT-Researcher / deep-research）",
        agents=[
            AgentRole("研报聚合员", "聚合多机构研报与公开数据", "📚"),
            AgentRole("交叉验证员", "观点一致性评分与 FactCheck", "🧪"),
            AgentRole("产业图谱师", "产业链、政策、里程碑梳理", "🕸️"),
        ],
        stages=["研报聚合", "观点交叉验证", "产业链梳理", "结论输出"],
        sections=["行业概览", "市场规模与增速", "机构观点一致性", "产业链图谱",
                  "竞争格局", "政策与监管", "技术趋势与里程碑", "投资结论与展望"],
        build_graph=_default_build_graph,
    ),
}


def get_module_config(key: str) -> ModuleConfig:
    return MODULE_REGISTRY.get(key, MODULE_REGISTRY["competitor"])


def list_modules() -> List[str]:
    return list(MODULE_REGISTRY.keys())
