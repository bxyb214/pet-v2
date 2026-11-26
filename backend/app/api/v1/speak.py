"""口语路由（S 组）：boot / sdp / log / days / 复盘 / 求助。密钥不出服务端。

付费接口统一走 `require_paid_ai`（P0-1）；免费接口只要求登录。
TTS 已拆到 `speak_media.py`（静态 URL + 缓存治理）。
"""
import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import check_paid_or_raise, get_current_user, require_paid_ai
from app.db import get_db
from app.models.speak import SpeakDay, SpeakLog, SpeakPlan, SpeakTime
from app.models.user import User
from app.services import budget, dev_mock, qwen_speak, speak_profile, speak_review, tencent_soe, usage

router = APIRouter(prefix="/speak", tags=["speak"])


class BootIn(BaseModel):
    mode: str = Field(pattern="^(shadow|talk)$")
    day: int = Field(default=0, ge=0, le=365)
    target: str = Field(default="", max_length=500)
    scene_title: str = Field(default="", max_length=200)
    scene_focus: str = Field(default="", max_length=500)
    patterns: list[str] = Field(default_factory=list, max_length=10)


@router.post("/boot")
def boot(body: BootIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """拼会话提示词（talk 附带历史问题摘要 + 当日画像 + 到期复盘热身句）。

    shadow 只拼评测提示词，不产生外部费用；talk 会生成/复用画像，走付费闸门。
    """
    if body.mode == "talk":
        check_paid_or_raise(db, user)
    issues = qwen_speak.recent_issues(db, user.id) if body.mode == "talk" else []
    scores = (
        db.query(SpeakLog.score)
        .filter(SpeakLog.user_id == user.id, SpeakLog.mode == "talk", SpeakLog.score > 0)
        .order_by(SpeakLog.id.desc())
        .limit(10)
        .all()
    )
    avg = round(sum(s[0] for s in scores) / len(scores)) if scores else 0
    profile = ""
    warmup: list[str] = []
    if body.mode == "talk":
        try:
            profile = speak_profile.get_profile(db, user.id)
            warmup = [x["improved_en"] for x in speak_review.due_items(db, user.id, limit=3)]
        except Exception:  # noqa: BLE001 画像失败不阻塞会话
            profile = ""
    instructions = qwen_speak.build_instructions(
        body.mode, body.day, body.target,
        body.scene_title, body.scene_focus, body.patterns, issues, avg,
        profile=profile, warmup=warmup,
    )
    return {"mode": body.mode, "instructions": instructions, "issues": issues, "avg": avg, "warmup": warmup}


class SdpIn(BaseModel):
    sdp: str = Field(min_length=20, max_length=200_000)
    mode: str = Field(pattern="^(shadow|talk)$")
    instructions_chars: int = Field(default=1200, ge=0, le=20_000)


@router.post("/sdp")
def sdp(
    body: SdpIn,
    user: User = Depends(require_paid_ai),
    db: Session = Depends(get_db),
) -> dict:
    if dev_mock.is_dev():
        raise HTTPException(503, "开发环境不连接语音服务（前端使用模拟对话）")
    # 建会话跟踪 + 计算本次可用时长（P0-1 / P0-2）
    sess = budget.session_start(db, user, body.mode, body.instructions_chars)
    try:
        out = qwen_speak.proxy_sdp(db, body.sdp, body.mode)
        return {**out, **sess}
    except PermissionError as e:
        budget.session_abort(db, sess["session_id"])
        raise HTTPException(503, str(e))
    except RuntimeError as e:
        budget.session_abort(db, sess["session_id"])
        raise HTTPException(502, str(e))


class SessionEndIn(BaseModel):
    seconds: int = Field(ge=0, le=7200)
    ai_seconds: int = Field(default=0, ge=0, le=7200)
    mode: str = Field(default="talk", pattern="^(shadow|make|talk)$")
    session_id: int = Field(default=0, ge=0)


@router.post("/session_end")
def session_end(body: SessionEndIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """会话关闭记账（免费接口，只记录）：服务端按官方换算率折算音频 token。

    P0-2：`sdp` 创建会话；正常结束或 `sendBeacon` 补报都走这里，幂等关闭。
    """
    if dev_mock.is_dev():
        return {"est_cost_milli": 0, "dev": True}
    return budget.session_end(db, user, body.seconds, body.ai_seconds, body.session_id)


class SoeUrlIn(BaseModel):
    ref_text: str = Field(default="", max_length=500)
    eval_mode: int = Field(default=1, ge=0, le=8)
    coeff: float | None = Field(default=None, ge=1.0, le=4.0)


@router.post("/soe_url")
def soe_url(body: SoeUrlIn, user: User = Depends(require_paid_ai), db: Session = Depends(get_db)) -> dict:
    """生成一次腾讯 SOE（口语评测新版）带签名的 WSS 地址。SecretKey 不回传。签发即记账。"""
    if dev_mock.is_dev():
        raise HTTPException(503, "开发环境不调用 SOE（前端使用模拟评分）")
    try:
        cfg = tencent_soe.soe_cfg(db)
        usage.record_soe(db, user.id, body.ref_text)
        return {
            "url": tencent_soe.build_soe_url(cfg, body.ref_text.strip(), body.eval_mode, body.coeff),
            "engine": cfg["engine"],
        }
    except LookupError as e:
        raise HTTPException(503, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


class LogIn(BaseModel):
    mode: str = Field(pattern="^(shadow|make|talk)$")
    ref: str = Field(default="", max_length=128)
    sentence_id: str = Field(default="", max_length=32)
    day: int = Field(default=0, ge=0, le=365)
    turns: int = Field(default=0, ge=0, le=200)
    score: int = Field(default=0, ge=0, le=100)
    issues: list[str] = Field(default_factory=list, max_length=20)
    words: list[dict] = Field(default_factory=list, max_length=100)
    transcript: list[dict] = Field(default_factory=list, max_length=100)


def _shadow_log(db: Session, user_id: int, body: LogIn) -> SpeakLog | None:
    """同一句（同天）只保留一条跟读记录：优先按 sentence_id，旧数据按 ref。"""
    q = db.query(SpeakLog).filter(
        SpeakLog.user_id == user_id,
        SpeakLog.mode == "shadow",
        SpeakLog.day == body.day,
    )
    if body.sentence_id:
        q = q.filter(SpeakLog.sentence_id == body.sentence_id)
    else:
        q = q.filter(SpeakLog.sentence_id == "", SpeakLog.ref == body.ref)
    return q.order_by(SpeakLog.id.desc()).first()


@router.post("/log")
def log(body: LogIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    if body.mode == "shadow":
        # 跟读只记录最高分和那次评分给出的评价内容；低分重试不新增记录
        row = _shadow_log(db, user.id, body)
        if row is None:
            row = SpeakLog(
                user_id=user.id, mode=body.mode, ref=body.ref,
                sentence_id=body.sentence_id, day=body.day,
                turns=body.turns, score=body.score,
                issues=json.dumps(body.issues, ensure_ascii=False),
                words=json.dumps(body.words, ensure_ascii=False),
                transcript=json.dumps(body.transcript, ensure_ascii=False),
            )
            db.add(row)
        elif body.score > row.score:
            row.score = body.score
            row.issues = json.dumps(body.issues, ensure_ascii=False)
            row.words = json.dumps(body.words, ensure_ascii=False)
    else:
        row = SpeakLog(
            user_id=user.id, mode=body.mode, ref=body.ref, sentence_id=body.sentence_id, day=body.day,
            turns=body.turns, score=body.score,
            issues=json.dumps(body.issues, ensure_ascii=False),
            words=json.dumps(body.words, ensure_ascii=False),
            transcript=json.dumps(body.transcript, ensure_ascii=False),
        )
        db.add(row)
    if body.day > 0:
        d = db.get(SpeakDay, (user.id, body.day))
        if d is None:
            d = SpeakDay(
                user_id=user.id, day=body.day, shadow_done=False,
                make_done=False, talk_done=False, score=0,
            )
            db.add(d)
        if body.mode == "shadow":
            d.shadow_done = True
        elif body.mode == "make":
            d.make_done = True
        else:
            d.talk_done = True
        if body.score > d.score:
            d.score = body.score
    db.commit()
    # talk 会话收尾：异步性不要求，同步生成摘要（失败静默，不阻塞打卡）
    if body.mode == "talk" and body.transcript:
        try:
            speak_profile.summarize_session(db, user.id, row)
        except Exception:  # noqa: BLE001
            pass
    return {"ok": True, "log_id": row.id}


@router.get("/days")
def days(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    rows = db.query(SpeakDay).filter(SpeakDay.user_id == user.id).all()
    return {
        "days": [
            {
                "day": r.day, "shadow_done": r.shadow_done,
                "make_done": r.make_done, "talk_done": r.talk_done, "score": r.score,
            }
            for r in sorted(rows, key=lambda r: r.day)
        ]
    }


class PlanIn(BaseModel):
    length: int = Field(ge=1, le=90)


@router.get("/plan")
def get_plan(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """口语计划天数；0 = 未创建（前端按默认 90 天展示）。"""
    row = db.get(SpeakPlan, user.id)
    return {"length": row.length if row else 0}


@router.put("/plan")
def put_plan(
    body: PlanIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    row = db.get(SpeakPlan, user.id)
    old_length = row.length if row else 0
    if row is None:
        row = SpeakPlan(user_id=user.id, length=body.length)
        db.add(row)
    else:
        row.length = body.length
    # 新计划从零开始：避免旧的 90 天打卡把新计划的第 1 天直接点亮
    if body.length != old_length:
        db.query(SpeakDay).filter(SpeakDay.user_id == user.id).delete()
    db.commit()
    return {"length": row.length}


@router.delete("/plan")
def delete_plan(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """删除计划但保留打卡记录（与词汇计划一致）。"""
    row = db.get(SpeakPlan, user.id)
    if row is not None:
        row.length = 0
        db.commit()
    return {"length": 0}


@router.get("/usage_today")
def usage_today(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """用户端「今日已用」轻展示（不限流）。"""
    return usage.day_row(db, user.id)


@router.get("/ai_status")
def ai_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """付费 AI 状态：开关、一次性总额度、剩余额度、单次会话上限（前端横幅与锁定用）。"""
    return budget.status(db, user)


@router.get("/shadow/recent")
def shadow_recent(
    limit: int = 10,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """最近跟读记录：供难度选句与弱音素加权（P0-3 / P2-5）。"""
    limit = max(1, min(int(limit), 50))
    rows = (
        db.query(SpeakLog)
        .filter(SpeakLog.user_id == user.id, SpeakLog.mode == "shadow")
        .order_by(SpeakLog.id.desc())
        .limit(limit * 6)
        .all()
    )
    items = []
    seen: dict[str, SpeakLog] = {}
    order: list[str] = []
    for r in rows:
        # 计划日会为同一句写多条日志（day=0 + 来源日）：按句子去重，取该句最高分那条
        key = r.sentence_id or f"log-{r.id}"
        if key not in seen:
            seen[key] = r
            order.append(key)
        elif r.score > seen[key].score:
            seen[key] = r
    for key in order[:limit]:
        r = seen[key]
        try:
            words = json.loads(r.words or "[]")
        except json.JSONDecodeError:
            words = []
        items.append(
            {
                "id": r.id,
                "ref": r.ref,
                "sentence_id": r.sentence_id,
                "score": r.score,
                "weak_words": [str(w.get("w", "")) for w in words if isinstance(w, dict) and not w.get("ok")],
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
        )
    return {"items": items}


# ---------- 今日练习时长（真实说话秒数，服务端累计，刷新不丢） ----------


def _time_totals(db: Session, user_id: int, day: str) -> dict:
    out = {"shadow": 0, "make": 0, "talk": 0}
    rows = db.query(SpeakTime).filter(SpeakTime.user_id == user_id, SpeakTime.day == day).all()
    for r in rows:
        if r.mode in out:
            out[r.mode] = r.seconds
    return out


class TimeIn(BaseModel):
    mode: str = Field(pattern="^(shadow|make|talk)$")
    seconds: int = Field(ge=1, le=600)


@router.get("/time/today")
def time_today(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    day = usage.today()
    return {"day": day, "totals": _time_totals(db, user.id, day)}


@router.post("/time")
def add_time(
    body: TimeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    """累加一段真实练习秒数（前端按说话时段分批上报）。"""
    day = usage.today()
    row = db.get(SpeakTime, (user.id, day, body.mode))
    if row is None:
        row = SpeakTime(user_id=user.id, day=day, mode=body.mode, seconds=0)
        db.add(row)
    row.seconds += body.seconds
    db.commit()
    return {"day": day, "mode": body.mode, "seconds": row.seconds, "totals": _time_totals(db, user.id, day)}


# ---------- 对话中即时优化（穿插在自由对话里） ----------


class ImproveIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    last_ai_text: str = Field(default="", max_length=500)
    scene_title: str = Field(default="", max_length=200)


_IMPROVE_PROMPT = (
    "You are a PET (B1 Preliminary for Schools) speaking coach. "
    "The child just said: \"{text}\". The coach's last line was: \"{last_ai}\". "
    "Rewrite the child's sentence into natural PET B1 English, keeping the child's meaning, "
    "max 18 words. Return ONE compact JSON object only: "
    '{{"improved_en": "...", "improved_cn": "中文翻译", '
    '"focus": "grammar|vocab|phrase", "dims": ["grammar:short-label"]}}. '
    "dims: 1-2 short labels describing what to practise."
)


@router.post("/improve")
def improve(
    body: ImproveIn, user: User = Depends(require_paid_ai), db: Session = Depends(get_db)
) -> dict:
    """自由对话中：把孩子刚说的一句改写成 PET B1 版本（穿插显示并跟读）。"""
    from app.services import ai_enrich

    if dev_mock.is_dev():
        return dev_mock.improve(body.text)
    prompt = _IMPROVE_PROMPT.format(text=body.text[:400], last_ai=body.last_ai_text[:200])
    try:
        data, llm_usage = ai_enrich.chat(
            db, [{"role": "user", "content": prompt}], max_tokens=240, temperature=0.2
        )
        usage.record_llm(db, user.id, llm_usage)
    except LookupError as e:
        raise HTTPException(503, str(e))
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    dims = [str(d)[:40] for d in data.get("dims", []) if str(d).strip()][:2]
    return {
        "child_said": body.text.strip()[:400],
        "improved_en": str(data.get("improved_en", "")).strip()[:200],
        "improved_cn": str(data.get("improved_cn", "")).strip()[:200],
        "focus": str(data.get("focus", "grammar")).strip()[:64],
        "dims": dims or ["grammar:general"],
    }


# ---------- 会后复盘（§5.5） ----------


class ReviewIn(BaseModel):
    log_id: int = Field(gt=0)


@router.post("/review")
def review(body: ReviewIn, user: User = Depends(require_paid_ai), db: Session = Depends(get_db)) -> dict:
    """会话结束 → LLM 挑句按 PET 改写（幂等）。"""
    row = db.get(SpeakLog, body.log_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(404, "会话不存在")
    try:
        items = speak_review.generate_review(db, user.id, row)
    except LookupError as e:
        raise HTTPException(503, str(e))
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    return {"items": items}


@router.get("/review/due")
def review_due(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"items": speak_review.due_items(db, user.id)}


class GradeIn(BaseModel):
    id: int = Field(gt=0)
    score: int = Field(ge=0, le=100)
    dims_ok: list[str] = Field(default_factory=list, max_length=4)


@router.post("/review/grade")
def review_grade(body: GradeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """复盘跟读评分 → 记忆曲线记账。"""
    out = speak_review.grade(db, user.id, body.id, body.score, body.dims_ok)
    if not out:
        raise HTTPException(404, "复盘句不存在")
    return out


class ReviewItemIn(BaseModel):
    child_said: str = Field(min_length=1, max_length=400)
    improved_en: str = Field(min_length=1, max_length=200)
    improved_cn: str = Field(default="", max_length=200)
    focus: str = Field(default="grammar", max_length=64)
    dims: list[str] = Field(default_factory=list, max_length=2)


class ReviewImportIn(BaseModel):
    log_id: int = Field(gt=0)
    items: list[ReviewItemIn] = Field(default_factory=list, max_length=12)


@router.post("/review/import")
def review_import(
    body: ReviewImportIn, user: User = Depends(require_paid_ai), db: Session = Depends(get_db)
) -> dict:
    """把对话中即时生成的优化句落库为复盘句（同一 log 幂等），返回带 id 的条目供评分。"""
    row = db.get(SpeakLog, body.log_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(404, "会话不存在")
    items = speak_review.import_items(db, user.id, row, [i.model_dump() for i in body.items])
    return {"items": items}


# ---------- 「怎么说？」求助 + 造句判定 ----------


class HelpIn(BaseModel):
    scene_title: str = Field(default="", max_length=200)
    last_ai_text: str = Field(default="", max_length=500)
    note: str = Field(default="", max_length=200)


@router.post("/help")
def help_(body: HelpIn, user: User = Depends(require_paid_ai), db: Session = Depends(get_db)) -> dict:
    """「怎么说？」：中文解释 + 简单英文示范句（气泡展示，不打断语音流）。"""
    from app.services import ai_enrich

    if dev_mock.is_dev():
        return dev_mock.help_payload(body.scene_title)

    prompt = (
        "A Chinese primary-school student is in a PET-level English conversation and is stuck. "
        f"Topic: {body.scene_title or 'daily chat'}. The coach just said: \"{body.last_ai_text[:200]}\". "
        f"The student hint: {body.note[:100]}. "
        'Reply with ONE compact JSON object: {"cn": "中文提示这句话意思和可以说什么", '
        '"en": "ONE simple English sentence the student can copy (max 12 words)", '
        '"en_cn": "示范句的中文翻译"}. JSON only.'
    )
    try:
        data, llm_usage = ai_enrich.chat(
            db, [{"role": "user", "content": prompt}], max_tokens=160, temperature=0.3
        )
        usage.record_llm(db, user.id, llm_usage)
    except LookupError as e:
        raise HTTPException(503, str(e))
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    return {
        "cn": str(data.get("cn", "")),
        "en": str(data.get("en", "")),
        "en_cn": str(data.get("en_cn", "")),
    }


class CheckIn(BaseModel):
    pattern: str = Field(max_length=300)
    prompt_cn: str = Field(default="", max_length=300)
    sentence: str = Field(min_length=1, max_length=300)


@router.post("/check")
def check(body: CheckIn, user: User = Depends(require_paid_ai), db: Session = Depends(get_db)) -> dict:
    """造句判定：孩子按中文提示说英文，LLM 判意 + 给 PET 级优化。"""
    from app.services import ai_enrich

    if dev_mock.is_dev():
        return dev_mock.check(body.sentence)

    prompt = (
        "A Chinese primary-school student is practising PET speaking. "
        + (f'The Chinese idea to express is: "{body.prompt_cn[:200]}". ' if body.prompt_cn else "")
        + f'The reference English answer is: "{body.pattern[:200]}". '
        + f'The student said: "{body.sentence[:200]}". '
        + "First decide whether the student expressed the same idea, then comment on grammar and word choice. "
        + 'Reply with ONE compact JSON object: {"ok": true/false, '
        + '"comment": "中文点评（一两句，先说意思有没有说到，再说哪里要改）", '
        + '"improved": "PET B1 水平的优化句（保留学生原意；若已经很好则原样返回）"}. JSON only.'
    )
    try:
        data, llm_usage = ai_enrich.chat(
            db, [{"role": "user", "content": prompt}], max_tokens=220, temperature=0.2
        )
        usage.record_llm(db, user.id, llm_usage)
    except LookupError as e:
        raise HTTPException(503, str(e))
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    return {
        "ok": bool(data.get("ok", False)),
        "comment": str(data.get("comment", "")),
        "improved": str(data.get("improved", "")),
    }


@router.post("/transcribe")
def transcribe(
    file: UploadFile | None = File(default=None),
    user: User = Depends(require_paid_ai),
    db: Session = Depends(get_db),
) -> dict:
    """造句页：本地录音上传 → ASR 转写英文文本（确定性，替代 Realtime 兼职转写）。

    file 允许为空：开发环境没有真实录音，前端发空表单直接拿 mock 转写跑通链路。
    """
    if dev_mock.is_dev():
        return {"text": dev_mock.transcribe()}
    if file is None:
        raise HTTPException(400, "缺少录音文件")
    try:
        text = qwen_speak.transcribe(db, file.file.read(), file.content_type or "")
    except PermissionError as e:
        raise HTTPException(503, str(e))
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    # 计量：按录音时长折算音频输入 token（与 Realtime 同口径 7 tok/s），走 rt_audio_in
    seconds = max(1, round(file.size / 32_000)) if file.size else 1  # webm/opus ≈32 kbps
    usage.record(db, user.id, rt_audio_in_tok=round(seconds * usage.AUDIO_IN_TPS))
    return {"text": text}

