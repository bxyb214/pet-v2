"""构建 v2 词库静态数据：旧站 PET/js/{data,ket-data}.js → frontend/public/data/banks.json

用法：python tools/build_data.py [--dry]
源：D:/Works/PETWebSite/PET/js/data.js（window.PET_DATA，PET 四库）
    D:/Works/PETWebSite/PET/js/ket-data.js（window.KET_DATA，KET 五库）
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
`bankMeta[bank].dims` 决定这个库考哪些维度（KET 按旧站规则不考拼写）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # D:/Works/PETWebSite
SRC_PET = ROOT / "PET" / "js" / "data.js"
SRC_KET = ROOT / "PET" / "js" / "ket-data.js"
OUT = Path(__file__).resolve().parent.parent / "frontend" / "public" / "data" / "banks.json"

BANKS = ["bimo", "gaopin", "guding", "tongyi"]
KET_BANKS = ["kword", "kcore", "kphrase", "kconfuse", "ksyn"]

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


BANK_META = {
    "bimo": {"exam": "pet", "name": "必默词", "short": "必默", "dims": FULL_DIMS,
             "desc": "按话题分类的核心必会词"},
    "gaopin": {"exam": "pet", "name": "高频词", "short": "高频", "dims": FULL_DIMS,
               "desc": "真题高频词，按组编排"},
    "guding": {"exam": "pet", "name": "固定搭配", "short": "固搭", "dims": FULL_DIMS,
               "desc": "动词短语与固定搭配"},
    "tongyi": {"exam": "pet", "name": "同义替换", "short": "同义", "dims": NO_SPELL,
               "desc": "阅读里的同义改写对照（原短语 ↔ 同义短语）"},
    "kword": {"exam": "ket", "name": "KET 核心词表", "short": "核心词", "dims": NO_SPELL,
              "desc": "KET 1500 词按话题分组"},
    "kcore": {"exam": "ket", "name": "KET 生难词 200", "short": "生难词", "dims": NO_SPELL,
              "desc": "拼写或词义容易出错的词"},
    "kphrase": {"exam": "ket", "name": "KET 动词短语 80", "short": "短语", "dims": NO_SPELL,
                "desc": "get / take / put 等高频短语"},
    "kconfuse": {"exam": "ket", "name": "KET 易混词 50 组", "short": "易混词", "dims": NO_SPELL,
                 "desc": "近义或形近、容易混用的词对"},
    "ksyn": {"exam": "ket", "name": "KET 同义替换", "short": "同义", "dims": NO_SPELL,
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


def convert_ket(banks: dict, groups: dict, meta: dict) -> None:
    old = _load_js(SRC_KET, "KET_DATA")
    for key in KET_BANKS:
        rows = []
        for w in old["words"][key]:
            en = w.get("term") or ""
            cn = w.get("meaning") or w.get("usage") or ""
            alt = ""
            alt_cn = ""
            if key == "ksyn":
                # 同义库没有独立释义：term / alt 各自「英文 中文」混排
                en, term_cn = split_en_cn(w.get("term"))
                cn = term_cn or cn
                alt, alt_cn = split_en_cn(w.get("alt"))
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
            rows.append(row)
        banks[key] = rows
        meta[key] = len(rows)
        groups[key] = old.get("groups", {}).get(key, [])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="只校验不写文件")
    args = ap.parse_args()

    banks: dict[str, list[dict]] = {}
    groups: dict[str, list[dict]] = {}
    meta: dict[str, int] = {}
    convert_pet(banks, groups, meta)
    convert_ket(banks, groups, meta)

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
    if broken_ket:
        print(f"警告：KET 同义库有 {len(broken_ket)} 条缺英文题面或同义说法：{broken_ket[:8]}")

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
