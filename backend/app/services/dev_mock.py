"""开发/测试环境的确定性模拟结果：不调用任何外部 AI 服务。

由 `PET_DEV_MODE=1` 开启。返回结构、字段与真实接口完全一致，
让前端整套流程（跟读 / 对话 / 优化 / 复盘 / 造句 / 加词 / TTS）可以离线跑通。
"""

from __future__ import annotations

import base64
import io
import math
import re
import struct
import wave
from functools import lru_cache

from app.core.config import get_settings

# 只做最常见的 B1 小错修正，保证模拟结果可读、可验收；不臆造新内容。
_FIXES = (
    (r"\bI like play\b", "I like playing"),
    (r"\bI very like\b", "I really like"),
)


def is_dev() -> bool:
    return bool(get_settings().dev_mode)


def sentence(text: str) -> str:
    """把输入整理成一句完整英文：首字母大写、补句号、常见小错修正。"""
    s = " ".join(str(text or "").split()).strip()
    if not s:
        return "I like learning English."
    for pattern, replacement in _FIXES:
        s = re.sub(pattern, replacement, s, flags=re.IGNORECASE)
    s = s[0].upper() + s[1:]
    if s[-1] not in ".!?":
        s += "."
    return s[:200]


def improve(text: str) -> dict:
    original = " ".join(str(text or "").split()).strip()[:400]
    return {
        "child_said": original,
        "improved_en": sentence(original),
        "improved_cn": "开发环境模拟：把这句话整理成完整、自然的 PET B1 句子。",
        "focus": "grammar",
        "dims": ["grammar:sentence"],
    }


def check(sentence_text: str) -> dict:
    return {
        "ok": True,
        "comment": "开发环境模拟判定：句子结构完整，表达清楚。",
        "improved": sentence(sentence_text),
    }


def help_payload(scene_title: str = "") -> dict:
    topic = f"「{scene_title}」" if scene_title else "这个话题"
    return {
        "cn": f"开发环境提示：围绕{topic}，用「主语 + 动词 + 宾语」说一句完整的话。",
        "en": "I would like to tell you about my weekend.",
        "en_cn": "我想和你说说我的周末。",
    }


def review_items(child_lines: list[str]) -> list[dict]:
    """会话复盘：只取孩子真实说过的话，做确定性改写；最多 3 条。"""
    out: list[dict] = []
    seen: set[str] = set()
    for raw in child_lines:
        line = " ".join(str(raw or "").split()).strip()
        if len(line) < 3 or line in seen:
            continue
        seen.add(line)
        out.append(
            {
                "child_said": line[:400],
                "improved_en": sentence(line),
                "improved_cn": "开发环境模拟：整理成完整句子。",
                "focus": "grammar",
                "dims": ["grammar:sentence"],
            }
        )
        if len(out) >= 3:
            break
    return out


def enrich_word(word: str) -> dict:
    w = " ".join(str(word or "").split()).strip()[:64] or "word"
    return {
        "pos": "n.",
        "definition": f"{w}（开发环境模拟释义）",
        "example_en": f"I use the word {w} in my English class.",
        "example_cn": f"我在英语课上使用 {w} 这个词。",
    }


@lru_cache(maxsize=1)
def _beep_wav_b64() -> str:
    """0.25 秒轻提示音：让「听示范」按钮在无 AI 时也有可播放的音频。"""
    rate = 16_000
    frames = bytearray()
    for i in range(int(rate * 0.25)):
        value = int(0.12 * 32767 * math.sin(2 * math.pi * 660 * i / rate))
        frames += struct.pack("<h", value)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
    return base64.b64encode(buf.getvalue()).decode()


def tts_payload() -> dict:
    return {"mime": "audio/wav", "b64": _beep_wav_b64(), "cached": False, "dev": True}
