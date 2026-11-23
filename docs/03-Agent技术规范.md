# 03 · Agent 技术规范

> 约束所有在本仓库工作的 AI Agent 与人类协作者。文档先行，阶段产物落盘到 `docs/dev/`，可追溯。
> 工作流：**需求 → 设计 → 实现 → 测试 → 依赖 → 部署 → 自省**。

## 0. 总则

- 任何功能改动先更新阶段文档，再动代码。
- 产物命名：`docs/dev/{feature}/{NN}-{阶段}.md`，如 `docs/dev/sync-v2/01-requirements.md`；多步迭代加 `-step2`。
- 不得跳过自省报告直接宣布完成。
- 不得引入白名单外依赖（见 §5）。
- 同步合并语义是红线：修改前必须在设计文档说明并获确认。
- 文档索引与归档规则见 [docs/README](README.md)。

## 1. 需求拆解

产出 `01-requirements.md`，必含：

1. 背景与目标（一句话：做什么、为什么）。
2. 用户故事：`作为<角色>，我希望<行为>，以便<价值>`，编号 `US-xx`。
3. 功能点：可独立验收，编号 `F-xx`，标 P0/P1/P2。
4. 边界与非目标。
5. 验收标准：Given/When/Then，与 `F-xx` 一一对应。
6. 影响面：模块、API、数据表、数据文件。

**DoD**：每条 `F-xx` 有可执行验收标准；无歧义代词。

## 2. 设计方案

产出 `02-design.md`，必含：

1. 方案概览：ASCII 或 mermaid 架构图 + 数据流。
2. API 契约：请求/响应 JSON、错误码、Pydantic schema 类名。
3. 数据模型变更：表结构 diff + Alembic 迁移草案。
4. 前端变更：组件树、store、路由。
5. 备选方案与取舍（至少 1 个被否方案及理由）。
6. 风险清单：兼容性、数据迁移、性能，各附缓解措施。

**DoD**：API 示例可直接作为 pytest 断言；schema 变更可生成迁移脚本。

## 3. 代码实现

### 3.1 后端

- 分层：`api/v1/` 路由薄（参数校验 + 调 service）→ `services/` → `models/`；schema 只由 Alembic 管理，禁用 `create_all`。
- 全量类型注解；Pydantic v2 做请求/响应；模块 snake_case、类 PascalCase、常量 UPPER；API 路径小写复数。
- 错误统一为 `{"code": "...", "message": "..."}`；业务错误码集中定义。
- 配置用 pydantic-settings；**密钥只从 env 或管理页配置读取，禁止硬编码、禁止入 git**。
- 关键路径（登录、push 冲突、口语 SDP）留 DEBUG 日志。
- 单文件 ≤ 400 行。

### 3.2 前端

- Vue 3 `<script setup lang="ts">`，Props/Emits 显式类型。
- HTTP 全部经 `src/core/api.ts`，组件内禁止裸 `fetch`。
- 同步/合并逻辑只在 `src/core/`，不得写进组件。
- 交互约定：拼写/看义选词/阅读答题前不朗读，答后给「听发音/听整句」；仅「看词选义」答题前有发音。
- 音频路径一律 ASCII slug；新页面必须补路由 `meta`。
- 单文件 ≤ 400 行。

### 3.3 Git

- 分支：`main`（可部署）+ `feat/xxx`、`fix/xxx`。
- Commit：`type(scope): summary`，type ∈ feat/fix/docs/test/refactor/chore。
- 每个功能一个 PR/一次合并，合并前自检通过。

## 4. 测试

| 层 | 工具 | 要求 |
|---|---|---|
| 后端 service | pytest + pytest-asyncio | 合并算法、错题维度记账、计划切库 **行覆盖 ≥90%** |
| 后端 API | pytest + httpx（ASGI 内存测试） | 每端点：正常 + 401 + 422 + 409（涉及同步） |
| 前端核心 | vitest | sync 合并、dims 状态机、plan 进度必须有单测 |
| 前端组件 | vitest + @vue/test-utils | 仅关键交互（测验提交、同步状态） |
| E2E | Playwright（可选） | 登录 → 做题 → 同步冒烟 |

必须存在的不变量：① dims 空 → 移出错题本；② 409 → 合并重试成功；③ 四库全测完才打勾；④ 计划模式强制全维度。

```bash
cd backend  && .venv/bin/python -m pytest tests/ -q
cd frontend && npm test
cd frontend && npm run build
```

## 5. 依赖

- 后端：`pyproject.toml` + venv/pip；Python 3.12。
- 前端：`package.json` + npm，提交 `package-lock.json`；Node 20+。
- 新依赖须在 `02-design.md` 说明：用途、为何不用现有依赖、维护活跃度。
- 基线白名单：fastapi、uvicorn、sqlalchemy、alembic、pydantic(+settings)、argon2-cffi、bcrypt、pyjwt、httpx、pytest 系；vue、vue-router、pinia、naive-ui、@vicons/ionicons5、vite、typescript、vitest、@vue/test-utils。

## 6. 部署

当前以 Compose 手工发布，完整流程见 [06 部署与运维](06-部署与运维.md)：

1. 构建前端 `dist`；后端镜像 tag 建议带版本。
2. `cp .env.example .env` 填 `PET_JWT_SECRET`，`docker compose up -d --build`。
3. api 启动时自动 `alembic upgrade head`；healthcheck 探 `/api/v1/healthz`。
4. 备份：部署前做一次 SQLite `.backup`，保留 14 份。
5. 回滚：切回上一镜像 tag；数据库 `alembic downgrade -1`（不可逆迁移须在设计文档声明）。

> CI 自动发布（tag → 构建 → 推送 NAS → 滚动更新）为后续目标，未接入前以 `tools/deploy_nas.py` 为准。

## 7. 自省检查报告

产出 `docs/dev/{feature}/99-self-review.md`，宣布完成前逐项自查：

| 类别 | 检查项 | 结果 |
|---|---|---|
| 需求 | 每条 `F-xx` 有实现与测试？ | ☐ |
| 设计 | 与 `02-design.md` 一致？偏差补记？ | ☐ |
| 代码 | 类型检查通过？无硬编码密钥/绝对路径/TODO？ | ☐ |
| 测试 | 全部通过？核心算法覆盖 ≥90%？ | ☐ |
| 依赖 | 新增依赖走白名单？lock 已更新？ | ☐ |
| 数据 | schema 有 Alembic 迁移且可回滚？ | ☐ |
| 同步 | 是否触碰合并语义？如触碰，已说明并确认？ | ☐ |
| 部署 | healthz 通过？备份已执行？ | ☐ |
| 文档 | 01/02/99 齐全？README/相关文档已更新？ | ☐ |

结论：**PASS / PASS-with-notes（附遗留项）/ FAIL（附失败项与补救）**。FAIL 不得宣称完成。

## 8. 会话工作模板

```text
1. 读 docs/README、01、02，确认影响面
2. 写 docs/dev/{feature}/01-requirements.md          → 用户确认
3. 写 docs/dev/{feature}/02-design.md                → 用户确认（涉及红线必须确认）
4. 实现 + 测试 + 依赖锁定
5. 写 docs/dev/{feature}/99-self-review.md           → PASS 才交付
6. 更新 README / 功能清单 / 相关文档
```
