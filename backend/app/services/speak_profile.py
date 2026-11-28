"""口语记忆画像（M1）：当日口语数据 + 历史会话摘要 → L2 画像文本（缓存日重建）。

红线（2026-11-22 用户确认）：画像只关联口语自己的数据（跟读包/场景/计划/复盘），
与单词、阅读数据零耦合。
"""

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.speak import SpeakLog, SpeakProfile, SpeakReview
from app.services import ai_enrich, dev_mock, speak_level, usage

_CST = timezone(timedelta(hours=8))

_PROFILE_PROMPT = """You maintain a learner profile for a {name} speaking coach. Based on TODAY'S speaking activity and recent session notes, write a compact English profile (max 90 words) with exactly these parts:
1. Today: what the child practised (packs/scenes/topics) and scores.
2. Weak points: recurring grammar/vocabulary/pronunciation issues (merge duplicates).
3. Warm-up: list the review sentences due today if any are given.
No greetings, no advice, no markdown — plain lines starting with "Today:", "Weak:", "Warm-up:". If there is almost no data, write "Today: no speaking practice yet today." and skip the rest."""


def _beijing_date(dt_utc: datetime) -> str:
    return dt_utc.replace(tzinfo=timezone.utc).astimezone(_CST).strftime("%Y-%m-%d")


def today_stats(db: Session, user_id: int) -> dict:
    """今天的口语数据（北京时间），供画像与 boot 使用。"""
    today = usage.today()
    logs = (
        db.query(SpeakLog)
        .filter(SpeakLog.user_id == user_id)
        .order_by(SpeakLog.id.desc())
        .limit(30)
        .all()
    )
    todays = [r for r in logs if _beijing_date(r.created_at) == today]
    due_reviews = (
        db.query(SpeakReview)
        .filter(
            SpeakReview.user_id == user_id,
            SpeakReview.done.is_(False),
            SpeakReview.due_at != "",
            SpeakReview.due_at <= today,
        )
        .order_by(SpeakReview.due_at)
        .limit(5)
        .all()
    )
    return {
        "today_logs": todays,
        "due_reviews": due_reviews,
        "n_shadow": sum(1 for r in todays if r.mode == "shadow"),
        "n_talk": sum(1 for r in todays if r.mode == "talk"),
    }


def _fallback_profile(db: Session, user_id: int, stats: dict) -> str:
    """无 LLM Key 时的确定性画像（结构化注入，不臆造）。"""
    lines = []
    refs = sorted({r.ref for r in stats["today_logs"] if r.ref})
    scores = [r.score for r in stats["today_logs"] if r.score > 0]
    if refs or scores:
        lines.append(f"Today: practised {refs or 'speaking'}; scores {scores or 'n/a'}.")
    else:
        lines.append("Today: no speaking practice yet today.")
    issues = []
    for r in stats["today_logs"]:
        try:
            issues.extend(x for x in json.loads(r.issues or "[]") if x)
        except json.JSONDecodeError:
            continue
    if issues:
        lines.append("Weak: " + "; ".join(issues[:4]) + ".")
    if stats["due_reviews"]:
        lines.append(
            "Warm-up: repeat these sentences first: "
            + " / ".join(x.improved_en for x in stats["due_reviews"][:3])
        )
    return "\n".join(lines)


def get_profile(db: Session, user_id: int, rebuild: bool = False) -> str:
    """取当日画像；built_day 不是今天则重建（LLM 失败降级确定性文本）。

    P1-2：默认复用当日缓存，不再每次 talk boot 都调用 LLM；会话摘要后由
    `invalidate()` 清空 built_day，下一次 boot 重建。
    """
    today = usage.today()
    row = db.get(SpeakProfile, user_id)
    if row is not None and row.built_day == today and not rebuild:
        return row.content
    stats = today_stats(db, user_id)

    # 组装输入：今日口语数据 + 最近 5 条会话摘要
    facts = []
    for r in stats["today_logs"]:
        facts.append(f"- {r.mode} {r.ref or ''} score={r.score} issues={r.issues[:120]}")
    recent = (
        db.query(SpeakLog.summary)
        .filter(SpeakLog.user_id == user_id, SpeakLog.summary != "")
        .order_by(SpeakLog.id.desc())
        .limit(5)
        .all()
    )
    for (s,) in recent:
        facts.append(f"- past session note: {s}")
    if stats["due_reviews"]:
        facts.append(
            "- review sentences due today: "
            + " | ".join(f"{x.improved_en} ({x.focus})" for x in stats["due_reviews"][:5])
        )
    user_block = "\n".join(facts) or "(no data)"

    if dev_mock.is_dev():
        content = _fallback_profile(db, user_id, stats)
    else:
        content = ""
        lv = speak_level.exam_level(speak_level.exam_of(db, user_id))
        try:
            data, llm_usage = ai_enrich.chat(
                db,
                [
                    {"role": "system", "content": _PROFILE_PROMPT.format(**lv)},
                    {"role": "user", "content": user_block[:3000]},
                ],
                max_tokens=220,
                temperature=0.2,
            )
            content = str(data.get("text") or "").strip()
            usage.record_llm(db, user_id, llm_usage)
        except (LookupError, RuntimeError):
            content = ""
        if not content:
            content = _fallback_profile(db, user_id, stats)

    if row is None:
        row = SpeakProfile(user_id=user_id, built_day=today, content=content)
        db.add(row)
    else:
        row.built_day = today
        row.content = content
    db.commit()
    return content


def summarize_session(db: Session, user_id: int, log: SpeakLog) -> str:
    """会话结束：LLM 生成 ≤50 词英文摘要，落 speak_logs.summary（失败留空，不阻塞）。"""
    try:
        turns = json.loads(log.transcript or "[]")
    except json.JSONDecodeError:
        turns = []
    convo = "\n".join(
        f"{'S' if (t.get('role') or t.get('who')) in ('user', 'me') else 'AI'}: {str(t.get('text', ''))[:200]}"
        for t in turns[-20:]
    )
    if not convo.strip():
        return ""
    if dev_mock.is_dev():
        log.summary = "Dev session: speaking practice completed (mock summary)."
        db.commit()
        return log.summary
    try:
        lv = speak_level.exam_level(speak_level.exam_of(db, user_id))
        data, llm_usage = ai_enrich.chat(
            db,
            [
                {
                    "role": "system",
                    "content": (
                        f"Summarize this {lv['name']} speaking practice session in ONE English "
                        "sentence (max 40 words): what topic, how the child performed, "
                        "main weaknesses. Plain text only."
                    ),
                },
                {"role": "user", "content": convo[:2500]},
            ],
            max_tokens=90,
            temperature=0.2,
        )
        summary = str(data.get("text") or "").strip()[:500]
        usage.record_llm(db, user_id, llm_usage)
    except (LookupError, RuntimeError):
        summary = ""
    if summary:
        log.summary = summary
        db.commit()
        invalidate(db, user_id)
    return summary


def invalidate(db: Session, user_id: int) -> None:
    """会话摘要更新后让当日画像失效：下次 talk boot 重建（P1-2）。"""
    row = db.get(SpeakProfile, user_id)
    if row is not None:
        row.built_day = ""
        db.commit()
