"""
豆包流式语音识别 2.0（Doubao Streaming ASR 2.0）

特点：
- 实时流式识别，延迟极低
- 成本极低（1小时 ≈ 1 RMB）
- 中文 + 中英混排识别精度高
- 基于 WebSocket 的流式协议

API 文档参考：https://www.volcengine.com/docs/6561/
"""

from __future__ import annotations

import asyncio
import gzip
import json
import logging
import uuid
from dataclasses import dataclass
from typing import AsyncGenerator, Optional

from .base import ASRResult, BaseASREngine
from .registry import EngineRegistry

logger = logging.getLogger(__name__)


@dataclass
class DoubaoConfig:
    """豆包 ASR 配置"""

    app_id: str = ""
    access_token: str = ""
    cluster: str = "volcengine_streaming_common"
    # 音频参数
    format: str = "pcm"  # pcm / wav / mp3 / ogg
    codec: str = "raw"  # raw / gzip
    sample_rate: int = 16000
    bits: int = 16
    channels: int = 1
    # 识别参数
    language: str = "zh-CN"  # zh-CN / en-US / auto
    show_utterances: bool = True  # 返回分句结果
    result_type: str = "full"  # full / single
    # WebSocket
    ws_url: str = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"


class DoubaoEngine(BaseASREngine):
    """
    豆包流式 ASR 引擎

    实现了 BaseASREngine 接口，通过 WebSocket 与豆包服务通信。

    Usage:
        engine = DoubaoEngine(
            app_id="your_app_id",
            access_token="your_token",
        )
        await engine.initialize()

        async for result in engine.recognize_stream(audio_stream):
            print(result.text, "FINAL" if result.is_final else "partial")
    """

    def __init__(self, **kwargs):
        self.config = DoubaoConfig(
            **{
                k: v
                for k, v in kwargs.items()
                if k in DoubaoConfig.__dataclass_fields__
            }
        )
        self._ws = None

    @property
    def name(self) -> str:
        return "doubao"

    @property
    def is_local(self) -> bool:
        return False

    @property
    def supports_streaming(self) -> bool:
        return True

    async def initialize(self) -> None:
        """验证配置"""
        if not self.config.app_id or not self.config.access_token:
            raise ValueError("DoubaoEngine requires app_id and access_token")
        logger.info("DoubaoEngine initialized")

    async def shutdown(self) -> None:
        if self._ws:
            await self._ws.close()
            self._ws = None

    def _build_connect_payload(self) -> dict:
        """构建 WebSocket 连接参数"""
        return {
            "header": {
                "appid": self.config.app_id,
                "token": self.config.access_token,
                "cluster": self.config.cluster,
                "custom_ws_id": str(uuid.uuid4()),
            },
            "payload": {
                "audio": {
                    "format": self.config.format,
                    "codec": self.config.codec,
                    "sample_rate": self.config.sample_rate,
                    "bits": self.config.bits,
                    "channel": self.config.channels,
                    "language": self.config.language,
                },
                "params": {
                    "show_utterances": self.config.show_utterances,
                    "result_type": self.config.result_type,
                },
            },
        }

    async def recognize_stream(
        self, audio_stream: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[ASRResult, None]:
        """
        流式识别实现

        协议流程：
        1. WebSocket 连接 + 发送 full_client_request
        2. 循环发送音频块（audio_only_request）
        3. 接收中间/最终识别结果
        4. 发送结束信号（last audio）
        """
        try:
            import websockets
        except ImportError:
            raise ImportError("Please install websockets: pip install websockets")

        connect_payload = self._build_connect_payload()

        async with websockets.connect(
            self.config.ws_url,
            extra_headers={
                "Authorization": f"Bearer; {self.config.access_token}",
            },
            max_size=None,
        ) as ws:
            self._ws = ws

            # 发送连接请求
            await ws.send(
                json.dumps(
                    {
                        "type": "full_client_request",
                        **connect_payload,
                    }
                )
            )

            # 启动接收任务
            result_queue: asyncio.Queue[Optional[ASRResult]] = asyncio.Queue()
            recv_task = asyncio.create_task(self._receive_results(ws, result_queue))

            # 发送音频块
            try:
                is_first = True
                async for chunk in audio_stream:
                    msg = {
                        "type": "audio_only_request",
                        "payload": {
                            "audio": {
                                "data": self._encode_audio(chunk),
                                "is_last": False,
                            },
                        },
                    }
                    if is_first:
                        msg["type"] = "full_client_request"
                        msg.update(connect_payload)
                        is_first = False
                    await ws.send(json.dumps(msg))

                # 发送结束信号
                await ws.send(
                    json.dumps(
                        {
                            "type": "audio_only_request",
                            "payload": {
                                "audio": {
                                    "data": "",
                                    "is_last": True,
                                },
                            },
                        }
                    )
                )
            except Exception as e:
                logger.error(f"Error sending audio: {e}")

            # 收集结果
            while True:
                result = await result_queue.get()
                if result is None:
                    break
                yield result

            recv_task.cancel()

    async def _receive_results(self, ws, result_queue: asyncio.Queue) -> None:
        """接收 WebSocket 消息并解析识别结果"""
        try:
            async for msg in ws:
                data = json.loads(msg)

                if "payload" in data and "result" in data["payload"]:
                    result_data = data["payload"]["result"]
                    text = result_data.get("text", "")
                    is_final = result_data.get("is_final", False)

                    if text:
                        await result_queue.put(
                            ASRResult(
                                text=text,
                                is_final=is_final,
                                confidence=result_data.get("confidence", 1.0),
                                language=result_data.get("language"),
                                raw=data,
                            )
                        )

                # 检查是否为最后一条消息
                if data.get("is_last_package", False):
                    break

        except Exception as e:
            logger.error(f"Error receiving results: {e}")
        finally:
            await result_queue.put(None)  # 结束信号

    @staticmethod
    def _encode_audio(chunk: bytes) -> str:
        """编码音频数据为 base64"""
        import base64

        return base64.b64encode(chunk).decode("utf-8")

    async def recognize(self, audio_data: bytes) -> ASRResult:
        """整段识别（通过流式接口模拟）"""

        async def _single_chunk():
            yield audio_data

        final_result = ASRResult(text="")
        async for result in self.recognize_stream(_single_chunk()):
            if result.is_final:
                final_result = result

        return final_result


# 自动注册
EngineRegistry.register("doubao", DoubaoEngine)
