"""把 data-src/english/<exam>/*.xlsx 构建成前端 JSON。

当前覆盖 KET 的阅读 / 语法 / 听力；PET 仍走旧站的 build_*_v2.js。
阅读 JSON 里额外带 `grammar.examples`（语法书例句 + 语法题），
供语法页在不污染阅读列表的前提下按考点出题。

用法：
    python tools/build_ket_content.py [--exam ket] [--dry]
"""
from __future__ import annotations

import json
import re
import sys
from collections import OrderedDict
from datetime import date
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "frontend" / "public" / "data" / "ket"

GRAMMAR_BOOKS = {"ket": "新东方10天掌握KET核心语法"}


def _rows(path: Path, sheet: str) -> list[tuple[Any, ...]]:
    wb = load_workbook(path, read_only=True, data_only=True)
    if sheet not in wb.sheetnames:
        raise SystemExit(f"{path.name} 缺少工作表：{sheet}")
    ws = wb[sheet]
    out: list[tuple[Any, ...]] = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue
        if all(v is None or str(v).strip() == "" for v in row):
            continue
        out.append(row)
    return out


def _s(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _i(v: Any, default: int = 0) -> int:
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return default


def _f(v: Any, default: float = 0.0) -> float:
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return default


def _id_key(v: Any) -> str:
    return _s(v)


def _split_kinds(raw: str) -> list[str]:
    return [x.strip() for x in (raw or "").replace("，", ",").split(",") if x.strip()]


class Book:
    def __init__(self, row: tuple[Any, ...]) -> None:
        self.id = _s(row[0])
        self.name = _s(row[1])
        self.desc = _s(row[2])
        if not self.id or not self.name:
            raise SystemExit(f"书目行不完整：{row}")


class GQ:
    def __init__(self, row: tuple[Any, ...]) -> None:
        # 句子ID, 题干, A, B, C, D, 答案(1-4), 解析, 考点编号
        self.sid = _id_key(row[0])
        self.stem = _s(row[1])
        self.opts = [_s(row[2]), _s(row[3]), _s(row[4]), _s(row[5])]
        self.answer = _i(row[6], 1) - 1
        self.why = _s(row[7])
        self.c = _i(row[8], 0)

    def as_dict(self) -> dict[str, Any]:
        return {"stem": self.stem, "opts": self.opts, "a": self.answer, "why": self.why, "c": self.c}


class GramRef:
    def __init__(self, row: tuple[Any, ...]) -> None:
        # 句子ID, 考点编号, 考点名称, 说明
        self.sid = _id_key(row[0])
        self.c = _i(row[1], 0)
        self.g = _s(row[2])
        self.d = _s(row[3])

    def as_dict(self) -> dict[str, Any]:
        return {"c": self.c, "g": self.g, "d": self.d}


def _parse_refs(rows: list[tuple[Any, ...]]) -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        sid, role, text = _s(row[0]), _s(row[1]), _s(row[2])
        if not sid or not role or not text:
            continue
        out.setdefault(sid, []).append({"r": role, "t": text})
    return out


def _sentence(
    base: dict[str, Any],
    parse: dict[str, list[dict[str, str]]],
    grams: dict[str, list[GramRef]],
    gqs: dict[str, list[GQ]],
) -> dict[str, Any]:
    sid = base["id"]
    base["parse"] = parse.get(sid, [])
    base["gram"] = [g.as_dict() for g in grams.get(sid, [])]
    base["gq"] = [q.as_dict() for q in gqs.get(sid, [])]
    return base


def build_reading(path: Path, gpath: Path, exam: str) -> dict[str, Any]:
    books = [Book(r).__dict__ for r in _rows(path, "书目")]
    book_ids = {b["id"] for b in books}

    tests: OrderedDict[tuple[str, int], dict[str, Any]] = OrderedDict()
    for row in _rows(path, "套题"):
        book, no = _s(row[0]), _i(row[1])
        if book not in book_ids:
            raise SystemExit(f"套题引用了不存在的书目：{book}")
        tests[(book, no)] = {
            "no": no,
            "book": book,
            "title": _s(row[2]) or f"Test {no}",
            "note": _s(row[3]),
            "parts": OrderedDict(),
        }
    for row in _rows(path, "Part"):
        book, no, part = _s(row[0]), _i(row[1]), _i(row[2])
        t = tests.get((book, no))
        if not t:
            raise SystemExit(f"Part 引用了不存在的套题：{book} Test {no}")
        t["parts"][part] = {"part": part, "kind": _s(row[3]), "focus": _s(row[4]), "sentences": []}

    parse = _parse_refs(_rows(path, "成分"))
    grams: dict[str, list[GramRef]] = {}
    for row in _rows(path, "语法点"):
        g = GramRef(row)
        if g.sid and g.c:
            grams.setdefault(g.sid, []).append(g)
    gqs: dict[str, list[GQ]] = {}
    for row in _rows(path, "语法题"):
        q = GQ(row)
        if q.sid and q.stem:
            gqs.setdefault(q.sid, []).append(q)

    seen: set[str] = set()
    for row in _rows(path, "句子"):
        book, no, part = _s(row[0]), _i(row[1]), _i(row[2])
        t = tests.get((book, no))
        if not t or part not in t["parts"]:
            raise SystemExit(f"句子引用了不存在的套题/Part：{book} Test {no} Part {part}")
        sid = _s(row[3])
        if not sid:
            raise SystemExit(f"句子缺少句子ID：{row}")
        if sid in seen:
            raise SystemExit(f"句子ID 重复：{sid}")
        seen.add(sid)
        t["parts"][part]["sentences"].append(
            _sentence(
                {
                    "id": sid,
                    "en": _s(row[4]),
                    "cn": _s(row[5]),
                    "key": _s(row[6]),
                    "quiz": _split_kinds(_s(row[7])) or ["meaning"],
                    "point": _s(row[9]) or _s(row[8]),
                    "note": _s(row[10]),
                    "tense": _s(row[11]),
                },
                parse,
                grams,
                gqs,
            )
        )

    gdays: OrderedDict[int, dict[str, Any]] = OrderedDict()
    for row in _rows(gpath, "语法体系"):
        day, dname = _i(row[0]), _s(row[1])
        if not day:
            continue
        d = gdays.setdefault(day, {"day": day, "name": dname or f"Day {day}", "points": []})
        c, name = _i(row[2], 0), _s(row[3])
        if c and name:
            d["points"].append({"c": c, "name": name})

    gparse = _parse_refs(_rows(gpath, "成分"))
    ggrams: dict[str, list[GramRef]] = {}
    for row in _rows(gpath, "例句"):
        sid, en, cn, c, name, note = (_s(row[i]) for i in range(6))
        if not sid or not en:
            continue
        ggrams.setdefault(sid, []).append(GramRef((sid, c, name, note)))
        gparse.setdefault(sid, [])
    ggqs: dict[str, list[GQ]] = {}
    for row in _rows(gpath, "语法题"):
        q = GQ(row)
        if q.sid and q.stem:
            ggqs.setdefault(q.sid, []).append(q)

    examples: list[dict[str, Any]] = []
    for row in _rows(gpath, "例句"):
        sid, en, cn, _c, _name, _note = (_s(row[i]) for i in range(6))
        if not sid or not en:
            continue
        if sid in seen:
            raise SystemExit(f"语法例句ID 与阅读句子重复：{sid}")
        seen.add(sid)
        examples.append(
            _sentence(
                {"id": sid, "en": en, "cn": cn, "key": "", "quiz": ["grammar"],
                 "point": _s(row[4]), "note": "", "tense": ""},
                gparse,
                ggrams,
                ggqs,
            )
        )

    out_tests = []
    for t in tests.values():
        out_tests.append({**t, "parts": list(t["parts"].values())})
    used_books = {t["book"] for t in out_tests}
    books = [b for b in books if b["id"] in used_books]

    total = sum(len(p["sentences"]) for t in out_tests for p in t["parts"])
    gq_total = sum(len(s["gq"]) for t in out_tests for p in t["parts"] for s in p["sentences"])
    gq_total += sum(len(s["gq"]) for s in examples)
    covered = {g["c"] for t in out_tests for p in t["parts"] for s in p["sentences"] for g in s["gram"]}
    covered |= {q["c"] for t in out_tests for p in t["parts"] for s in p["sentences"] for q in s["gq"]}
    covered |= {q["c"] for s in examples for q in s["gq"]}

    return {
        "grammar": {
            "book": GRAMMAR_BOOKS.get(exam, f"{exam.upper()} 语法"),
            "days": list(gdays.values()),
            "examples": examples,
        },
        "books": books,
        "tests": out_tests,
        "meta": {
            "sentences": total,
            "gq": gq_total,
            "points_covered": len(covered),
            "built": date.today().isoformat(),
            "source": f"data-src/english/{exam}/reading.xlsx + grammar.xlsx",
        },
    }


def build_listening(path: Path, exam: str) -> dict[str, Any]:
    books = [Book(r).__dict__ for r in _rows(path, "书目")]
    book_ids = {b["id"] for b in books}
    tests: OrderedDict[tuple[str, int], dict[str, Any]] = OrderedDict()
    for row in _rows(path, "套题"):
        book, no = _s(row[0]), _i(row[1])
        if book not in book_ids:
            raise SystemExit(f"套题引用了不存在的书目：{book}")
        tests[(book, no)] = {
            "no": no,
            "book": book,
            "title": _s(row[2]) or f"Test {no}",
            "duration": _f(row[3]),
            "parts": OrderedDict(),
        }
    for row in _rows(path, "Part"):
        book, no, part = _s(row[0]), _i(row[1]), _i(row[2])
        t = tests.get((book, no))
        if not t:
            raise SystemExit(f"Part 引用了不存在的套题：{book} Test {no}")
        audio = _s(row[6])
        if audio and not audio.startswith("/"):
            audio = f"/audio/listen/{exam}/{audio}"
        t["parts"][part] = {
            "part": part,
            "qRange": _s(row[5]),
            "label": _s(row[4]),
            "kind": _s(row[3]),
            "audio": audio,
            "duration": _f(row[7]),
            "sentences": [],
            "items": [],
        }

    for row in _rows(path, "原文"):
        book, no, part = _s(row[0]), _i(row[1]), _i(row[2])
        p = tests.get((book, no), {}).get("parts", {}).get(part)
        if not p:
            raise SystemExit(f"原文引用了不存在的 Part：{book} Test {no} Part {part}")
        p["sentences"].append({
            "t0": _f(row[4]),
            "t1": _f(row[5]) if _s(row[5]) else None,
            "text": _s(row[6]),
            "no": None,
        })
    for p in (p for t in tests.values() for p in t["parts"].values()):
        p["sentences"].sort(key=lambda s: s["t0"])

    for row in _rows(path, "题目"):
        book, no, part = _s(row[0]), _i(row[1]), _i(row[2])
        p = tests.get((book, no), {}).get("parts", {}).get(part)
        if not p:
            raise SystemExit(f"题目引用了不存在的 Part：{book} Test {no} Part {part}")
        opts = [_s(row[6]), _s(row[7]), _s(row[8])]
        opts = opts if any(opts) else None
        answer: Any = _s(row[5])
        if p["kind"] in ("picture", "choice"):
            answer = _i(row[5], 1) - 1
        img = _s(row[9])
        if img and not img.startswith("/"):
            img = "/" + img.lstrip("/")
        p["items"].append({
            "no": _i(row[3]),
            "stem": _s(row[4]),
            "answer": answer,
            "img": img or None,
            "options": opts,
            "t0": _f(row[10]),
        })

    out_tests = [{**t, "parts": list(t["parts"].values())} for t in tests.values()]
    used_books = {t["book"] for t in out_tests}
    books = [b for b in books if b["id"] in used_books]
    for p in (p for t in out_tests for p in t["parts"]):
        p["transcript"] = " ".join(s["text"] for s in p["sentences"])
        if not p["duration"] and p["sentences"]:
            p["duration"] = p["sentences"][-1]["t1"] or p["sentences"][-1]["t0"]

    items = sum(len(p["items"]) for t in out_tests for p in t["parts"])
    by_kind: dict[str, int] = {}
    for t in out_tests:
        for p in t["parts"]:
            by_kind[p["kind"]] = by_kind.get(p["kind"], 0) + len(p["items"])
    return {
        "books": books,
        "tests": out_tests,
        "meta": {
            "tests": len(out_tests),
            "parts": sum(len(t["parts"]) for t in out_tests),
            "items": items,
            "items_by_kind": by_kind,
            "sentences": sum(len(p["sentences"]) for t in out_tests for p in t["parts"]),
            "built": date.today().isoformat(),
            "source": f"data-src/english/{exam}/listening.xlsx",
        },
    }


def _lines(value: Any) -> list[str]:
    return [x.strip() for x in re.split(r"[\n|]", _s(value)) if x.strip()]


def _csv(value: Any) -> list[str]:
    return [x.strip() for x in re.split(r"[,，]", _s(value)) if x.strip()]


def _word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text))


KET_RUBRIC = {
    "global": [
        {"level": 5, "desc": "能持续、自然地互动，表达清楚，偶有小错不影响理解。"},
        {"level": 4, "desc": "能围绕话题交流，意思基本清楚，错误偶尔影响理解。"},
        {"level": 3, "desc": "能完成大部分简单交流，需要较多重复或解释。"},
        {"level": 2, "desc": "只能用简单词句回应，交流经常中断。"},
        {"level": 1, "desc": "只能说出个别单词，难以形成交流。"},
        {"level": 0, "desc": "没有可理解的表达。"},
    ],
    "dims": [
        {
            "key": "grammar_vocab", "name": "Grammar and Vocabulary", "cn": "语法与词汇",
            "levels": [
                {"level": 5, "desc": "能用日常词汇和简单句型清楚表达，错误很少。"},
                {"level": 3, "desc": "词汇够用，简单句基本正确，复杂结构常出错。"},
                {"level": 1, "desc": "词汇有限，句子结构错误多，影响理解。"},
            ],
        },
        {
            "key": "pronunciation", "name": "Pronunciation", "cn": "发音",
            "levels": [
                {"level": 5, "desc": "发音清楚自然，重音和语调基本正确。"},
                {"level": 3, "desc": "总体能听懂，个别音和重音不准。"},
                {"level": 1, "desc": "发音不清，听者需要费力猜测。"},
            ],
        },
        {
            "key": "interaction", "name": "Interactive Communication", "cn": "互动交流",
            "levels": [
                {"level": 5, "desc": "能主动提问、回应和接话，交流顺畅。"},
                {"level": 3, "desc": "能回应同伴，但较少主动发起或追问。"},
                {"level": 1, "desc": "基本不回应，交流难以继续。"},
            ],
        },
    ],
    "note": "KET 口语按语法与词汇、发音、互动交流三项评分；练习时先保证完整句和接话，再追求复杂表达。",
}


def build_speaking(path: Path, exam: str) -> dict[str, Any]:
    packs: list[dict[str, Any]] = []
    pack_by_id: dict[str, dict[str, Any]] = {}
    for row in _rows(path, "场景包"):
        pid = _s(row[0])
        if not pid:
            raise SystemExit(f"场景包缺少 pack_id：{row}")
        p = {
            "id": pid,
            "part": _i(row[1], 1),
            "name": _s(row[2]),
            "cn": _s(row[3]),
            "goal": _s(row[4]),
            "level": _s(row[5]) or "A2",
            "order": _i(row[6], len(packs) + 1),
            "ids": [],
        }
        packs.append(p)
        pack_by_id[pid] = p
    packs.sort(key=lambda p: p["order"])
    for i, p in enumerate(packs, 1):
        p["order"] = i

    shadow: list[dict[str, Any]] = []
    shadow_by_id: dict[str, dict[str, Any]] = {}
    for row in _rows(path, "跟读句"):
        pid = _s(row[1])
        pack = pack_by_id.get(pid)
        if not pack:
            raise SystemExit(f"跟读句引用了不存在的 pack_id：{pid}")
        sid = _s(row[0]) or f"{pid}-{len(pack['ids']) + 1}"
        if sid in shadow_by_id:
            raise SystemExit(f"跟读句 ID 重复：{sid}")
        en = _s(row[2])
        item = {
            "id": sid,
            "pack": pid,
            "packName": pack["name"],
            "part": pack["part"],
            "en": en,
            "cn": _s(row[3]),
            "tip": _s(row[4]),
            "difficulty": _i(row[5], 2),
            "words": _word_count(en),
            "focus": _csv(row[6]),
            "source": _s(row[7]),
            "active": _s(row[8]) != "否",
        }
        shadow.append(item)
        shadow_by_id[sid] = item
        pack["ids"].append(sid)

    make: list[dict[str, Any]] = []
    make_by_id: dict[str, dict[str, Any]] = {}
    for row in _rows(path, "造句题"):
        pid = _s(row[1])
        if pid not in pack_by_id:
            raise SystemExit(f"造句题引用了不存在的 pack_id：{pid}")
        mid = _s(row[0]) or f"{pid}-m{sum(1 for m in make if m['pack'] == pid) + 1}"
        if mid in make_by_id:
            raise SystemExit(f"造句题 ID 重复：{mid}")
        item = {
            "id": mid,
            "pack": pid,
            "prompt_cn": _s(row[2]),
            "answer": _s(row[3]),
            "pattern": _s(row[4]),
        }
        make.append(item)
        make_by_id[mid] = item

    make_by_pack: dict[str, list[dict[str, Any]]] = {}
    for m in make:
        make_by_pack.setdefault(m["pack"], []).append(m)

    scenes: list[dict[str, Any]] = []
    seen_scenes: set[str] = set()
    for row in _rows(path, "场景"):
        sid = _s(row[0])
        pid = _s(row[1])
        pack = pack_by_id.get(pid)
        if not sid or not pack:
            raise SystemExit(f"场景行不完整或 pack_id 不存在：{row}")
        if sid in seen_scenes:
            raise SystemExit(f"场景 ID 重复：{sid}")
        seen_scenes.add(sid)
        shadow_ids = _csv(row[7]) or list(pack["ids"])
        make_ids = _csv(row[8]) or [m["id"] for m in make_by_pack.get(pid, [])]
        scenes.append({
            "id": sid,
            "pack": pid,
            "part": _i(row[2], pack["part"]),
            "title": _s(row[3]),
            "cn": _s(row[4]),
            "level": _s(row[5]) or pack["level"],
            "focus": pack["goal"],
            "openers": _lines(row[6]),
            "sourceRefs": [],
            "source": "KET 官方题库 + 14 周计划",
            "shadowIds": shadow_ids,
            "make": [{k: make_by_id[mid][k] for k in ("id", "prompt_cn", "answer", "pattern")}
                     for mid in make_ids if mid in make_by_id],
        })

    patterns: list[dict[str, Any]] = []
    pattern_by_id: dict[str, dict[str, Any]] = {}
    for row in _rows(path, "句型库(可选)"):
        part, gid, name, cn = _i(row[0], 1), _s(row[1]), _s(row[2]), _s(row[3])
        if not gid:
            continue
        g = pattern_by_id.get(gid)
        if not g:
            g = {"id": gid, "part": part, "name": name, "cn": cn, "items": []}
            pattern_by_id[gid] = g
            patterns.append(g)
        g["items"].append({"id": f"{gid}-{len(g['items']) + 1}", "en": _s(row[4]), "cn": _s(row[5])})

    part1bank = [
        {"no": _i(row[0], i + 1), "q": _s(row[1]), "cn": _s(row[2]), "ans": _s(row[3])}
        for i, row in enumerate(_rows(path, "Part1题库(可选)"))
    ]
    essays = [
        {"no": _s(row[0]) or str(i + 1), "q": _s(row[1]), "ans": _s(row[2])}
        for i, row in enumerate(_rows(path, "范文(可选)"))
    ]

    scene_by_pid = {s["pack"]: s for s in scenes}
    days: list[dict[str, Any]] = []
    for i, p in enumerate(packs, 1):
        scene = scene_by_pid.get(p["id"])
        days.append({
            "d": i,
            "phase": 0 if p["part"] == 1 else 1,
            "pack": p["id"],
            "title": p["name"],
            "goal": f"跟读 {len(p['ids'])} 句 → 和 AI 聊「{scene['title'] if scene else p['cn']}」",
            "focus": scene["focus"] if scene else p["goal"],
            "shadow": list(p["ids"]),
            "scene": scene["id"] if scene else p["id"],
        })
    n1 = sum(1 for p in packs if p["part"] == 1)
    phases = [
        {"name": "Part 1 · 个人信息与日常问答", "desc": f"第 1–{n1} 天", "from": 1, "to": n1},
        {"name": "Part 2 · 图片讨论", "desc": f"第 {n1 + 1}–{len(packs)} 天",
         "from": n1 + 1, "to": len(packs)},
    ]

    free = [
        {"id": m["id"], "pack": m["pack"], "en": m["answer"], "cn": m["prompt_cn"]}
        for m in make
    ]

    return {
        "meta": {
            "schema": 5,
            "level": "A2",
            "built": date.today().isoformat(),
            "source": f"data-src/english/{exam}/speaking.xlsx",
            "counts": {
                "packs": len(packs),
                "scenes": len(scenes),
                "shadow": len(shadow),
                "make": len(make),
                "patterns": sum(len(g["items"]) for g in patterns),
            },
        },
        "packs": packs,
        "shadow": shadow,
        "free": free,
        "scenes": scenes,
        "plan": {
            "title": f"KET 口语 {len(packs)} 天计划",
            "phases": phases,
            "days": days,
        },
        "patterns": patterns,
        "rubric": KET_RUBRIC,
        "part1bank": part1bank,
        "essays": essays,
    }


def main() -> int:
    args = sys.argv[1:]
    exam = "ket"
    if "--exam" in args:
        exam = args[args.index("--exam") + 1]
    dry = "--dry" in args
    base = ROOT / "data-src" / "english" / exam

    reading = build_reading(base / "reading.xlsx", base / "grammar.xlsx", exam)
    listening = build_listening(base / "listening.xlsx", exam)
    speaking = build_speaking(base / "speaking.xlsx", exam)

    print(f"{exam} reading: books={len(reading['books'])} tests={len(reading['tests'])} "
          f"sentences={reading['meta']['sentences']} gq={reading['meta']['gq']} "
          f"grammar_examples={len(reading['grammar']['examples'])} days={len(reading['grammar']['days'])}")
    print(f"{exam} listening: tests={listening['meta']['tests']} parts={listening['meta']['parts']} "
          f"items={listening['meta']['items']} sentences={listening['meta']['sentences']}")
    counts = speaking["meta"]["counts"]
    print(f"{exam} speaking: packs={counts['packs']} scenes={counts['scenes']} "
          f"shadow={counts['shadow']} make={counts['make']} patterns={counts['patterns']} "
          f"plan_days={len(speaking['plan']['days'])}")
    if dry:
        print("(dry run, 未写入)")
        return 0
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "reading.json").write_text(json.dumps(reading, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "listening.json").write_text(json.dumps(listening, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "speak.json").write_text(json.dumps(speaking, ensure_ascii=False), encoding="utf-8")
    print(f"写入 {OUT_DIR}/reading.json, listening.json, speak.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
