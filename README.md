# PET 备考网站 v2 · 火焰学习

面向小学生的 PET（B1 Preliminary for Schools）备考站点：**单词 / 阅读 / 语法 / 听力 / 口语 / 数学**。
前端 Vue 3 + Naive UI，后端 FastAPI + SQLite，自托管于家用 NAS。

![Vue 3](https://img.shields.io/badge/Vue-3-42b883?logo=vue.js&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178c6?logo=typescript&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-WAL-003b57?logo=sqlite&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ed?logo=docker&logoColor=white)

## 功能

| 板块 | 能力 |
|---|---|
| 单词 | PET 四词库 1680 词（必默 712 / 高频 414 / 固搭 254 / 同义 300），另支持 KET 1484 词；任意天数计划；学习 / 测试分库；三题型；错题本按 1/2/4/7/15 天复习；手动加词（AI 补全） |
| 阅读 | 207 句精读（解析 / 知识点 / 生词）；416 道语法题（42 考点）；阅读计划按教材切分；错题本；手动加句 |
| 语法 | 独立板块，10 天 / 42 考点 |
| 听力 | 6 套真题 24 个 Part、150 题；纯播放器：音频 + 可隐藏滚动字幕 + 0.8–1.2 五档倍速；纸质卷作答 |
| 口语 | 45 个真题场景；135 句跟读 + 90 道造句；每天 5 分钟跟读 + 10 分钟造句 + 15 分钟自由对话；Qwen Realtime 对话、腾讯 SOE 评分、AI 即时改写与复盘；练习时长按真实开口秒数累计 |
| 数学 | 李永乐「一课通关」三年级 13 节、四年级 51 节；视频支持拖动 / 倍速 / 全屏 / AirPlay；登录后签短时效令牌取流；进度跨设备同步 |
| 管理 | 概览 / AI 配置 / 用户与额度 / 用量与预算；Key 掩码；按人 AI 开关与日、月预算；用量报表与 CSV；TTS 缓存管理 |
| 用户 | 设置页含「AI 计费」：查看自己的日 / 周 / 月 / 年预估费用与逐日明细 |

学习数据默认存 localStorage，联网后增量同步；多端按「并集 / 欠得多 / 取大」合并。
未开通付费 AI 的用户仍可使用题库、浏览器朗读与标准答案；付费按钮会给出明确提示，不产生外部调用。

## 技术栈

- **前端**：Vue 3 · TypeScript · Vite · Pinia · vue-router · Naive UI · vitest
- **后端**：FastAPI · SQLAlchemy 2 · SQLite(WAL) · Alembic · JWT · argon2/bcrypt · pytest
- **AI**：阿里云百炼 Qwen（Realtime / 文本 / TTS）、腾讯云 SOE；免费发音用浏览器 `speechSynthesis`
- **部署**：生产 Docker Compose（nginx + api，飞牛 NAS）；开发 Docker Compose（Vite + uvicorn 热更新）

## 快速开始

### 开发环境（macOS / Windows 统一，Docker + 热更新）

```bash
python tools/dev.py check
python tools/dev.py assets --host <NAS_IP>   # 首次：从 NAS 拉题库/音频（密码走 NAS_PASS）
python tools/dev.py init                     # 构建 + 迁移 + 演示数据
# → http://localhost:5173
```

Vite :5173 + uvicorn :8000，源码 bind mount，前后端改完即生效；开发库在 `data/dev/pet.db`，与生产隔离。
演示账号 `admin` / `kid` / `kid-free`（密码见 `backend/app/seed_dev.py`），邀请码 `CLAIM` / `DEV-INVITE`。
日常：`python tools/dev.py logs api`、`seed --reset`、`reset-db`、`test`、`down`。详见[部署文档 §2](docs/06-部署与运维.md)。

### 生产（飞牛 NAS）

```bash
export NAS_PASS=...                                              # 也可交互输入
python tools/deploy_nas.py deploy --host <NAS_IP> --with-audio   # 首次（含 85 MB 音频）
python tools/deploy_nas.py deploy --host <NAS_IP>                # 日常发布
```

发布脚本会构建前端、上传、部署前备份、按 tag 启动、健康检查并清理旧镜像。
访问 `http://<NAS_IP>:8088`；首次注册邀请码 `CLAIM`，第一个账号自动成为管理员；AI Key 在 `/admin` 配置。
备份/回滚：`python tools/deploy_nas.py backup --host <IP> --download`、`rollback --host <IP>`，
见[部署文档 §4](docs/06-部署与运维.md)。

### 无 Docker 的 Windows（仅发布前验证）

```powershell
# 首次：准备后端环境
cd backend
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"

# 仓库根目录：构建前端并启动
backend\.venv\Scripts\python.exe tools\dev_local.py --build
# 打开 http://localhost:8088
```

默认 `PET_DEV_MODE=1`（AI 走模拟，顶栏显示 DEV）；`--prod-mode` 关闭模拟。
数据库在 `backend/data/pet.db`；设 `PET_MATH_MEDIA=D:\path\to\math` 才会挂载课程视频。
详见[部署文档 §2.5](docs/06-部署与运维.md)。

### 本地验证生产 compose（可选）

```bash
cd frontend && npm run build             # nginx 直接挂载 dist
cd ../deploy
cp .env.example .env                     # 填 PET_JWT_SECRET（openssl rand -hex 32）
docker compose up -d --build             # api 启动时自动迁移 + bootstrap
```

访问 <http://localhost:8088>。题库 JSON、音频等运行期素材不进仓库，首次需从 NAS 同步（`tools/dev.py assets`）
或按 `data-src/README.md` 重新构建。

## 常用命令

```bash
python tools/dev.py up                  # 开发环境（Docker，5173 + 8000）
python tools/dev.py test                # 容器内 pytest + vitest
cd frontend && npm test                 # 本机 vitest（Node 22）
cd frontend && npx vitest run src/core/merge.test.ts
cd frontend && npm run build            # vue-tsc + 清理 dist/assets + vite build
cd backend  && .venv/bin/python -m pytest tests/ -q
cd backend  && .venv/bin/python -m pytest tests/test_merge.py -q
node tools/check_overflow.js http://localhost:5178   # 路由 × 3 视口横向溢出
python tools/check_tokens.py                         # CSS 变量引用检查
python tools/deploy_nas.py deploy --host <NAS_IP>    # 生产发布（密码走 NAS_PASS）
python tools/deploy_nas.py backup --host <NAS_IP> --download
python tools/deploy_nas.py rollback --host <NAS_IP>
```

> Node 26 的实验性 `localStorage` 会让 vitest 失败；测试与构建统一 Node 22（`.nvmrc` / `engines`）。
> Windows 用 `.venv/Scripts/` 代替 `.venv/bin/`。

## 目录

```text
frontend/     Vue 3 应用（src/core 纯逻辑，src/views 页面）
backend/      FastAPI（api/v1 → services → models，Alembic 迁移）
data-src/     学习数据源（构建产物在 frontend/public/data）
tools/        构建、迁移、部署、检查脚本
deploy/       compose（prod/dev）、nginx、backup.sh
docs/         需求 / 架构 / 开发规范 / 功能 / 设计 / 部署 / 口语 / AI 额度
```

## 文档

完整索引与阅读路径见 **[docs/README.md](docs/README.md)**。

| 文档 | 内容 |
|---|---|
| [01 需求清单](docs/01-需求清单.md) | 冻结的需求基线与决议 |
| [02 技术架构](docs/02-技术架构.md) | 选型、API、数据模型、同步 |
| [03 开发规范](docs/03-开发规范.md) | 改动流程、分层约束、测试、红线 |
| [04 功能清单](docs/04-功能清单.md) | 功能编号与当前能力 |
| [05 前端设计规范](docs/05-前端设计规范.md) | Design Token 与组件模式 |
| [06 部署与运维](docs/06-部署与运维.md) | 本地 / NAS / 备份 / 迁移 |
| [07 口语实时对话方案](docs/07-口语实时对话方案.md) | 提示词、记忆、成本、复盘 |
| [08 AI 额度与计费](docs/08-AI额度与计费.md) | 权益、预算、闸门、管理页 |

## 数据与素材

- `frontend/public/audio/`（约 85 MB）、教材 PDF 与数学视频**不进版本库**，部署时单独同步。
- `frontend/public/data/*.json` 由 `data-src/` 经 `tools/build_*` 生成，不手改。
- 旧站参考代码在上级目录 `../PET/`，只读。

## 许可

个人学习项目；教材内容版权归原出版方，请勿用于商业分发。
