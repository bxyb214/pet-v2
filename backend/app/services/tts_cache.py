"""TTS 磁盘缓存：目录、统计、LRU（Qwen 与本地 Piper 共用）。

缓存文件放在 sqlite 同级的 `data/tts/`，文件名是 40 位 sha1 + `.wav`。
生产 compose 挂载 `../data:/app/data`，因此重启不丢；它属于可再生数据，不纳入备份。
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings

DEFAULT_MAX_MB = 1024


def cache_dir() -> str:
    """缓存目录与 sqlite 同级（./data/tts）；生产 compose 挂卷即可持久化。"""
    settings = get_settings()
    db_path = settings.database_url.replace("sqlite:///", "", 1)
    return str(Path(db_path).parent / "tts")


def tts_cache_cfg(db: Session) -> int:
    """TTS 缓存上限（MB），存 app_cfg 'speak.tts_cache'，默认 1024。"""
    from app.services.ai_enrich import get_cfg

    raw = get_cfg(db, "speak.tts_cache", "")
    try:
        d = json.loads(raw) if raw else {}
        if not isinstance(d, dict):
            return DEFAULT_MAX_MB
        return max(16, int(d.get("max_mb", DEFAULT_MAX_MB)))
    except (json.JSONDecodeError, TypeError, ValueError):
        return DEFAULT_MAX_MB


def _wav_files(cache_dir: str) -> list[Path]:
    d = Path(cache_dir)
    if not d.is_dir():
        return []
    return [p for p in d.glob("*.wav") if p.is_file()]


def tts_cache_stats(cache_dir: str, max_mb: int) -> dict:
    files = _wav_files(cache_dir)
    total = sum(p.stat().st_size for p in files)
    return {"files": len(files), "bytes": total, "max_mb": max_mb}


def clear_tts_cache(cache_dir: str) -> int:
    n = 0
    for p in _wav_files(cache_dir):
        try:
            p.unlink()
            n += 1
        except OSError:
            continue
    return n


def enforce_tts_cache(cache_dir: str, max_mb: int) -> int:
    """按 mtime 做 LRU：超过上限时删最久未用的文件，直到回到上限内。"""
    limit = max_mb * 1024 * 1024
    files = sorted(_wav_files(cache_dir), key=lambda p: p.stat().st_mtime)
    total = sum(p.stat().st_size for p in files)
    removed = 0
    for p in files:
        if total <= limit:
            break
        try:
            size = p.stat().st_size
            p.unlink()
            total -= size
            removed += 1
        except OSError:
            continue
    return removed


def store_atomic(path: Path, data: bytes) -> None:
    """先写同目录临时文件再原子替换，避免并发读到半个 WAV。"""
    fd, tmp_name = tempfile.mkstemp(prefix=f"{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def normalize_wav(data: bytes) -> bytes:
    """修正流式 WAV 的假长度头部。

    云端 TTS 有时返回 `RIFF size=0x7fffffbf` / `data size=0x7fffff9b` 的流式 WAV。
    桌面浏览器能容忍，iOS Safari 会按约 2GB 解析而无法起播，因此写缓存前改成真实长度。
    非 WAV 或已经正确的数据原样返回。
    """
    if len(data) < 44 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        return data
    idx = 12
    while idx + 8 <= len(data):
        chunk = data[idx:idx + 4]
        size = int.from_bytes(data[idx + 4:idx + 8], "little")
        if chunk == b"data":
            actual = len(data) - (idx + 8)
            if int.from_bytes(data[4:8], "little") == len(data) - 8 and size == actual:
                return data
            fixed = bytearray(data)
            fixed[4:8] = (len(data) - 8).to_bytes(4, "little")
            fixed[idx + 4:idx + 8] = actual.to_bytes(4, "little")
            return bytes(fixed)
        if size > len(data):
            return data
        idx += 8 + size + (size & 1)
    return data


def repair_wav_file(path: Path) -> None:
    """自愈历史缓存：读取前 44 字节，发现 RIFF 长度不符时原地修正。

    只多一次 stat + 44 字节读；只有确实损坏时才整文件读写，正常情况下开销可忽略。
    """
    try:
        size = path.stat().st_size
        if size < 44:
            return
        with path.open("rb") as fh:
            head = fh.read(44)
        if head[:4] != b"RIFF" or head[8:12] != b"WAVE":
            return
        if int.from_bytes(head[4:8], "little") == size - 8:
            return
        data = path.read_bytes()
        fixed = normalize_wav(data)
        if fixed != data:
            store_atomic(path, fixed)
    except OSError:
        return
