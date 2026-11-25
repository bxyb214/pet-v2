"""生词 Excel 批量导入（V11a）：管理员代导 + 学生自助导入共用。"""
import io

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.extra import CustomWord

# 允许的级别与词库（FCE 当前为敬请期待，仍允许预导入）
IMPORT_EXAMS = {
    "pet": {"bimo", "gaopin", "guding", "tongyi"},
    "ket": {"kword", "kcore", "kphrase", "kconfuse", "ksyn"},
    "fce": {"bimo", "gaopin", "guding", "tongyi"},
}
# Excel 模板列名
IMPORT_HEADERS = ["单词", "词库", "词性", "释义", "英文例句", "中文翻译"]
# 词库中文短名 → bank key
BANK_NAME_MAP = {
    "必默": "bimo", "必默词": "bimo", "必默词700": "bimo",
    "高频": "gaopin", "高频词": "gaopin",
    "固搭": "guding", "固定搭配": "guding",
    "同义": "tongyi", "同义替换": "tongyi",
    "核心词": "kword", "核心词表": "kword",
    "生难词": "kcore", "生难词200": "kcore",
    "短语": "kphrase", "动词短语": "kphrase",
    "易混词": "kconfuse", "易混词组": "kconfuse",
}


def _norm_cell(v: object) -> str:
    """单元格规范化：None → 空串，其余去首尾空白。"""
    return str(v).strip() if v is not None else ""


def _bank_of(name: str) -> str:
    """词库列（中文名）→ bank key；未知词库报错让用户改表。"""
    key = BANK_NAME_MAP.get(name)
    if key is None:
        raise HTTPException(400, f"词库「{name}」无法识别，请使用模板中的词库名（必默/高频/固搭/同义…）")
    return key


def import_words_from_excel(db: Session, user_id: int, exam: str, data: bytes) -> dict:
    """解析 Excel 并导入到 user_id 的生词本；返回 {added, skipped, skipped_more}。"""
    if exam not in IMPORT_EXAMS:
        raise HTTPException(400, "级别仅支持 pet / ket / fce")

    try:
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception:
        raise HTTPException(400, "Excel 文件无法解析，请下载模板后填写再上传")

    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    if not rows:
        raise HTTPException(400, "表格是空的")

    # 表头校验（列顺序可变，但六个列名必须都出现且在前 8 列内）
    header = [_norm_cell(c) for c in rows[0][:8]]
    missing = [h for h in IMPORT_HEADERS if h not in header]
    if missing:
        raise HTTPException(400, f"表头缺少列：{'、'.join(missing)}，请按模板填写")
    col = {h: header.index(h) for h in IMPORT_HEADERS}

    allowed = IMPORT_EXAMS[exam]
    seen: set[str] = set()
    words: list[dict] = []
    skipped: list[str] = []
    for i, row in enumerate(rows[1:], start=2):
        vals = {h: _norm_cell(row[col[h]] if col[h] < len(row) else None) for h in IMPORT_HEADERS}
        word = vals["单词"]
        if not word:
            continue  # 空行
        if not vals["词库"]:
            skipped.append(f"第{i}行「{word}」缺词库")
            continue
        bank = _bank_of(vals["词库"])
        if bank not in allowed:
            skipped.append(f"第{i}行「{word}」的词库不属于 {exam.upper()}")
            continue
        if word.lower() in seen:
            skipped.append(f"第{i}行「{word}」与前面的行重复")
            continue
        seen.add(word.lower())
        words.append({
            "word": word[:64],
            "bank": bank,
            "pos": vals["词性"][:64],
            "definition": vals["释义"][:256],
            "example_en": vals["英文例句"][:512],
            "example_cn": vals["中文翻译"][:512],
        })

    if not words:
        raise HTTPException(400, "没有可导入的行：" + ("；".join(skipped) if skipped else "表格没有数据"))

    # 同词已存在（该学生）→ 服务端最新优先：跳过而不是重复插入
    existing = {
        w.word.lower()
        for w in db.query(CustomWord).filter(CustomWord.user_id == user_id)
    }
    added = 0
    for item in words:
        if item["word"].lower() in existing:
            skipped.append(f"「{item['word']}」已在生词本中")
            continue
        db.add(CustomWord(user_id=user_id, source="import", exam=exam, **item))
        added += 1
    db.commit()

    return {"added": added, "skipped": skipped[:20], "skipped_more": max(0, len(skipped) - 20)}


def template_xlsx() -> bytes:
    """生成导入模板（含一行示例）。"""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "生词导入"
    ws.append(IMPORT_HEADERS)
    ws.append(["shadow", "高频", "n.", "影子", "The cat has a long shadow.", "猫有一个长影子。"])
    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 10
    ws.column_dimensions["C"].width = 8
    ws.column_dimensions["D"].width = 24
    ws.column_dimensions["E"].width = 36
    ws.column_dimensions["F"].width = 24
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
