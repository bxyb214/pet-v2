"""下载 Piper 音色到 PIPER_DATA_DIR（默认 /models），已存在则跳过。

国内网络可把 PIPER_VOICE_BASE_URL 指向 hf-mirror：
  https://hf-mirror.com/rhasspy/piper-voices/resolve/main
"""
from __future__ import annotations

import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
_RAW_VOICES = os.environ.get("PIPER_VOICES") or os.environ.get(
    "PIPER_VOICE", "en_GB-alan-medium,zh_CN-huayan-medium"
)
VOICES = [v.strip() for v in _RAW_VOICES.split(",") if v.strip()]
DATA_DIR = Path(os.environ.get("PIPER_DATA_DIR", "/models"))
BASE = os.environ.get("PIPER_VOICE_BASE_URL", DEFAULT_BASE).rstrip("/")
TIMEOUT = float(os.environ.get("PIPER_DOWNLOAD_TIMEOUT", "120"))


def _voice_path(voice: str) -> str:
    parts = voice.split("-")
    if len(parts) != 3:
        raise SystemExit(f"bad voice name: {voice}")
    lang, name, quality = parts
    return f"{lang.split('_')[0]}/{lang}/{name}/{quality}/{voice}"


def _download(url: str, dest: Path) -> None:
    tmp = dest.with_name(dest.name + ".tmp")
    # hf-mirror 的 Cloudflare 会拦截 python-urllib 默认 UA（error code: 1010），
    # 普通浏览器 UA 才能拿到 .onnx.json 这类小文件。
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp, tmp.open("wb") as fh:
        while True:
            chunk = resp.read(1 << 16)
            if not chunk:
                break
            fh.write(chunk)
    os.replace(tmp, dest)


def _fetch(url: str, dest: Path, min_size: int) -> bool:
    if dest.is_file() and dest.stat().st_size >= min_size:
        print(f"exists: {dest}")
        return True
    for attempt in range(1, 4):
        try:
            print(f"download ({attempt}/3): {url}")
            _download(url, dest)
            break
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            print(f"failed: {exc}", file=sys.stderr)
            if attempt == 3:
                return False
            time.sleep(3)
    return dest.is_file() and dest.stat().st_size >= min_size


def main() -> int:
    if not VOICES:
        raise SystemExit("PIPER_VOICES 为空")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for voice in VOICES:
        rel = _voice_path(voice)
        if not _fetch(f"{BASE}/{rel}.onnx", DATA_DIR / f"{voice}.onnx", 1_000_000):
            return 1
        if not _fetch(f"{BASE}/{rel}.onnx.json", DATA_DIR / f"{voice}.onnx.json", 1_000):
            return 1
        print(f"voice ready: {voice}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
