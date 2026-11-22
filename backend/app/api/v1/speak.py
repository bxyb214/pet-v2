"""口语路由（S 组）：boot / sdp / log / days / tts / 用量 / 复盘 / 求助。密钥不出服务端。"""
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import require_speak
from app.db import get_db
from app.models.speak import SpeakDay, SpeakLog
from app.models.user import User
from app.services import qwen_speak, speak_profile, speak_review, tencent_soe, usage

router = APIRouter(prefix="/speak", tags=["speak"])


class BootIn(BaseModel):
    mode: str = Field(pattern="^(shadow|talk)$")
    day: int = Field(default=0, ge=0, le=365)
    target: str = Field(default="", max_length=500)
    scene_title: str = Field(default="", max_length=200)
    scene_focus: str = Field(default="", max_length=500)
    patterns: list[str] = Field(default_factory=list, max_length=10)


@router.post("/boot")
def boot(body: BootIn, user: User = Depends(require_speak), db: Session = Depends(get_db)) -> dict:
    """拼会话提示词（talk 附带历史问题摘要 + 当日画像 + 到期复盘热身句）。"""
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


@router.post("/sdp")
def sdp(body: SdpIn, user: User = Depends(require_speak), db: Session = Depends(get_db)) -> dict:
    try:
        return qwen_speak.proxy_sdp(db, body.sdp, body.mode)
    except PermissionError as e:
        raise HTTPException(503, str(e))
    except RuntimeError as e:
        raise HTTPException(502, str(e))


class SessionEndIn(BaseModel):
    seconds: int = Field(ge=0, le=7200)
    ai_seconds: int = Field(default=0, ge=0, le=7200)
    mode: str = Field(default="talk", pattern="^(shadow|talk)$")


@router.post("/session_end")
def session_end(body: SessionEndIn, user: User = Depends(require_speak), db: Session = Depends(get_db)) -> dict:
    """会话关闭记账（不限流，只记录）：服务端按官方换算率折算音频 token。"""
    row = usage.record_session(db, user.id, body.seconds, body.ai_seconds)
    return {"est_cost_milli": row.est_cost_milli}


class SoeUrlIn(BaseModel):
    ref_text: str = Field(default="", max_length=500)
    eval_mode: int = Field(default=1, ge=0, le=8)
    coeff: float | None = Field(default=None, ge=1.0, le=4.0)


@router.post("/soe_url")
def soe_url(body: SoeUrlIn, user: User = Depends(require_speak), db: Session = Depends(get_db)) -> dict:
    """生成一次腾讯 SOE（口语评测新版）带签名的 WSS 地址。SecretKey 不回传。签发即记账。"""
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
    mode: str = Field(pattern="^(shadow|talk)$")
    ref: str = Field(default="", max_length=128)
    day: int = Field(default=0, ge=0, le=365)
    turns: int = Field(default=0, ge=0, le=200)
    score: int = Field(default=0, ge=0, le=100)
    issues: list[str] = Field(default_factory=list, max_length=20)
    transcript: list[dict] = Field(default_factory=list, max_length=100)


@router.post("/log")
def log(body: LogIn, user: User = Depends(require_speak), db: Session = Depends(get_db)) -> dict:
    row = SpeakLog(
        user_id=user.id, mode=body.mode, ref=body.ref, day=body.day,
        turns=body.turns, score=body.score,
        issues=json.dumps(body.issues, ensure_ascii=False),
        transcript=json.dumps(body.transcript, ensure_ascii=False),
    )
    db.add(row)
    if body.day > 0:
        d = db.get(SpeakDay, (user.id, body.day))
        if d is None:
            d = SpeakDay(user_id=user.id, day=body.day, shadow_done=False, talk_done=False, score=0)
            db.add(d)
        if body.mode == "shadow":
            d.shadow_done = True
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
def days(user: User = Depends(require_speak), db: Session = Depends(get_db)) -> dict:
    rows = db.query(SpeakDay).filter(SpeakDay.user_id == user.id).all()
    return {
        "days": [
            {"day": r.day, "shadow_done": r.shadow_done, "talk_done": r.talk_done, "score": r.score}
            for r in sorted(rows, key=lambda r: r.day)
        ]
    }


@router.get("/usage_today")
def usage_today(user: User = Depends(require_speak), db: Session = Depends(get_db)) -> dict:
    """用户端「今日已用」轻展示（不限流）。"""
    return usage.day_row(db, user.id)


# ---------- 会后复盘（§5.5） ----------


class ReviewIn(BaseModel):
    log_id: int = Field(gt=0)


@router.post("/review")
def review(body: ReviewIn, user: User = Depends(require_speak), db: Session = Depends(get_db)) -> dict:
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
def review_due(user: User = Depends(require_speak), db: Session = Depends(get_db)) -> dict:
    return {"items": speak_review.due_items(db, user.id)}


class GradeIn(BaseModel):
    id: int = Field(gt=0)
    score: int = Field(ge=0, le=100)
    dims_ok: list[str] = Field(default_factory=list, max_length=4)


@router.post("/review/grade")
def review_grade(body: GradeIn, user: User = Depends(require_speak), db: Session = Depends(get_db)) -> dict:
    """复盘跟读评分 → 记忆曲线记账。"""
    out = speak_review.grade(db, user.id, body.id, body.score, body.dims_ok)
    if not out:
        raise HTTPException(404, "复盘句不存在")
    return out


# ---------- 「怎么说？」求助 + 造句判定 ----------


class HelpIn(BaseModel):
    scene_title: str = Field(default="", max_length=200)
    last_ai_text: str = Field(default="", max_length=500)
    note: str = Field(default="", max_length=200)


@router.post("/help")
def help_(body: HelpIn, user: User = Depends(require_speak), db: Session = Depends(get_db)) -> dict:
    """「怎么说？」：中文解释 + 简单英文示范句（气泡展示，不打断语音流）。"""
    from app.services import ai_enrich

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
    sentence: str = Field(min_length=1, max_length=300)


@router.post("/check")
def check(body: CheckIn, user: User = Depends(require_speak), db: Session = Depends(get_db)) -> dict:
    """造句判定：孩子按句型造句，LLM 判对错并给 PET 级优化。"""
    from app.services import ai_enrich

    prompt = (
        "A Chinese primary-school student practised this English pattern: "
        f'"{body.pattern[:200]}". The student wrote/said: "{body.sentence[:200]}". '
        'Reply with ONE compact JSON object: {"ok": true/false, '
        '"comment": "中文点评（一句话，说清哪里好/哪里要改）", '
        '"improved": "PET B1 水平的优化句（若已经很好则原样返回）"}. JSON only.'
    )
    try:
        data, llm_usage = ai_enrich.chat(
            db, [{"role": "user", "content": prompt}], max_tokens=160, temperature=0.2
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


class TtsIn(BaseModel):
    text: str = Field(min_length=1, max_length=300)
    voice: str = Field(default="", max_length=64)


@router.post("/tts")
def tts(body: TtsIn, user: User = Depends(require_speak), db: Session = Depends(get_db)) -> dict:
    # 缓存目录与 sqlite 同级（./data/tts），生产 compose 挂卷即可持久化
    settings = get_settings()
    db_path = settings.database_url.replace("sqlite:///", "", 1)
    from pathlib import Path

    cache_dir = str(Path(db_path).parent / "tts")
    try:
        return qwen_speak.tts(db, cache_dir, body.text, body.voice)
    except PermissionError as e:
        raise HTTPException(503, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(502, str(e))
