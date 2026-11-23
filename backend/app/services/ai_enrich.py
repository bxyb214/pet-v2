"""LLM 词条补全（V11）：OpenAI 兼容接口，Key 从 app_cfg 读，代码零 Key。"""
import json

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.extra import AppCfg
from app.services import dev_mock

_TIMEOUT = 15.0

_PROMPT = (
    "你是小学英语老师。给定一个英语单词，返回 JSON："
    '{{"pos": "词性缩写如 n./v./adj.", "definition": "不超过15字的中文释义", '
    '"example_en": "一个适合小学生水平的英文例句", "example_cn": "例句的中文翻译"}}。'
    '只输出 JSON，不要多余文字。单词：{word}'
)


def get_cfg(db: Session, key: str, default: str = "") -> str:
    row = db.get(AppCfg, key)
    return row.value if row else default


def set_cfg(db: Session, key: str, value: str) -> None:
    row = db.get(AppCfg, key)
    if row is None:
        db.add(AppCfg(key=key, value=value))
    else:
        row.value = value
    db.commit()


def enrich_word(db: Session, word: str) -> dict:
    """调用 LLM 生成词性/释义/例句。未配 Key 抛 LookupError，调用方转 503。"""
    if dev_mock.is_dev():
        return dev_mock.enrich_word(word)
    data = chat(db, [{"role": "user", "content": _PROMPT.format(word=word)}], max_tokens=200)
    return {
        "pos": str(data.get("pos", "")),
        "definition": str(data.get("definition", "")),
        "example_en": str(data.get("example_en", "")),
        "example_cn": str(data.get("example_cn", "")),
    }


def chat(db: Session, messages: list[dict], max_tokens: int = 300, temperature: float = 0.2) -> tuple[dict, dict | None]:
    """通用 OpenAI 兼容 chat。返回 (JSON解析结果或{"text":...}, usage)。
    未配 Key 抛 LookupError；HTTP/解析错误抛 RuntimeError（调用方决定降级）。"""
    if get_settings().dev_mode:
        # 兜底闸门：任何遗漏的 AI 调用在开发环境直接失败，绝不访问外部服务
        raise RuntimeError("开发环境已关闭外部 AI 调用")
    api_key = get_cfg(db, "llm.api_key")
    if not api_key:
        raise LookupError("未配置 AI Key")
    base_url = get_cfg(db, "llm.base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    model = get_cfg(db, "llm.model", "qwen3.8-flash")

    resp = httpx.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens},
        timeout=30.0,
    )
    resp.raise_for_status()
    body = resp.json()
    usage = body.get("usage")
    content = body["choices"][0]["message"]["content"].strip()
    content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(content), usage
    except json.JSONDecodeError:
        return {"text": content}, usage
