"""配置管理。

支持三种运行模式：
- mock      : 内置示例数据，无需任何 API Key，开箱即用（演示/测试）
- demo      : 与 mock 相同，但保留真实调用路径的占位
- real      : 接入真实搜索 API（Tavily）与 LLM API（OpenAI 兼容）

优先级：环境变量 > 配置文件 > 默认值。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Settings:
    """全局配置。"""

    # 运行模式
    run_mode: str = field(default_factory=lambda: os.getenv("AGENT_RUN_MODE", "mock"))

    # LLM 配置（OpenAI 兼容）
    llm_provider: str = field(default_factory=lambda: os.getenv("AGENT_LLM_PROVIDER", "openai"))
    llm_api_key: str = field(default_factory=lambda: os.getenv("AGENT_LLM_API_KEY", ""))
    llm_base_url: str = field(default_factory=lambda: os.getenv("AGENT_LLM_BASE_URL", "https://api.openai.com/v1"))
    llm_model: str = field(default_factory=lambda: os.getenv("AGENT_LLM_MODEL", "gpt-4o"))
    llm_temperature: float = 0.3

    # 搜索配置
    search_provider: str = field(default_factory=lambda: os.getenv("AGENT_SEARCH_PROVIDER", "tavily"))
    search_api_key: str = field(default_factory=lambda: os.getenv("AGENT_SEARCH_API_KEY", ""))
    search_max_results: int = 8
    search_timeout: int = 10

    # Agent 流程参数
    max_retry: int = 3                    # Critic 最大重试次数
    parallel_agents: bool = True          # 是否启用多 Agent 并行
    timeout_seconds: int = 300

    # 向量库 / 缓存
    vector_store_backend: str = "memory"  # memory / chroma
    cache_dir: str = field(default_factory=lambda: os.path.join(os.getcwd(), ".cache"))

    # 模型可用列表（对齐 UI 的多模型切换）
    available_models: List[str] = field(default_factory=lambda: [
        "mock", "gpt-4o", "doubao-pro", "deepseek-v4", "glm-5", "kimi-k2",
    ])

    # 专家模式映射（对齐 UI 的专家模式）
    expert_prompts: Dict[str, str] = field(default_factory=lambda: {
        "competitor": "竞品分析专家：多维度横评，输出差异化策略",
        "market": "市场研究专家：侧重市场规模与增长趋势",
        "user": "用户研究专家：侧重用户反馈与痛点洞察",
        "growth": "增长策略专家：侧重增长路径与获客策略",
    })

    @property
    def is_mock(self) -> bool:
        return self.run_mode in ("mock", "demo")

    def ensure_cache_dir(self) -> None:
        os.makedirs(self.cache_dir, exist_ok=True)


# 模块级单例
settings = Settings()
