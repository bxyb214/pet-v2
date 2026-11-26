# PET 本地 TTS sidecar：Piper + 极简 HTTP（文本 → WAV）
# 模型不打进镜像：首次启动由 entrypoint 下载到 /models 命名卷。
FROM python:3.12-slim

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIPER_VOICE=en_GB-alan-medium \
    PIPER_DATA_DIR=/models \
    TTS_PORT=8100

WORKDIR /app

# onnxruntime 需要 libgomp；slim 镜像默认不带
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -i "$PIP_INDEX_URL" --trusted-host "$PIP_TRUSTED_HOST" -r requirements.txt

COPY app.py download_voice.py entrypoint.sh ./
RUN chmod +x entrypoint.sh

EXPOSE 8100
CMD ["/app/entrypoint.sh"]
