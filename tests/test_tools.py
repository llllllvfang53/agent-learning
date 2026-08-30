"""测试：工具层（搜索 / 引用管理 / JSON 解析）。"""
from __future__ import annotations

from src.models import AuthorityLevel, Source
from src.tools.citation import CitationManager, make_citation_manager
from src.tools.llm import parse_json_response
from src.tools.search import get_search


def test_search_mock_returns_sources():
    search = get_search()
    sources = search.call(query="AI 笔记应用 市场规模")
    assert len(sources) > 0
    assert all(isinstance(s, Source) for s in sources)
    assert all(s.url for s in sources)


def test_citation_manager_dedup_by_url():
    cm = make_citation_manager()
    s1 = Source(url="https://a.com/1", title="A", authority=AuthorityLevel.HIGH, domain="a.com")
    s2 = Source(url="https://a.com/1", title="A 副本", authority=AuthorityLevel.HIGH, domain="a.com")
    id1 = cm.register(s1)
    id2 = cm.register(s2)
    assert id1 == id2  # 按 URL 去重
    assert cm.count() == 1


def test_citation_manager_metrics():
    cm = make_citation_manager()
    cm.register(Source(url="https://a.com", title="A", authority=AuthorityLevel.HIGH, domain="a.com"))
    cm.register(Source(url="https://b.com", title="B", authority=AuthorityLevel.MEDIUM, domain="b.com"))
    cm.register(Source(url="https://c.com", title="C", authority=AuthorityLevel.LOW, domain="c.com"))
    assert cm.count() == 3
    assert cm.count_high_authority() == 1
    assert cm.high_authority_ratio() == 1 / 3
    assert cm.domain_diversity() == 3


def test_citation_coverage():
    cm = make_citation_manager()
    cm.register(Source(url="https://a.com", title="A", domain="a.com"))
    text = (
        "根据多方信源交叉验证，该产品整体处于成长期，市场规模保持两位数增长，建议持续关注头部玩家动态 [src1]。\n\n"
        "头部玩家加速 AI 功能迭代，差异化竞争集中于场景深度与生态整合，垂直细分场景仍有结构性机会 [src1]。\n\n"
        "这是没有标注引用的段落内容，仅供演示引用覆盖率计算逻辑。"
    )
    coverage = cm.citation_coverage(text)
    assert 0 < coverage < 1


def test_parse_json_with_fence():
    text = '```json\n{"a": 1}\n```'
    assert parse_json_response(text) == {"a": 1}


def test_parse_json_with_noise():
    text = '解释如下：{"analysis_object": "飞书文档"} 完毕'
    assert parse_json_response(text)["analysis_object"] == "飞书文档"
