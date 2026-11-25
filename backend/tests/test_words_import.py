"""管理员 Excel 批量导入生词（b8e2f6a9c3d1：custom_words.bank/exam）。"""
import io

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.main import app

client = TestClient(app)
HEAD = {}


def _setup_admin() -> int:
    """注册管理员 + 一个学生，返回 (admin_headers, student_id)。

    conftest 每个测试后清表：claim（仅库内无账号时）建管理员，学生用邀请码注册。
    """
    from app.db import SessionLocal
    from app.models.user import InviteCode

    db = SessionLocal()
    db.add(InviteCode(code="IMP-INVITE"))
    db.add(InviteCode(code="IMP-STUDENT"))
    db.commit()
    db.close()
    r = client.post(
        "/api/v1/auth/claim",
        json={"username": "imp-admin", "password": "pet-test-pass", "invite_code": "IMP-INVITE"},
    )
    admin_head = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r2 = client.post(
        "/api/v1/auth/register",
        json={"username": "imp-student", "password": "pet-test-pass", "invite_code": "IMP-STUDENT"},
    )
    return admin_head, r2.json()["user_id"]


def _xlsx(rows: list[list[object]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_import_requires_admin():
    admin_head, student_id = _setup_admin()
    r = client.post(
        f"/api/v1/admin/users/{student_id}/words/import?exam=pet",
        files={"file": ("w.xlsx", _xlsx([["单词", "词库", "词性", "释义", "英文例句", "中文翻译"]]), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 401  # 未带 token
    # 学生 token 也不能导入
    r2 = client.post(
        "/api/v1/auth/login", json={"username": "imp-student", "password": "pet-test-pass"}
    )
    stu_head = {"Authorization": f"Bearer {r2.json()['access_token']}"}
    r3 = client.post(
        f"/api/v1/admin/users/{student_id}/words/import?exam=pet",
        headers=stu_head,
        files={"file": ("w.xlsx", _xlsx([["单词", "词库", "词性", "释义", "英文例句", "中文翻译"]]))},
    )
    assert r3.status_code == 403
    assert admin_head  # 已建好管理员备用


def test_self_import_own_wordbook():
    """学生自助导入：登录即可，导入到自己的生词本；未登录 401。"""
    _, student_id = _setup_admin()
    r = client.post(
        "/api/v1/auth/login", json={"username": "imp-student", "password": "pet-test-pass"}
    )
    stu_head = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # 模板下载
    t = client.get("/api/v1/words/custom/import/template", headers=stu_head)
    assert t.status_code == 200
    assert "spreadsheetml" in t.headers["content-type"]

    data = _xlsx([
        ["单词", "词库", "词性", "释义", "英文例句", "中文翻译"],
        ["shadow", "高频", "n.", "影子", "", ""],
        ["guest", "核心词", "n.", "客人", "", ""],  # KET 级别才允许核心词
    ])
    imp = client.post(
        "/api/v1/words/custom/import?exam=pet",
        headers=stu_head,
        files={"file": ("w.xlsx", data)},
    )
    assert imp.status_code == 200
    assert imp.json()["added"] == 1
    assert any("不属于 PET" in s for s in imp.json()["skipped"])

    lst = client.get("/api/v1/words/custom", headers=stu_head).json()
    assert [w["word"] for w in lst] == ["shadow"]
    assert lst[0]["bank"] == "gaopin"
    assert lst[0]["exam"] == "pet"

    # 未登录 401
    assert client.get("/api/v1/words/custom/import/template").status_code == 401


def test_import_roundtrip_and_list():
    admin_head, student_id = _setup_admin()
    data = _xlsx([
        ["单词", "词库", "词性", "释义", "英文例句", "中文翻译"],
        ["shadow", "高频", "n.", "影子", "The cat has a long shadow.", "猫有一个长影子。"],
        ["make something to take home", "同义", "", "制作可带回家的物品", "", ""],
        ["", "", "", "", "", ""],  # 空行跳过
        ["walk", "未知词库", "", "", "", ""],  # 词库无法识别 → 400
    ])
    r = client.post(
        f"/api/v1/admin/users/{student_id}/words/import?exam=pet",
        headers=admin_head,
        files={"file": ("w.xlsx", data)},
    )
    assert r.status_code == 400
    assert "无法识别" in r.json()["detail"]

    data_ok = _xlsx([
        ["单词", "词库", "词性", "释义", "英文例句", "中文翻译"],
        ["shadow", "高频", "n.", "影子", "The cat has a long shadow.", "猫有一个长影子。"],
        ["make something to take home", "同义", "", "制作可带回家的物品", "", ""],
        ["", "", "", "", "", ""],
    ])
    r2 = client.post(
        f"/api/v1/admin/users/{student_id}/words/import?exam=pet",
        headers=admin_head,
        files={"file": ("w.xlsx", data_ok)},
    )
    assert r2.status_code == 200
    assert r2.json()["added"] == 2
    assert r2.json()["skipped"] == []

    # 学生视角：生词本可见，带 bank/exam；同步 pull 也透传
    stu = client.post("/api/v1/auth/login", json={"username": "imp-student", "password": "pet-test-pass"}).json()
    stu_head = {"Authorization": f"Bearer {stu['access_token']}"}
    lst = client.get("/api/v1/words/custom", headers=stu_head).json()
    assert {w["word"] for w in lst} == {"shadow", "make something to take home"}
    by_word = {w["word"]: w for w in lst}
    assert by_word["shadow"]["bank"] == "gaopin"
    assert by_word["shadow"]["exam"] == "pet"
    assert by_word["make something to take home"]["bank"] == "tongyi"

    pull = client.get("/api/v1/sync/pull", headers=stu_head).json()
    cw = pull["data"]["custom_words"]
    assert {w["word"]: w["bank"] for w in cw}["shadow"] == "gaopin"


def test_import_rejects_wrong_exam_bank_and_duplicates():
    admin_head, student_id = _setup_admin()
    # KET 级别导 PET 的必默词 → 整行跳过
    data = _xlsx([
        ["单词", "词库", "词性", "释义", "英文例句", "中文翻译"],
        ["shadow", "高频", "n.", "影子", "", ""],
        ["guest", "核心词", "n.", "客人", "", ""],
        ["shadow", "核心词", "n.", "重复词", "", ""],
    ])
    r = client.post(
        f"/api/v1/admin/users/{student_id}/words/import?exam=ket",
        headers=admin_head,
        files={"file": ("w.xlsx", data)},
    )
    assert r.status_code == 200
    body = r.json()
    # shadow（高频）不属于 KET 被跳过、不计入去重；第二个 shadow（核心词）+ guest 都入库
    assert body["added"] == 2
    assert any("不属于 KET" in s for s in body["skipped"])

    # 再传一次：已存在的跳过
    r2 = client.post(
        f"/api/v1/admin/users/{student_id}/words/import?exam=ket",
        headers=admin_head,
        files={"file": ("w.xlsx", data)},
    )
    assert r2.status_code == 200
    assert r2.json()["added"] == 0
    assert any("已在生词本" in s for s in r2.json()["skipped"])

    # 非法级别
    r3 = client.post(
        f"/api/v1/admin/users/{student_id}/words/import?exam=toefl",
        headers=admin_head,
        files={"file": ("w.xlsx", data)},
    )
    assert r3.status_code == 400


def test_import_template_download():
    admin_head, _ = _setup_admin()
    r = client.get("/api/v1/admin/words/import/template", headers=admin_head)
    assert r.status_code == 200
    assert "spreadsheetml" in r.headers["content-type"]
    wb = Workbook()  # 能被 openpyxl 读回
    from openpyxl import load_workbook
    out = load_workbook(io.BytesIO(r.content))
    ws = out.active
    assert [c.value for c in ws[1]] == ["单词", "词库", "词性", "释义", "英文例句", "中文翻译"]
