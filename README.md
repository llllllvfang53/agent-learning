# 竞品分析 Agent（Competitor Analysis Agent）

> 一句话描述你的分析需求，自动产出一份**带引用、可对话修改、多模块差异化**的结构化研究报告。

一个面向「AI 产品岗面试作品集」的完整 Agent 项目，包含两部分：

1. **可交互 Web Demo**（`index.html`）——产品形态与交互展示，打开即用
2. **工程化 Python 多 Agent 代码库**（`src/`）——完整可运行的 Agent 架构实现，含状态机、8 核心节点、Critic 自检闭环、模块化注册表、评估与测试

支持 **竞品分析 / 市场研究 / 用户洞察 / 行业报告** 四大研究模块。

---

## ✨ 核心功能

### 1. 竞品分析（主场景）
- **对话式创建**：输入一句话需求，AI 自动解析分析对象、竞品、维度、专家视角
- **多 Agent 并行分析**：数据研究员 / 策略分析师 / 报告撰写师三线协同，进度实时可视化
- **8 章节报告**：执行摘要、竞品概览、功能对比、能力雷达、商业模式、用户反馈、竞争格局、策略建议
- **对话修改报告**：自然语言局部修改（rewrite / append / insert / delete / restyle），重建报告
- **引用溯源**：事实性陈述标注 `[srcN]`，信源按权威度分级（high / medium / low）
- **Critic 自检闭环**：信源充分性 / 切题度 / 事实准确性 / 结构逻辑四维评分

### 2. 市场研究 Agent（📈）
- TAM / SAM / SOM 市场规模建模
- 增长趋势预测、竞争密度 / CR4 集中度
- 市场细分拆解、定价与盈利模型、赛道机会评分

### 3. 用户洞察 Agent（📣）
- 38+ 平台用户声音聚合（VOC）
- 情感极性分析、痛点优先级矩阵、热门需求 Top5
- 用户画像分群、满意度驱动因子、流失归因

### 4. 行业报告 Agent（📚）
- 12 家机构研报聚合、观点交叉验证与一致性评分
- 产业链图谱、政策监管、技术趋势与里程碑

### 5. 通用能力
- **专家模式**：竞品分析 / 市场研究 / 用户研究 / 增长策略
- **多模型切换**：GPT-4o / 豆包 / DeepSeek / GLM / Kimi
- 运行模式：`mock`（零依赖开箱即跑） / `demo` / `real`（接入真实 LLM + 搜索）

---

## 🚀 快速开始

### 方式一：打开 Web Demo
```bash
open index.html          # 直接打开
python3 -m http.server 8080   # 或本地起服务，访问 http://localhost:8080
```

### 方式二：跑 Python Agent（mock 模式，零依赖）
```bash
# 一键 Demo：四模块演示 + 对话修改演示
python3 -m src.agent.demo_agent                 # 竞品分析
python3 -m src.agent.demo_agent --module market # 市场研究
python3 -m src.agent.demo_agent --module user   # 用户洞察
python3 -m src.agent.demo_agent --module industry # 行业报告

# 命令行交互（输入需求 → 生成报告 → 对话修改）
python3 -m src.ui.cli

# 示例脚本
python3 examples/run_analysis.py
python3 examples/chat_modify.py                 # 演示 rewrite/insert/delete
```

### 方式三：接入真实 LLM + 搜索
```bash
export AGENT_LLM_API_KEY=xxx          # OpenAI 兼容接口（GPT/豆包/DeepSeek/GLM/Kimi）
export AGENT_LLM_BASE_URL=https://api.openai.com/v1
export AGENT_SEARCH_API_KEY=xxx       # Tavily
python3 -m src.agent.demo_agent
```

### 运行测试与评估
```bash
python3 -m pytest tests/ -q           # 17 个单元测试（状态机/节点/工具/模块）
python3 scripts/evaluate.py --quick   # 4 组对比 + 消融实验
python3 scripts/evaluate.py --json results.json
```

---

## 🏗️ 工程结构

```
competitor-analyzer-demo/
├── index.html                      # 可交互 Web Demo（产品形态）
├── src/
│   ├── models.py                   # 数据模型：AnalysisState / Source / Citation / EditInstruction
│   ├── config.py                   # 全局配置：运行模式 / 模型列表 / 专家模式
│   ├── tools/                      # 工具层
│   │   ├── base.py                 #   Tool 抽象 + 指数退避重试 + safe_call 降级
│   │   ├── llm.py                  #   OpenAI 兼容 LLM（mock 内置模板响应 + real 调用）
│   │   ├── search.py               #   搜索（mock 信源库 / real Tavily）
│   │   ├── web_fetch.py            #   网页精读（mock 正文 / real 抓取降级 snippet）
│   │   └── citation.py             #   引用管理：URL 去重 / 权威度统计 / 引用覆盖率
│   ├── agent/
│   │   ├── graph.py                #   AgentGraph 状态机（add_node/条件路由/并行/防死循环）
│   │   ├── nodes.py                #   8 核心节点 + 对话修改（parse_edit_instruction/apply_edit）
│   │   ├── critics.py              #   CriticEngine 四维质量评分
│   │   ├── orchestrator.py         #   多 Agent 编排器（调度/进度回调/模块注入）
│   │   └── demo_agent.py           #   一键 Demo 入口
│   ├── modules/
│   │   └── registry.py             # 模块注册表：四模块差异化（角色/阶段/章节/主题色）
│   ├── prompts/                    # 核心 Prompt（intent_parser / planner / writer / critic）
│   └── ui/
│       └── cli.py                  # 命令行交互 + 对话修改循环
├── examples/
│   ├── run_analysis.py             # 便捷调用示例
│   └── chat_modify.py              # 对话修改三场景示例
├── scripts/
│   └── evaluate.py                 # 评估脚本（A 完整 Agent / B 单轮 LLM / C LLM+搜索 / D 人工基准 + 消融）
├── tests/                          # 17 个单元测试（test_graph / test_nodes / test_tools / test_modules）
└── requirements.txt
```

---

## 🧠 Agent 架构（对齐 PRD 第 6 章）

```
┌─────────────────────────────────────────────────────────────┐
│                    用户一句话需求                            │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Orchestrator（编排器）                                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  AgentGraph 状态机（可条件路由 / 可并行 / 防死循环）    │  │
│  │                                                      │  │
│  │  intent_parser → planner → searcher → filter          │  │
│  │       │              ▲                                │  │
│  │       ▼              │ 质量不达标则回退重写             │  │
│  │  reader → writer ──► critic ──► assembler ──► 报告    │  │
│  │                                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│  多 Agent 协同：数据研究员 / 策略分析师 / 报告撰写师          │
│  Critic 自检：信源充分性 / 切题度 / 事实准确性 / 结构逻辑      │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
        带引用标注的结构化报告 + 对话修改（rewrite/append/insert/delete/restyle）
```

**核心设计**
- **8 核心节点**（PRD 附录 A.2）：IntentParser → Planner → Searcher → Filter → Reader → Writer → Critic → Assembler
- **AgentGraph 轻量状态机**（零依赖实现 LangGraph 语义）：`add_node` / `add_edge` / `set_entry` / 条件路由 `route` / 线程池并行 / `max_steps` 防死循环 / `execution_trace` 执行追踪
- **Critic 自检闭环**：writer 输出 → critic 评分 → 不达标则回退重写（最多 `max_retry` 次）
- **模块差异化**（注册表驱动）：四模块复用同一状态机，通过 `ModuleConfig` 差异化 Agent 角色、阶段管线、报告章节、主题色——新增模块只需在 registry 加一条配置
- **对话修改闭环**（PRD 附录 A.4）：自然语言指令 → 解析为 `EditInstruction`（action + target_section + requirements）→ `apply_edit` 执行修改 → 重建报告

---

## 🧪 效果评估（PRD 第 9 章）

`scripts/evaluate.py` 实现 4 组对比实验 + 消融实验：

| 组别 | 说明 | 作用 |
|---|---|---|
| A 完整 Agent | 本系统全流程 | 验证整体效果 |
| B 单轮 LLM | 无 Agent 流程 | 证明编排的价值 |
| C LLM + 搜索 | 无编排 / 无 Critic | 证明 Critic 与多 Agent 的价值 |
| D 人工基准 | 专家目标值 | 对照目标 |

**消融实验**：分别去掉 Critic / Planner / Reader / 多 Agent，观察指标衰减，验证每个组件的必要性。

> mock 模式下指标用于验证流程正确性；真实质量指标（事实准确率 / 幻觉率）需接入真实 LLM + 标注集评测。

---

## 🎓 面试亮点

- **产品设计**：对标腾讯 WorkBuddy「对话式创建 + 自动化」范式，做竞品分析垂直深水区
- **Agent 架构**：多 Agent 并行 + Critic 自检闭环、对话式创建、对话修改报告（增量重生成）
- **模块化工程**：共性抽象 + 场景定制，注册表驱动扩展新研究模块
- **验证体系**：4 组对比实验 + 消融实验验证每个组件价值
- **落地能力**：从用户洞察、产品设计、Agent 架构到工程实现的全流程

---

## 📄 文档

- `index.html` — 可交互 Web Demo（产品形态演示）
- `src/` — 工程化 Python 多 Agent 实现（本仓库核心代码）
- 完整 PRD 与 Agent 架构设计详见飞书文档（含 TAM/SAM/SOM 建模、观点交叉验证、效果评估方案）

---

## ⚠️ 说明

- Demo 与 mock 模式报告数据为**示例数据**，用于展示产品交互与架构逻辑
- 生产环境需接入真实搜索 API（如 Tavily）与 LLM API（如 GPT / 豆包 / DeepSeek）

## License
MIT
