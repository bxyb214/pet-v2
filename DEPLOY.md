# 本地 Docker 运行指南（macOS）

本项目自带容器配置，入口在 `deploy/`：

- `deploy/docker-compose.yml`：`nginx`（宿主 8088 → 80）+ `api`（FastAPI，内部 8000）
- `backend/Dockerfile`：Python 3.12，构建时安装依赖
- `deploy/nginx.conf`：静态站 + `/api/` 反代
- NAS 部署见 `docs/08-飞牛NAS部署手册.md`，本文件只讲本机

## 前置条件

- Docker Desktop 已安装并启动
- Node 18+（构建前端）
- 项目根目录执行以下命令

## 一次性准备

### 1. Docker CLI（本机 PATH 未配置时）

```bash
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
export DOCKER_CLI_PLUGIN_EXTRA_DIRS="/Applications/Docker.app/Contents/Resources/cli-plugins"

docker version          # Server 段有输出即守护进程正常
docker compose version  # 应输出 v5.x
```

### 2. 环境变量

```bash
cd deploy
cp .env.example .env
# 编辑 .env，填入 64 位随机串：
#   openssl rand -hex 32
```

`deploy/.env` 已被 gitignore，**不要提交**。

### 3. 构建前端（compose 不会替你构建）

```bash
cd frontend
npm install
npm run build
```

产物在 `frontend/dist/`，nginx 直接挂载该目录。
注意 `vite.config.ts` 设了 `emptyOutDir: false`，不要手动清空 `dist`（里面有音频）。

### 4. 学习数据与媒体

运行期数据不在 git 里，需要从 NAS 同步（默认路径 `/vol1/1000/docker/pet-v2`）：

| NAS 源 | 本地目标 |
|---|---|
| `frontend/dist/data/*.json` | `frontend/public/data/` 和 `frontend/dist/data/` |
| `frontend/dist/audio/` | `frontend/public/audio/` 和 `frontend/dist/audio/` |

- `frontend/public/` 是源目录，重新 `npm run build` 会带进 dist
- `frontend/dist/` 是 nginx 实际读取的目录，放这里立即生效、无需重启

### 5. 数据库（可选）

```bash
mkdir -p data
# 从 NAS 拷一致快照，放到：
#   data/pet.db
```

- 不拷也能用：空库时用邀请码 `claim` 注册的第一个账号自动成为管理员
- 拷库前先停 NAS 上的 api，或使用 SQLite `.backup` 生成快照；不要单独拷 `-wal` / `-shm`
- 启动时容器会自动执行 `alembic upgrade head`

## 启动

```bash
cd deploy
docker compose up -d --build
```

首次构建会拉基础镜像并经清华源装依赖，约几分钟。
api 容器启动时自动迁移数据库；SQLite 落在项目根 `data/pet.db`。

访问：**http://localhost:8088**

## 健康检查

```bash
cd deploy
docker compose ps

curl -s http://localhost:8088/api/v1/healthz
# {"status":"ok","version":"0.2.0","app":"PET v2 API"}

curl -I http://localhost:8088/          # 200
curl -I http://localhost:8088/data/banks.json
curl -I http://localhost:8088/audio/listen/t1-p1.mp3
```

api 的 compose healthcheck 每 30 秒探测一次，`docker compose ps` 中显示 `healthy` 即正常。

## 日常操作

```bash
cd deploy

docker compose logs -f api      # 后端日志
docker compose logs -f nginx    # nginx 日志
docker compose restart          # 重启
docker compose stop             # 停止（保留容器与数据）
docker compose start            # 再次启动
docker compose down             # 删除容器和网络（data/ 与 dist/ 是 bind mount，不受影响）
```

代码或前端有改动时：

```bash
cd frontend && npm run build
cd ../deploy && docker compose restart nginx   # 静态资源重新构建后刷新即可
# 后端代码改动：
cd ../deploy && docker compose up -d --build api
```

## 常见问题

- **`docker: command not found` / `docker compose: unknown command`**：执行上面的两个 `export`，或把 Docker CLI 加入 PATH。
- **8088 被占用**：`lsof -nP -iTCP:8088 -sTCP:LISTEN` 查看；换端口需改 `deploy/docker-compose.yml` 的 `8088:80` 映射。
- **页面能开但学习板块为空/报错**：检查 `frontend/dist/data/` 是否有 4 个 JSON。
- **听力没有声音**：检查 `frontend/dist/audio/listen/*.mp3` 是否存在。
- **首次构建很慢**：`deploy/.env` 中可覆盖 `PIP_INDEX_URL` 换源。

## 安全约定

- 密钥只放 `deploy/.env`（本地）或环境变量（NAS），禁止提交
- AI Key 在「管理 → AI 配置」页填写，存数据库，接口只回尾 4 位
- 数据库 `data/pet.db` 含账号信息，已在 gitignore 中
