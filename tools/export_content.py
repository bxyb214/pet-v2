"""把现有 PET / KET 结构化数据导出到 data-src/english 模板。

数据来源是构建产物 frontend/public/data/*.json（由 tools/build_*.py|js 生成）：
- PET：words / reading / grammar / listening / speaking 全量导出；
- KET：只有 words（必默/高频/固搭/同义），其余模块保持空白（目前没有数据）。

用法：
  backend/.venv/Scripts/python.exe tools/export_content.py            # 导出 pet + ket
  ... --exam pet                                                     # 只导出 PET
  ... --dry                                                          # 只统计，不写文件

目标工作簿已有数据时默认拒绝覆盖，确认后加 --force（会重建模板再写入）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import content_schema as S
import make_content_templates as T
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DATA = ROOT / "frontend" / "public" / "data"

# 级别 → 词库 key（顺序即工作表顺序）
WORD_BANKS = {
    "pet": [("必默", "bimo"), ("高频", "gaopin"), ("固搭", "guding"), ("同义", "tongyi")],
    "ket": [("必默", "kword"), ("高频", "kcore"), ("固搭", "kphrase"), ("同义", "ksyn")],
}
CJK = re.compile(r"[㐀-䶿一-鿿]")


def load(name: str) -> Any:
    path = PUBLIC_DATA / f"{name}.json"
    if not path.exists():
        raise SystemExit(f"缺少 {path.relative_to(ROOT)}，请先运行对应 build 脚本")
    return json.loads(path.read_text(encoding="utf-8"))


def split_example(example: str, example_cn: str = "") -> tuple[str, str]:
    """把旧词库混排的「英文例句 + 中文翻译」拆成两列（与前端 splitExample 同义）。"""
    text = (example or "").strip()
    if not text:
        return "", example_cn or ""
    m = CJK.search(text)
    if not m:
        return text, example_cn or ""
    en = text[: m.start()].strip().rstrip(",;，；")
    cn = text[m.start():].strip()
    return en, cn or example_cn or ""


def norm_en(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip()).lower()


def combine(a: str, b: str) -> str:
    """合并两个释义/分组：相同或包含则取长的那句，否则用「；」连接。"""
    a, b = str(a or "").strip(), str(b or "").strip()
    if not b or a == b or b in a:
        return a
    if not a or a in b:
        return b
    return f"{a}；{b}"


def dedupe_words(rows: list[list[Any]], sheet: str) -> list[list[Any]]:
    """同表按英文去重（旧 PET 必默同一词会出现在多个话题组）。

    保留首行；重复行补空字段，释义/分组不同则合并。空英文/空同义短语跳过。
    """
    index: dict[str, int] = {}
    out: list[list[Any]] = []
    merged = skipped = 0
    for row in rows:
        en = str(row[1] or "").strip()
        if not en or (sheet == "同义" and not str(row[3] or "").strip()):
            skipped += 1
            continue
        key = norm_en(en)
        if sheet == "同义":
            key += "\u0000" + norm_en(row[3])  # 同一原短语的多个同义说法都保留
        if key not in index:
            index[key] = len(out)
            out.append(row)
            continue
        base, merged = out[index[key]], merged + 1
        base[0] = combine(base[0], row[0])
        base[2] = combine(base[2], row[2])
        if sheet == "同义":
            base[3] = base[3] or row[3]
            base[4] = combine(base[4], row[4])
            base[5] = base[5] or row[5]
        else:
            for i in (3, 4, 5, 6, 8):
                base[i] = base[i] or row[i]
    if merged or skipped:
        print(f"    {sheet}：合并重复 {merged} 行，跳过无效 {skipped} 行")
    return out


def words_rows(exam: str, data: dict) -> dict[str, list[list[Any]]]:
    out: dict[str, list[list[Any]]] = {}
    for sheet, key in WORD_BANKS[exam]:
        rows: list[list[Any]] = []
        for w in data["banks"].get(key, []):
            if sheet == "同义":
                rows.append([w.get("category", ""), w.get("en", ""), w.get("cn", ""),
                             w.get("alt", ""), w.get("alt_cn", ""), w.get("audio", "")])
            else:
                en_ex, cn_ex = split_example(w.get("example", ""), w.get("example_cn", ""))
                rows.append([w.get("category", ""), w.get("en", ""), w.get("cn", ""),
                             w.get("phonetic", ""), w.get("pos", ""), en_ex, cn_ex,
                             "", w.get("audio", "")])
        out[sheet] = dedupe_words(rows, sheet)
    return out


def reading_rows(data: dict) -> dict[str, list[list[Any]]]:
    tests, parts, sents, parses, points, gqs = [], [], [], [], [], []
    for t in data["tests"]:
        book, no = t.get("book") or "t2", t["no"]
        tests.append([book, no, t.get("title", ""), t.get("note", "")])
        for p in t["parts"]:
            parts.append([book, no, p["part"], p.get("kind", ""), p.get("focus", "")])
            for s in p["sentences"]:
                gram = s.get("gram") or []
                sents.append([
                    book, no, p["part"], s["id"], s.get("en", ""), s.get("cn", ""),
                    s.get("key", ""), ",".join(s.get("quiz") or []),
                    gram[0]["c"] if gram else "", s.get("point", ""),
                    s.get("note", ""), s.get("tense", ""),
                ])
                parses += [[s["id"], x.get("r", ""), x.get("t", "")] for x in s.get("parse") or []]
                points += [[s["id"], x.get("c", ""), x.get("g", ""), x.get("d", "")]
                           for x in gram]
                gqs += [gq_row(s["id"], q) for q in s.get("gq") or []]
    return {"套题": tests, "Part": parts, "句子": sents, "成分": parses,
            "语法点": points, "语法题": gqs}


def gq_row(sid: str, q: dict) -> list[Any]:
    opts = (q.get("opts") or []) + [""] * 4
    return [sid, q.get("stem", ""), opts[0], opts[1], opts[2], opts[3],
            int(q.get("a", 0)) + 1, q.get("why", ""), q.get("c", "")]


def grammar_rows(data: dict, reading: dict) -> dict[str, list[list[Any]]]:
    system: list[list[Any]] = []
    for day in data["grammar"]["days"]:
        for pt in day["points"]:
            system.append([day["day"], day.get("name", ""), pt["c"], pt.get("name", "")])
    return {"语法体系": system, "例句": [], "成分": [],
            "语法题": reading["语法题"]}


def listening_rows(data: dict) -> dict[str, list[list[Any]]]:
    tests, parts, items, lines = [], [], [], []
    for t in data["tests"]:
        book, no = t.get("book") or "t1", t["no"]
        tests.append([book, no, t.get("title", ""), round(t.get("duration") or 0, 1)])
        for p in t["parts"]:
            parts.append([book, no, p["part"], p.get("kind", ""), p.get("label", ""),
                          p.get("qRange", ""), p.get("audio", ""),
                          round(p.get("duration") or 0, 1)])
            for q in p.get("items") or []:
                opts = (q.get("options") or []) + [""] * 3
                answer = q.get("answer", "")
                if p.get("kind") != "fill" and isinstance(answer, int):
                    answer += 1
                items.append([book, no, p["part"], q.get("no", ""), q.get("stem", ""),
                              answer, opts[0], opts[1], opts[2], q.get("img") or "",
                              q.get("t0", "")])
            for i, s in enumerate(p.get("sentences") or [], start=1):
                lines.append([book, no, p["part"], i, s.get("t0", ""), s.get("t1", ""),
                              s.get("text", "")])
    return {"套题": tests, "Part": parts, "题目": items, "原文": lines}


def speaking_rows(data: dict) -> dict[str, list[list[Any]]]:
    scenes = {s["id"]: s for s in data["scenes"]}
    packs, shadow, make, scene_rows = [], [], [], []
    for p in data["packs"]:
        s = scenes.get(p["id"], {})
        packs.append([p["id"], p.get("part", ""), p.get("name", ""),
                      s.get("cn") or p.get("name", ""), s.get("focus", ""),
                      s.get("level", ""), p.get("order", "")])
    for s in data["shadow"]:
        shadow.append([s["id"], s.get("pack", ""), s.get("en", ""), s.get("cn", ""),
                       s.get("tip", ""), s.get("difficulty", ""),
                       ",".join(s.get("focus") or []), s.get("source", ""),
                       "是" if s.get("active", True) else "否"])
    for s in data["scenes"]:
        mids = []
        for m in s.get("make") or []:
            mids.append(m["id"])
            make.append([m["id"], s["id"], m.get("prompt_cn", ""),
                         m.get("answer", ""), m.get("pattern", "")])
        scene_rows.append([s["id"], s["id"], s.get("part", ""), s.get("title", ""),
                           s.get("cn", ""), s.get("level", ""),
                           "\n".join(s.get("openers") or []),
                           ",".join(s.get("shadowIds") or []), ",".join(mids)])
    patterns = []
    for pat in data.get("patterns") or []:
        for item in pat.get("items") or []:
            patterns.append([pat.get("part", ""), pat.get("id", ""), pat.get("name", ""),
                             pat.get("cn", ""), item.get("en", ""), item.get("cn", "")])
    part1 = [[x.get("no", ""), x.get("q", ""), x.get("cn", ""), x.get("ans", "")]
             for x in data.get("part1bank") or []]
    essays = [[x.get("no", ""), x.get("q", ""), x.get("ans", "")]
              for x in data.get("essays") or []]
    return {"场景包": packs, "跟读句": shadow, "造句题": make, "场景": scene_rows,
            "句型库(可选)": patterns, "Part1题库(可选)": part1, "范文(可选)": essays}


def rows_for(exam: str, module: str) -> dict[str, list[list[Any]]]:
    if module == "words":
        return words_rows(exam, load("banks"))
    if module == "reading":
        return reading_rows(load("reading"))
    if module == "grammar":
        reading = load("reading")
        return grammar_rows(reading, reading_rows(reading))
    if module == "listening":
        return listening_rows(load("listening"))
    if module == "speaking":
        return speaking_rows(load("speak"))
    raise SystemExit(f"未知模块：{module}")


def has_content(path: Path) -> bool:
    """除说明页和预填书目外，是否已有数据行。"""
    wb = load_workbook(path, read_only=True)
    try:
        for ws in wb.worksheets:
            if ws.title in ("说明", "书目"):
                continue
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i and any(v is not None and str(v).strip() for v in row):
                    return True
    finally:
        wb.close()
    return False


def append_row(ws, row: list[Any]) -> None:
    """追加一行；以 = 开头的文本（如「loads of = a lot of」）强制按文本存，避免被当成公式。"""
    ws.append(row)
    rn = ws.max_row
    for col, value in enumerate(row, start=1):
        if isinstance(value, str) and value.startswith("="):
            ws.cell(row=rn, column=col).data_type = "s"


def write_module(exam: str, module: str, rows: dict[str, list[list[Any]]], dry: bool) -> int:
    path = S.module_path(ROOT, exam, module)
    if not dry:
        T.build(exam, module, force=True)  # 重建说明/表头/预填书目
        wb = load_workbook(path)
        for sheet, data in rows.items():
            ws = wb[sheet]
            if ws.max_row > 1:
                ws.delete_rows(2, ws.max_row - 1)
            for row in data:
                append_row(ws, row)
        wb.save(path)
    total = sum(len(v) for v in rows.values())
    print(f"  {exam}/{module}.xlsx：" + "，".join(f"{k} {len(v)}" for k, v in rows.items())
          + (f"（共 {total} 行）" if total else "（空）"))
    return total


def main() -> int:
    ap = argparse.ArgumentParser(description="导出 PET/KET 现有数据到英语内容模板")
    ap.add_argument("--exam", action="append", choices=["pet", "ket"], help="可重复；默认 pet+ket")
    ap.add_argument("--dry", action="store_true", help="只统计，不写文件")
    ap.add_argument("--force", action="store_true", help="覆盖已填写的数据")
    args = ap.parse_args()

    exams = args.exam or ["pet", "ket"]
    targets = {
        "pet": S.MODULES,
        "ket": ["words"],  # KET 只有词库；其余模块保持空白
    }
    blocked = []
    for exam in exams:
        print(f"\n{exam.upper()}：")
        for module in targets[exam]:
            path = S.module_path(ROOT, exam, module)
            if path.exists() and has_content(path) and not args.force:
                blocked.append(f"{exam}/{module}.xlsx")
                continue
            write_module(exam, module, rows_for(exam, module), args.dry)

    if blocked:
        print("\n以下工作簿已有数据，未覆盖（确认后加 --force）：", "、".join(blocked))
        return 1
    print("\n完成。校验：python tools/check_content.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
