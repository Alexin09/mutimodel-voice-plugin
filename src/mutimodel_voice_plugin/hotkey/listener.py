"""
全局快捷键监听器

按住说话（Push-to-Talk）/ 按一下开始按一下停止（Toggle）两种模式。
默认快捷键参考蛐蛐的 F2。

依赖：pynput（跨平台键盘监听）
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class HotkeyMode(Enum):
    PUSH_TO_TALK = "push_to_talk"  # 按住说，松开停
    TOGGLE = "toggle"  # 按一次开，再按停


@dataclass
class HotkeyConfig:
    """快捷键配置"""

    key: str = "f2"  # 快捷键（支持组合键如 "ctrl+shift+space"）
    mode: HotkeyMode = HotkeyMode.TOGGLE


class HotkeyListener:
    """
    全局快捷键监听器

    Usage:
        listener = HotkeyListener(
            config=HotkeyConfig(key="f2", mode=HotkeyMode.TOGGLE),
            on_start=start_recording,
            on_stop=stop_recording,
        )
        await listener.start()
    """

    def __init__(
        self,
        config: Optional[HotkeyConfig] = None,
        on_start: Optional[Callable] = None,
        on_stop: Optional[Callable] = None,
    ):
        self.config = config or HotkeyConfig()
        self.on_start = on_start
        self.on_stop = on_stop
        self._is_recording = False
        self._listener = None

    async def start(self) -> None:
        """启动热键监听（在后台线程运行）"""
        logger.info(
            f"Hotkey listener started: {self.config.key} ({self.config.mode.value})"
        )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._start_listener)

    def _start_listener(self) -> None:
        """启动 pynput 监听"""
        try:
            from pynput import keyboard

            def on_press(key):
                if self._match_key(key):
                    if self.config.mode == HotkeyMode.PUSH_TO_TALK:
                        if not self._is_recording:
                            self._is_recording = True
                            self._fire_callback(self.on_start)
                    elif self.config.mode == HotkeyMode.TOGGLE:
                        if self._is_recording:
                            self._is_recording = False
                            self._fire_callback(self.on_stop)
                        else:
                            self._is_recording = True
                            self._fire_callback(self.on_start)

            def on_release(key):
                if self._match_key(key):
                    if self.config.mode == HotkeyMode.PUSH_TO_TALK:
                        if self._is_recording:
                            self._is_recording = False
                            self._fire_callback(self.on_stop)

            self._listener = keyboard.Listener(
                on_press=on_press,
                on_release=on_release,
            )
            self._listener.start()

        except ImportError:
            logger.error("pynput not installed. Run: pip install pynput")

    def _match_key(self, key) -> bool:
        """匹配按键"""
        from pynput import keyboard

        target = self.config.key.lower()

        # 功能键匹配
        try:
            if hasattr(key, "name") and key.name and key.name.lower() == target:
                return True
        except AttributeError:
            pass

        # 普通键匹配
        try:
            if hasattr(key, "char") and key.char and key.char.lower() == target:
                return True
        except AttributeError:
            pass

        return False

    def _fire_callback(self, callback: Optional[Callable]) -> None:
        """触发回调"""
        if callback:
            try:
                result = callback()
                # 如果是协程，放入事件循环
                if asyncio.iscoroutine(result):
                    asyncio.get_event_loop().call_soon_threadsafe(
                        asyncio.ensure_future, result
                    )
            except Exception as e:
                logger.error(f"Hotkey callback error: {e}")

    def stop(self) -> None:
        """停止监听"""
        if self._listener:
            self._listener.stop()
            self._listener = None
        logger.info("Hotkey listener stopped")

    @property
    def is_recording(self) -> bool:
        return self._is_recording
