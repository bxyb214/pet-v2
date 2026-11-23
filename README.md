# PET 备考网站 v2

面向小学生的 PET（B1 Preliminary for Schools）备考站点：**单词 / 阅读 / 语法 / 听力 / 口语** + 语文·数学占位。
前端 Vue 3 + Naive UI，后端 FastAPI + SQLite，Docker Compose 自托管于家用 NAS。

![Vue 3](https://img.shields.io/badge/Vue-3-42b883?logo=vue.js&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178c6?logo=typescript&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-WAL-003b57?logo=sqlite&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ed?logo=docker&logoColor=white)

## 功能

| 板块 | 能力 |
|---|---|
| 单词 | 四词库 1680 词（必默 712 / 高频 414 / 固搭 254 / 同义 300）；任意天数计划；三题型测验；错题本按 1/2/4/7/15 天复习；手动加词（AI 补全） |
| 阅读 | 207 句精读（解析 / 知识点 / 生词）；416 道语法题（42 考点）；阅读计划可按教材切分；错题本；手动加句 |
| 语法 | 独立板块，10 天 / 42 考点 |
| 听力 | 6 套真题 24 个 Part；纯播放器：音频 + 可隐藏滚动字幕 + 0.8–1.2 五档倍速；纸质卷作答 |
| 口语 | 手动计划（1–90 天）；每天 5 分钟跟读 + 10 分钟造句 + 15 分钟自由对话（10 对话 + 5 复盘）；AI 即时改写并跟读；161 个真题场景题库；练习时长按真实开口秒数累计 |
| 管理 | AI 配置（Key 掩码）、按人按天用量与费用、邀请码、口语权限开关 |

学习数据默认存 localStorage，联网后增量同步；多端按「并集 / 欠得多 / 取大」合并。

## 技术栈

- **前端**：Vue 3 · TypeScript · Vite · Pinia · vue-router · Naive UI · vitest
- **后端**：FastAPI · SQLAlchemy 2 · SQLite(WAL) · Alembic · JWT · argon2/bcrypt · pytest
- **AI**：阿里云百炼 Qwen（Realtime / 文本 / TTS）、腾讯云 SOE
- **部署**：Docker Compose（nginx + api）

## 快速开始

### Docker（推荐）

```bash
cd frontend && npm install && npm run build   # nginx 直接挂载 dist
cd ../deploy
cp .env.example .env                          # 填 PET_JWT_SECRET（openssl rand -hex 32）
docker compose up -d --build                  # api 启动时自动迁移
```

访问 <http://localhost:8088>。运行期数据（JSON / 音频 / 数据库）不随仓库分发，首次需从 NAS 同步，详见 [部署文档](docs/06-部署与运维.md)。

空库首次用邀请码 `claim` 注册，第一个账号自动成为管理员；AI Key 部署后在 `/admin` 填写。

> 测试环境没有 AI Key：在 `deploy/.env` 设 `PET_DEV_MODE=1` 后重建 api。顶栏显示 **DEV**，
> 口语/造句/加词返回模拟结果，不调用外部服务；正式环境保持 `0`。

### 本地开发

```bash
# 后端（Python 3.12+）
cd backend
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m uvicorn app.main:app --port 8000 --reload

# 前端（Node 20+）
cd frontend
npm install
npm run dev        # http://localhost:5173，/api 代理到 8000
```

> README 的历史版本写的是 Windows 路径 `.venv/Scripts/`；macOS/Linux 用 `.venv/bin/`。

## 常用命令

```bash
cd frontend && npm test                 # vitest
cd frontend && npx vitest run src/core/merge.test.ts
cd frontend && npm run build            # vue-tsc + vite build（无独立 lint）
cd backend  && .venv/bin/python -m pytest tests/ -q
cd backend  && .venv/bin/python -m pytest tests/test_merge.py -q
node tools/check_overflow.js http://localhost:5178   # 20 路由 × 3 视口
python tools/check_tokens.py                         # CSS 变量引用检查
```

## 目录

```text
frontend/     Vue 3 应用（src/core 纯逻辑，src/views 页面）
backend/      FastAPI（api/v1 → services → models，Alembic 迁移）
data-src/     学习数据源（构建产物在 frontend/public/data）
tools/        构建、迁移、部署、检查脚本
deploy/       Dockerfile、compose、nginx
docs/         需求 / 架构 / 规范 / 部署 / 口语方案 / 功能开发记录
```

## 文档

完整索引与阅读路径见 **[docs/README.md](docs/README.md)**。

| 文档 | 内容 |
|---|---|
| [01 需求清单](docs/01-需求清单.md) | 冻结的需求基线与决议 |
| [02 技术架构](docs/02-技术架构.md) | 选型、API、数据模型、同步 |
| [03 Agent 技术规范](docs/03-Agent技术规范.md) | 七阶段工作流与 DoD |
| [04 功能清单](docs/04-功能清单.md) | 功能编号与验收口径 |
| [05 前端设计规范](docs/05-前端设计规范.md) | Design Token 与组件模式 |
| [06 部署与运维](docs/06-部署与运维.md) | 本地 / NAS / 备份 / 迁移 |
| [07 口语实时对话](docs/07-口语实时对话方案.md) | 提示词、记忆、成本、复盘 |

## 数据与素材

- `frontend/public/audio/`（约 85 MB）与教材 PDF **不进版本库**，部署时单独同步。
- `frontend/public/data/*.json` 由 `data-src/` 经 `tools/build_*` 生成，不手改。
- 旧站参考代码在上级目录 `../PET/`，只读。

## 许可

个人学习项目；教材内容版权归原出版方，请勿用于商业分发。
