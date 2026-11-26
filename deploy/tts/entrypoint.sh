#!/bin/sh
# 首次启动下载音色，然后前台运行 sidecar；容器重启会重试下载。
set -eu
python /app/download_voice.py
exec uvicorn app:app --host 0.0.0.0 --port "${TTS_PORT:-8100}" --workers 1
