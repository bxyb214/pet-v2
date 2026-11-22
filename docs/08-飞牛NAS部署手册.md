# 08 · 飞牛 NAS（fnOS）部署手册

> 目标架构：`deploy/docker-compose.yml` 两个容器——nginx（静态 + 反代 :8088）+ pet-api（FastAPI + SQLite）。
> 所有 AI Key 不进环境变量，部署后在管理页 `/admin` 配置，存 `app_cfg` 表。

---

## 一、飞牛系统要做的准备（你操作）

### 1. 安装 Docker（必须）
- fnOS **应用中心 → Docker**，安装并启动（自带 `docker compose` 插件）
- 不需要装 Docker Desktop（那是 Windows/Mac 桌面版，NAS 上用不上）
- 装好后 SSH 里执行 `docker --version && docker compose version` 能出版本号即可

### 2. 开启 SSH（必须）
- fnOS 系统设置 → 远程访问/SSH → 开启
- 告诉我：`NAS 内网 IP`、`SSH 端口`、`SSH 用户名/密码`（或你自己粘贴执行我给的命令）

### 3. 建工作目录（必须）
- 在 NVMe 存储空间上建目录，例如：`/vol1/1000/docker/pet-v2/`
- 之后整个项目（backend/frontend/deploy + dist 产物）就放在这里，`data/` 会挂进容器存 SQLite

### 4. 网络与 HTTPS（必须，按你已有条件二选一）
- **已有端口映射 + HTTPS**（你提过）：确认路由器把外部 HTTPS 端口转发到 `NAS内网IP:8088`（容器 nginx），证书在前置层终结
- 或 fnOS 自带反向代理/HTTPS 设置里配域名 + 证书，反代到 8088
- 首次验证也可以先局域网直接 `http://NAS内网IP:8088` 访问，通了再上外网

### 5. Docker 镜像加速（建议）
- 国内拉 `nginx:1.27-alpine` / `python:3.12-slim` 可能很慢或超时
- fnOS Docker 设置 → 镜像加速：填一个国内 mirror（如 `https://docker.m.daocloud.io`）

### 6. 资源确认（你已经满足）
- 内存：8GB 足够（api ≈200MB、nginx ≈10MB）
- 磁盘：预留 ≥2GB（镜像 ~400MB + dist 含 85MB 音频 + 数据库与 TTS 缓存）
- 系统时间/时区正确（容器内已固定 TZ=Asia/Shanghai，用量记账按北京时间）

### 7. Key 准备（部署后再填，不用提前给文件）
| 服务 | 用途 | 去哪拿 |
|---|---|---|
| 阿里云百炼 API Key + 业务空间 ID | 实时对话/跟读/加词/复盘改写 | bailian.console.aliyun.com（qwen3.8 Realtime 必须绑业务空间）|
| 腾讯云智聆口语评测（新版）AppID/SecretId/SecretKey | 跟读精准评分（可选） | console.cloud.tencent.com/soenew，开通并购 9.9 元调试包 |

### 8. 旧数据迁移（可选，单独一步）
- 旧 MySQL 在内网（仅代码服务器可达）。若 NAS 与它不通：在代码服务器跑 `pet-v2/tools/migrate_legacy.py --mysql ... --sqlite export.db`，把导出的 SQLite 文件传到 NAS `data/pet.db` 后再首次启动
- 详见 `docs/06-旧数据迁移.md`

---

## 二、部署步骤（NAS Docker 就绪后我执行）

> **2026-11-22 已实际部署成功**，下面命令仅作参考；日常请用 `tools/deploy_nas.py`（见第五节）。

```bash
# 0. 代码上 NAS（打包上传，dist 产物一起）
#    pet-v2/{backend,frontend/dist,deploy} → /vol1/1000/docker/pet-v2/

# 1. 首次构建 + 启动（自动 alembic upgrade head → 起服务）
cd /vol1/1000/docker/pet-v2/deploy
cp .env.example .env && nano .env      # 填 PET_JWT_SECRET（64 位随机串）
docker compose up -d --build

# 2. 验证
curl http://127.0.0.1:8088/api/v1/healthz     # {"status":"ok"}

# 3. 首次初始化
#    浏览器打开站点 → 注册页「首次初始化」：邀请码 + 管理员账号密码
#    → /admin 填 Qwen Key + 业务空间 ID + 腾讯 SOE 三件套

# 4. 真机首测清单
#    ① 手机/平板浏览器：登录 → 词汇/阅读/听力  # 麦克风权限弹窗
#    ② 口语·跟读（AI 点评 + 腾讯 SOE 双引擎）
#    ③ 口语·实时对话（12 分钟收尾 → 自动生成复盘句 → 复盘跟读评分）
#    ④ 造句页 → AI 判定
#    ⑤ /admin 用量区块有数字
```

## 三、日常运维

| 操作 | 命令 |
|---|---|
| 更新前端 | 本地 `npm run build` → 传新 dist → `docker compose restart nginx` |
| 更新后端 | 传新 backend → `docker compose up -d --build api`（自动跑迁移）|
| 看日志 | `docker compose logs -f api` |
| 备份 | 停写后复制 `pet-v2/data/pet.db`（SQLite 单文件）；建议 fnOS 计划任务每日复制 |
| 回滚 | `docker compose down && 恢复上一版代码 && docker compose up -d --build` |

## 四、已知边界

- SQLite WAL 模式，单机单实例部署没问题；uvicorn 2 worker 并发写安全（WAL + 短事务）
- TTS 缓存目录在 `data/tts/`，跟数据库同一挂卷，持久化
- WebSocket（SOE 评测 WSS、WebRTC 信令）都是浏览器直连第三方，**不经过 NAS**——NAS 只承担 HTTPS 静态与 REST API，带宽压力很小
- WebRTC 需要页面为 HTTPS（或 localhost），所以外网访问必须走你的 HTTPS 域名

---

## 五、实际部署记录（2026-11-22 首次上线）

### 环境实测

| 项 | 实测值 |
|---|---|
| NAS 内网地址 | `<NAS内网IP>`（与开发机不在同一网段，ping 1ms 可达；实际 IP 记在本地凭据文件） |
| 系统 | fnOS / Debian 12，内核 `6.18.18.c1186-trim` |
| Docker | 28.5.2，compose v2.40.3 |
| 项目目录 | `/vol1/1000/docker/pet-v2`（可直接写，**免 sudo**） |
| 磁盘 | `/vol1/1000` 390G 可用 |
| 内存 | 7.6G（实际占用：api ≈ 90MB，nginx ≈ 5MB） |
| 访问地址 | `http://<NAS内网IP>:8088`（管理页 `/admin`） |

### 两个必须知道的坑

**1. `admin` 用户不在 docker 组，docker 命令必须 sudo**

```
permission denied while trying to connect to the Docker daemon socket
```

`tools/deploy_nas.py` 会自动探测：直连 `docker info` 失败就整体切到 `sudo -S`（密码走 stdin，不落盘不回显）。注意 `sudo cmd1 && cmd2` 只有 cmd1 提权，必须 `sudo sh -c "cmd1 && cmd2"`，脚本里已按此处理。

**2. fnOS 自带镜像加速对部分镜像返回 401，pip 也太慢**

```
failed to resolve source metadata for docker.io/library/python:3.12-slim:
unexpected status from HEAD request to https://docker.fnnas.com/...: 401 Unauthorized
```

`daemon.json` 里注册的是 `docker.fnnas.com` + `registry.hub.docker.com`，前者对 `python:3.12-slim` 报 401、后者在国内不可达（`nginx:1.27-alpine` 却能拉下来）。处理方式：

```bash
# 用可达的镜像源显式拉，再打上官方标签，之后 build 会用本地镜像，不去访问 registry
sudo docker pull docker.m.daocloud.io/library/python:3.12-slim
sudo docker tag  docker.m.daocloud.io/library/python:3.12-slim python:3.12-slim
```

`backend/Dockerfile` 已改成默认走清华 PyPI（`PIP_INDEX_URL` 可在 `deploy/.env` 覆盖），否则 `pip install` 实测只有 20 kB/s，装一次 8 分钟还装不完。

### 首次初始化（关键）

库里没有任何账号时，前端「注册」页会自动进入**首次初始化**模式，调用 `/api/v1/auth/claim` 建管理员。但它需要一个**尚未使用的邀请码**，而新库是空的 —— 已预置一个：

预置方式：直接向 SQLite 的 `invite_codes` 表插一条未使用的码（`claim` 要求有可用邀请码）。

操作：打开 `http://<NAS内网IP>:8088/register` → 填预置邀请码 + 用户名 + 密码 → 自动创建管理员并登录。
（预置的邀请码明文记在本地凭据文件，不入库。）

之后的账号：登录管理员 → `/admin` → 「账号与邀请码」标签 → 生成邀请码 → 孩子在 `/register` 用码注册。
（对齐接口：`GET/POST /api/v1/admin/codes`、`GET /api/v1/admin/users`、`GET /api/v1/auth/setup`）

### 部署耗时基准

| 场景 | 耗时 |
|---|---|
| 首次 pip 安装（清华源） | ≈ 3 分钟 |
| 代码不变的重跑（全 CACHED） | 13 秒 |
| 只改前端 dist | ≈ 15 秒 + 上传 73MB |
| 打包上传 73MB（局域网） | ≈ 10 秒 |
