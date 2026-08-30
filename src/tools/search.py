"""搜索工具。

- mock 模式：返回内置的赛道示例搜索结果（含权威度标注）
- real 模式：调用 Tavily Search API
- 结果统一为结构化列表，供 Filter 节点筛选

对齐 PRD A.2.3「Searcher」与 6.5「技术选型」。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.config import settings
from src.models import AuthorityLevel, Source
from src.tools.base import Tool, ToolError

# 内置示例数据（mock 模式）：不同分析对象对应不同搜索结果
_MOCK_DB: Dict[str, List[Dict[str, Any]]] = {
    "AI 笔记应用": [
        {"url": "https://www.notion.com/product", "title": "Notion 官方产品页",
         "snippet": "Notion 提供 AI 驱动的工作空间与笔记能力，2026 年订阅用户持续增长。",
         "authority": "high", "domain": "notion.com", "date": "2026-08"},
        {"url": "https://www.obsidian.md", "title": "Obsidian 官方",
         "snippet": "Obsidian 本地优先的笔记工具，双链与插件生态强大。",
         "authority": "high", "domain": "obsidian.md", "date": "2026-08"},
        {"url": "https://36kr.com/p/ai-note-market", "title": "36氪：AI 笔记应用赛道观察",
         "snippet": "AI 笔记应用进入成长期，头部玩家加速 AI 功能迭代，垂直场景仍有空间。",
         "authority": "medium", "domain": "36kr.com", "date": "2026-07"},
        {"url": "https://zhihu.com/question/ai-note-trend", "title": "知乎：AI 笔记产品对比讨论",
         "snippet": "用户普遍关注 AI 检索准确率与多端同步体验，是主要痛点。",
         "authority": "low", "domain": "zhihu.com", "date": "2026-06"},
    ],
    "短视频工具": [
        {"url": "https://www.capcut.com", "title": "剪映 CapCut 官方",
         "snippet": "剪映提供 AI 视频剪辑与模板能力，覆盖全球创作者。",
         "authority": "high", "domain": "capcut.com", "date": "2026-08"},
        {"url": "https://www.adobe.com/premiere-pro", "title": "Adobe Premiere Pro",
         "snippet": "专业视频剪辑软件，AI 驱动的自动字幕与场景编辑。",
         "authority": "high", "domain": "adobe.com", "date": "2026-08"},
    ],
    "在线协作文档": [
        {"url": "https://www.feishu.cn/product/docs", "title": "飞书文档官方",
         "snippet": "飞书文档强调多人实时协作与知识管理，深度集成办公生态。",
         "authority": "high", "domain": "feishu.cn", "date": "2026-08"},
        {"url": "https://www.google.com/docs/about", "title": "Google Docs",
         "snippet": "Google Docs 支持多人协作与 AI 写作辅助。",
         "authority": "high", "domain": "google.com", "date": "2026-08"},
    ],
}

# 默认兜底数据
_DEFAULT = [
    {"url": "https://example.com/research/1", "title": "行业研究：赛道概览",
     "snippet": "该赛道处于成长期，市场规模保持两位数增长，竞争格局尚未固化。",
     "authority": "medium", "domain": "example.com", "date": "2026-08"},
    {"url": "https://example.com/research/2", "title": "竞品对比：头部玩家分析",
     "snippet": "头部玩家加速 AI 功能迭代，差异化竞争集中于场景深度与生态整合。",
     "authority": "medium", "domain": "example.com", "date": "2026-08"},
    {"url": "https://example.com/research/3", "title": "用户反馈：痛点与需求",
     "snippet": "用户普遍关注 AI 准确率、多端同步与定价感知，是主要机会与风险点。",
     "authority": "low", "domain": "example.com", "date": "2026-07"},
]

_AUTHORITY_MAP = {
    "high": AuthorityLevel.HIGH,
    "medium": AuthorityLevel.MEDIUM,
    "low": AuthorityLevel.LOW,
}


class SearchTool(Tool):
    """联网搜索工具。"""

    name = "search"

    def _execute(self, *, query: str, max_results: Optional[int] = None) -> List[Source]:
        max_results = max_results or settings.search_max_results
        if settings.is_mock:
            return self._mock_search(query, max_results)
        return self._real_search(query, max_results)

    def _mock_search(self, query: str, max_results: int) -> List[Source]:
        """在 mock 数据库中按关键词匹配，返回带权威度的 Source 列表。"""
        results: List[Dict[str, Any]] = []
        for key, items in _MOCK_DB.items():
            if any(kw in query for kw in key.replace(" ", "").split() if len(kw) >= 2) or \
               any(kw in key for kw in [k for k in query if len(k) >= 2]):
                results = items
                break
        if not results:
            results = _DEFAULT
        sources = []
        for item in results[:max_results]:
            sources.append(Source(
                url=item["url"],
                title=item["title"],
                snippet=item["snippet"],
                authority=_AUTHORITY_MAP.get(item.get("authority", "medium"), AuthorityLevel.MEDIUM),
                domain=item.get("domain", ""),
                published_at=item.get("date", ""),
            ))
        return sources

    def _real_search(self, query: str, max_results: int) -> List[Source]:
        if not settings.search_api_key:
            raise ToolError("搜索 API Key 未配置，请设置 AGENT_SEARCH_API_KEY 或使用 mock 模式")
        try:
            import urllib.request
            body = f'{{"query": "{query}", "max_results": {max_results}, "search_depth": "advanced"}}'.encode("utf-8")
            req = urllib.request.Request(
                "https://api.tavily.com/search",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.search_api_key}",
                },
            )
            with urllib.request.urlopen(req, timeout=settings.search_timeout) as resp:
                import json
                data = json.loads(resp.read().decode("utf-8"))
            sources = []
            for r in data.get("results", []):
                sources.append(Source(
                    url=r["url"],
                    title=r.get("title", ""),
                    snippet=r.get("content", "")[:300],
                    authority=self._guess_authority(r["url"]),
                    domain=self._extract_domain(r["url"]),
                ))
            return sources
        except Exception as e:  # noqa: BLE001
            raise ToolError(f"搜索调用失败: {e}") from e

    @staticmethod
    def _guess_authority(url: str) -> AuthorityLevel:
        high_domains = ("gov.", ".gov", "report", "annual", "official", "about.com")
        medium_domains = ("36kr.com", "eastmoney.com", "sina.com", "qq.com", "163.com")
        if any(h in url.lower() for h in high_domains):
            return AuthorityLevel.HIGH
        if any(m in url.lower() for m in medium_domains):
            return AuthorityLevel.MEDIUM
        return AuthorityLevel.LOW

    @staticmethod
    def _extract_domain(url: str) -> str:
        from urllib.parse import urlparse
        return urlparse(url).netloc


def get_search() -> SearchTool:
    return SearchTool()
