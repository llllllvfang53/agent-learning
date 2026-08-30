"""数据模型定义。

所有 Agent 流程中流转的数据结构都定义在这里，保证类型清晰、可序列化、可测试。
对齐 PRD 附录 A.1「全局状态定义（AnalysisState）」。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 枚举与常量
# ---------------------------------------------------------------------------
class AuthorityLevel(str, Enum):
    """信源权威度分级。"""

    HIGH = "high"        # 🔴 官网 / 财报 / 行业协会 / 顶级咨询
    MEDIUM = "medium"    # 🟡 主流财经 / 行业媒体
    LOW = "low"          # 🟢 自媒体 / 论坛，仅作参考


class ExpertMode(str, Enum):
    """专家模式。"""

    COMPETITOR = "competitor"   # 竞品分析专家
    MARKET = "market"           # 市场研究专家
    USER = "user"               # 用户研究专家
    GROWTH = "growth"           # 增长策略专家


class EditAction(str, Enum):
    """对话修改报告的指令动作（对齐 PRD 附录 A.4）。"""

    REWRITE = "rewrite"     # 重写目标章节
    APPEND = "append"       # 在章节后追加内容
    INSERT = "insert"       # 新增章节
    DELETE = "delete"       # 删除章节
    RESTYLE = "restyle"     # 改写风格


# ---------------------------------------------------------------------------
# 基础实体
# ---------------------------------------------------------------------------
@dataclass
class Source:
    """一条信源（网页 / 研报 / 用户评价）。"""

    url: str
    title: str
    snippet: str = ""
    authority: AuthorityLevel = AuthorityLevel.MEDIUM
    published_at: Optional[str] = None
    domain: str = ""
    source_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    @property
    def authority_label(self) -> str:
        return {"high": "🔴 高权威", "medium": "🟡 中权威", "low": "🟢 普通"}[self.authority.value]


@dataclass
class Citation:
    """一条引用。"""

    source_id: str
    statement: str
    evidence: str = ""


@dataclass
class Competitor:
    """一个竞品。"""

    name: str
    category: str = ""
    summary: str = ""
    sources: List[str] = field(default_factory=list)


@dataclass
class AgentOutput:
    """单个 Agent 的产出。"""

    agent_name: str
    role: str
    content: Any = None
    sources: List[Source] = field(default_factory=list)
    status: str = "pending"  # pending / running / done / failed


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
@dataclass
class AnalysisConfig:
    """一次分析任务的配置（对应对话式创建/手动配置的产物）。"""

    analysis_object: str = "AI 笔记应用"
    competitors: List[str] = field(default_factory=list)
    dimensions: List[str] = field(
        default_factory=lambda: ["功能对比", "商业模式", "用户反馈", "竞争格局"]
    )
    expert: str = ExpertMode.COMPETITOR.value
    model: str = "mock"          # mock / openai / doubao / deepseek / glm / kimi
    depth: str = "standard"      # fast / standard / deep
    module: str = "competitor"   # competitor / market / user / industry


# ---------------------------------------------------------------------------
# Agent 状态（PRD 附录 A.1）
# ---------------------------------------------------------------------------
@dataclass
class AnalysisState:
    """贯穿整个 Agent 流程的全局状态。"""

    # 输入
    user_request: str = ""
    config: Optional[AnalysisConfig] = None

    # 解析产物
    parsed_config: Optional[AnalysisConfig] = None

    # 数据
    competitors: List[Competitor] = field(default_factory=list)
    dimensions: List[str] = field(default_factory=list)
    sources: Dict[str, Source] = field(default_factory=dict)     # source_id -> Source
    agent_outputs: Dict[str, AgentOutput] = field(default_factory=dict)
    citations: List[Citation] = field(default_factory=list)

    # 流程
    stage: int = 0
    total_stages: int = 8
    retry_count: int = 0
    max_retry: int = 3
    critic_feedback: Dict[str, Any] = field(default_factory=dict)

    # 对话修改报告（PRD 附录 A.4）
    edit_instruction: Optional[str] = None
    parsed_edit: Optional[EditInstruction] = None
    target_section: Optional[str] = None
    edit_history: List[str] = field(default_factory=list)

    # 产出
    final_report: str = ""
    report_sections: Dict[str, str] = field(default_factory=dict)

    # 定时追踪（PRD F-009）
    cron_config: Optional[Dict[str, Any]] = None

    # 进度回调（用于 UI 展示）
    on_progress: Optional[Any] = None

    def report_progress(self, message: str, percent: Optional[float] = None) -> None:
        """向外部回调推送进度，便于 UI / CLI 实时展示。"""
        if self.on_progress:
            self.on_progress({"stage": self.stage, "message": message, "percent": percent})


@dataclass
class EditInstruction:
    """对话修改指令的解析结果（PRD 附录 A.4.1）。"""

    action: EditAction = EditAction.REWRITE
    target_section: Optional[str] = None    # None 表示全文
    requirements: str = ""
    needs_search: bool = False
