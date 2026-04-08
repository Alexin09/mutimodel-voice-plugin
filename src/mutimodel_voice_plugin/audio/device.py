"""
音频设备管理器 — 自动发现、选择、监控音频输入设备

核心场景：
- DJI Mic 通过 USB-C 接入后自动识别
- 支持热插拔检测
- 用户可在 config 中指定偏好设备名关键词（如 "DJI"）
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class AudioDevice:
    """音频输入设备信息"""

    index: int
    name: str
    channels: int
    sample_rate: int
    is_default: bool = False

    def __str__(self) -> str:
        default_mark = " [DEFAULT]" if self.is_default else ""
        return f"[{self.index}] {self.name} ({self.channels}ch, {self.sample_rate}Hz){default_mark}"


class AudioDeviceManager:
    """
    音频设备管理器

    职责：
    1. 枚举系统所有音频输入设备
    2. 根据偏好关键词自动选择最佳设备（如 "DJI"）
    3. 监控设备热插拔事件
    """

    def __init__(self, preferred_keywords: Optional[list[str]] = None):
        """
        Args:
            preferred_keywords: 偏好设备名关键词列表，按优先级排序
                               例如 ["DJI", "Wireless"] 会优先选 DJI Mic
        """
        self.preferred_keywords = preferred_keywords or []
        self._devices: list[AudioDevice] = []

    def list_devices(self) -> list[AudioDevice]:
        """枚举系统所有音频输入设备"""
        try:
            import sounddevice as sd
        except ImportError:
            logger.warning("sounddevice not installed, falling back to pyaudio")
            return self._list_devices_pyaudio()

        return self._list_devices_sounddevice()

    def _list_devices_sounddevice(self) -> list[AudioDevice]:
        """使用 sounddevice 枚举设备"""
        import sounddevice as sd

        devices = []
        default_input = sd.default.device[0]

        for i, dev in enumerate(sd.query_devices()):
            if dev["max_input_channels"] > 0:  # 只要输入设备
                devices.append(
                    AudioDevice(
                        index=i,
                        name=dev["name"],
                        channels=dev["max_input_channels"],
                        sample_rate=int(dev["default_samplerate"]),
                        is_default=(i == default_input),
                    )
                )

        self._devices = devices
        return devices

    def _list_devices_pyaudio(self) -> list[AudioDevice]:
        """使用 pyaudio 枚举设备（fallback）"""
        import pyaudio

        p = pyaudio.PyAudio()
        devices = []
        default_idx = p.get_default_input_device_info()["index"]

        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info["maxInputChannels"] > 0:
                devices.append(
                    AudioDevice(
                        index=i,
                        name=info["name"],
                        channels=info["maxInputChannels"],
                        sample_rate=int(info["defaultSampleRate"]),
                        is_default=(i == default_idx),
                    )
                )

        p.terminate()
        self._devices = devices
        return devices

    def select_best_device(self) -> AudioDevice:
        """
        根据偏好关键词自动选择最佳输入设备

        选择策略：
        1. 按 preferred_keywords 顺序匹配设备名
        2. 找不到偏好设备时，使用系统默认设备
        3. 没有默认设备时，用第一个可用设备
        """
        if not self._devices:
            self.list_devices()

        if not self._devices:
            raise RuntimeError("No audio input devices found")

        # 1. 按偏好关键词匹配
        for keyword in self.preferred_keywords:
            for device in self._devices:
                if keyword.lower() in device.name.lower():
                    logger.info(f"Selected preferred device: {device}")
                    return device

        # 2. 系统默认设备
        for device in self._devices:
            if device.is_default:
                logger.info(f"Selected default device: {device}")
                return device

        # 3. 第一个可用设备
        logger.warning(f"No preferred/default device, using first: {self._devices[0]}")
        return self._devices[0]

    async def watch_hotplug(self, callback, interval: float = 2.0):
        """
        监控设备热插拔（轮询方式）

        当 DJI Mic 被插入/拔出时触发回调

        Args:
            callback: async callable, 签名 callback(event: str, device: AudioDevice)
                      event 为 "connected" 或 "disconnected"
            interval: 轮询间隔秒数
        """
        known = {d.index: d for d in self.list_devices()}

        while True:
            await asyncio.sleep(interval)
            current = {d.index: d for d in self.list_devices()}

            # 新增设备
            for idx in current.keys() - known.keys():
                logger.info(f"Device connected: {current[idx]}")
                await callback("connected", current[idx])

            # 移除设备
            for idx in known.keys() - current.keys():
                logger.info(f"Device disconnected: {known[idx]}")
                await callback("disconnected", known[idx])

            known = current
