"""
LLM 智能润色处理器

用大语言模型对 ASR 文本进行：
- 上下文纠错（"周三开会不对是周四" → "周四开会"）
- 语句润色（口语 → 书面语）
- 结构化输出（根据场景自动格式化为邮件/会议纪要/代码注释等）

支持任何兼容 OpenAI API 的服务商：
- 国产：通义千问、Kimi、智谱、豆包
- 国外：OpenAI、Anthropic
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Optional

from .base import BaseProcessor, ProcessorResult

logger = logging.getLogger(__name__)

# 默认系统提示词
DEFAULT_SYSTEM_PROMPT = """你是一个语音转文字的后处理助手。你的任务是将语音识别的原始文本优化为自然、准确的书面文字。

规则：
1. 修正明显的语音识别错误（同音字、谐音词）
2. 删除重复和自我纠正的部分（如"周三，不对，周四开会"→"周四开会"）
3. 补充必要的标点符号
4. 保持原意不变，不要添加原文没有的信息
5. 不要添加任何解释，直接输出优化后的文字
6. 如果原文已经很好，直接原样输出"""


@dataclass
class LLMPolishConfig:
    """LLM 润色配置"""

    # API 配置
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"  # 兼容 OpenAI 接口
    model: str = "gpt-4o-mini"
    # 提示词
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    # 生成参数
    temperature: float = 0.3  # 低温度 = 更忠实原文
    max_tokens: int = 2048
    # 超时
    timeout: float = 10.0
    # 是否启用（可以全局关闭 LLM 润色来省钱/提速）
    enabled: bool = True


class LLMPolishProcessor(BaseProcessor):
    """
    LLM 润色处理器

    调用兼容 OpenAI 的 LLM API 对 ASR 文本进行智能优化。
    """

    def __init__(self, config: LLMPolishConfig | None = None, **kwargs):
        if config:
            self.config = config
        else:
            self.config = LLMPolishConfig(
                **{
                    k: v
                    for k, v in kwargs.items()
                    if k in LLMPolishConfig.__dataclass_fields__
                }
            )
        self._client = None

    @property
    def name(self) -> str:
        return "llm_polish"

    @property
    def enabled(self) -> bool:
        return self.config.enabled and bool(self.config.api_key)

    async def _get_client(self):
        """懒加载 httpx 客户端"""
        if self._client is None:
            import httpx

            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.config.timeout,
            )
        return self._client

    async def process(self, result: ProcessorResult) -> ProcessorResult:
        if not self.enabled:
            return result

        if not result.text.strip():
            return result

        try:
            polished = await self._call_llm(result.text)
            if polished:
                result.metadata["llm_original"] = result.text
                result.text = polished
        except Exception as e:
            logger.warning(f"LLM polish failed, keeping original text: {e}")
            # LLM 失败不阻塞流程

        return result

    async def _call_llm(self, text: str) -> Optional[str]:
        """调用 LLM API"""
        client = await self._get_client()

        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": self.config.system_prompt},
                {"role": "user", "content": text},
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        response = await client.post("/chat/completions", json=payload)
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]

        return content.strip() if content else None

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None
