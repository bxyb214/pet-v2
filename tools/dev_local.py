#!/usr/bin/env python3
"""本地开发/预发布环境：Windows 原生进程，http://localhost:8088

不依赖 Docker / nginx：同一个 uvicorn 进程同时提供 FastAPI 与 `frontend/dist`，
路由规则与生产 nginx 对齐（SPA 回退、数据文件 no-cache、媒体令牌鉴权）。

在仓库根目录执行：

    backend/.venv/Scripts/python.exe tools/dev_local.py
    backend/.venv/Scripts/python.exe tools/dev_local.py --build     # 先构建前端
    backend/.venv/Scripts/python.exe tools/dev_local.py --prod-mode # 关闭模拟 AI

环境变量（已设置则优先；`--prod-mode` 例外，显式关闭模拟）：
    PET_DATABASE_URL  默认 sqlite:///./data/pet.db（相对 backend/）
    PET_DEV_MODE      默认 1；--prod-mode 等价于 0
    PET_MATH_MEDIA    设置后挂载 /media/math（本地课程视频目录）

生产部署仍用 `tools/deploy_nas.py deploy --host <NAS-IP>`（nginx + api 容器）。
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
DIST = FRONTEND / "dist"


def die(msg: str) -> None:
    print(f"\n[×] {msg}", file=sys.stderr)
    sys.exit(1)


def info(msg: str) -> None:
    print(f"[·] {msg}")


def run(cmd: list[str], cwd: Path) -> None:
    print(f"   $ {' '.join(cmd)}")
    code = subprocess.call(cmd, cwd=str(cwd))
    if code != 0:
        die(f"命令失败（退出码 {code}）：{' '.join(cmd)}")


def build_frontend() -> None:
    npm = shutil.which("npm")
    if not npm:
        die("找不到 npm：确认 Node.js 已安装并加入 PATH（安装后请重开终端）")
    cmd = [npm, "run", "build"]
    if os.name == "nt" and Path(npm).suffix.lower() in (".cmd", ".bat"):
        cmd = ["cmd.exe", "/c", *cmd]
    info("构建前端（npm run build）…")
    run(cmd, FRONTEND)


def migrate() -> None:
    info("应用数据库迁移（alembic upgrade head）…")
    run([sys.executable, "-m", "alembic", "upgrade", "head"], BACKEND)


def main() -> None:
    ap = argparse.ArgumentParser(description="本地开发环境（localhost:8088，无 Docker）")
    ap.add_argument("--host", default="127.0.0.1", help="监听地址（默认仅本机）")
    ap.add_argument("--port", type=int, default=8088, help="HTTP 端口（默认 8088）")
    ap.add_argument("--build", action="store_true", help="启动前执行 npm run build")
    ap.add_argument("--prod-mode", action="store_true", help="关闭 PET_DEV_MODE 模拟（默认开启）")
    ap.add_argument("--skip-migrate", action="store_true", help="跳过 alembic upgrade head")
    args = ap.parse_args()

    if args.build:
        build_frontend()
    if not (DIST / "index.html").is_file():
        die("缺少 frontend/dist/index.html：先执行 npm run build，或加 --build 启动")

    if not args.skip_migrate:
        migrate()

    # 配置在 app.main 导入时读取并缓存，必须先写环境变量
    if args.prod_mode:
        os.environ["PET_DEV_MODE"] = "0"  # 显式参数优先于外部环境
    else:
        os.environ.setdefault("PET_DEV_MODE", "1")

    media_root = None
    if raw := os.environ.get("PET_MATH_MEDIA"):
        media_root = Path(raw).expanduser()
        if not media_root.is_dir():
            die(f"PET_MATH_MEDIA 不是目录：{media_root}")
        info(f"课程视频目录：{media_root}")
    else:
        info("未设置 PET_MATH_MEDIA：/media/math 不挂载")

    sys.path.insert(0, str(BACKEND))
    os.chdir(BACKEND)

    from app.dev_static import mount_static
    from app.main import app

    mount_static(app, DIST, media_root)

    import uvicorn

    dev_mode = os.environ["PET_DEV_MODE"]
    print()
    print("=" * 72)
    print(f"本地环境：http://{args.host}:{args.port}   PET_DEV_MODE={dev_mode}")
    print(f"数据库：  {os.environ.get('PET_DATABASE_URL', 'sqlite:///./data/pet.db')}")
    print("停止：    Ctrl+C")
    print("=" * 72)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
