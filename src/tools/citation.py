"""引用管理工具。

负责：
- source_id 分配与去重
- 信源权威度分级（对齐 PRD F-006）
- 引用覆盖率统计（对齐 PRD 9.4 评估指标）
- 报告引用列表生成

对齐 PRD A.2.8「Assembler」与 F-006「引用溯源」。
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Set

from src.models import AuthorityLevel, Citation, Source


class CitationManager:
    """引用管理器：贯穿 Agent 流程的信源与引用注册中心。"""

    def __init__(self) -> None:
        self.sources: Dict[str, Source] = {}
        self.citations: List[Citation] = []

    # ------------------------------------------------------------------
    # 信源注册
    # ------------------------------------------------------------------
    def register(self, source: Source) -> str:
        """注册一条信源，返回 source_id（已存在则复用）。"""
        if source.source_id in self.sources:
            return source.source_id
        # 按 URL 去重
        for sid, existing in self.sources.items():
            if existing.url == source.url:
                return sid
        self.sources[source.source_id] = source
        return source.source_id

    def get(self, source_id: str) -> Optional[Source]:
        return self.sources.get(source_id)

    @property
    def all_sources(self) -> List[Source]:
        return list(self.sources.values())

    # ------------------------------------------------------------------
    # 引用注册
    # ------------------------------------------------------------------
    def add_citation(self, statement: str, source_ids: List[str]) -> None:
        """为一段陈述登记引用。"""
        for sid in source_ids:
            if sid in self.sources:
                self.citations.append(Citation(source_id=sid, statement=statement))

    # ------------------------------------------------------------------
    # 统计指标（对齐 PRD 9.4）
    # ------------------------------------------------------------------
    def count(self) -> int:
        return len(self.sources)

    def count_high_authority(self) -> int:
        return sum(1 for s in self.sources.values() if s.authority == AuthorityLevel.HIGH)

    def high_authority_ratio(self) -> float:
        return self.count_high_authority() / self.count() if self.count() else 0.0

    def domain_diversity(self) -> int:
        return len({s.domain for s in self.sources.values() if s.domain})

    def citation_coverage(self, report_text: str) -> float:
        """引用覆盖率：含 [srcN] 标注的事实性段落占比（简化估算）。"""
        if not report_text:
            return 0.0
        paragraphs = [p for p in report_text.split("\n\n") if len(p) > 20]
        if not paragraphs:
            return 0.0
        cited = sum(1 for p in paragraphs if re.search(r"\[src\d+\]", p))
        return round(cited / len(paragraphs), 2)

    def references_markdown(self) -> str:
        """生成参考文献列表。"""
        lines = []
        for sid, s in self.sources.items():
            lines.append(f"[{sid}] {s.title} — {s.url}（{s.authority_label}，{s.published_at}）")
        return "\n".join(lines) if lines else "暂无信源"


def make_citation_manager() -> CitationManager:
    return CitationManager()
