#!/usr/bin/env python3
"""构建单词量评测题库：words.xlsx + 教材真题 → frontend/public/data/vocab-test.json

用法：
  python tools/build_vocab_test.py --dry
  python tools/build_vocab_test.py

- 词库：data-src/english/{ket,pet}/words.xlsx 的 必默/高频/固搭 三表（同义不计入评测）。
- 真题：data-src/教材/{KET,PET}/01-*真题/**/*.md；只做词形近似匹配，记录出现次数。
  真题没有题目/答案，本脚本不生成题目、不补写释义。
- 教材目录缺失时仍会生成 hits=0 的题库（前端有兜底），并跳过待补清单。
- 真题生词待补清单输出到 _work/真题生词待补.md（_work 已 gitignore）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from content_schema import COLUMNS  # noqa: E402

EXAMS: dict[str, dict[str, Any]] = {
    "ket": {
        "name": "KET",
        "words": ROOT / "data-src/english/ket/words.xlsx",
        "corpus": "KET/01-KET-真题",
        "banks": [("kword", "必默"), ("kcore", "高频"), ("kphrase", "固搭")],
    },
    "pet": {
        "name": "PET",
        "words": ROOT / "data-src/english/pet/words.xlsx",
        "corpus": "PET/01-PET-真题",
        "banks": [("bimo", "必默"), ("gaopin", "高频"), ("guding", "固搭")],
    },
}

PER_EXAM = 25
EXAM_SHARE = 0.6

# 待补清单过滤：功能词与考试元信息，避免清单被噪声淹没
STOPWORDS = set(
    """
    a an the and or but if because so than then that this these those there here
    i you he she it we they me him her us them my your his its our their mine yours
    am is are was were be been being do does did done have has had having will would
    can could shall should may might must to of in on at by for with from into onto
    about after before during over under up down out off again only just also very
    too more most much many some any no not none all both each every few other another
    same own such what which who whom whose when where why how
    s t don doesn didn isn wasn aren weren haven hasn hadn won wouldn shouldn couldn
    m re ve ll d
    yes yeah ok okay oh ah well now still even soon though however maybe perhaps really
    mr mrs ms miss sir madam
    ket pet test tests part parts question questions answer answers transcript repeat
    audioscript audioscripts script scripts track tracks cd gap gaps sheet sheets
    page section unit audio listen listening read reading write writing speak speaking
    one two three four five six seven eight nine ten first second third
    """.split()
)

TOKEN_RE = re.compile(r"[a-z][a-z'-]*")
WORD_CHARS = re.compile(r"[a-z0-9]+")


def text(v: Any) -> str:
    if v is None:
        return ""
    return re.sub(r"\s+", " ", str(v)).strip()


def norm(s: str) -> str:
    return text(s).lower()


CONTRACTIONS = {
    "can't": "can not",
    "won't": "will not",
    "shan't": "shall not",
    "don't": "do not",
    "doesn't": "does not",
    "didn't": "did not",
    "isn't": "is not",
    "aren't": "are not",
    "wasn't": "was not",
    "weren't": "were not",
    "haven't": "have not",
    "hasn't": "has not",
    "hadn't": "had not",
    "wouldn't": "would not",
    "shouldn't": "should not",
    "couldn't": "could not",
    "mustn't": "must not",
    "needn't": "need not",
}
SUFFIX_RE = re.compile(r"'(m|re|ve|ll|d|s)\b")


def expand_contractions(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'")
    for k, v in CONTRACTIONS.items():
        s = s.replace(k, v)
    suffix = {"m": " am", "re": " are", "ve": " have", "ll": " will", "d": " would", "s": " is"}
    return SUFFIX_RE.sub(lambda m: suffix[m.group(1)], s)


def tokens(s: str) -> list[str]:
    return [t.strip("'-") for t in TOKEN_RE.findall(expand_contractions(norm(s))) if t.strip("'-")]


# 常见不规则动词：只用于词形归一，不参与任何释义/内容生成
IRREGULAR = {
    "am": "be", "is": "be", "are": "be", "was": "be", "were": "be", "been": "be", "being": "be",
    "went": "go", "gone": "go", "said": "say", "saw": "see", "seen": "see",
    "knew": "know", "known": "know", "became": "become", "began": "begin", "begun": "begin",
    "bought": "buy", "brought": "bring", "thought": "think", "took": "take", "taken": "take",
    "gave": "give", "given": "give", "found": "find", "made": "make", "came": "come",
    "got": "get", "gotten": "get", "ran": "run", "ate": "eat", "eaten": "eat",
    "wrote": "write", "written": "write", "spoke": "speak", "spoken": "speak",
    "told": "tell", "heard": "hear", "felt": "feel", "left": "leave", "kept": "keep",
    "slept": "sleep", "met": "meet", "paid": "pay", "spent": "spend", "built": "build",
    "sent": "send", "lent": "lend", "lost": "lose", "won": "win", "stood": "stand",
    "understood": "understand", "taught": "teach", "caught": "catch", "fought": "fight",
    "flew": "fly", "flown": "fly", "grew": "grow", "grown": "grow", "drew": "draw",
    "drawn": "draw", "threw": "throw", "thrown": "throw", "showed": "show", "shown": "show",
    "fell": "fall", "fallen": "fall", "rode": "ride", "ridden": "ride",
    "drove": "drive", "driven": "drive", "chose": "choose", "chosen": "choose",
    "wore": "wear", "worn": "wear", "sat": "sit", "held": "hold", "hung": "hang",
    "swam": "swim", "swum": "swim", "sang": "sing", "sung": "sing",
    "drank": "drink", "drunk": "drink", "rang": "ring", "rung": "ring",
    "sank": "sink", "sunk": "sink", "broke": "break", "broken": "break",
}


def stems(t: str) -> set[str]:
    """token → 可能的词形集合（含原形），用于粗略词形匹配。"""
    out = {t}
    base = IRREGULAR.get(t)
    if base:
        out.add(base)
    if len(t) > 4 and t.endswith("ies"):
        out.add(t[:-3] + "y")
    if len(t) > 3 and t.endswith("ied"):
        out.add(t[:-3] + "y")
    if len(t) > 3 and t.endswith("es"):
        out.add(t[:-2])
    if len(t) > 3 and t.endswith("s") and not t.endswith(("ss", "us", "is")):
        out.add(t[:-1])
    if len(t) > 4 and t.endswith("ing"):
        b = t[:-3]
        if len(b) >= 3:
            out.add(b)
            out.add(b + "e")
            if len(t) > 5 and t[-4] == t[-5] and t[-4] not in "aeiou":
                out.add(t[:-4])
    if len(t) > 3 and t.endswith("ed"):
        b = t[:-2]
        if len(b) >= 3:
            out.add(b)
            out.add(b + "e")
            if len(t) > 4 and t[-3] == t[-4] and t[-3] not in "aeiou":
                out.add(t[:-3])
    if len(t) > 4 and t.endswith("er"):
        b = t[:-2]
        if len(b) >= 3:
            out.add(b)
            if t[-3] == t[-4] and t[-3] not in "aeiou":
                out.add(t[:-3])
    if len(t) > 5 and t.endswith("est"):
        b = t[:-3]
        if len(b) >= 3:
            out.add(b)
            if t[-4] == t[-5] and t[-4] not in "aeiou":
                out.add(t[:-4])
    if len(t) > 4 and t.endswith("ly"):
        out.add(t[:-2])
    return {s for s in out if len(s) >= 2}


def slug(s: str) -> str:
    return "-".join(WORD_CHARS.findall(norm(s))) or "word"


def rows_of(ws) -> Iterable[dict[str, Any]]:
    it = ws.iter_rows(values_only=True)
    try:
        header = next(it)
    except StopIteration:
        return []
    names = [text(c) for c in header]
    out: list[dict[str, Any]] = []
    for row in it:
        out.append({names[i]: row[i] for i in range(min(len(names), len(row))) if names[i]})
    return out


def make_id(exam: str, bank: str, en: str, used: set[str]) -> str:
    base = f"{exam}-{bank}-{slug(en)}"
    candidate = base
    n = 2
    while candidate in used:
        candidate = f"{base}-{n}"
        n += 1
    used.add(candidate)
    return candidate


def load_eval_words(exam: str, cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int], dict[str, int]]:
    """读三张评测词库表；返回按级别去重后的词池。"""
    path: Path = cfg["words"]
    if not path.exists():
        raise SystemExit(f"缺少词库文件：{path}")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        used_ids: set[str] = set()
        seen: set[str] = set()
        pools: list[dict[str, Any]] = []
        stats: dict[str, int] = {}
        skipped = 0
        duplicate = 0
        for bank, sheet in cfg["banks"]:
            if sheet not in wb.sheetnames:
                raise SystemExit(f"{path} 缺少工作表：{sheet}")
            words: list[dict[str, Any]] = []
            for row in rows_of(wb[sheet]):
                en = text(row.get("英文"))
                cn = text(row.get("中文"))
                if not en or not cn:
                    skipped += 1
                    continue
                key = norm(en)
                if key in seen:
                    duplicate += 1
                    continue
                seen.add(key)
                words.append({"id": make_id(exam, bank, en, used_ids), "en": en, "cn": cn, "hits": 0})
            pools.append({"key": bank, "name": sheet, "words": words})
            stats[bank] = len(words)
        return pools, stats, {"skipped": skipped, "duplicate": duplicate}
    finally:
        wb.close()


def load_known_terms() -> set[str]:
    """所有词库（含同义表）中出现的英文词形，作为待补清单的排除集。"""
    known: set[str] = set()
    for exam, cfg in EXAMS.items():
        path: Path = cfg["words"]
        if not path.exists():
            continue
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            for sheet in ("必默", "高频", "固搭", "同义"):
                if sheet not in wb.sheetnames:
                    continue
                for row in rows_of(wb[sheet]):
                    for col in ("英文", "原短语", "同义短语"):
                        value = text(row.get(col))
                        if not value:
                            continue
                        for t in tokens(value):
                            known.add(t)
                            known.update(stems(t))
        finally:
            wb.close()
    return known


def load_corpus(base: Path) -> tuple[list[str], list[str], list[str]]:
    toks: list[str] = []
    tests: list[str] = []
    srcs: list[str] = []
    if not base.exists():
        return toks, tests, srcs
    for path in sorted(base.rglob("*.md")):
        rel = path.relative_to(base).as_posix()
        test = "/".join(rel.split("/")[:2])
        body = path.read_text(encoding="utf-8", errors="ignore")
        ts = tokens(body)
        toks.extend(ts)
        tests.extend([test] * len(ts))
        srcs.extend([rel] * len(ts))
    return toks, tests, srcs


def scan(toks: list[str], tests: list[str], srcs: list[str]) -> tuple[Counter, dict[str, set[str]], dict[str, str]]:
    hits: Counter = Counter()
    hit_tests: dict[str, set[str]] = defaultdict(set)
    first_src: dict[str, str] = {}
    for tok, test, src in zip(toks, tests, srcs):
        for s in stems(tok):
            hits[s] += 1
            hit_tests[s].add(test)
            first_src.setdefault(s, src)
    return hits, hit_tests, first_src


def count_phrases(toks: list[str], phrases: list[str]) -> Counter:
    by_first: dict[str, list[tuple[str, ...]]] = defaultdict(list)
    for phrase in phrases:
        parts = tuple(tokens(phrase))
        if len(parts) < 2:
            continue
        by_first[parts[0]].append(parts)
    counts: Counter = Counter()
    for i, tok in enumerate(toks):
        for s in stems(tok):
            for parts in by_first.get(s, ()):
                n = len(parts)
                if i + n > len(toks):
                    continue
                if all(parts[j] in stems(toks[i + j]) for j in range(1, n)):
                    counts[" ".join(parts)] += 1
    return counts


def tag_words(pools: list[dict[str, Any]], toks: list[str], word_hits: Counter) -> None:
    phrases: list[str] = []
    for pool in pools:
        for w in pool["words"]:
            if len(tokens(w["en"])) >= 2:
                phrases.append(w["en"])
    phrase_hits = count_phrases(toks, phrases)
    for pool in pools:
        for w in pool["words"]:
            parts = tokens(w["en"])
            if len(parts) >= 2:
                w["hits"] = int(phrase_hits.get(" ".join(parts), 0))
            else:
                w["hits"] = int(word_hits.get(parts[0], 0)) if parts else 0


def pending_candidates(
    toks: list[str],
    tests: list[str],
    srcs: list[str],
    known: set[str],
    min_tests: int,
    limit: int,
) -> list[dict[str, Any]]:
    counts: Counter = Counter()
    seen_tests: dict[str, set[str]] = defaultdict(set)
    first_src: dict[str, str] = {}
    for tok, test, src in zip(toks, tests, srcs):
        counts[tok] += 1
        seen_tests[tok].add(test)
        first_src.setdefault(tok, src)
    out: list[dict[str, Any]] = []
    for tok, count in counts.items():
        if not (3 <= len(tok) <= 18) or "'" in tok:
            continue
        if tok in STOPWORDS or not re.search(r"[aeiouy]", tok):
            continue
        if len(seen_tests[tok]) < min_tests:
            continue
        if any(s in known for s in stems(tok)):
            continue
        out.append(
            {
                "word": tok,
                "count": count,
                "tests": len(seen_tests[tok]),
                "src": first_src[tok],
            }
        )
    out.sort(key=lambda r: (-r["tests"], -r["count"], r["word"]))
    return out[:limit]


def validate(exams: dict[str, dict[str, Any]], meta: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    used: set[str] = set()
    for exam, data in exams.items():
        seen: set[str] = set()
        total = 0
        for pool in data["banks"]:
            if not pool["words"]:
                errors.append(f"{exam}/{pool['key']} 为空")
            for w in pool["words"]:
                if w["id"] in used:
                    errors.append(f"重复 id：{w['id']}")
                used.add(w["id"])
                key = norm(w["en"])
                if key in seen:
                    errors.append(f"{exam} 重复英文：{w['en']}")
                seen.add(key)
                if not w["cn"]:
                    errors.append(f"{exam}/{w['id']} 中文为空")
                total += 1
        if total != meta["exams"][exam]["total"]:
            errors.append(f"{exam} 计数不一致：{total} != {meta['exams'][exam]['total']}")
    return errors


def write_pending(
    path: Path,
    sections: dict[str, list[dict[str, Any]]],
    built: str,
    min_tests: int,
    limit: int,
) -> None:
    lines = [
        "# 真题生词待补",
        "",
        f"> 生成于 {built}；来源 `data-src/教材`。匹配为词形近似，OCR 粘连词可能混入噪声，需人工筛选。",
        f"> 仅统计出现于 ≥{min_tests} 个套题、且不在现有 KET/PET 词库（含同义表）中的词；最多 {limit} 条。",
        "> 本清单不自动入库，也不自动翻译。",
        "",
    ]
    for exam, rows in sections.items():
        lines += [
            f"## {EXAMS[exam]['name']}（{len(rows)} 条）",
            "",
            "| # | 单词 | 出现次数 | 出现套题 | 示例出处 |",
            "|---|---|---:|---:|---|",
        ]
        for i, row in enumerate(rows, 1):
            lines.append(f"| {i} | {row['word']} | {row['count']} | {row['tests']} | {row['src']} |")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="构建 KET/PET 单词评测题库")
    ap.add_argument("--dry", action="store_true", help="只统计/校验，不写文件")
    ap.add_argument("--out", default=str(ROOT / "frontend/public/data/vocab-test.json"))
    ap.add_argument("--exams-root", default=str(ROOT / "data-src/教材"))
    ap.add_argument("--pending-out", default=str(ROOT / "_work/真题生词待补.md"))
    ap.add_argument("--pending-min-tests", type=int, default=4)
    ap.add_argument("--pending-limit", type=int, default=300)
    args = ap.parse_args()

    exams_root = Path(args.exams_root)
    pools_by_exam: dict[str, list[dict[str, Any]]] = {}
    stats_by_exam: dict[str, dict[str, int]] = {}
    build_report: dict[str, dict[str, int]] = {}
    for exam, cfg in EXAMS.items():
        pools, stats, report = load_eval_words(exam, cfg)
        pools_by_exam[exam] = pools
        stats_by_exam[exam] = stats
        build_report[exam] = report
        base = exams_root / cfg["corpus"]
        if not base.exists():
            print(f"[warn] 未找到{cfg['name']}真题目录：{base}（本次 hits=0）", file=sys.stderr)
            continue
        toks, tests, srcs = load_corpus(base)
        word_hits, _, _ = scan(toks, tests, srcs)
        tag_words(pools, toks, word_hits)

    known = load_known_terms()
    pending: dict[str, list[dict[str, Any]]] = {}
    for exam, cfg in EXAMS.items():
        base = exams_root / cfg["corpus"]
        if not base.exists():
            pending[exam] = []
            continue
        toks, tests, srcs = load_corpus(base)
        pending[exam] = pending_candidates(
            toks, tests, srcs, known, args.pending_min_tests, args.pending_limit
        )

    built = date.today().isoformat()
    meta: dict[str, Any] = {
        "source": "data-src/english/{ket,pet}/words.xlsx + data-src/教材/*真题",
        "perExam": PER_EXAM,
        "examShare": EXAM_SHARE,
        "pending": {exam: len(rows) for exam, rows in pending.items()},
        "exams": {},
    }
    for exam, pools in pools_by_exam.items():
        total = sum(len(p["words"]) for p in pools)
        tagged = sum(1 for p in pools for w in p["words"] if w["hits"] > 0)
        meta["exams"][exam] = {"banks": stats_by_exam[exam], "total": total, "tagged": tagged}

    exams_out = {
        exam: {"name": EXAMS[exam]["name"], "banks": pools_by_exam[exam]}
        for exam in EXAMS
    }
    errors = validate(exams_out, meta)

    for exam in EXAMS:
        name = EXAMS[exam]["name"]
        m = meta["exams"][exam]
        rep = build_report[exam]
        print(
            f"{name} 评测词 {m['total']}（真题标注 {m['tagged']}）"
            f" · 跳过空行 {rep['skipped']} · 去重 {rep['duplicate']}"
            f" · 待补候选 {len(pending[exam])}"
        )

    if errors:
        for err in errors:
            print(f"[error] {err}", file=sys.stderr)
        raise SystemExit(1)

    if args.dry:
        print("[dry] 校验通过，未写文件")
        return

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"version": 1, "built": built, "meta": meta, "exams": exams_out},
                   ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    write_pending(Path(args.pending_out), pending, built, args.pending_min_tests, args.pending_limit)
    print(f"题库：{out_path}")
    print(f"待补清单：{args.pending_out}")


if __name__ == "__main__":
    main()
