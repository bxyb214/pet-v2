"""同步合并语义（红线）：全部纯函数，前后端同语义。

原则：合并 = 保留「欠得多/进度多」的状态，绝不覆盖丢失。
"""
from __future__ import annotations

import json
from typing import Any, TypedDict


def _split(s: Any) -> list[str]:
    """兼容 list / 逗号分隔字符串两种输入。"""
    if isinstance(s, list):
        return [str(x) for x in s if x]
    return [x for x in (s or "").split(",") if x]


def _join(items: list[str]) -> str:
    return ",".join(sorted(set(items)))


class MistakeItem(TypedDict):
    word_id: str
    dims: list[str]
    stage: int
    due_at: str
    repeats: int


def merge_mastery(server: list[dict], client: list[dict]) -> list[dict]:
    """mastered_dims 并集，返回 list 形式。"""
    by_id: dict[str, set[str]] = {}
    for r in [*server, *client]:
        by_id.setdefault(r["word_id"], set()).update(_split(r.get("mastered_dims")))
    return [{"word_id": k, "mastered_dims": sorted(v)} for k, v in sorted(by_id.items())]


def merge_mistakes(server: list[dict], client: list[dict]) -> list[dict]:
    """dims 并集；stage 取小、due_at 取早、repeats 取小（欠得多者优先）。

    仅在单侧存在时直接保留该侧。
    """
    srv = {r["word_id"]: r for r in server}
    out: dict[str, dict] = {}
    for r in client:
        wid = r["word_id"]
        if wid in srv:
            out[wid] = _merge_one_mistake(srv[wid], r)
        else:
            out[wid] = dict(r)
    for wid, r in srv.items():
        if wid not in out:
            out[wid] = dict(r)
    return [out[k] for k in sorted(out)]


def _merge_one_mistake(a: dict, b: dict) -> dict:
    dims = _join([*a.get("dims", []), *b.get("dims", [])]).split(",")
    dims = [d for d in dims if d]
    return {
        "word_id": a["word_id"],
        "dims": dims,
        "stage": min(a.get("stage", 0), b.get("stage", 0)),
        "due_at": min(a.get("due_at") or "9999-99-99", b.get("due_at") or "9999-99-99"),
        "repeats": min(a.get("repeats", 0), b.get("repeats", 0)),
    }


def _seen_list(v: Any) -> list[str]:
    if isinstance(v, list):
        return [str(x) for x in v]
    try:
        parsed = json.loads(v or "[]")
        return [str(x) for x in parsed] if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def merge_progress(server: list[dict], client: list[dict]) -> list[dict]:
    """seen 并集 + idx 取大。"""
    by_key: dict[str, dict] = {}
    for r in [*server, *client]:
        key = r["key"]
        if key not in by_key:
            by_key[key] = {"key": key, "seen": set(_seen_list(r.get("seen"))), "idx": r.get("idx", 0)}
        else:
            cur = by_key[key]
            cur["seen"].update(_seen_list(r.get("seen")))
            cur["idx"] = max(cur["idx"], r.get("idx", 0))
    return [
        {"key": k, "seen": sorted(v["seen"]), "idx": v["idx"]} for k, v in sorted(by_key.items())
    ]


def _plan_at(plan: dict, key: str) -> int:
    try:
        return int(plan.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def merge_plan(server: dict | None, client: dict | None) -> dict:
    """计划合并。

    - 创建/删除/改天数属于“结构性变更”，用 plan_updated_at / reading_updated_at
      取较新的一方；否则删除后会被服务端旧计划并回来。
    - 同一代际（时间戳相同，含老数据）仍保持红线语义：days_done 并集、length 取非 0。
    - 词汇与阅读计划各自独立。
    """
    srv = server or {}
    cli = client or {}
    srv_days = set(_seen_list(srv.get("days_done")))
    cli_days = set(_seen_list(cli.get("days_done")))
    srv_rdays = set(_seen_list(srv.get("reading_days_done")))
    cli_rdays = set(_seen_list(cli.get("reading_days_done")))

    srv_at = _plan_at(srv, "plan_updated_at")
    cli_at = _plan_at(cli, "plan_updated_at")
    if cli_at > srv_at:
        length = cli.get("length") or 0
        days = cli_days
    elif srv_at > cli_at:
        length = srv.get("length") or 0
        days = srv_days
    else:
        length = cli.get("length") or srv.get("length") or 0
        days = srv_days | cli_days

    srv_rat = _plan_at(srv, "reading_updated_at")
    cli_rat = _plan_at(cli, "reading_updated_at")
    if cli_rat > srv_rat:
        rlength = cli.get("reading_length") or 0
        rdays = cli_rdays
        rbooks = _seen_list(cli.get("reading_books"))
    elif srv_rat > cli_rat:
        rlength = srv.get("reading_length") or 0
        rdays = srv_rdays
        rbooks = _seen_list(srv.get("reading_books"))
    else:
        rlength = cli.get("reading_length") or srv.get("reading_length") or 0
        rdays = srv_rdays | cli_rdays
        # 教材选择是「同一份计划的属性」，不做并集：客户端非空即以客户端为准
        rbooks = _seen_list(cli.get("reading_books")) or _seen_list(srv.get("reading_books"))

    return {
        "length": length,
        "days_done": sorted(days, key=lambda x: int(x)),
        "reading_length": rlength,
        "reading_days_done": sorted(rdays, key=lambda x: int(x)),
        "reading_books": sorted(set(rbooks)),
        "plan_updated_at": max(srv_at, cli_at),
        "reading_updated_at": max(srv_rat, cli_rat),
    }


def merge_custom_words(server: list[dict], client: list[dict]) -> list[dict]:
    """按 word 小写为业务键取并集；同词双侧内容不同 → 服务端优先（人工修正场景，避免复杂三方合并）。

    id 仅作本地列表 key，不参与合并键。
    """
    by_word: dict[str, dict] = {}
    for r in client:
        by_word[r["word"].lower()] = dict(r)
    for r in server:
        by_word[r["word"].lower()] = dict(r)  # 服务端覆盖
    return sorted(by_word.values(), key=lambda r: r["word"].lower())


def merge_custom_sentences(server: list[dict], client: list[dict]) -> list[dict]:
    """按 sid 为业务键取并集；冲突服务端优先（与 custom_words 一致）。"""
    by_sid: dict[str, dict] = {}
    for r in client:
        by_sid[r["sid"]] = dict(r)
    for r in server:
        by_sid[r["sid"]] = dict(r)
    return sorted(by_sid.values(), key=lambda r: r["sid"])


def merge_sync_data(server: dict, client: dict) -> dict:
    """六类数据合并入口。"""
    return {
        "mastery": merge_mastery(server.get("mastery", []), client.get("mastery", [])),
        "mistakes": merge_mistakes(server.get("mistakes", []), client.get("mistakes", [])),
        "progress": merge_progress(server.get("progress", []), client.get("progress", [])),
        "plan": merge_plan(server.get("plan"), client.get("plan")),
        "custom_words": merge_custom_words(
            server.get("custom_words", []), client.get("custom_words", [])
        ),
        "custom_sentences": merge_custom_sentences(
            server.get("custom_sentences", []), client.get("custom_sentences", [])
        ),
    }
