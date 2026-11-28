"""校验英语内容 Excel 模板（data-src/english/<exam>/<module>.xlsx）。

用法：
  backend/.venv/Scripts/python.exe tools/check_content.py
  ... --exam ket --module reading
  ... --strict            # 警告也当失败

规则与列定义见 tools/content_schema.py；模板由 tools/make_content_templates.py 生成。
"""
from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable
from pathlib import Path

import content_schema as S
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "frontend" / "public"


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}：{msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"{where}：{msg}")

    def merge(self, other: Report) -> None:
        self.errors += other.errors
        self.warnings += other.warnings


class Table:
    def __init__(self, name: str, rows: list[tuple]) -> None:
        self.name = name
        self.rows = rows
        self.header = [str(v or "").strip() for v in (rows[0] if rows else ())]
        self.idx = {h: i for i, h in enumerate(self.header) if h}

    def has(self, name: str) -> bool:
        return name in self.idx

    def value(self, row: tuple, name: str) -> str:
        return S.cell(row, self.idx.get(name, -1))

    def data(self) -> Iterable[tuple[int, tuple]]:
        for i, row in enumerate(self.rows[1:], start=2):
            if not S.is_blank_row(row):
                yield i, row

    def empty(self) -> bool:
        return next(self.data(), None) is None


def as_int(text: str) -> int | None:
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def as_float(text: str) -> float | None:
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def load_tables(path: Path) -> dict[str, Table]:
    """读取工作簿；返回 sheet→Table（忽略说明页）。"""
    wb = load_workbook(path, read_only=True, data_only=True)
    tables: dict[str, Table] = {}
    for ws in wb.worksheets:
        if ws.title == "说明":
            continue
        tables[ws.title] = Table(ws.title, list(ws.iter_rows(values_only=True)))
    wb.close()
    return tables


def check_headers(module: str, tables: dict[str, Table], where: str, rep: Report) -> None:
    for sheet, cols in S.COLUMNS[module].items():
        optional = "(可选)" in sheet
        table = tables.get(sheet)
        if table is None:
            if not optional:
                rep.err(where, f"缺少工作表「{sheet}」")
            continue
        missing = [c for c in cols if not table.has(c)]
        if missing:
            rep.err(f"{where}/{sheet}", f"表头缺少列：{'、'.join(missing)}")


def missing(sheet: str, module: str) -> str:
    return f"{S.MODULE_NAMES[module]}/{sheet}"


# ---------------- words ----------------
def check_words(tables: dict[str, Table], where: str, rep: Report) -> None:
    bank_terms: dict[str, set[str]] = {}
    for sheet, en_col, cn_col in (
        ("必默", "英文", "中文"), ("高频", "英文", "中文"),
        ("固搭", "英文", "中文"), ("同义", "原短语", "原短语中文"),
    ):
        table = tables.get(sheet)
        if table is None:
            continue
        tag = missing(sheet, "words")
        if table.empty():
            rep.warn(f"{where}/{tag}", "尚无数据")
            continue
        seen: dict[str, int] = {}
        terms: set[str] = set()
        for rn, row in table.data():
            en = table.value(row, en_col)
            if not en:
                rep.err(f"{where}/{tag} 第 {rn} 行", f"{en_col}为空")
                continue
            key = S.norm_term(en)
            uniq = key
            if sheet == "同义":
                alt = table.value(row, "同义短语")
                # 同义库的去重单位是「原短语 → 同义短语」；同一原短语可有多个同义说法
                uniq = key + "\u0000" + S.norm_term(alt)
            if uniq in seen:
                rep.err(f"{where}/{tag} 第 {rn} 行", f"与第 {seen[uniq]} 行重复：{en}")
            else:
                seen[uniq] = rn
                terms.add(key)
            if sheet == "同义":
                alt = table.value(row, "同义短语")
                if not alt:
                    rep.err(f"{where}/{tag} 第 {rn} 行", "同义短语为空")
                elif S.norm_term(alt) == key:
                    rep.err(f"{where}/{tag} 第 {rn} 行", "同义短语与原短语相同")
            elif not table.value(row, cn_col):
                rep.err(f"{where}/{tag} 第 {rn} 行", f"{cn_col}为空")
        bank_terms[sheet] = terms
    keys = list(bank_terms)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            both = bank_terms[a] & bank_terms[b]
            if both:
                sample = "、".join(sorted(both)[:5])
                rep.warn(f"{where}", f"{a} 与 {b} 有 {len(both)} 个重复词（不自动删）：{sample}")


# ---------------- ordering / reading ----------------
def check_books(table: Table, tag: str, rep: Report, where: str) -> set[str]:
    books: set[str] = set()
    if table is None:
        rep.err(where, f"缺少工作表「{tag}」")
        return books
    if table.empty():
        rep.warn(f"{where}/{missing(tag, 'reading')}", "尚无数据")
        return books
    for rn, row in table.data():
        bid = table.value(row, "book_id")
        if not bid:
            rep.err(f"{where}/{tag} 第 {rn} 行", "book_id 为空")
        elif bid in books:
            rep.err(f"{where}/{tag} 第 {rn} 行", f"book_id 重复：{bid}")
        else:
            books.add(bid)
    return books


def check_tests_and_parts(tables: dict[str, Table], books: set[str], module: str,
                          where: str, rep: Report) -> tuple[set[tuple[str, int]], set[tuple[str, int, int]]]:
    tests: set[tuple[str, int]] = set()
    parts: set[tuple[str, int, int]] = set()
    t = tables.get("套题")
    if t and not t.empty():
        for rn, row in t.data():
            bid, no = t.value(row, "book_id"), as_int(t.value(row, "test_no"))
            tag = f"{where}/套题 第 {rn} 行"
            if bid not in books:
                rep.err(tag, f"book_id 不存在：{bid}")
            if no is None:
                rep.err(tag, "test_no 不是整数")
                continue
            if (bid, no) in tests:
                rep.err(tag, f"套题重复：{bid} / {no}")
            tests.add((bid, no))
    elif t is not None:
        rep.warn(f"{where}/套题", "尚无数据")
    p = tables.get("Part")
    if p and not p.empty():
        for rn, row in p.data():
            bid, no = p.value(row, "book_id"), as_int(p.value(row, "test_no"))
            pt = as_int(p.value(row, "part"))
            tag = f"{where}/Part 第 {rn} 行"
            if (bid, no) not in tests:
                rep.err(tag, f"套题不存在：{bid} / {no}")
            if pt is None or pt < 1:
                rep.err(tag, "part 不是正整数")
                continue
            key = (bid, no, pt)
            if key in parts:
                rep.err(tag, f"Part 重复：{bid} / {no} / {pt}")
            parts.add(key)
            if module == "reading" and not p.value(row, "题型"):
                rep.err(tag, "题型为空")
            if module == "listening":
                if p.value(row, "题型") not in S.ENUMS["listening"]["Part"]["题型"]:
                    rep.err(tag, f"题型非法：{p.value(row, '题型')}")
                if not p.value(row, "音频文件"):
                    rep.err(tag, "音频文件为空")
    elif p is not None:
        rep.warn(f"{where}/Part", "尚无数据")
    return tests, parts


def check_reading(tables: dict[str, Table], where: str, rep: Report,
                  grammar_points: set[int], grammar_examples: set[str]) -> None:
    books = check_books(tables.get("书目"), "书目", rep, where)
    _, parts = check_tests_and_parts(tables, books, "reading", where, rep)
    sent = tables.get("句子")
    sentence_ids: set[str] = set()
    parse_count: dict[str, int] = {}
    gq_count: dict[str, int] = {}
    if sent and not sent.empty():
        for rn, row in sent.data():
            sid = sent.value(row, "句子ID")
            tag = f"{where}/句子 第 {rn} 行"
            if not sid:
                rep.err(tag, "句子ID为空")
                continue
            if sid in sentence_ids:
                rep.err(tag, f"句子ID重复：{sid}")
            sentence_ids.add(sid)
            key = (sent.value(row, "book_id"), as_int(sent.value(row, "test_no")),
                   as_int(sent.value(row, "part")))
            if key not in parts:
                rep.err(tag, f"Part 不存在：{key[0]} / {key[1]} / {key[2]}")
            en, cn = sent.value(row, "英文"), sent.value(row, "中文")
            if not en:
                rep.err(tag, "英文为空")
            if not cn:
                rep.err(tag, "中文为空")
            quiz = [q.strip() for q in re.split(r"[,，]", sent.value(row, "题型")) if q.strip()]
            bad = [q for q in quiz if q not in S.ENUMS["reading"]["句子"]["题型"]]
            if bad:
                rep.err(tag, f"题型非法：{'、'.join(bad)}")
            k = sent.value(row, "关键信息")
            if k and en and k not in en:
                rep.err(tag, f"关键信息不在英文原句里：{k}")
            c = as_int(sent.value(row, "考点"))
            if c is not None and grammar_points and c not in grammar_points:
                rep.err(tag, f"考点编号不存在：{c}")
    elif sent is not None:
        rep.warn(f"{where}/句子", "尚无数据")
    parse = tables.get("成分")
    if parse:
        for rn, row in parse.data():
            sid = parse.value(row, "句子ID")
            if sid not in sentence_ids:
                rep.err(f"{where}/成分 第 {rn} 行", f"句子ID不存在：{sid}")
            parse_count[sid] = parse_count.get(sid, 0) + 1
    gram = tables.get("语法点")
    if gram:
        for rn, row in gram.data():
            sid = gram.value(row, "句子ID")
            c = as_int(gram.value(row, "考点编号"))
            tag = f"{where}/语法点 第 {rn} 行"
            if sid not in sentence_ids:
                rep.err(tag, f"句子ID不存在：{sid}")
            if c is None:
                rep.err(tag, "考点编号不是整数")
            elif grammar_points and c not in grammar_points:
                rep.err(tag, f"考点编号不存在：{c}")
    gq = tables.get("语法题")
    if gq:
        for rn, row in gq.data():
            sid = gq.value(row, "句子ID")
            tag = f"{where}/语法题 第 {rn} 行"
            if sid not in sentence_ids:
                rep.err(tag, f"句子ID不存在：{sid}")
            gq_count[sid] = gq_count.get(sid, 0) + 1
            check_gq_row(gq, row, tag, rep, grammar_points)
    for sid in sentence_ids:
        if parse_count.get(sid, 0) < 3:
            rep.err(f"{where}", f"句子 {sid} 的成分少于 3 块")
        if gq_count.get(sid, 0) < 1:
            rep.err(f"{where}", f"句子 {sid} 没有语法题")
    if grammar_examples:
        overlap = sentence_ids & grammar_examples
        if overlap:
            rep.err(f"{where}", f"句子ID 与 grammar.xlsx 例句重复：{'、'.join(sorted(overlap)[:5])}")


def check_gq_row(table: Table, row: tuple, tag: str, rep: Report, points: set[int]) -> None:
    opts = [table.value(row, x) for x in ("A", "B", "C", "D")]
    if any(not o for o in opts):
        rep.err(tag, "四个选项必须都填写")
    answer = as_int(table.value(row, "答案"))
    if answer is None or answer not in (1, 2, 3, 4):
        rep.err(tag, "答案必须是 1–4")
    if not table.value(row, "题干"):
        rep.err(tag, "题干为空")
    if not table.value(row, "解析"):
        rep.err(tag, "解析为空")
    c = as_int(table.value(row, "考点编号"))
    if c is None:
        rep.err(tag, "考点编号不是整数")
    elif points and c not in points:
        rep.err(tag, f"考点编号不存在：{c}")


# ---------------- grammar ----------------
def load_grammar_refs(exam: str) -> tuple[set[int], set[str]]:
    path = S.module_path(ROOT, exam, "grammar")
    if not path.exists():
        return set(), set()
    tables = load_tables(path)
    points = {as_int(t.value(r, "考点编号")) for t in [tables.get("语法体系")] if t
              for _, r in t.data()}
    examples = {t.value(r, "句子ID") for t in [tables.get("例句")] if t
                for _, r in t.data() if t.value(r, "句子ID")}
    return {p for p in points if p is not None}, examples


def load_reading_refs(exam: str) -> tuple[set[int], set[str]]:
    path = S.module_path(ROOT, exam, "reading")
    if not path.exists():
        return set(), set()
    tables = load_tables(path)
    points, _ = load_grammar_refs(exam)
    sent = tables.get("句子")
    ids = {sent.value(r, "句子ID") for _, r in sent.data()} if sent else set()
    if sent:
        for _, row in sent.data():
            c = as_int(sent.value(row, "考点"))
            if c is not None:
                points.add(c)
    return points, {i for i in ids if i}


def check_grammar(tables: dict[str, Table], where: str, rep: Report,
                  reading_sentences: set[str]) -> None:
    sys_t = tables.get("语法体系")
    points: set[int] = set()
    if sys_t and not sys_t.empty():
        days: dict[int, str] = {}
        for rn, row in sys_t.data():
            tag = f"{where}/语法体系 第 {rn} 行"
            day, c = as_int(sys_t.value(row, "天")), as_int(sys_t.value(row, "考点编号"))
            if day is None or day < 1:
                rep.err(tag, "天不是正整数")
            elif sys_t.value(row, "天名称") and days.get(day) not in (None, sys_t.value(row, "天名称")):
                rep.warn(tag, f"第 {day} 天的名称前后不一致")
            else:
                days[day] = sys_t.value(row, "天名称")
            if c is None:
                rep.err(tag, "考点编号不是整数")
            elif c in points:
                rep.err(tag, f"考点编号重复：{c}")
            else:
                points.add(c)
            if not sys_t.value(row, "考点名称"):
                rep.err(tag, "考点名称为空")
    elif sys_t is not None:
        rep.warn(f"{where}/语法体系", "尚无数据")
    examples: set[str] = set()
    ex_t = tables.get("例句")
    if ex_t and not ex_t.empty():
        for rn, row in ex_t.data():
            tag = f"{where}/例句 第 {rn} 行"
            sid = ex_t.value(row, "句子ID")
            if not sid:
                rep.err(tag, "句子ID为空")
                continue
            if sid in examples or sid in reading_sentences:
                rep.err(tag, f"句子ID重复：{sid}")
            examples.add(sid)
            if not ex_t.value(row, "英文"):
                rep.err(tag, "英文为空")
            if not ex_t.value(row, "中文"):
                rep.err(tag, "中文为空")
            c = as_int(ex_t.value(row, "考点编号"))
            if c is None:
                rep.err(tag, "考点编号不是整数")
            elif points and c not in points:
                rep.err(tag, f"考点编号不存在：{c}")
    elif ex_t is not None:
        rep.warn(f"{where}/例句", "尚无数据")
    parse = tables.get("成分")
    if parse:
        for rn, row in parse.data():
            sid = parse.value(row, "句子ID")
            if sid not in examples:
                rep.err(f"{where}/成分 第 {rn} 行", f"例句ID不存在：{sid}")
    gq = tables.get("语法题")
    gq_count: dict[str, int] = {}
    if gq:
        for rn, row in gq.data():
            sid = gq.value(row, "句子ID")
            tag = f"{where}/语法题 第 {rn} 行"
            if sid not in examples and sid not in reading_sentences:
                rep.err(tag, f"句子ID不存在：{sid}")
            gq_count[sid] = gq_count.get(sid, 0) + 1
            check_gq_row(gq, row, tag, rep, points)
    for sid in examples:
        if gq_count.get(sid, 0) < 1:
            rep.err(f"{where}", f"例句 {sid} 没有语法题")
    covered = {as_int(gq.value(r, "考点编号")) for _, r in gq.data()} if gq else set()
    for c in sorted(points - covered):
        rep.warn(f"{where}", f"考点 {c} 还没有语法题")


# ---------------- listening ----------------
def media_path(value: str, kind: str) -> Path | None:
    if not value:
        return None
    v = value.replace("\\", "/")
    if v.startswith("/"):
        return PUBLIC / v.lstrip("/")
    if "/" in v:
        return PUBLIC / v
    default = "audio/listen" if kind == "audio" else "img/listen"
    return PUBLIC / default / v


def check_listening(tables: dict[str, Table], where: str, rep: Report) -> None:
    books = check_books(tables.get("书目"), "书目", rep, where)
    _tests, parts = check_tests_and_parts(tables, books, "listening", where, rep)
    part_kind: dict[tuple[str, int, int], str] = {}
    p = tables.get("Part")
    if p:
        for rn, row in p.data():
            key = (p.value(row, "book_id"), as_int(p.value(row, "test_no")),
                   as_int(p.value(row, "part")))
            part_kind[key] = p.value(row, "题型")
            if not p.value(row, "音频文件"):
                continue
            f = media_path(p.value(row, "音频文件"), "audio")
            if f and not f.exists():
                rep.warn(f"{where}/Part 第 {rn} 行", f"音频文件不存在：{p.value(row, '音频文件')}")
    items = tables.get("题目")
    item_parts: set[tuple[str, int, int]] = set()
    if items and not items.empty():
        for rn, row in items.data():
            key = (items.value(row, "book_id"), as_int(items.value(row, "test_no")),
                   as_int(items.value(row, "part")))
            tag = f"{where}/题目 第 {rn} 行"
            if key not in parts:
                rep.err(tag, f"Part 不存在：{key[0]} / {key[1]} / {key[2]}")
                continue
            item_parts.add(key)
            kind = part_kind.get(key, "")
            if as_int(items.value(row, "题号")) is None:
                rep.err(tag, "题号不是整数")
            if not items.value(row, "题干"):
                rep.err(tag, "题干为空")
            answer = items.value(row, "答案")
            options = [items.value(row, x) for x in ("选项A", "选项B", "选项C")]
            if kind in ("picture", "choice") and as_int(answer) not in (1, 2, 3):
                rep.err(tag, "选择题答案必须是 1–3")
            if kind == "choice":
                if any(not o for o in options):
                    rep.err(tag, "choice 题必须填写 3 个选项")
            elif kind == "picture":
                if any(options) and any(not o for o in options):
                    rep.err(tag, "picture 题选项要么全填、要么留空")
            elif kind == "fill":
                if not answer:
                    rep.err(tag, "填空题答案为空")
                if any(options):
                    rep.warn(tag, "填空题不需要选项")
            if kind == "picture" and not items.value(row, "配图"):
                rep.err(tag, "picture 题缺配图")
            img = items.value(row, "配图")
            f = media_path(img, "img") if img else None
            if f and not f.exists():
                rep.warn(tag, f"配图不存在：{img}")
    elif items is not None:
        rep.warn(f"{where}/题目", "尚无数据")
    tr = tables.get("原文")
    last_t0: dict[tuple[str, int, int], float] = {}
    tr_parts: set[tuple[str, int, int]] = set()
    if tr:
        for rn, row in tr.data():
            key = (tr.value(row, "book_id"), as_int(tr.value(row, "test_no")),
                   as_int(tr.value(row, "part")))
            tag = f"{where}/原文 第 {rn} 行"
            if key not in parts:
                rep.err(tag, f"Part 不存在：{key[0]} / {key[1]} / {key[2]}")
                continue
            tr_parts.add(key)
            t0, t1 = as_float(tr.value(row, "t0")), as_float(tr.value(row, "t1"))
            if t0 is None:
                rep.warn(tag, "缺少 t0，播放时不能逐句高亮")
            elif t0 < last_t0.get(key, -1):
                rep.err(tag, "t0 不是升序")
            else:
                last_t0[key] = t0
            if t0 is not None and t1 is not None and t1 <= t0:
                rep.err(tag, "t1 必须大于 t0")
            if not tr.value(row, "文本"):
                rep.err(tag, "文本为空")
    for key in sorted(parts - tr_parts):
        # 纯音频 Part（没有题目也没有原文）是允许的；只有带题目的 Part 缺原文才提示
        if key in item_parts:
            rep.warn(f"{where}/原文", f"{key[0]} Test {key[1]} Part {key[2]} 没有原文")


# ---------------- speaking ----------------
def check_speaking(tables: dict[str, Table], where: str, rep: Report) -> None:
    packs_t = tables.get("场景包")
    packs: set[str] = set()
    if packs_t and not packs_t.empty():
        orders: dict[int, str] = {}
        for rn, row in packs_t.data():
            tag = f"{where}/场景包 第 {rn} 行"
            pid = packs_t.value(row, "pack_id")
            if not pid:
                rep.err(tag, "pack_id 为空")
                continue
            if pid in packs:
                rep.err(tag, f"pack_id 重复：{pid}")
            packs.add(pid)
            part = as_int(packs_t.value(row, "part"))
            if part not in (1, 2, 3, 4):
                rep.err(tag, "part 必须是 1–4")
            if not packs_t.value(row, "名称") or not packs_t.value(row, "中文"):
                rep.err(tag, "名称/中文为空")
            order = as_int(packs_t.value(row, "顺序"))
            if order is None:
                rep.err(tag, "顺序不是整数")
            elif order in orders:
                rep.err(tag, f"顺序重复：{order}（{orders[order]}）")
            else:
                orders[order] = pid
    elif packs_t is not None:
        rep.warn(f"{where}/场景包", "尚无数据")
    shadow_t = tables.get("跟读句")
    shadow_ids: set[str] = set()
    if shadow_t and not shadow_t.empty():
        for rn, row in shadow_t.data():
            tag = f"{where}/跟读句 第 {rn} 行"
            pid = shadow_t.value(row, "pack_id")
            if pid not in packs:
                rep.err(tag, f"pack_id 不存在：{pid}")
            en = shadow_t.value(row, "英文")
            if not en or not shadow_t.value(row, "中文"):
                rep.err(tag, "英文/中文为空")
            sid = shadow_t.value(row, "句子ID(可空)") or f"{pid}-{rn - 1}"
            if sid in shadow_ids:
                rep.err(tag, f"句子ID重复：{sid}")
            shadow_ids.add(sid)
            diff = shadow_t.value(row, "难度")
            if diff and as_int(diff) not in (1, 2, 3, 4, 5):
                rep.err(tag, "难度必须是 1–5")
            for w in re.split(r"[,，]", shadow_t.value(row, "重读词")):
                w = w.strip()
                if w and en and w.lower() not in en.lower():
                    rep.warn(tag, f"重读词不在英文里：{w}")
    elif shadow_t is not None:
        rep.warn(f"{where}/跟读句", "尚无数据")
    make_t = tables.get("造句题")
    make_ids: set[str] = set()
    if make_t and not make_t.empty():
        for rn, row in make_t.data():
            tag = f"{where}/造句题 第 {rn} 行"
            pid = make_t.value(row, "pack_id")
            if pid not in packs:
                rep.err(tag, f"pack_id 不存在：{pid}")
            if not make_t.value(row, "中文提示") or not make_t.value(row, "参考答案"):
                rep.err(tag, "中文提示/参考答案为空")
            mid = make_t.value(row, "题ID(可空)") or f"{pid}-m{rn - 1}"
            if mid in make_ids:
                rep.err(tag, f"题ID重复：{mid}")
            make_ids.add(mid)
    elif make_t is not None:
        rep.warn(f"{where}/造句题", "尚无数据")
    scenes_t = tables.get("场景")
    scene_ids: set[str] = set()
    if scenes_t and not scenes_t.empty():
        for rn, row in scenes_t.data():
            tag = f"{where}/场景 第 {rn} 行"
            sid = scenes_t.value(row, "场景ID")
            if not sid:
                rep.err(tag, "场景ID为空")
                continue
            if sid in scene_ids:
                rep.err(tag, f"场景ID重复：{sid}")
            scene_ids.add(sid)
            pid = scenes_t.value(row, "pack_id")
            if pid not in packs:
                rep.err(tag, f"pack_id 不存在：{pid}")
            if as_int(scenes_t.value(row, "part")) not in (1, 2, 3, 4):
                rep.err(tag, "part 必须是 1–4")
            if not scenes_t.value(row, "标题") or not scenes_t.value(row, "中文"):
                rep.err(tag, "标题/中文为空")
            for sid2 in re.split(r"[,，]", scenes_t.value(row, "跟读句IDs(可空)")):
                if sid2.strip() and sid2.strip() not in shadow_ids:
                    rep.warn(tag, f"跟读句ID不存在：{sid2.strip()}")
            for mid in re.split(r"[,，]", scenes_t.value(row, "造句题IDs(可空)")):
                if mid.strip() and mid.strip() not in make_ids:
                    rep.warn(tag, f"造句题ID不存在：{mid.strip()}")
    elif scenes_t is not None:
        rep.warn(f"{where}/场景", "尚无数据")


# ---------------- driver ----------------
CHECKERS = {
    "words": lambda t, w, r, **_: check_words(t, w, r),
    "reading": lambda t, w, r, exam: check_reading(t, w, r, *load_grammar_refs(exam)),
    "grammar": lambda t, w, r, exam: check_grammar(t, w, r, load_reading_refs(exam)[1]),
    "listening": lambda t, w, r, **_: check_listening(t, w, r),
    "speaking": lambda t, w, r, **_: check_speaking(t, w, r),
}


def check_file(exam: str, module: str) -> Report:
    rep = Report()
    path = S.module_path(ROOT, exam, module)
    where = f"{exam}/{module}.xlsx"
    if not path.exists():
        return rep
    tables = load_tables(path)
    check_headers(module, tables, where, rep)
    if not rep.errors:
        CHECKERS[module](tables, where, rep, exam=exam)
    return rep


def main() -> int:
    ap = argparse.ArgumentParser(description="校验英语内容 Excel 模板")
    ap.add_argument("--exam", action="append", choices=S.EXAMS)
    ap.add_argument("--module", action="append", choices=S.MODULES)
    ap.add_argument("--strict", action="store_true", help="警告也当失败")
    args = ap.parse_args()

    exams = args.exam or S.EXAMS
    modules = args.module or S.MODULES
    errors = warnings = missing = 0
    for exam in exams:
        for module in modules:
            path = S.module_path(ROOT, exam, module)
            if not path.exists():
                print(f"— {exam}/{module}.xlsx：未填写（跳过）")
                missing += 1
                continue
            rep = check_file(exam, module)
            errors += len(rep.errors)
            warnings += len(rep.warnings)
            status = "通过" if not rep.errors else f"{len(rep.errors)} 个错误"
            print(f"— {exam}/{module}.xlsx：{status}（{len(rep.warnings)} 个警告）")
            for line in rep.errors:
                print(f"    错误  {line}")
            for line in rep.warnings:
                print(f"    警告  {line}")

    print(f"\n合计：{errors} 个错误，{warnings} 个警告，{missing} 份未填写。")
    if errors or (args.strict and warnings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
