# PET 备考网站 v2

面向小学生的 PET（B1 Preliminary for Schools）备考站点：单词 / 阅读 / 听力 / 口语四大板块 + 语文·数学占位。
前端 Vue 3 + Naive UI，后端 FastAPI + SQLite，Docker Compose 部署于家用 NAS。

## 功能

| 板块 | 能力 |
|---|---|
| 单词 | 1680 词四库（必默 712 / 高频 414 / 固定搭配 254 / 同义 300）；任意天数计划；三题型测验（拼写 / 看词选义 / 看义选词）；错题本按 1/2/4/7/15 天记忆曲线复习；手动加词（AI 补全词性/释义/例句）；发音（浏览器 TTS） |
| 阅读 | 207 句精读（语法解析 + 知识点 + 生词提示）；416 道语法题（42 考点，10 天）；错题本；阅读计划（按 Part 切分）；手动加句 |
| 听力 | 6 套真题 24 个 Part；Part 1 图片选、Part 2 三选一、Part 3 笔记填空、Part 4 采访三选一；字幕对齐；错题复习 |
| 口语 | 90 天计划；跟读纠音（AI 点评 + 腾讯云 SOE 精准评分双引擎）；实时对话（Qwen Realtime WebRTC）；会后复盘（把说过的话改成 PET 标准句 → 跟读评分 → 记忆曲线）；造句练习 |
| 管理 | AI 配置（LLM / Qwen Realtime / 腾讯 SOE，Key 掩码）、按人按天的 AI 用量与费用统计（只记录不限流） |

数据默认本地保存（localStorage）并自动同步到服务端；多端登录时按「并集 / 取欠得多 / 取大」规则合并。

## 技术栈

- **前端**：Vue 3 · TypeScript · Vite · Pinia · vue-router · Naive UI · @vicons/ionicons5 · vitest（jsdom）
- **后端**：FastAPI · SQLAlchemy 2 · SQLite(WAL) · Alembic · argon2 + bcrypt 兼容 · PyJWT
- **AI**：阿里云百炼 Qwen（Realtime 语音对话 / 文本补全 / TTS）、腾讯云智聆口语评测（SOE 新版）
- **部署**：Docker Compose（nginx + api 两容器）

## 目录

```
backend/            FastAPI 服务
  app/api/v1/       路由：auth / sync / words / speak / admin
  app/models/       数据模型（learning / extra / speak / usage / user）
  app/services/     合并、AI 补全、Qwen Realtime、腾讯 SOE、画像、复盘、用量
  alembic/          数据库迁移
  tests/            pytest（64+ 用例）
frontend/           Vue 3 应用
  src/core/         纯逻辑（merge / sync / plan / reading / listening / speak / soe / say）
  src/views/        页面（单词 / 阅读 / 听力 / 口语 / 管理）
  src/layouts/      布局壳 + 学科导航
  public/data/      构建产物 JSON（banks / reading / listening / speak）
data-src/           数据源（教材结构化后的 JSON）
tools/              构建脚本（词库 / 阅读 / 听力 / 口语数据生成、旧数据迁移）
deploy/             Dockerfile、compose、nginx 配置
docs/               需求、架构、功能清单、设计规范、部署手册、走查报告
```

## 本地开发

```bash
# 后端（Python 3.11+）
cd backend
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python -m uvicorn app.main:app --port 8000 --reload

# 前端（Node 18+）
cd frontend
npm install
npm run dev        # http://localhost:5173，/api 代理到 8000
```

首次使用：数据库为空时，注册页用任意邀请码 `claim` 的第一个账号自动成为管理员；之后由管理员在「管理 → 用户」发放邀请码。

## 测试与构建

```bash
cd backend  && .venv/Scripts/python -m pytest tests/ -q     # 后端
cd frontend && npx vitest run && npx vue-tsc --noEmit && npm run build
```

## 部署

见 `docs/08-飞牛NAS部署手册.md`。要点：

```bash
cd deploy
cp .env.example .env         # 填 PET_JWT_SECRET（必填）
docker compose up -d --build
```

- 首次启动自动执行 Alembic 迁移；数据库落在挂载卷 `data/pet.db`
- AI Key 在「管理 → AI 配置」页填写，**不写入代码或环境文件**；服务端只回显尾 4 位
- 语音相关 Key（Qwen / 腾讯 SOE）全程只在服务端使用，前端拿到的是带签名的临时地址

## 素材与体积说明

- `frontend/public/audio/`（听力音频约 85MB）与教材 PDF **不进版本库**，部署时单独同步
- 词库、阅读、听力、口语的运行期数据在 `frontend/public/data/*.json`，由 `tools/build_*.js|py` 从 `data-src/` 生成

## 许可

个人学习用途项目，教材内容版权归原出版方所有，请勿用于商业分发。
