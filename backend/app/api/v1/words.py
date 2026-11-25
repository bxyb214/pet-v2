"""自加词路由（V11 / V11a）。"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import check_paid_or_raise, get_current_user, require_paid_ai
from app.db import get_db
from app.models.extra import CustomWord
from app.models.user import User
from app.services import ai_enrich, word_import

router = APIRouter(prefix="/words/custom", tags=["words"])


class WordIn(BaseModel):
    word: str = Field(min_length=1, max_length=64)
    pos: str = Field(default="", max_length=64)
    definition: str = Field(default="", max_length=256)
    example_en: str = Field(default="", max_length=512)
    example_cn: str = Field(default="", max_length=512)


class EnrichIn(BaseModel):
    word: str = Field(min_length=1, max_length=64)


def _out(w: CustomWord) -> dict:
    return {
        "id": w.id,
        "word": w.word,
        "pos": w.pos,
        "definition": w.definition,
        "example_en": w.example_en,
        "example_cn": w.example_cn,
        "bank": w.bank or "",
        "exam": w.exam or "",
    }


@router.get("")
def list_words(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = db.execute(
        select(CustomWord).where(CustomWord.user_id == user.id).order_by(CustomWord.id.desc())
    ).scalars().all()
    return [_out(w) for w in rows]


@router.post("", status_code=201)
def add_word(
    body: WordIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    # 四项全空且配置了 Key → 服务端自动 enrich（付费 AI，走闸门）
    if not (body.pos or body.definition or body.example_en or body.example_cn):
        if not ai_enrich.dev_mock.is_dev():
            check_paid_or_raise(db, user)
        try:
            filled = ai_enrich.enrich_word(db, body.word, user.id)
        except LookupError:
            raise HTTPException(503, "未配置 AI Key，请先在管理页配置或手动填写")
        except Exception:
            raise HTTPException(502, "AI 生成失败，请稍后重试或手动填写")
        body.pos = filled["pos"]
        body.definition = filled["definition"]
        body.example_en = filled["example_en"]
        body.example_cn = filled["example_cn"]
    row = CustomWord(user_id=user.id, **body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return _out(row)


@router.put("/{word_id}")
def update_word(
    word_id: int,
    body: WordIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    row = db.get(CustomWord, word_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(404, "词条不存在")
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    db.commit()
    return _out(row)


@router.delete("/{word_id}", status_code=204)
def delete_word(
    word_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    row = db.get(CustomWord, word_id)
    if row is not None and row.user_id == user.id:
        db.delete(row)
        db.commit()


@router.post("/enrich")
def enrich(
    body: EnrichIn,
    user: User = Depends(require_paid_ai),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return ai_enrich.enrich_word(db, body.word, user.id)
    except LookupError:
        raise HTTPException(503, "未配置 AI Key")
    except Exception:
        raise HTTPException(502, "AI 生成失败")


@router.post("/import")
def import_words(
    exam: str,
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """学生自助 Excel 批量导入生词到自己的生词本（模板同管理员导入）。"""
    return word_import.import_words_from_excel(db, user.id, exam, file.file.read())


@router.get("/import/template")
def import_template(_user: User = Depends(get_current_user)) -> Response:
    """下载导入模板（含一行示例）。"""
    return Response(
        content=word_import.template_xlsx(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=pet-word-import-template.xlsx"},
    )
