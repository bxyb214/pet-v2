"""生成英语内容 Excel 模板（每级每模块一份，共 15 份）。

用法：
  backend/.venv/Scripts/python.exe tools/make_content_templates.py            # 缺失才生成
  ... --exam ket --module reading                                            # 只生成一份
  ... --force                                                                # 覆盖已有文件（会覆盖已填内容！）

产物：data-src/english/<exam>/<module>.xlsx
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import content_schema as S
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parent.parent
EXCEL_DIR = ROOT / "data-src" / "english"

HEADER_FILL = PatternFill("solid", fgColor="DCEFE2")
NOTE_FILL = PatternFill("solid", fgColor="F4F7F2")
HEADER_FONT = Font(bold=True, color="1F3D2B")


def _note_sheet(ws, exam: str, module: str) -> None:
    """说明页：标题 + 工作表清单 + 通用/模块规则 + 示例。"""
    ws.column_dimensions["A"].width = 118
    lines: list[str] = [
        f"英语内容模板 · {S.EXAM_NAMES[exam]} · {S.MODULE_NAMES[module]}",
        "",
        "用途：按本表整理教材资料，保存后运行校验器；后续接入构建脚本生成前端 JSON。",
        "",
        "工作表与列：",
    ]
    for sheet, cols in S.COLUMNS[module].items():
        lines.append(f"  · {sheet}：{' | '.join(cols)}")
    lines += ["", "通用规则："] + [f"  · {x}" for x in S.COMMON_NOTES]
    lines += ["", "本模块规则："] + [f"  · {x}" for x in S.MODULE_NOTES[module]]
    examples = S.EXAMPLES.get(module, {})
    if examples:
        lines += ["", "填写示例（仅说明，不要照抄进数据表）："]
        for sheet, row in examples.items():
            cols = S.COLUMNS[module][sheet]
            lines.append(f"  · {sheet}：")
            lines.append("    " + " | ".join(f"{c}={v}" for c, v in zip(cols, row)))
    lines += ["", "提示：数据表从第 2 行开始填；空行自动忽略；同一表内按英文去重。"]

    for i, text in enumerate(lines, start=1):
        cell = ws.cell(row=i, column=1, value=text)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        if i == 1:
            cell.font = Font(bold=True, size=14, color="1F3D2B")
        elif text.endswith("：") or text in ("通用规则：", "本模块规则：", "工作表与列："):
            cell.font = Font(bold=True, color="1F3D2B")
        elif text.startswith("  · "):
            cell.fill = NOTE_FILL


def _data_sheet(wb: Workbook, sheet: str, columns: list[str], enums: dict[str, list[str]]) -> None:
    ws = wb.create_sheet(sheet)
    ws.append(columns)
    for idx, _ in enumerate(columns, start=1):
        c = ws.cell(row=1, column=idx)
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
        c.alignment = Alignment(horizontal="center", vertical="center")
        width = max(10, min(28, len(columns[idx - 1]) * 2 + 6))
        ws.column_dimensions[get_column_letter(idx)].width = width
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 22
    for name, options in enums.items():
        if name not in columns:
            continue
        col = get_column_letter(columns.index(name) + 1)
        dv = DataValidation(
            type="list",
            formula1='"' + ",".join(options) + '"',
            allow_blank=True,
            showDropDown=False,
        )
        ws.add_data_validation(dv)
        dv.add(f"{col}2:{col}5000")


def _fill_books(ws, exam: str) -> None:
    for book_id, name, desc in S.BOOKS[exam]:
        ws.append([book_id, name, desc])


def build(exam: str, module: str, force: bool) -> str:
    path = S.module_path(ROOT, exam, module)
    if path.exists() and not force:
        return f"跳过 {path.relative_to(ROOT)}（已存在；--force 覆盖）"
    path.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    note = wb.active
    note.title = "说明"
    _note_sheet(note, exam, module)

    enums = S.ENUMS.get(module, {})
    for sheet, cols in S.COLUMNS[module].items():
        _data_sheet(wb, sheet, cols, enums.get(sheet, {}))
        if S.BOOK_SHEETS.get(module) == sheet:
            _fill_books(wb[sheet], exam)

    wb.save(path)
    return f"已生成 {path.relative_to(ROOT)}"


def main() -> int:
    ap = argparse.ArgumentParser(description="生成英语内容 Excel 模板")
    ap.add_argument("--exam", action="append", choices=S.EXAMS, help="可重复；默认全部")
    ap.add_argument("--module", action="append", choices=S.MODULES, help="可重复；默认全部")
    ap.add_argument("--force", action="store_true", help="覆盖已有文件（会覆盖已填内容）")
    args = ap.parse_args()

    exams = args.exam or S.EXAMS
    modules = args.module or S.MODULES
    for exam in exams:
        for module in modules:
            print(build(exam, module, args.force))
    print(f"\n模板目录：{EXCEL_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
