"""运维命令：SQLite 在线备份。

在 api 容器内执行（见 deploy/backup.sh）：

    python -m app.maintenance backup

使用 sqlite3 在线备份 API，WAL 模式下也能得到一致快照；备份写到
数据库同级的 backups/（生产即宿主 ../data/backups），默认保留最近 14 份。
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import time
from pathlib import Path

from app.core.config import get_settings


def database_path() -> Path:
    url = get_settings().database_url
    if not url.startswith("sqlite:///"):
        raise SystemExit(f"仅支持 SQLite 备份，当前 PET_DATABASE_URL={url}")
    return Path(url.removeprefix("sqlite:///")).expanduser().resolve()


def backup(keep: int = 14) -> Path:
    src = database_path()
    if not src.is_file():
        raise SystemExit(f"数据库不存在：{src}")
    out_dir = src.parent / "backups"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"pet-{time.strftime('%Y%m%d-%H%M%S')}.db"

    source = sqlite3.connect(str(src))
    target = sqlite3.connect(str(out))
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()

    os.chmod(out, 0o600)
    existing = sorted(out_dir.glob("pet-*.db"))
    for old in existing[:-max(1, keep)]:
        old.unlink(missing_ok=True)
    print(f"[backup] {out}（保留最近 {max(1, keep)} 份）")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="PET v2 运维命令")
    ap.add_argument("action", choices=["backup"])
    ap.add_argument("--keep", type=int, default=14, help="保留份数（默认 14）")
    args = ap.parse_args()
    if args.action == "backup":
        backup(args.keep)


if __name__ == "__main__":
    main()
