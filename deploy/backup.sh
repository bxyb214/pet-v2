#!/bin/sh
# 每日数据库备份（fnOS 计划任务调用；也可手动执行）
#   cd /vol1/1000/docker/pet-v2/deploy && sh backup.sh
#   sh backup.sh --keep 7
set -eu

cd "$(dirname "$0")"

# fnOS 上 admin 不一定在 docker 组；能免密 sudo 时自动提权
if docker info >/dev/null 2>&1; then
    DOCKER="docker"
else
    DOCKER="sudo docker"
fi

$DOCKER compose exec -T api python -m app.maintenance backup "$@"
