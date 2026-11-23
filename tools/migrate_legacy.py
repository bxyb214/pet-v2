"""旧站（ai.wizoom.net PET，MySQL）→ 新版 pet-v2（SQLite）数据迁移。

用法（本机需可直连旧库；或在能连旧库的机器上运行）：
    python tools/migrate_legacy.py \
        --mysql "mysql+pymysql://user:pass@host:3306/ai-wizoom?charset=utf8mb4" \
        [--sqlite /path/to/pet.db] [--execute]

默认 dry-run：只打印映射统计，不写库；--execute 才写入。
新库表不存在时自动建表（与 Alembic 初始迁移同构）。

映射规则（对应旧 api/index.php load_state/save_state）：
- pet_users   → users（bcrypt 哈希原样迁移，登录后自动升级 argon2；role=admin → is_admin）
- pet_codes   → invite_codes（只迁 active=1 且 used_count<max_uses 的码）
- pet_mastery（一行一维度）→ mastery（一词一行，维度逗号合并）
- pet_mistakes（dims_json JSON 数组）→ mistakes（dims 逗号串；stage=0 / due_at=last_at 日期 /
  repeats=0，旧欠账全部视为到期，记忆曲线重新开始走）
- pet_progress → progress：只迁阅读（reading::t{N}p{K} → read:{book}:{N}:{K}；idx>0 另记
  rstudy:{book}:{N}:{K} 续学位置；N<=6 归 Trainer 2、101+ 归 Trainer 1）；plan/browse 来源跳过
- pet_plan（exam='pet'）→ plans（length=固定 30（v1 PLAN_DAYS）；days_done=state='done' 天；
  超出 30 的脏数据行忽略并 warning）；exam='ket' 跳过并报告
- pet_speak → speak_logs（scene→ref；issues_json 里对象取 text 归一）
- pet_speak_day → speak_days
- pet_session / pet_ai_usage / pet_tokens：跳过（v2 无对应/重新登录/重新发 token）
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from sys import path as sys_path

sys_path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

_RD_KEY = re.compile(r"^t(\d+)p(\d+)$")
_BOOK_BY_TEST = lambda n: "t2" if n <= 6 else "t1"  # noqa: E731  1-6=Trainer 2，101+=Trainer 1


# ---------- 纯映射函数（可单测，不依赖 DB） ----------

def _dt(v):
    """MySQL 驱动给的是 datetime，JSON 存档给的是字符串，统一成 datetime。"""
    if not v:
        return None
    if isinstance(v, datetime):
        return v
    s = str(v).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def map_users(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """返回 (users, warnings)。只迁 active 用户。"""
    out: list[dict] = []
    warns: list[str] = []
    for r in rows:
        status = r.get("status", "active")
        if status and status != "active":
            warns.append(f"用户 {r.get('username')} status={status}，跳过")
            continue
        out.append(
            {
                "id": int(r["id"]),
                "username": str(r["username"]),
                "password_hash": str(r.get("pass_hash") or ""),
                "perms": str(r.get("perms") or ""),
                "is_admin": str(r.get("role")) == "admin",
                "data_rev": max(int(r.get("data_rev") or 1), 1),
                "created_at": _dt(r.get("created_at")),
            }
        )
    return out, warns


def map_codes(rows: list[dict]) -> list[dict]:
    """只迁未用完且启用的邀请码。"""
    out = []
    for r in rows:
        if int(r.get("active") or 0) != 1:
            continue
        if int(r.get("used_count") or 0) >= max(int(r.get("max_uses") or 1), 1):
            continue
        out.append({"code": str(r["code"])})
    return out


def map_mastery(rows: list[dict]) -> dict[int, dict[str, str]]:
    """user_id → {word_id: 逗号合并维度}。"""
    out: dict[int, dict[str, str]] = {}
    for r in rows:
        wid = str(r["word_id"])
        dim = str(r.get("dim") or "").strip()
        if not dim:
            continue
        per = out.setdefault(int(r["user_id"]), {})
        lst = [d for d in per.get(wid, "").split(",") if d]
        if dim not in lst:
            lst.append(dim)
        per[wid] = ",".join(sorted(lst))
    return out


def map_mistakes(rows: list[dict]) -> dict[int, list[dict]]:
    """user_id → mistakes 行。dims_json 是 JSON 数组（还欠的维度）。"""
    out: dict[int, list[dict]] = {}
    for r in rows:
        try:
            dims = json.loads(r.get("dims_json") or "[]")
        except json.JSONDecodeError:
            dims = []
        if not isinstance(dims, list):
            dims = []
        dims = sorted({str(d).strip() for d in dims if str(d).strip()})
        if not dims:
            continue  # 空维度在旧语义里等于已移出错题本
        last = str(r.get("last_at") or "")[:10] or TODAY
        out.setdefault(int(r["user_id"]), []).append(
            {
                "word_id": str(r["word_id"]),
                "dims": ",".join(dims),
                "stage": 0,
                "due_at": last if last <= TODAY else TODAY,
                "repeats": 0,
            }
        )
    return out


def map_progress(rows: list[dict]) -> tuple[dict[int, list[dict]], list[str]]:
    """user_id → progress 行。只迁阅读来源；返回 (rows, warnings)。"""
    out: dict[int, list[dict]] = {}
    warns: list[str] = []
    for r in rows:
        gk = str(r.get("group_key") or "")
        src = str(r.get("source") or "")
        if src != "reading":
            continue
        uid = int(r["user_id"])
        m = _RD_KEY.match(gk.split("::", 1)[1] if "::" in gk else gk)
        if not m:
            warns.append(f"user {uid}：reading 进度 key 无法解析「{gk}」，跳过")
            continue
        n, k = int(m.group(1)), int(m.group(2))
        book = _BOOK_BY_TEST(n)
        try:
            seen = json.loads(r.get("seen_json") or "[]")
        except json.JSONDecodeError:
            seen = []
        seen = [str(s) for s in seen if s]
        idx = int(r.get("idx") or 0)
        lst = out.setdefault(uid, [])
        lst.append({"key": f"read:{book}:{n}:{k}", "seen": seen, "idx": 0})
        if idx > 0:
            lst.append({"key": f"rstudy:{book}:{n}:{k}", "seen": [], "idx": idx})
    return out, warns


def map_plan(rows: list[dict], plan_days: int = 0) -> tuple[dict[int, dict], list[str]]:
    """user_id → plans 行（length + days_done）。

    旧站计划天数是代码里写死的 `PLAN_DAYS = 30`（js/app.js），库里只存已经动过的那些天，
    所以 CLI 传 plan_days=30 兜底，否则「做完 23 天」会被当成「23 天计划已全部完成」。
    传了 plan_days 时以它为准：超出范围的行（历史脏数据）忽略并 warning，
    不能把 v2 计划拉成 34 天（否则按 34 天切分，第 24 天会少词）。
    plan_days=0 时按最大天数推断（纯函数默认，单测用）。
    阅读计划是 v2 才有的，旧库没有对应数据，reading_length 保持 0。
    """
    out: dict[int, dict] = {}
    warns: list[str] = []
    by_user: dict[int, dict[int, list[dict]]] = {}
    for r in rows:
        uid = int(r["user_id"])
        exam = str(r.get("exam") or "pet")
        if exam != "pet":
            warns.append(f"user {uid}：exam={exam} 的计划 v2 暂无对应，跳过")
            continue
        by_user.setdefault(uid, {}).setdefault(int(r["day"]), []).append(r)
    for uid, days in by_user.items():
        # v1 的 PLAN_DAYS 固定 30；超出范围的行（历史脏数据）不能把计划拉长。
        valid = {d: rs for d, rs in days.items() if d >= 1}
        if plan_days:
            for d in sorted(valid):
                if d > plan_days:
                    warns.append(f"user {uid}：day={d} 超出 v1 固定 {plan_days} 天，忽略")
            valid = {d: rs for d, rs in valid.items() if d <= plan_days}
            length = plan_days
        else:
            length = max(valid) if valid else 0
        done = sorted(d for d, rs in valid.items() if any(str(x.get("state")) == "done" for x in rs))
        out[uid] = {"length": length, "days_done": done}
    return out, warns


def map_speak_logs(rows: list[dict]) -> dict[int, list[dict]]:
    """user_id → speak_logs 行。issues_json 兼容对象 {text:…} 归一为字符串数组。"""
    out: dict[int, list[dict]] = {}

    def norm(arr: list) -> list[str]:
        res = []
        for it in arr:
            t = str(it.get("text") if isinstance(it, dict) else it or "").strip()
            if t:
                res.append(t[:160])
        return res

    for r in rows:
        try:
            issues = json.loads(r.get("issues_json") or "[]")
        except json.JSONDecodeError:
            issues = []
        try:
            transcript = json.loads(r.get("transcript_json") or "[]")
        except json.JSONDecodeError:
            transcript = []
        out.setdefault(int(r["user_id"]), []).append(
            {
                "mode": str(r.get("mode") or "talk"),
                "ref": str(r.get("scene") or "")[:128],
                "day": int(r.get("day") or 0),
                "turns": int(r.get("turns") or 0),
                "score": int(r.get("score") or 0),
                "issues": json.dumps(norm(issues if isinstance(issues, list) else []), ensure_ascii=False),
                "transcript": json.dumps([it for it in transcript if isinstance(it, dict)] if isinstance(transcript, list) else [], ensure_ascii=False),
                "created_at": _dt(r.get("created_at")),
            }
        )
    return out


def map_speak_days(rows: list[dict]) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = {}
    for r in rows:
        out.setdefault(int(r["user_id"]), []).append(
            {
                "day": int(r["day"]),
                "shadow_done": bool(r.get("shadow_done")),
                "talk_done": bool(r.get("talk_done")),
                "score": int(r.get("score") or 0),
            }
        )
    return out


# ---------- 读取旧库 ----------

_OLD_TABLES = ("pet_users", "pet_codes", "pet_mastery", "pet_mistakes",
               "pet_progress", "pet_plan", "pet_speak", "pet_speak_day")


def fetch_old(mysql_url: str) -> dict[str, list[dict]]:
    from sqlalchemy import create_engine, text

    eng = create_engine(mysql_url)
    tables: dict[str, list[dict]] = {}
    with eng.connect() as conn:
        for t in _OLD_TABLES:
            try:
                rows = conn.execute(text(f"SELECT * FROM {t}")).mappings().all()
                tables[t] = [dict(r) for r in rows]
            except Exception as e:
                print(f"[warn] 读取 {t} 失败：{e}")
                tables[t] = []
    eng.dispose()
    return tables


def load_json_dump(path: str) -> dict[str, list[dict]]:
    """读 PHP 导出的 JSON 存档（旧库在内网、本机连不上时的推荐方式）。"""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    return {t: doc.get(t, []) for t in _OLD_TABLES}


# ---------- 写入新库 ----------

def build_mapped(old: dict[str, list[dict]], plan_days: int = 0) -> tuple[dict, list[str]]:
    users, warns = map_users(old["pet_users"])
    progress, pw = map_progress(old["pet_progress"])
    plans, plw = map_plan(old["pet_plan"], plan_days)
    warns += pw + plw
    return {
        "users": users,
        "codes": map_codes(old["pet_codes"]),
        "mastery": map_mastery(old["pet_mastery"]),
        "mistakes": map_mistakes(old["pet_mistakes"]),
        "progress": progress,
        "plans": plans,
        "speak_logs": map_speak_logs(old["pet_speak"]),
        "speak_days": map_speak_days(old["pet_speak_day"]),
    }, warns


def _rebind_engine(sqlite_path: str) -> None:
    """--sqlite 指定目标库：设置环境变量后重建 app.db 模块级 engine。"""
    import importlib
    import os

    os.environ["PET_DATABASE_URL"] = f"sqlite:///{sqlite_path}"
    import app.core.config as cfg
    import app.db as appdb

    cfg.get_settings.cache_clear()
    importlib.reload(cfg)
    importlib.reload(appdb)


def write_new(mapped: dict) -> dict[str, int]:
    from sqlalchemy import inspect

    from app.db import Base, SessionLocal, engine
    from app.models.learning import Mastery, Mistake, Plan, Progress
    from app.models.speak import SpeakDay, SpeakLog
    from app.models.user import InviteCode, User

    if "users" not in inspect(engine).get_table_names():
        Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    counts: dict[str, int] = {}

    old2new: dict[int, int] = {}
    for u in mapped["users"]:
        exists = db.query(User).filter(User.username == u["username"]).first()
        if exists:
            old2new[u["id"]] = exists.id
            counts["users_existed"] = counts.get("users_existed", 0) + 1
            continue
        row = User(
            username=u["username"], password_hash=u["password_hash"],
            display_name=u.get("display_name") or u["username"],
            perms=u["perms"], is_admin=u["is_admin"], data_rev=u["data_rev"],
        )
        if u.get("created_at"):
            row.created_at = u["created_at"]
        db.add(row)
        db.flush()
        old2new[u["id"]] = row.id
        counts["users"] = counts.get("users", 0) + 1
    db.commit()

    for c in mapped["codes"]:
        if not db.query(InviteCode).filter(InviteCode.code == c["code"]).first():
            db.add(InviteCode(code=c["code"]))
    db.commit()
    counts["codes"] = len(mapped["codes"])

    def scope(per_user: dict) -> dict:
        """旧 user_id 为键 → 新 user_id 为键。"""
        return {old2new[k]: v for k, v in per_user.items() if k in old2new}

    n_ma = 0
    for uid, words in scope(mapped["mastery"]).items():
        for wid, dims in words.items():
            db.merge(Mastery(user_id=uid, word_id=wid, mastered_dims=dims))
            n_ma += 1
    counts["mastery"] = n_ma

    n_mi = 0
    for uid, items in scope(mapped["mistakes"]).items():
        for m in items:
            db.merge(Mistake(user_id=uid, word_id=m["word_id"], dims=m["dims"],
                             stage=m["stage"], due_at=m["due_at"], repeats=m["repeats"]))
            n_mi += 1
    counts["mistakes"] = n_mi

    n_pr = 0
    for uid, items in scope(mapped["progress"]).items():
        for p in items:
            if db.get(Progress, (uid, p["key"])):
                continue
            db.add(Progress(user_id=uid, key=p["key"], seen=json.dumps(p["seen"]), idx=p["idx"]))
            n_pr += 1
    counts["progress"] = n_pr

    n_pl = 0
    for uid, plan in scope(mapped["plans"]).items():
        row = db.get(Plan, uid)
        if row is None:
            row = Plan(user_id=uid)
            db.add(row)
        if plan["length"]:
            row.length = plan["length"]
            row.days_done = json.dumps(plan["days_done"])
        n_pl += 1
    counts["plans"] = n_pl

    n_sl = 0
    for uid, items in scope(mapped["speak_logs"]).items():
        for s in items:
            db.add(SpeakLog(user_id=uid, mode=s["mode"], ref=s["ref"], day=s["day"],
                            turns=s["turns"], score=s["score"], issues=s["issues"],
                            transcript=s["transcript"]))
            n_sl += 1
    counts["speak_logs"] = n_sl

    n_sd = 0
    for uid, items in scope(mapped["speak_days"]).items():
        for d in items:
            db.merge(SpeakDay(user_id=uid, day=d["day"], shadow_done=d["shadow_done"],
                              talk_done=d["talk_done"], score=d["score"]))
            n_sd += 1
    counts["speak_days"] = n_sd

    db.commit()
    db.close()
    return counts


# ---------- 主流程 ----------

def main() -> None:
    ap = argparse.ArgumentParser(description="旧站 MySQL → pet-v2 SQLite 数据迁移")
    ap.add_argument("--mysql", default="", help="旧库 SQLAlchemy URL（mysql+pymysql://…）")
    ap.add_argument("--json", default="", help="改用 PHP 导出的 JSON 存档（与 --mysql 二选一）")
    ap.add_argument("--sqlite", default="", help="新库 SQLite 文件路径（默认 PET_DATABASE_URL / backend/data/pet.db）")
    ap.add_argument("--plan-days", type=int, default=30,
                    help="旧站计划天数（旧版 js/app.js 里 PLAN_DAYS 写死 30），默认 30")
    ap.add_argument("--execute", action="store_true", help="实际写库（默认 dry-run）")
    args = ap.parse_args()

    if not args.mysql and not args.json:
        ap.error("必须给 --mysql 或 --json 之一")
    if args.sqlite:
        _rebind_engine(args.sqlite)

    from app.db import SessionLocal  # noqa: F401  _rebind 后再取

    old = load_json_dump(args.json) if args.json else fetch_old(args.mysql)
    print(f"旧库行数：{ {k: len(v) for k, v in old.items()} }")
    mapped, warns = build_mapped(old, args.plan_days)
    for w in warns:
        print(f"[warn] {w}")

    print("== 映射统计 ==")
    print(f"users: {len(mapped['users'])}")
    print(f"invite_codes(未用): {len(mapped['codes'])}")
    print(f"mastery 词数: {sum(len(v) for v in mapped['mastery'].values())}")
    print(f"mistakes 条数: {sum(len(v) for v in mapped['mistakes'].values())}")
    print(f"progress 行: {sum(len(v) for v in mapped['progress'].values())}")
    print(f"plans 用户: {len(mapped['plans'])}")
    for uid, p in mapped["plans"].items():
        print(f"   user#{uid}: {p['length']} 天计划，已完成 {len(p['days_done'])} 天")
    print(f"speak_logs 条: {sum(len(v) for v in mapped['speak_logs'].values())}")
    print(f"speak_days 天: {sum(len(v) for v in mapped['speak_days'].values())}")

    if not args.execute:
        print("\n[dry-run] 未写库。加 --execute 执行写入。")
        return

    counts = write_new(mapped)
    print("== 写入完成 ==")
    print(counts)


if __name__ == "__main__":
    main()
