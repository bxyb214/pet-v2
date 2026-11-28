"""构建 v2 词库静态数据：旧站 PET/js/{data,ket-data}.js → frontend/public/data/banks.json

用法：python tools/build_data.py [--dry]
源：D:/Works/PETWebSite/PET/js/data.js（window.PET_DATA，PET 四库）
    D:/Works/PETWebSite/PET/js/ket-data.js（window.KET_DATA，KET 四库）
出：pet-v2/frontend/public/data/banks.json（nginx/静态托管：/data/banks.json）

输出结构：
{
  "exams":    [{"id":"pet","name":"PET"},{"id":"ket","name":"KET"}],
  "bankMeta": {bank: {exam, name, short, dims[], desc}},
  "banks":    {bank: [word…]},
  "groups":   {bank: [group…]},
  "meta":     {bank: 条数}
}
同义库（tongyi / ksyn）额外输出纯字段：en/cn 为原短语英文/中文，
alt/alt_cn 为同义短语英文/中文；题面与选项只使用英文字段。
`bankMeta[bank].dims` 决定这个库考哪些维度（KET 必默三型，其余两型）。

KET 合并规则（2026-11-28）：
- 核心词（kword）+ 易混词（kconfuse）→ 必默（kword），按英文规范化去重；
  重复时保留核心词条目，用易混词补空字段，易混词的 id 丢弃。
- 生难词（kcore）→ 高频；短语（kphrase）→ 固搭；同义（ksyn）不变。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # D:/Works/PETWebSite
SRC_PET = ROOT / "PET" / "js" / "data.js"
SRC_KET = ROOT / "PET" / "js" / "ket-data.js"
OUT = Path(__file__).resolve().parent.parent / "frontend" / "public" / "data" / "banks.json"

BANKS = ["bimo", "gaopin", "guding", "tongyi"]
KET_BANKS = ["kword", "kcore", "kphrase", "ksyn"]
KET_MERGE_PREFIX = "易混 · "

FULL_DIMS = ["m2w", "w2m", "spell"]
NO_SPELL = ["m2w", "w2m"]

# 同义库源数据把「英文 中文」混排在一个字段里（如「wonderful restaurant 绝佳餐厅」）。
# 这里按首个中文字符拆开，产出纯英文字段给题面/选项，纯中文字段给释义，避免前端反复解析。
_CJK_RE = re.compile(r"[\u3000-\u303F\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\uFF00-\uFFEF]")
# \u4E2D\u6587\u91CC\u4EE5\u6570\u5B57\u5F00\u5934\u7684\u91CF\u8BCD/\u5355\u4F4D\uFF1A\u6E90\u6570\u636E\u5E38\u5199\u6210\u300C10 \u7C73\u9AD8\u2026\u300D\uFF0C\u5207\u5206\u65F6\u6570\u5B57\u8981\u8DDF\u4E2D\u6587\u8D70
_CN_UNIT_PREFIXES = (
    "\u5C81", "\u7C73", "\u4E16\u7EAA", "\u5206\u949F", "\u5C0F\u65F6", "\u516C\u91CC", "\u516C\u65A4", "\u5143", "\u5757", "\u82F1\u9551", "\u7F8E\u5143",
    "\u5E74", "\u6708", "\u65E5", "\u5929", "\u4E2A", "\u540D", "\u4F4D", "\u6B21", "\u500D", "\u6298", "\u5C42", "\u697C",
    "\u53F7", "\u9875", "\u9898", "\u8BFE", "\u73ED", "\u7EC4", "\u7EA7",
)
# \u8FD9\u4E9B\u8BCD\u867D\u7136\u4EE5\u300C\u5E74/\u6708/\u65E5\u2026\u300D\u5F00\u5934\uFF0C\u4F46\u4E0D\u662F\u91CF\u8BCD\uFF0C\u672B\u5C3E\u6570\u5B57\u5E94\u7559\u5728\u82F1\u6587\u91CC
_CN_UNIT_EXCLUDE = ("\u5E74\u9F84", "\u5E74\u7EAA", "\u5E74\u4EE3", "\u5E74\u5EA6", "\u5E74\u7EA7", "\u65E5\u5E38", "\u65E5\u671F", "\u65E5\u5B50")
_TRAILING_NUM_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*$")


def split_en_cn(text: str | None) -> tuple[str, str]:
    s = (text or "").strip()
    if not s:
        return "", ""
    m = _CJK_RE.search(s)
    if not m:
        return s, ""
    i = m.start()
    raw_en, tail = s[:i], s[i:]
    num = _TRAILING_NUM_RE.search(raw_en)
    if num:
        token = num.group(1)
        starts_unit = tail.startswith(_CN_UNIT_PREFIXES)
        excluded = tail.startswith(_CN_UNIT_EXCLUDE)
        # \u4E2D\u6587\u91CC\u5DF2\u7ECF\u91CD\u590D\u51FA\u73B0\u540C\u4E00\u4E2A\u6570\u5B57\u65F6\uFF08\u5982\u300Cmembers aged 12-18 \u5E74\u9F84\u5728 12-18 \u5C81\u2026\u300D\uFF09\uFF0C
        # \u8BF4\u660E\u672B\u5C3E\u6570\u5B57\u5C5E\u4E8E\u82F1\u6587\uFF0C\u4E0D\u80FD\u632A\u8D70
        duplicated = re.search(rf"(?<!\d){re.escape(token)}(?!\d)", tail) is not None
        if starts_unit and not excluded and not duplicated:
            tail = num.group(0) + tail
            raw_en = raw_en[:num.start()]
    return raw_en.strip(), tail.strip()


def _split_syn_pair(text: str | None) -> tuple[str, str]:
    """同义配对字段：「英文 中文」；兼容源数据的两种脏格式：
    「反义词：everything 所有事情」（前面带中文标签）、「中文=take photos of」（英文在等号后）。"""
    raw = (text or "").strip()
    en, cn = split_en_cn(raw)
    if en:
        return en, cn
    label = re.match(r"^[^A-Za-z]*[：:]\s*(.+)$", raw)
    if label:
        en2, cn2 = split_en_cn(label.group(1))
        if en2:
            return en2, cn2
    if "=" in raw:
        left, _, right = raw.rpartition("=")
        en3, cn3 = split_en_cn(right)
        if en3:
            return en3, cn3 or left.strip()
    return en, cn


BANK_META = {
    "bimo": {"exam": "pet", "name": "必默词", "short": "必默", "dims": FULL_DIMS,
             "desc": "按话题分类的核心必会词"},
    "gaopin": {"exam": "pet", "name": "高频词", "short": "高频", "dims": FULL_DIMS,
               "desc": "真题高频词，按组编排"},
    "guding": {"exam": "pet", "name": "固定搭配", "short": "固搭", "dims": FULL_DIMS,
               "desc": "动词短语与固定搭配"},
    "tongyi": {"exam": "pet", "name": "同义替换", "short": "同义", "dims": NO_SPELL,
               "desc": "阅读里的同义改写对照（原短语 ↔ 同义短语）"},
    "kword": {"exam": "ket", "name": "必默词", "short": "必默", "dims": FULL_DIMS,
              "desc": "KET 核心词 + 易混词（已去重）"},
    "kcore": {"exam": "ket", "name": "高频词", "short": "高频", "dims": NO_SPELL,
              "desc": "KET 生难词，按类别分组"},
    "kphrase": {"exam": "ket", "name": "固定搭配", "short": "固搭", "dims": NO_SPELL,
                "desc": "get / take / put 等高频短语"},
    "ksyn": {"exam": "ket", "name": "同义替换", "short": "同义", "dims": NO_SPELL,
             "desc": "听力/阅读里前后换说法的地方"},
}

EXAMS = [
    {"id": "pet", "name": "PET", "desc": "B1 级别 · 单词 / 阅读 / 听力 / 口语"},
    {"id": "ket", "name": "KET", "desc": "A2 级别 · 单词（暂只有词库）"},
    {"id": "fce", "name": "FCE", "desc": "B2 级别 · 敬请期待", "soon": True},
    {"id": "junior", "name": "初中英语", "desc": "课内同步 · 敬请期待", "soon": True},
]


def _load_js(path: Path, var: str) -> dict:
    s = path.read_text(encoding="utf-8")
    m = re.search(rf"window\.{var}\s*=\s*(\{{.*)", s, re.S)
    if not m:
        raise SystemExit(f"{path.name} 中未找到 window.{var}")
    return json.loads(m.group(1).strip().rstrip(";\n"))


def convert_pet(banks: dict, groups: dict, meta: dict) -> None:
    old = _load_js(SRC_PET, "PET_DATA")
    for key in BANKS:
        rows = []
        for w in old["words"][key]:
            en = w.get("term") or ""
            cn = w.get("meaning") or ""
            alt = ""
            alt_cn = ""
            if key == "tongyi":
                # 同义库：term / alt 都是「英文 中文」混排，拆成四个纯字段
                en, cn = split_en_cn(w.get("term"))
                alt, alt_cn = split_en_cn(w.get("alt"))
            row = {
                "id": w["id"],
                "en": en,
                "cn": cn,
                "phonetic": w.get("phonetic") or "",
                "pos": w.get("pos") or "",
                "example": w.get("example") or "",
                "example_cn": w.get("example_cn") or "",
                "category": w.get("category") or "",
                "audio": w.get("audio") or "",
            }
            if alt:
                row["alt"] = alt
            if alt_cn:
                row["alt_cn"] = alt_cn
            rows.append(row)
        banks[key] = rows
        meta[key] = len(rows)
    groups.update(old.get("groups", {}))


def _norm_en(text: str) -> str:
    """KET 合并去重键：去首尾空格、连续空白归一、转小写。"""
    return re.sub(r"\s+", " ", str(text or "").strip()).lower()


def _merge_fields(target: dict, src: dict) -> None:
    """重复词：保留目标条目，用来源补空字段；usage 两边都有时用「；」拼接。"""
    for field in ("phonetic", "pos", "example", "example_cn"):
        if not target.get(field) and src.get(field):
            target[field] = src[field]
    usage = src.get("usage")
    if usage:
        old = target.get("usage") or ""
        if not old:
            target["usage"] = usage
        elif usage not in old:
            target["usage"] = f"{old}；{usage}"


def _ket_row(w: dict, key: str) -> dict:
    en = w.get("term") or ""
    cn = w.get("meaning") or w.get("usage") or ""
    alt = ""
    alt_cn = ""
    if key == "ksyn":
        # 同义库没有独立释义：term / alt 各自「英文 中文」混排
        en, term_cn = _split_syn_pair(w.get("term"))
        cn = term_cn or cn
        alt, alt_cn = _split_syn_pair(w.get("alt"))
    row = {
        "id": w["id"],
        "en": en,
        "cn": cn,
        "phonetic": w.get("phonetic") or "",
        "pos": w.get("pos") or "",
        "example": w.get("example") or "",
        "example_cn": w.get("example_cn") or "",
        "category": w.get("grp") or w.get("category") or "",
        "audio": "",
    }
    if w.get("usage"):
        row["usage"] = w["usage"]
    if alt:
        row["alt"] = alt
    if alt_cn:
        row["alt_cn"] = alt_cn
    return row


def _merge_ket_bimo(old: dict) -> tuple[list[dict], list[dict], int]:
    """核心词 + 易混词 → 必默；返回 (词表, 分组, 丢弃的重复条数)。"""
    rows: list[dict] = []
    by_key: dict[str, dict] = {}
    dropped = 0

    def add(row: dict) -> None:
        nonlocal dropped
        key = _norm_en(row["en"])
        if key in by_key:
            _merge_fields(by_key[key], row)
            dropped += 1
            return
        by_key[key] = row
        rows.append(row)

    for w in old["words"]["kword"]:
        add(_ket_row(w, "kword"))

    groups = [dict(g) for g in old.get("groups", {}).get("kword", [])]
    names = {g.get("name") for g in groups}
    for w in old["words"]["kconfuse"]:
        row = _ket_row(w, "kconfuse")
        if row["category"] and not row["category"].startswith(KET_MERGE_PREFIX):
            row["category"] = KET_MERGE_PREFIX + row["category"]
        add(row)

    for g in old.get("groups", {}).get("kconfuse", []):
        name = g.get("name") or g.get("key") or ""
        prefixed = KET_MERGE_PREFIX + name
        if name and prefixed not in names:
            item = dict(g)
            item["key"] = prefixed
            item["name"] = prefixed
            groups.append(item)
            names.add(prefixed)
    return rows, groups, dropped


def _report_ket_dups(banks: dict) -> None:
    """跨库重复只报告、不删除（与 PET 现状一致，避免丢掌握度）。"""
    seen: dict[str, list[str]] = defaultdict(list)
    for key in ("kword", "kcore", "kphrase"):
        for w in banks[key]:
            seen[_norm_en(w["en"])].append(key)
    dup = {k: v for k, v in seen.items() if len(v) > 1}
    if dup:
        sample = "、".join(f"{k}({'/'.join(v)})" for k, v in list(dup.items())[:5])
        print(f"KET 跨库重复 {len(dup)} 条（不自动删）：{sample}")


def _move_ket_phrases(banks: dict) -> dict[str, int]:
    """必默里带空格的词组（多词）移入固定搭配。

    同一英文已存在于固定搭配时合并字段并丢弃必默里的重复条目；
    留下的条目沿用原 id，掌握度/错题记录不串号（固定搭配不考拼写）。
    """
    keep: list[dict] = []
    by_key = {_norm_en(w["en"]): w for w in banks["kphrase"]}
    moved = merged = 0
    for w in banks["kword"]:
        if not re.search(r"\s", str(w.get("en") or "").strip()):
            keep.append(w)
            continue
        key = _norm_en(w["en"])
        hit = by_key.get(key)
        if hit is None:
            banks["kphrase"].append(w)
            by_key[key] = w
            moved += 1
        else:
            _merge_fields(hit, w)
            merged += 1
    banks["kword"] = keep
    return {"moved": moved, "merged": merged}


def convert_ket(banks: dict, groups: dict, meta: dict) -> dict:
    old = _load_js(SRC_KET, "KET_DATA")
    rows, kword_groups, dropped = _merge_ket_bimo(old)
    banks["kword"] = rows
    groups["kword"] = kword_groups
    meta["kword"] = len(rows)
    for key in ("kcore", "kphrase", "ksyn"):
        rows = [_ket_row(w, key) for w in old["words"][key]]
        banks[key] = rows
        meta[key] = len(rows)
        groups[key] = old.get("groups", {}).get(key, [])
    move = _move_ket_phrases(banks)
    meta["kword"] = len(banks["kword"])
    meta["kphrase"] = len(banks["kphrase"])
    _report_ket_dups(banks)
    return {
        "kword_src": len(old["words"]["kword"]),
        "kconfuse_src": len(old["words"]["kconfuse"]),
        "kword_merged": len(banks["kword"]),
        "dropped": dropped,
        "moved": move["moved"],
        "merged": move["merged"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="只校验不写文件")
    args = ap.parse_args()

    banks: dict[str, list[dict]] = {}
    groups: dict[str, list[dict]] = {}
    meta: dict[str, int] = {}
    convert_pet(banks, groups, meta)
    stats = convert_ket(banks, groups, meta)
    print(
        "KET 必默合并：核心词 {kword_src} + 易混词 {kconfuse_src} → {kword_merged}"
        "（去重 {dropped} 条）".format(**stats)
    )
    print(
        "KET 必默多词词组移入固定搭配：{moved} 条"
        "（与既有固搭重复合并 {merged} 条）".format(**stats)
    )

    # 校验：ID 唯一、跨库无重复、计数与 meta 一致
    seen: set[str] = set()
    for key, rows in banks.items():
        ids = [w["id"] for w in rows]
        assert len(ids) == len(set(ids)), f"{key} 内 id 重复"
        dup = seen & set(ids)
        assert not dup, f"{key} 跨库重复 id: {list(dup)[:5]}"
        seen |= set(ids)
        assert meta[key] == len(ids), f"{key} 计数不符: {meta[key]} != {len(ids)}"
        assert rows, f"{key} 空库"
    ket_keys = {k for k in banks if BANK_META[k]["exam"] == "ket"}
    assert set(KET_BANKS) == ket_keys, f"KET 词库应只有 {KET_BANKS}，实际 {sorted(ket_keys)}"

    # 同义库必须成对：题面/选项只用纯英文，中文只做释义
    broken_pet = [
        w["id"] for w in banks["tongyi"]
        if not (w.get("en") and w.get("cn") and w.get("alt") and w.get("alt_cn"))
    ]
    assert not broken_pet, f"tongyi 字段不完整: {broken_pet[:5]}"
    broken_ket = [
        w["id"] for w in banks["ksyn"]
        if not (w.get("en") and w.get("alt"))
    ]
    assert not broken_ket, f"ksyn 字段不完整（缺英文原短语或同义短语）: {broken_ket[:8]}"

    doc = {
        "exams": EXAMS,
        "bankMeta": {k: BANK_META[k] for k in banks},
        "banks": banks,
        "groups": groups,
        "meta": meta,
    }
    pet_n = sum(len(banks[k]) for k in BANKS)
    ket_n = sum(len(banks[k]) for k in KET_BANKS)
    print(f"校验通过：PET {pet_n} 条（{len(BANKS)} 库） · KET {ket_n} 条（{len(KET_BANKS)} 库） · 合计 {pet_n + ket_n}")

    if args.dry:
        print("dry run，未写出")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"已写出 {OUT}（{OUT.stat().st_size // 1024} KB）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
