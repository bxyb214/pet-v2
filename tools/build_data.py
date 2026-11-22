"""构建 v2 词库静态数据：旧站 PET/js/data.js → frontend/public/data/banks.json

用法：python tools/build_data.py [--dry]
源：D:/Works/PETWebSite/PET/js/data.js（window.PET_DATA）
出：pet-v2/frontend/public/data/banks.json（nginx/静态托管：/data/banks.json）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # D:/Works/PETWebSite
SRC = ROOT / "PET" / "js" / "data.js"
OUT = Path(__file__).resolve().parent.parent / "frontend" / "public" / "data" / "banks.json"

BANKS = ["bimo", "gaopin", "guding", "tongyi"]


def load_old_data() -> dict:
    s = SRC.read_text(encoding="utf-8")
    m = re.search(r"window\.PET_DATA=(.*)", s, re.S)
    if not m:
        raise SystemExit("data.js 中未找到 window.PET_DATA")
    return json.loads(m.group(1).strip().rstrip(";\n"))


def convert(old: dict) -> dict:
    banks: dict[str, list[dict]] = {}
    for key in BANKS:
        words = old["words"][key]
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
            }
            for w in words
        ]
    doc = {"banks": banks, "groups": old.get("groups", {}), "meta": old.get("meta", {})}
    return doc


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="只校验不写文件")
    args = ap.parse_args()

    old = load_old_data()
    doc = convert(old)

    # 校验：ID 唯一、跨库无重复、计数与 meta 一致
    seen: set[str] = set()
    for key in BANKS:
        ids = [w["id"] for w in doc["banks"][key]]
        assert len(ids) == len(set(ids)), f"{key} 内 id 重复"
        dup = seen & set(ids)
        assert not dup, f"跨库重复 id: {dup}"
        seen |= set(ids)
        if doc["meta"].get(key) is not None:
            assert doc["meta"][key] == len(ids), f"{key} meta 计数不符: {doc['meta'][key]} != {len(ids)}"
    total = sum(len(doc["banks"][k]) for k in BANKS)
    print(f"校验通过：bimo={len(doc['banks']['bimo'])} gaopin={len(doc['banks']['gaopin'])} "
          f"guding={len(doc['banks']['guding'])} tongyi={len(doc['banks']['tongyi'])} 总计={total}")

    if args.dry:
        print("dry run，未写出")
        return

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"已写出 {OUT}（{OUT.stat().st_size // 1024} KB）")


if __name__ == "__main__":
    sys.exit(main())
