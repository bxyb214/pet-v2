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
