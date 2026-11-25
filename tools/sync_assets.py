#!/usr/bin/env python3
"""从 NAS 拉取运行期素材到本地开发目录（题库 JSON + 听力音频）。

    python tools/sync_assets.py --host 192.168.1.10
    python tools/sync_assets.py --host 192.168.1.10 --only data
    python tools/sync_assets.py --host 192.168.1.10 --force

凭据：--password > 环境变量 NAS_PASS > 交互输入（不回显）。
源目录默认 NAS 生产站的 frontend/dist；只读，不会修改 NAS。
"""

from __future__ import annotations

import argparse
import getpass
import os
import stat
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REMOTE = "/vol1/1000/docker/pet-v2/frontend/dist"
DEFAULT_DEST = ROOT / "frontend" / "public"
PARTS = ("data", "audio")


def die(msg: str) -> None:
    print(f"\n[×] {msg}", file=sys.stderr)
    sys.exit(1)


def info(msg: str) -> None:
    print(f"[·] {msg}")


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def display(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def connect(args):
    try:
        import paramiko
    except ImportError:
        die(
            "缺少 paramiko：pip install paramiko\n"
            "  或使用后端虚拟环境：backend/.venv/bin/python tools/sync_assets.py ..."
        )

    password = args.password or os.environ.get("NAS_PASS")
    if not password and not args.key:
        password = getpass.getpass(f"{args.user}@{args.host} 的 SSH 密码：")

    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    info(f"连接 {args.user}@{args.host}:{args.port} …")
    try:
        cli.connect(
            hostname=args.host,
            port=args.port,
            username=args.user,
            password=password,
            key_filename=args.key,
            timeout=15,
            banner_timeout=20,
            auth_timeout=20,
            look_for_keys=False,
            allow_agent=False,
        )
    except Exception as exc:  # noqa: BLE001
        die(f"SSH 连接失败：{exc}")
    info("SSH 已连接")
    return cli


def should_skip(local: Path, size: int, force: bool) -> bool:
    return not force and local.is_file() and local.stat().st_size == size


def download_file(sftp, remote: str, local: Path, size: int) -> None:
    local.parent.mkdir(parents=True, exist_ok=True)
    tmp = local.with_name(local.name + ".part")
    last = [0.0]

    def cb(done: int, total: int) -> None:
        now = time.time()
        if size >= 1024 * 1024 and (now - last[0] >= 1 or done >= total):
            last[0] = now
            pct = done * 100 / total if total else 100
            print(f"\r    {pct:5.1f}%  {human(done)} / {human(total)}", end="", flush=True)

    sftp.get(remote, str(tmp), callback=cb if size >= 1024 * 1024 else None)
    if size >= 1024 * 1024:
        print()
    tmp.replace(local)


def sync_tree(
    sftp, remote_root: str, local_root: Path, *, force: bool, dry_run: bool
) -> tuple[int, int, int]:
    files = total_bytes = copied = 0
    stack: list[tuple[str, Path]] = [(remote_root, local_root)]
    while stack:
        rdir, ldir = stack.pop()
        try:
            entries = sftp.listdir_attr(rdir)
        except OSError as exc:
            die(f"读取远端目录失败：{rdir}（{exc}）")
        for entry in entries:
            rpath = f"{rdir}/{entry.filename}"
            lpath = ldir / entry.filename
            if entry.st_mode is not None and stat.S_ISDIR(entry.st_mode):
                if not dry_run:
                    lpath.mkdir(parents=True, exist_ok=True)
                stack.append((rpath, lpath))
                continue
            size = int(entry.st_size or 0)
            files += 1
            total_bytes += size
            if should_skip(lpath, size, force):
                continue
            if dry_run:
                print(f"   would get {display(lpath)}  {human(size)}")
                continue
            download_file(sftp, rpath, lpath, size)
            copied += 1
            print(f"   [{copied}] {display(lpath)}  {human(size)}")
    return files, total_bytes, copied


def main() -> None:
    ap = argparse.ArgumentParser(description="从 NAS 同步开发素材（data/audio）")
    ap.add_argument("--host", required=True, help="NAS 内网 IP")
    ap.add_argument("--port", type=int, default=22)
    ap.add_argument("--user", default="admin")
    ap.add_argument("--password", help="不推荐明文；优先 NAS_PASS 或交互输入")
    ap.add_argument("--key", help="改用私钥登录")
    ap.add_argument("--remote", default=DEFAULT_REMOTE, help="远端 dist 目录")
    ap.add_argument("--dest", default=str(DEFAULT_DEST), help="本地 frontend/public")
    ap.add_argument("--only", choices=PARTS, action="append", help="只同步某一部分，可重复")
    ap.add_argument("--force", action="store_true", help="大小相同也重新下载")
    ap.add_argument("--dry-run", action="store_true", help="只列出将下载的文件")
    args = ap.parse_args()

    dest = Path(args.dest).expanduser().resolve()
    parts = tuple(args.only) if args.only else PARTS
    cli = connect(args)
    try:
        sftp = cli.open_sftp()
        for name in parts:
            remote = f"{args.remote.rstrip('/')}/{name}"
            local = dest / name
            try:
                sftp.stat(remote)
            except OSError:
                info(f"跳过 {name}：远端不存在 {remote}")
                continue
            info(f"同步 {name}: {remote} → {local}")
            files, total, copied = sync_tree(
                sftp, remote, local, force=args.force, dry_run=args.dry_run
            )
            action = "将下载" if args.dry_run else "已下载"
            info(f"{name}: {files} 个文件 / {human(total)}，{action} {copied} 个")
        sftp.close()
    finally:
        cli.close()

    if not args.dry_run and not (dest / "data" / "banks.json").is_file():
        info("提醒：未找到 data/banks.json；页面可能为空，请检查 --remote 路径")
    info("完成")


if __name__ == "__main__":
    main()
