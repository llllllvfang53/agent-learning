"""工具基类。

所有 Agent 可调用工具统一继承 Tool 基类，保证：
- 统一的 call 接口
- 统一的错误处理与重试语义（对齐 PRD A.6 错误处理）
- 便于 mock / 真实实现切换
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional


class ToolError(Exception):
    """工具执行异常。"""


class Tool(ABC):
    """工具抽象基类。"""

    name: str = "tool"
    description: str = ""

    def __init__(self, retries: int = 2, backoff: float = 1.0) -> None:
        self.retries = retries
        self.backoff = backoff

    @abstractmethod
    def _execute(self, **kwargs: Any) -> Any:
        """实际执行逻辑，由子类实现。"""

    def call(self, **kwargs: Any) -> Any:
        """带重试的统一入口（指数退避，对齐 PRD A.6）。"""
        last_err: Optional[Exception] = None
        for attempt in range(self.retries + 1):
            try:
                return self._execute(**kwargs)
            except ToolError as e:
                last_err = e
                if attempt < self.retries:
                    time.sleep(self.backoff * (2 ** attempt))
        raise ToolError(f"{self.name} 连续失败 {self.retries + 1} 次: {last_err}")


def safe_call(tool: Tool, on_error: Optional[Callable[[Exception], Any]] = None, **kwargs: Any) -> Any:
    """安全调用工具，失败时返回降级结果（不阻塞整体流程）。"""
    try:
        return tool.call(**kwargs)
    except Exception as e:  # noqa: BLE001
        if on_error:
            return on_error(e)
        return None
