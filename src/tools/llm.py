"""LLM 调用封装。

- mock 模式：内置模板响应，用于演示与测试（无需 API Key）
- real 模式：OpenAI 兼容协议（可对接 OpenAI / 豆包 / DeepSeek / GLM / Kimi）
- 统一处理：JSON 解析兜底、重试、降级 prompt

对齐 PRD A.2.1「Intent Parser」、A.5「核心 Prompt 设计」、A.6「错误处理」。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from src.config import settings
from src.tools.base import Tool, ToolError


class LLMTool(Tool):
    """LLM 工具：完成自然语言理解与生成。"""

    name = "llm"

    def __init__(self, model: Optional[str] = None) -> None:
        super().__init__(retries=2, backoff=1.0)
        self.model = model or settings.llm_model

    # ------------------------------------------------------------------
    # 对外统一接口
    # ------------------------------------------------------------------
    def _execute(self, *, system: str, user: str, response_format: Optional[str] = None) -> str:
        if settings.is_mock:
            return self._mock_response(system, user, response_format)
        return self._real_call(system, user, response_format)

    # ------------------------------------------------------------------
    # Mock 实现
    # ------------------------------------------------------------------
    def _mock_response(self, system: str, user: str, response_format: Optional[str]) -> str:
        """根据 system prompt 标识词返回合理的 mock 输出。"""
        if "需求解析" in system or "intent" in system.lower():
            return self._mock_intent(user)
        if "搜索规划" in system or "planner" in system.lower():
            return json.dumps({"queries": ["{object} 市场规模", "{object} 竞品", "{object} 用户评价"]}, ensure_ascii=False)
        if "质量审核" in system or "critic" in system.lower():
            return json.dumps({
                "scores": {"信源充分性": 4, "切题度": 4, "事实准确性": 4, "结构逻辑": 4},
                "pass": True,
                "issues": [],
                "suggestion": "质量达标，无需修改。",
            }, ensure_ascii=False)
        if "修改指令" in system or "edit" in system.lower():
            return self._mock_edit(user)
        # 报告撰写师等默认写作响应
        return self._mock_writer(user)

    def _mock_edit(self, user: str) -> str:
        """按关键词识别修改动作（对齐 PRD A.4 指令解析）。"""
        action, target = "rewrite", None
        if "新增" in user or "增加" in user or "添加" in user:
            action, target = "insert", self._extract_quote_title(user)
        elif "删除" in user or "移除" in user or "去掉" in user:
            action, target = "delete", self._extract_quote_title(user)
        elif "追加" in user or "补充" in user or "扩展" in user:
            action = "append"
        elif "风格" in user or "语气" in user:
            action = "restyle"
        return json.dumps({
            "action": action, "target_section": target,
            "requirements": user, "needs_search": False,
        }, ensure_ascii=False)

    @staticmethod
    def _extract_quote_title(text: str) -> str:
        """提取「...」或『...』或引号中的章节名。"""
        m = re.search(r"[「『\"]([^」』\"]+)[」』\"]", text)
        return m.group(1) if m else None

    def _mock_intent(self, user: str) -> str:
        obj = "AI 笔记应用"
        for kw in [("笔记", "AI 笔记应用"), ("文档", "在线协作文档"), ("视频", "短视频工具"),
                   ("编程", "AI 编程助手"), ("客服", "智能客服"), ("市场", "低空经济市场")]:
            if kw[0] in user:
                obj = kw[1]
                break
        return json.dumps({
            "analysis_object": obj,
            "competitors": ["Notion", "Obsidian", "飞书文档", "Logseq"],
            "dimensions": ["功能对比", "商业模式", "用户反馈", "竞争格局"],
            "expert": "competitor",
        }, ensure_ascii=False)

    def _mock_writer(self, user: str) -> str:
        # 提取章节名：user 形如 撰写「AI 笔记应用」报告的「功能对比分析」章节
        # 对象名在第一组「」，章节名在最后一组「」
        quoted = re.findall(r"[「『\"]([^」』\"]+)[」』\"]", user)
        section = quoted[-1] if quoted else "执行摘要"
        obj = quoted[0] if quoted else "分析对象"
        templates = {
            "执行摘要": (
                f"**核心结论**：{obj} 赛道整体处于成长期，市场规模保持两位数增速，"
                f"竞争格局尚未固化，存在结构性进入机会。\n\n"
                f"- 头部玩家加速 AI 功能迭代，差异化优势集中在场景深度与生态整合 [src1][src2]\n"
                f"- 垂直细分场景（科研、教育、企业知识管理）尚未被充分覆盖 [src2]\n"
                f"- 建议以差异化定位切入细分场景，避开头部直接竞争"),
            "竞品概览": (
                f"**头部玩家**：Notion、Obsidian、飞书文档、Logseq 构成第一梯队 [src1][src3]\n\n"
                f"- Notion：All-in-One 工作空间，AI 能力全面，生态强\n"
                f"- Obsidian：本地优先 + 双链，隐私友好，插件生态 1800+\n"
                f"- 飞书文档：企业协作场景深，办公生态整合优势明显"),
            "功能对比分析": (
                f"**对比维度**：AI 能力、协作、生态、隐私、定价 [src1][src3]\n\n"
                f"- AI 能力：Notion 与飞书文档领先，均已落地智能检索与写作辅助\n"
                f"- 协作：飞书文档多端实时协作最佳；Obsidian 偏个人场景\n"
                f"- 定价：Notion 免费增值 $10/月起，Obsidian 个人免费、商业 $50/年"),
            "综合能力雷达": (
                f"**五维评估**（1-5）：\n\n"
                f"- AI 能力：Notion 4.5 / Obsidian 3.8 / 飞书 4.2\n"
                f"- 生态整合：Notion 4.6 / Obsidian 4.0 / 飞书 4.4\n"
                f"- 用户体验：Notion 4.2 / Obsidian 3.9 / 飞书 4.3 [src1][src3]"),
            "商业模式分析": (
                f"**模式**：免费增值 + 订阅为主 [src1]\n\n"
                f"- Notion：免费 + Pro $10/月 + 团队版 $20/月，企业版占比提升\n"
                f"- Obsidian：个人免费，商业授权 $50/年\n"
                f"- 飞书文档：以企业订阅/整体办公套件售卖为主"),
            "用户反馈分析": (
                f"**主要痛点**：AI 检索准确率、多端同步、定价感知 [src2]\n\n"
                f"- 正向反馈：AI 摘要与检索提升效率，社区生态活跃\n"
                f"- 负向反馈：部分用户反馈 AI 生成内容质量不稳定，隐私顾虑仍存"),
            "竞争格局分析": (
                f"**格局判断**：一超多强、加速集中 [src1][src2][src3]\n\n"
                f"- 头部份额持续提升，但垂直场景（科研/教育/企业知识管理）仍有空间\n"
                f"- 潜在进入者：大厂 AI 助手、垂直知识管理工具"),
            "策略建议": (
                f"**核心策略**：差异化切入 + 场景深耕\n\n"
                f"- 短期：聚焦「企业知识管理」场景，以 AI 检索准确率 + 数据安全为卖点\n"
                f"- 中期：构建插件/模板生态，提升用户粘性与网络效应\n"
                f"- 长期：向协作与工作流平台延伸，提升客单价"),
            # ---- 市场研究模块 ----
            "市场概览": (
                f"**市场阶段**：{obj} 处于成长期 [src1]\n\n"
                f"- 市场规模保持两位数增速，渗透率仍处低位，空间可观\n"
                f"- 驱动因素：技术成熟度提升、政策支持、需求场景扩大"),
            "TAM/SAM/SOM 测算": (
                f"**市场规模测算**（示例口径，需按真实数据校准）[src1][src2]\n\n"
                f"- TAM（潜在市场）：¥2,800 亿，覆盖全部相关需求场景\n"
                f"- SAM（可服务市场）：¥860 亿，考虑目标客群与区域\n"
                f"- SOM（可获取市场）：¥120 亿，按 3 年目标份额估算"),
            "增长趋势预测": (
                f"**增长判断**：未来三年 CAGR 约 22% [src1]\n\n"
                f"- 短期：需求拉动 + 政策催化\n"
                f"- 中期：供给侧降本 + 场景深化\n"
                f"- 风险：技术路线变化与监管不确定性"),
            # ---- 用户洞察模块 ----
            "VOC 总览": (
                f"**用户声音聚合**：覆盖 38+ 平台，共采集 4,200 条有效反馈 [src2]\n\n"
                f"- 主要来源：应用商店、社交媒体、客服工单、行业论坛\n"
                f"- 正向 62% / 中性 21% / 负向 17%"),
            "情感极性分析": (
                f"**情感分布**：整体偏正向 [src2]\n\n"
                f"- 正向聚焦：AI 提效、界面简洁、生态丰富\n"
                f"- 负向聚焦：AI 准确率不稳定、定价偏贵、多端同步体验差"),
            "痛点优先级矩阵": (
                f"**痛点排序**（影响度 × 频率）[src2]\n\n"
                f"- P0：AI 检索准确率（影响度 9 / 频率 8）\n"
                f"- P1：多端同步体验（影响度 8 / 频率 7）\n"
                f"- P2：定价感知偏贵（影响度 6 / 频率 6）"),
            # ---- 行业报告模块 ----
            "行业概览": (
                f"**行业阶段**：{obj} 处于快速成长期 [src1][src3]\n\n"
                f"- 产业链上下游加速协同，应用场景从点状走向规模化\n"
                f"- 头部机构一致看好中长期空间"),
            "机构观点一致性": (
                f"**12 家机构观点交叉验证** [src1][src3]\n\n"
                f"- 一致性 85%：市场规模保持两位数增长\n"
                f"- 分歧点：商业化节奏与技术路线选择\n"
                f"- 少数派观点：短期存在估值与产能风险"),
            "产业链图谱": (
                f"**产业链分层** [src1][src3]\n\n"
                f"- 上游：基础设施 / 核心零部件 / 技术供给\n"
                f"- 中游：平台 / 解决方案集成商\n"
                f"- 下游：行业应用 / 终端消费者"),
        }
        return templates.get(section, (
            f"**概述**：{section} 是本次分析的重要维度，基于多方信源交叉验证得出以下结论。\n\n"
            f"- 数据来源覆盖官方、行业媒体与用户社区 [src1][src2]\n"
            f"- 关键发现与竞争差异已在全文标注引用，便于溯源核查"))

    # ------------------------------------------------------------------
    # 真实实现（OpenAI 兼容）
    # ------------------------------------------------------------------
    def _real_call(self, system: str, user: str, response_format: Optional[str]) -> str:
        if not settings.llm_api_key:
            raise ToolError("LLM API Key 未配置，请设置 AGENT_LLM_API_KEY 或使用 mock 模式")
        try:
            import urllib.request
            body = json.dumps({
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": settings.llm_temperature,
                **({"response_format": {"type": response_format}} if response_format == "json" else {}),
            }).encode("utf-8")
            req = urllib.request.Request(
                settings.llm_base_url.rstrip("/") + "/chat/completions",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.llm_api_key}",
                },
            )
            with urllib.request.urlopen(req, timeout=settings.timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except Exception as e:  # noqa: BLE001
            raise ToolError(f"LLM 调用失败: {e}") from e


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def parse_json_response(text: str) -> Dict[str, Any]:
    """解析 LLM 返回的 JSON，容忍 markdown 代码块包裹与前后缀噪音。"""
    if not text:
        raise ToolError("LLM 返回为空")
    text = text.strip()
    # 去掉 ```json ... ``` 包裹
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    # 提取第一个 { ... } 块
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ToolError(f"无法从响应中解析 JSON: {text[:120]}")
    return json.loads(text[start : end + 1])


def get_llm(model: Optional[str] = None) -> LLMTool:
    return LLMTool(model=model)
