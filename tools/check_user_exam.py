#!/usr/bin/env python3
"""核对 users.exam 与 mastery 词库前缀是否一致，并可选修正。

背景：旧站（v1）只有 PET 内容，迁移用户默认应为 PET。若账号之后在设置页被切到
KET，计划页会按 KET 词库重新切分（30 天第 24 天 = 50 词、核心词 56 题），
与已学的 PET 数据（57 词、必默 72 题）对不上。

词库 id 前缀：b/g/d/t = PET（必默/高频/固搭/同义），k* = KET。

用法：
    python tools/check_user_exam.py --sqlite data/pet.db            # 只检查
    python tools/check_user_exam.py --sqlite data/pet.db --execute  # 修正不一致用户
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from collections.abc import Iterable

PET_HEADS = {"b", "g", "d", "t"}
KET_HEADS = {"k"}
MIN_WORDS = 20       # 太少不足以判断（新用户/只学了几个词）
DOMINANCE = 0.9      # 单一级别占已识别词的比例


def infer_exam(word_ids: Iterable[str]) -> tuple[str | None, int, int]:
    """根据已掌握词的 id 前缀推断级别。返回 (exam|None, pet_count, ket_count)。"""
    pet = ket = 0
    for wid in word_ids:
        head = str(wid)[:1].lower()
        if head in PET_HEADS:
            pet += 1
        elif head in KET_HEADS:
            ket += 1
    known = pet + ket
    if known < MIN_WORDS:
        return None, pet, ket
    if ket == 0 and pet >= DOMINANCE * known:
        return "pet", pet, ket
    if pet == 0 and ket >= DOMINANCE * known:
        return "ket", pet, ket
    return None, pet, ket


def audit(db: sqlite3.Connection) -> list[dict]:
    """返回不一致的用户；不写库。"""
    out: list[dict] = []
    rows = db.execute("select id, username, coalesce(exam, 'pet') from users order by id").fetchall()
    for uid, name, exam in rows:
        ids = [r[0] for r in db.execute("select word_id from mastery where user_id=?", (uid,))]
        inferred, pet, ket = infer_exam(ids)
        if inferred and inferred != exam:
            out.append({"id": uid, "username": name, "current": exam,
                        "inferred": inferred, "pet": pet, "ket": ket})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="检查/修正 users.exam 与掌握词库不一致")
    ap.add_argument("--sqlite", required=True, help="SQLite 数据库路径")
    ap.add_argument("--execute", action="store_true", help="实际写入（默认只检查）")
    args = ap.parse_args()

    db = sqlite3.connect(args.sqlite)
    rows = db.execute("select id, username, coalesce(exam,'pet') from users order by id").fetchall()
    print(f"{'id':>3}  {'username':<12} {'exam':<5} {'pet':>5} {'ket':>5}  推断")
    mismatches = []
    for uid, name, exam in rows:
        ids = [r[0] for r in db.execute("select word_id from mastery where user_id=?", (uid,))]
        inferred, pet, ket = infer_exam(ids)
        flag = ""
        if inferred and inferred != exam:
            flag = f"  ← 不一致，应为 {inferred}"
            mismatches.append((uid, name, inferred))
        print(f"{uid:>3}  {name:<12} {exam:<5} {pet:>5} {ket:>5}  {inferred or '-'}{flag}")

    if not mismatches:
        print("\n没有发现级别与已学词库不一致的账号。")
        db.close()
        return

    print(f"\n发现 {len(mismatches)} 个不一致账号：")
    for uid, name, inferred in mismatches:
        print(f"  - {name}（id={uid}）→ {inferred}")

    if not args.execute:
        print("\n只检查，未写入。确认后加 --execute 修正。")
        db.close()
        return

    for uid, name, inferred in mismatches:
        db.execute("update users set exam=? where id=?", (inferred, uid))
        print(f"  已修正 {name} → {inferred}")
    db.commit()
    db.close()
    sys.exit(0)


if __name__ == "__main__":
    main()
