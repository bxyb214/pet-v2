#!/usr/bin/env python3
"""PET v2 开发环境入口（macOS / Windows 统一，Docker）。

    python tools/dev.py init                 # 首次：构建 + 迁移 + 灌演示数据
    python tools/dev.py up                   # http://localhost:5173
    python tools/dev.py logs api             # 跟日志
    python tools/dev.py seed --reset         # 重建演示数据
    python tools/dev.py reset-db             # 删 data/dev/pet.db 后重来
    python tools/dev.py test                 # 容器内 pytest + vitest
    python tools/dev.py assets --host <NAS>  # 从 NAS 拉题库/音频

需要 Docker Desktop；本机不装 Python/Node 也能跑（构建与测试都在容器内）。
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPOSE_FILE = ROOT / "deploy" / "docker-compose.dev.yml"
DATA_DIR = ROOT / "data" / "dev"
PUBLIC_DATA = ROOT / "frontend" / "public" / "data"
HEALTH_URL = "http://127.0.0.1:8000/api/v1/healthz"
WEB_URL = "http://localhost:5173"


def die(msg: str) -> None:
    print(f"\n[×] {msg}", file=sys.stderr)
    sys.exit(1)


def info(msg: str) -> None:
    print(f"[·] {msg}")


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    print(f"   $ {shlex.join(cmd)}")
    try:
        return subprocess.run(cmd, cwd=str(ROOT), check=check)
    except FileNotFoundError:
        die(f"找不到命令：{cmd[0]}")
    except subprocess.CalledProcessError as exc:
        die(f"命令失败（退出码 {exc.returncode}）")


def compose(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return run(["docker", "compose", "-f", str(COMPOSE_FILE), *args], check=check)


def compose_quiet(*args: str) -> str:
    r = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    return r.stdout.strip() if r.returncode == 0 else ""


def _prepare_path() -> None:
    """macOS 的 Docker Desktop 默认不把 CLI 放进 PATH。"""
    # compose 里 ${DEV_POLL:-0} 在变量完全未定义时会警告；显式给默认值
    os.environ.setdefault("DEV_POLL", "0")
    if sys.platform == "darwin":
        extra = Path("/Applications/Docker.app/Contents/Resources/bin")
        if extra.is_dir():
            os.environ["PATH"] = str(extra) + os.pathsep + os.environ.get("PATH", "")
        os.environ.setdefault(
            "DOCKER_CLI_PLUGIN_EXTRA_DIRS",
            "/Applications/Docker.app/Contents/Resources/cli-plugins",
        )


def require_docker() -> None:
    _prepare_path()
    if shutil.which("docker") is None:
        die("未找到 docker：请安装并启动 Docker Desktop（macOS / Windows）")
    r = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True)
    if r.returncode != 0:
        die("docker compose 不可用：请先启动 Docker Desktop，再重试")
    info("Docker 就绪")


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def wait_health(timeout: int = 120) -> None:
    info(f"等待 API 健康检查（{HEALTH_URL}）…")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=2) as resp:
                if resp.status == 200:
                    info("API 已就绪")
                    return
        except Exception:  # noqa: BLE001 - 启动期间连接失败是正常的
            pass
        time.sleep(2)
    die("健康检查超时：python tools/dev.py logs api")


def api_running() -> bool:
    return bool(compose_quiet("ps", "--status=running", "-q", "api"))


def ensure_up(*, build: bool = False) -> None:
    require_docker()
    ensure_dirs()
    if build or not api_running():
        compose("up", "-d", "--build")
    else:
        # 已运行时也 up 一次：compose 文件/环境变量变更会自动重建容器，镜像不重建
        compose("up", "-d")
    wait_health()


def print_urls() -> None:
    print()
    print("=" * 64)
    print(f"  前端： {WEB_URL}")
    print(f"  API ： {HEALTH_URL}")
    print("  停止： python tools/dev.py down")
    print("=" * 64)


def cmd_up(_args: argparse.Namespace) -> None:
    ensure_up(build=True)
    print_urls()


def cmd_down(_args: argparse.Namespace) -> None:
    require_docker()
    compose("down")


def cmd_ps(_args: argparse.Namespace) -> None:
    require_docker()
    compose("ps")


def cmd_logs(args: argparse.Namespace) -> None:
    require_docker()
    tail = ["--tail=200"]
    compose("logs", "-f", *tail, *([args.service] if args.service else []))


def cmd_check(_args: argparse.Namespace) -> None:
    require_docker()
    compose("config", "-q")
    info("compose 配置校验通过")
    if not (PUBLIC_DATA / "banks.json").is_file():
        info("缺少 frontend/public/data/banks.json：先运行 tools/dev.py assets --host <NAS_IP>")
    else:
        info("题库数据已就位")
    info(f"开发数据库目录：{DATA_DIR}")


def cmd_seed(args: argparse.Namespace) -> None:
    ensure_up()
    extra = ["--reset"] if args.reset else []
    compose("exec", "-T", "api", "python", "-m", "app.seed_dev", *extra)


def cmd_reset_db(_args: argparse.Namespace) -> None:
    require_docker()
    ensure_dirs()
    compose("down", check=False)
    removed = 0
    for name in ("pet.db", "pet.db-wal", "pet.db-shm"):
        path = DATA_DIR / name
        if path.exists():
            path.unlink()
            removed += 1
    info(f"已删除 {removed} 个开发库文件：{DATA_DIR}")
    compose("up", "-d", "--build")
    wait_health()
    compose("exec", "-T", "api", "python", "-m", "app.seed_dev")
    print_urls()


def cmd_test(args: argparse.Namespace) -> None:
    require_docker()
    if not args.frontend_only:
        info("后端 pytest（容器内）…")
        # 开发容器固定 PET_DEV_MODE=1；测试用例按正式模式断言（无 Key 应 503 等）
        compose(
            "run", "--rm", "--no-deps", "-e", "PET_DEV_MODE=0",
            "api", "pytest", "-q",
        )
    if not args.backend_only:
        info("前端 vitest（容器内）…")
        compose(
            "run",
            "--rm",
            "--no-deps",
            "web",
            "sh",
            "-c",
            "if [ ! -x node_modules/.bin/vitest ]; then npm ci; fi; npm test",
        )


def cmd_init(args: argparse.Namespace) -> None:
    if not (PUBLIC_DATA / "banks.json").is_file():
        info("提示：缺少 frontend/public/data；页面会空白，先运行 tools/dev.py assets --host <NAS_IP>")
    ensure_up()
    extra = ["--reset"] if args.reset else []
    compose("exec", "-T", "api", "python", "-m", "app.seed_dev", *extra)
    print_urls()


def cmd_shell(_args: argparse.Namespace) -> None:
    ensure_up()
    compose("exec", "api", "sh")


def _tool_python() -> str:
    """同步素材需要 paramiko：优先用 backend/.venv，其次当前解释器。"""
    for cand in (
        ROOT / "backend" / ".venv" / "bin" / "python",
        ROOT / "backend" / ".venv" / "Scripts" / "python.exe",
    ):
        if cand.is_file():
            return str(cand)
    return sys.executable


def cmd_assets(args: argparse.Namespace) -> None:
    cmd = [_tool_python(), str(ROOT / "tools" / "sync_assets.py"), *args.rest]
    run(cmd)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="PET v2 开发环境（Docker + 热更新）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("up", help="启动并等待健康检查").set_defaults(func=cmd_up)
    sub.add_parser("down", help="停止容器（保留 node_modules 卷与 data/dev）").set_defaults(
        func=cmd_down
    )
    sub.add_parser("ps", help="查看容器状态").set_defaults(func=cmd_ps)
    p_logs = sub.add_parser("logs", help="跟随日志")
    p_logs.add_argument("service", nargs="?", choices=["api", "web"])
    p_logs.set_defaults(func=cmd_logs)
    sub.add_parser("check", help="检查 Docker / compose / 题库数据").set_defaults(func=cmd_check)
    p_seed = sub.add_parser("seed", help="灌入开发演示数据")
    p_seed.add_argument("--reset", action="store_true", help="先清空所有业务数据")
    p_seed.set_defaults(func=cmd_seed)
    sub.add_parser("reset-db", help="删除 data/dev/pet.db* 后重建并灌数").set_defaults(
        func=cmd_reset_db
    )
    p_test = sub.add_parser("test", help="容器内跑后端 + 前端测试")
    g = p_test.add_mutually_exclusive_group()
    g.add_argument("--backend-only", action="store_true")
    g.add_argument("--frontend-only", action="store_true")
    p_test.set_defaults(func=cmd_test)
    p_init = sub.add_parser("init", help="首次初始化：启动 + 迁移 + 灌数")
    p_init.add_argument("--reset", action="store_true")
    p_init.set_defaults(func=cmd_init)
    sub.add_parser("shell", help="进入 api 容器").set_defaults(func=cmd_shell)
    p_assets = sub.add_parser("assets", help="从 NAS 拉取 public/data 与 public/audio")
    # 其余参数原样交给 tools/sync_assets.py（用 parse_known_args 收集）
    p_assets.set_defaults(func=cmd_assets, rest=[])

    args, unknown = ap.parse_known_args()
    if args.cmd == "assets":
        args.rest = unknown
    elif unknown:
        ap.error("unrecognized arguments: " + " ".join(unknown))
    args.func(args)


if __name__ == "__main__":
    main()
