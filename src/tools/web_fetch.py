"""网页抓取工具（Reader 节点精读）。

- mock 模式：返回内置示例正文
- real 模式：urllib 抓取 + 简单正文抽取（生产可替换为 Trafilatura）
- 失败时降级返回搜索 snippet（对齐 PRD A.6 错误处理）
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from src.models import Source
from src.tools.base import Tool, ToolError

# 内置示例正文（mock）
_MOCK_PAGES: Dict[str, str] = {
    "notion.com": (
        "Notion 是一款融合笔记、文档、知识库与项目管理的 All-in-One 工作空间。"
        "其 AI 能力包括智能搜索、自动摘要、写作辅助与数据库问答。"
        "2026 年官方数据显示订阅用户持续增长，企业版占比提升至 40%。"
        "定价采用免费增值模式，个人 Pro $10/月，团队版 $20/月。"
    ),
    "obsidian.md": (
        "Obsidian 是本地优先的笔记工具，核心特性为双向链接与图谱视图，"
        "拥有超过 1800 个社区插件。采用个人免费 + 商业授权（$50/年）模式，"
        "不依赖云服务，隐私友好。"
    ),
    "36kr.com": (
        "AI 笔记应用赛道进入成长期：头部产品加速 AI 功能迭代，"
        "垂直场景（科研、教育、企业知识管理）仍有结构性机会。"
        "预计未来三年市场规模保持两位数增长。"
    ),
}

_DEFAULT_PAGE = (
    "该信息源提供了分析对象的核心描述。结合权威度与时效性，"
    "可用于支撑竞品对比、商业模式与用户反馈等维度的判断。"
)


class WebFetchTool(Tool):
    """网页正文抓取与精读工具。"""

    name = "web_fetch"

    def _execute(self, *, source: Source) -> str:
        if settings_is_mock():
            return _MOCK_PAGES.get(source.domain, _DEFAULT_PAGE)
        return self._real_fetch(source)

    def _real_fetch(self, source: Source) -> str:
        try:
            import urllib.request
            req = urllib.request.Request(
                source.url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; AgentResearch/1.0)"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
            return self._extract_text(html)
        except Exception as e:  # noqa: BLE001
            # 降级：返回搜索 snippet，不阻塞整体流程
            return source.snippet or _DEFAULT_PAGE

    @staticmethod
    def _extract_text(html: str) -> str:
        """极简 HTML 正文抽取（生产环境建议换 Trafilatura）。"""
        text = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
        text = re.sub(r"<style.*?</style>", " ", text, flags=re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()[:1500]


def settings_is_mock() -> bool:
    from src.config import settings
    return settings.is_mock


def get_web_fetch() -> WebFetchTool:
    return WebFetchTool()
