"""会后复盘（§5.5，M2）：会话结束 → LLM 挑句按 PET B1 改写 → 跟读 SOE 评分 → 记忆曲线。

红线：只改写孩子真实说过的话（transcript 里有原文），不臆造；
记忆曲线间隔 1/2/4/7/15 天，dims 记账语义与词汇/阅读错题一致。
"""

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.speak import SpeakLog, SpeakReview
from app.services import ai_enrich, usage

_CST = timezone(timedelta(hours=8))
_INTERVALS = [1, 2, 4, 7, 15]

_REVIEW_PROMPT = """You are a PET (B1 Preliminary for Schools) speaking teacher. Given a transcript of a child's speaking session, pick 3 to 6 sentences the child ACTUALLY SAID that need improvement. For each, output one JSON object with:
- "child_said": the child's original utterance, verbatim from the transcript (if the child only said fragments, join them minimally; never invent content the child did not say)
- "improved_en": one improved sentence at PET B1 level, keeping the child's meaning, max 18 words
- "improved_cn": 中文翻译
- "focus": one of "grammar", "vocab", "phrase"
- "dims": array of 1-2 short labels of what was weak, e.g. ["grammar:third-person-s"] or ["vocab:weekend"]
Return a JSON array only, no markdown. Prefer variety across grammar/vocab/phrase. If the child spoke very well, return fewer items (minimum 1) — do not manufacture problems."""


def generate_review(db: Session, user_id: int, log: SpeakLog) -> list[dict]:
    """按会话生成复盘句（幂等：同 log_id 重新生成时先删旧）。失败抛 LookupError/RuntimeError。"""
    try:
        turns = json.loads(log.transcript or "[]")
    except json.JSONDecodeError:
        turns = []
    child_lines = [
        str(t.get("text", "")).strip()
        for t in turns
        if (t.get("role") or t.get("who")) in ("user", "me") and len(str(t.get("text", "")).strip()) >= 3
    ]
    convo = "\n".join(f"S: {x[:220]}" for x in child_lines[:40])
    if not convo:
        return []

    data, llm_usage = ai_enrich.chat(
        db,
        [
            {"role": "system", "content": _REVIEW_PROMPT},
            {"role": "user", "content": convo[:3000]},
        ],
        max_tokens=900,
        temperature=0.3,
    )
    usage.record_llm(db, user_id, llm_usage)

    items = data if isinstance(data, list) else data.get("items", [])
    # 幂等：清掉同会话旧句再写
    db.query(SpeakReview).filter(SpeakReview.user_id == user_id, SpeakReview.log_id == log.id).delete()
    out: list[dict] = []
    today = usage.today()
    for it in items[:6]:
        if not isinstance(it, dict):
            continue
        child = str(it.get("child_said", "")).strip()[:400]
        improved = str(it.get("improved_en", "")).strip()[:200]
        dims = [str(d)[:40] for d in it.get("dims", []) if str(d).strip()][:2]
        if not child or not improved or not dims:
            continue
        row = SpeakReview(
            user_id=user_id,
            log_id=log.id,
            child_said=child,
            improved_en=improved,
            improved_cn=str(it.get("improved_cn", "")).strip()[:200],
            focus=str(it.get("focus", "grammar")).strip()[:64],
            dims=json.dumps(dims, ensure_ascii=False),
            stage=0,
            due_at=today,  # 当天即可练
        )
        db.add(row)
        db.flush()  # 先拿到自增 id，前端才能按 id 提交评分
        out.append(_to_dict(row))
    db.commit()
    return out


def import_items(
    db: Session, user_id: int, log: SpeakLog, items: list[dict]
) -> list[dict]:
    """把对话中即时优化的句子落库（同一 log + child_said 幂等更新，不清旧评分）。"""
    existing = {
        r.child_said: r
        for r in db.query(SpeakReview)
        .filter(SpeakReview.user_id == user_id, SpeakReview.log_id == log.id)
        .all()
    }
    today = usage.today()
    out: list[dict] = []
    for it in items[:12]:
        child = str(it.get("child_said", "")).strip()[:400]
        improved = str(it.get("improved_en", "")).strip()[:200]
        if not child or not improved:
            continue
        dims = [str(d)[:40] for d in it.get("dims", []) if str(d).strip()][:2]
        dims = dims or ["grammar:general"]
        row = existing.get(child)
        if row is None:
            row = SpeakReview(
                user_id=user_id,
                log_id=log.id,
                child_said=child,
                improved_en=improved,
                improved_cn=str(it.get("improved_cn", "")).strip()[:200],
                focus=str(it.get("focus", "grammar")).strip()[:64],
                dims=json.dumps(dims, ensure_ascii=False),
                stage=0,
                due_at=today,
            )
            db.add(row)
            db.flush()
        else:
            row.improved_en = improved
            row.improved_cn = str(it.get("improved_cn", "")).strip()[:200]
            row.focus = str(it.get("focus", "grammar")).strip()[:64]
            row.dims = json.dumps(dims, ensure_ascii=False)
        out.append(_to_dict(row))
    db.commit()
    return out


def _to_dict(r: SpeakReview) -> dict:
    return {
        "id": r.id,
        "log_id": r.log_id,
        "child_said": r.child_said,
        "improved_en": r.improved_en,
        "improved_cn": r.improved_cn,
        "focus": r.focus,
        "dims": json.loads(r.dims or "[]"),
        "stage": r.stage,
        "due_at": r.due_at,
        "repeats": r.repeats,
        "done": r.done,
    }


def due_items(db: Session, user_id: int, limit: int = 20) -> list[dict]:
    """到期复盘句（跟读页队列 + 会话热身用）。"""
    today = usage.today()
    rows = (
        db.query(SpeakReview)
        .filter(
            SpeakReview.user_id == user_id,
            SpeakReview.done.is_(False),
            SpeakReview.due_at != "",
            SpeakReview.due_at <= today,
        )
        .order_by(SpeakReview.due_at, SpeakReview.id)
        .limit(limit)
        .all()
    )
    return [_to_dict(r) for r in rows]


def grade(db: Session, user_id: int, review_id: int, score: int, dims_ok: list[str]) -> dict:
    """跟读评分记账：
    - <60：全部维度重新欠，回第 1 阶段，今天再来
    - 60~84：维度不变，今天再练一遍（不前进、不重置）
    - >=85：划掉 dims_ok 里的维度；全部划完则毕业，否则 stage 前进 + 按 1/2/4/7/15 天排下次
    """
    row = db.get(SpeakReview, review_id)
    if row is None or row.user_id != user_id:
        return {}
    dims: list[str] = json.loads(row.dims or "[]")
    if score < 60:
        row.stage = 0
        row.repeats += 1
        row.due_at = usage.today()
    elif score < 85:
        row.repeats += 1
        row.due_at = usage.today()
    else:
        dims = [d for d in dims if d not in set(dims_ok)]
        if not dims:
            row.done = True
        else:
            row.stage = min(row.stage + 1, len(_INTERVALS) - 1)
            row.repeats += 1
            delta = _INTERVALS[row.stage]
            row.due_at = (datetime.now(_CST) + timedelta(days=delta)).strftime("%Y-%m-%d")
        row.dims = json.dumps(dims, ensure_ascii=False)
    db.commit()
    return _to_dict(row)
