"""本地开发静态挂载：SPA 回退、404 边界、媒体令牌与路径穿越。"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.security import make_media_token
from app.db import SessionLocal
from app.dev_static import _safe_file, mount_static
from app.models.user import User


def _client(tmp_path: Path, media_root: Path | None = None) -> TestClient:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>spa</html>", encoding="utf-8")
    (dist / "assets").mkdir()
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (dist / "data").mkdir()
    (dist / "data" / "banks.json").write_text("[]", encoding="utf-8")

    app = FastAPI()

    @app.get("/api/ping")
    def ping() -> dict:
        return {"ok": True}

    mount_static(app, dist, media_root)
    return TestClient(app)


def _user(username: str) -> int:
    db = SessionLocal()
    user = User(username=username, password_hash="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    uid = user.id
    db.close()
    return uid


def test_api_route_wins_and_unknown_api_is_404(tmp_path: Path) -> None:
    client = _client(tmp_path)
    assert client.get("/api/ping").json() == {"ok": True}
    assert client.get("/api/nope").status_code == 404


def test_static_file_and_cache_headers(tmp_path: Path) -> None:
    client = _client(tmp_path)
    js = client.get("/assets/app.js")
    assert js.status_code == 200
    assert js.text == "console.log(1)"
    assert "max-age=2592000" in js.headers["cache-control"]

    data = client.get("/data/banks.json")
    assert data.status_code == 200
    assert data.headers["cache-control"] == "no-cache"


def test_spa_fallback_and_missing_asset(tmp_path: Path) -> None:
    client = _client(tmp_path)
    spa = client.get("/vocab/plan")
    assert spa.status_code == 200
    assert "spa" in spa.text
    assert client.get("/missing.js").status_code == 404
    assert client.get("/media/math/none.mp4").status_code == 404
    assert client.head("/vocab/plan").status_code == 200
    assert client.head("/assets/app.js").status_code == 200


def test_media_requires_valid_token_and_supports_range(tmp_path: Path) -> None:
    media = tmp_path / "media"
    media.mkdir()
    (media / "lesson.mp4").write_bytes(b"0123456789")
    client = _client(tmp_path, media)

    assert client.get("/media/math/lesson.mp4").status_code == 401

    token, _ = make_media_token(_user("viewer"))
    ok = client.get(f"/media/math/lesson.mp4?mt={token}")
    assert ok.status_code == 200
    assert ok.content == b"0123456789"

    part = client.get(f"/media/math/lesson.mp4?mt={token}", headers={"Range": "bytes=0-3"})
    assert part.status_code == 206
    assert part.content == b"0123"


def test_media_path_traversal_rejected(tmp_path: Path) -> None:
    media = tmp_path / "media"
    media.mkdir()
    (tmp_path / "secret.txt").write_text("no", encoding="utf-8")
    assert _safe_file(media.resolve(), "../secret.txt") is None
