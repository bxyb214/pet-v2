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

BANK_META = {
    "bimo": {"exam": "pet", "name": "必默词", "short": "必默", "dims": FULL_DIMS,
             "desc": "按话题分类的核心必会词"},
    "gaopin": {"exam": "pet", "name": "高频词", "short": "高频", "dims": FULL_DIMS,
               "desc": "真题高频词，按组编排"},
    "guding": {"exam": "pet", "name": "固定搭配", "short": "固搭", "dims": FULL_DIMS,
               "desc": "动词短语与固定搭配"},
    "tongyi": {"exam": "pet", "name": "同义替换", "short": "同义", "dims": FULL_DIMS,
               "desc": "阅读里的同义改写对照"},
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
        banks[key] = [
            {
                "id": w["id"],
                "en": w["term"],
                "cn": w["meaning"],
                "phonetic": w.get("phonetic") or "",
                "pos": w.get("pos") or "",
                "example": w.get("example") or "",
                "example_cn": w.get("example_cn") or "",
                "category": w.get("category") or "",
                "audio": w.get("audio") or "",
                # 同义替换库：term 是原说法，alt 是同义说法（中英对照），成对显示
                **({"alt": w["alt"]} if w.get("alt") else {}),
            }
            for w in old["words"][key]
        ]
        meta[key] = len(banks[key])
    groups.update(old.get("groups", {}))


def convert_ket(banks: dict, groups: dict, meta: dict) -> None:
    old = _load_js(SRC_KET, "KET_DATA")
    for key in KET_BANKS:
        rows = []
        for w in old["words"][key]:
            en = w.get("term") or ""
            cn = w.get("meaning") or w.get("usage") or ""
            # 同义库没有释义：term 是原说法，alt 是同义说法，配对显示
            if key == "ksyn" and not w.get("meaning"):
                cn = w.get("alt") or ""
            rows.append(
                {
                    "id": w["id"],
                    "en": en,
                    "cn": cn,
                    "phonetic": w.get("phonetic") or "",
                    "pos": w.get("pos") or "",
                    "example": w.get("example") or "",
                    "example_cn": w.get("example_cn") or "",
                    "category": w.get("grp") or w.get("category") or "",
                    "audio": "",
                    # KET 特有：用法/口诀、同义说法
                    **({"usage": w["usage"]} if w.get("usage") else {}),
                    **({"alt": w["alt"]} if w.get("alt") else {}),
                }
            )
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
