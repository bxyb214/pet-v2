"""测试环境隔离：独立 sqlite 文件 + 会话级建表 + 函数级清数据。"""
import os
import tempfile

_test_db = os.path.join(tempfile.gettempdir(), "pet_v2_test.db")
if os.path.exists(_test_db):
    os.remove(_test_db)
os.environ["PET_DATABASE_URL"] = f"sqlite:///{_test_db}"
os.environ["PET_JWT_SECRET"] = "x" * 40  # 避免 InsecureKeyLength 警告

import pytest  # noqa: E402

from app.db import Base, engine, SessionLocal  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(autouse=True)
def _clean_data():
    """每个测试后清空所有表数据（保留 schema）。"""
    yield
    session = SessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()
