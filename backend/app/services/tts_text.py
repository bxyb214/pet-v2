"""TTS 文本规范化：GET / POST / 预生成共用同一套规则。

缓存键基于规范化后的文本，因此改规则后必须升 `speak.local.cache_version`
并重跑 `tools/build_tts.py`，否则旧音频仍会被命中。
"""
from __future__ import annotations

import re

_CJK_RE = re.compile(r"[㐀-䶿一-鿿豈-﫿]")
_SPACE_RE = re.compile(r"\s+")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([.,!?;:])")

# 常见缩写/符号：只处理会明显读错的，数字与日期交给 espeak-ng。
_ABBREVIATIONS: tuple[tuple[str, str], ...] = (
    (r"\be\.g\.", "for example"),
    (r"\bi\.e\.", "that is"),
    (r"\betc\.", "etcetera"),
    (r"\bvs\b\.?", "versus"),
    (r"\bMr\b\.?", "Mister"),
    (r"\bMrs\b\.?", "Missus"),
    (r"\bMs\b\.?", "Miss"),
    (r"\bDr\b\.?", "Doctor"),
    (r"\bNo\.(?=\s*\d)", "number"),
    (r"&", " and "),
    (r"%", " percent "),
    (r"£", " pounds "),
    (r"€", " euros "),
    (r"\$", " dollars "),
    (r"°C\b", " degrees Celsius "),
)

# 考试缩写按字母读，避免被当成普通单词。
_EXAM_ACRONYMS = re.compile(r"\b(PET|KET|FCE|CAE|CPE|CEFR|IELTS|TOEFL)\b")
_MARKDOWN = re.compile(r"[*_#`~]+")


def english_only(s: str) -> str:
    """截到第一个汉字前，与前端 `englishOnly()` 保持一致。"""
    text = s or ""
    m = _CJK_RE.search(text)
    return (text[: m.start()] if m else text).strip()


def has_cjk(s: str) -> bool:
    return bool(_CJK_RE.search(s or ""))


def normalize_for_tts(text: str, pronounce: dict[str, str] | None = None) -> str:
    """英文 TTS 规范化；输入为空或规范化后为空时返回空串。"""
    s = english_only(text)
    if not s:
        return ""
    s = _EXAM_ACRONYMS.sub(lambda m: " ".join(m.group(1)), s)
    for pattern, repl in _ABBREVIATIONS:
        s = re.sub(pattern, repl, s, flags=re.IGNORECASE)
    s = _MARKDOWN.sub(" ", s)
    s = _SPACE_RE.sub(" ", s).strip()
    s = _SPACE_BEFORE_PUNCT.sub(r"\1", s)
    if pronounce:
        for word, said in pronounce.items():
            if not word or not said:
                continue
            s = re.sub(rf"\b{re.escape(word)}\b", said, s, flags=re.IGNORECASE)
        s = _SPACE_RE.sub(" ", s).strip()
    return s


def truncate_text(text: str, max_chars: int) -> str:
    """超长时尽量在句末截断，避免半个单词/半个句子。"""
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    for sep in (". ", "! ", "? ", "; ", "。", "！", "？", "；"):
        i = cut.rfind(sep)
        if i >= max_chars // 2:
            return cut[: i + 1].strip()
    i = cut.rfind(" ")
    return (cut[:i] if i > 0 else cut).strip()
