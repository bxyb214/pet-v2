# PET v2 — AI Agent 前后端技术规范（v0.1）

> 本规范约束所有在本仓库工作的 AI Agent（及人类协作者）。每个阶段的产出物落盘到 `docs/dev/`，形成可追溯链路。
> 完整工作流：**需求拆解 → 设计方案 → 代码实现 → 单元测试 → 依赖配置 → 自动化部署 → 自省检查报告**。

---

## 0. 总则

- 文档先行：任何功能改动先更新对应阶段文档，再动代码。
- 每个阶段产出物文件命名：`docs/dev/{feature}/{NN}-{阶段}.md`，如 `docs/dev/sync-v2/01-requirements.md`。
- Agent 不得跳过「自省检查报告」直接宣布完成。
- 不得引入规范外依赖（见 §5 依赖白名单机制）。
- 合并语义（§02 架构 §4）是红线：修改同步/合并逻辑必须先在设计方案中说明并获确认。

## 1. 需求拆解（Requirements）

产出：`01-requirements.md`

必含内容：
1. **背景与目标**：一句话说清做什么、为什么。
2. **用户故事**：`作为<角色>，我希望<行为>，以便<价值>`，编号 US-xx。
3. **功能点清单**：每条可独立验收，编号 F-xx，标注优先级 P0/P1/P2。
4. **边界与非目标**：明确本迭代不做什么。
5. **验收标准**：Given/When/Then 格式，与 F-xx 一一对应。
6. **影响面**：涉及的模块、API、数据表、数据文件。

验收（DoD）：每条 F-xx 都有可执行的验收标准；无歧义代词（"它/那个"）。

## 2. 设计方案（Design）

产出：`02-design.md`

必含内容：
1. **方案概览**：架构小图（ASCII 或 mermaid）+ 数据流。
2. **API 契约**：新增/修改端点的请求/响应 JSON 示例、错误码（遵循 FastAPI Pydantic 模型，写明将落地的 schema 类名）。
3. **数据模型变更**：表结构 diff + Alembic 迁移草案。
4. **前端变更**：组件树、store 变更、路由变更。
5. **备选方案与取舍**：至少 1 个被否方案及否决理由。
6. **风险清单**：兼容性、数据迁移、性能，各附缓解措施。

验收（DoD）：API 示例可直接作为 pytest 契约断言；schema 变更可生成迁移脚本。

## 3. 代码实现（Implementation）

### 3.1 后端（Python / FastAPI）

- 目录职责：路由层薄（只做参数校验+调 service），业务在 `services/`，数据访问经 SQLAlchemy 模型。
- 全量类型注解，Pydantic v2 模型做请求/响应。
- 命名：模块 snake_case、类 PascalCase、常量 UPPER；API 路径小写复数（`/users`）。
- 错误处理：统一异常 → `{"code": "...", "message": "..."}` 结构；业务错误码集中定义于 `core/errors.py`。
- 配置：pydantic-settings 读环境变量，**密钥（Qwen Key、JWT secret）只从 env/配置文件读，禁止硬编码、禁止写入 git**。
- 日志：structlog/标准 logging，关键路径（登录、push 冲突、speak SDP）必须留 DEBUG 日志。
- 单文件 ≤ 400 行，超限拆分。

### 3.2 前端（Vue 3 / TS）

- `<script setup lang="ts">`；组件 Props/Emits 显式类型。
- API 调用全部经 `core/api.ts` 客户端，组件内禁止裸 fetch。
- 同步引擎（sync）独立模块，禁止在业务组件里直接操作合并逻辑。
- 现有交互约定原样保留：测验答题前不给朗读（拼写/看义选词/阅读），答后在反馈区给「听发音/听整句」；仅「看词选义」答题前有发音。
- 音频路径一律 ASCII slug。

### 3.3 Git 约定

- 分支：`main`（可部署）+ `feat/xxx`、`fix/xxx`。
- Commit：`type(scope): summary`，type ∈ feat/fix/docs/test/refactor/chore。
- 每个功能一个 PR/一次合并，合并前自检通过（§7）。

## 4. 单元测试（Testing）

| 层 | 工具 | 覆盖要求 |
|----|------|---------|
| 后端 service 层 | pytest + pytest-asyncio | **合并算法、错题维度记账、计划切库算法 = 行级覆盖 ≥ 90%** |
| 后端 API | pytest + httpx（ASGI 内存测试，不起真服务） | 每个端点：正常 + 401 + 422 + 409（涉及同步） |
| 前端核心逻辑 | vitest | sync 合并、错题 dims 状态机、plan 进度判断必须单测 |
| 前端组件 | vitest + @vue/test-utils | 仅关键交互组件（测验提交、同步状态） |
| E2E（可选） | Playwright | 登录→做题→同步 冒烟一条链 |

- 测试数据用 fixture，禁止依赖真实用户数据。
- 关键不变量测试（必须存在）：① 错题本 dims 空 → 移出；② 同步冲突 409 → 合并重试成功；③ 计划四库全测完才打勾；④ 计划模式强制全维度。

## 5. 依赖配置（Dependencies）

- 后端：`pyproject.toml` + `uv`（或 pip-tools）锁定 `requirements.lock`；运行镜像 python:3.12-slim。
- 前端：`package.json` + pnpm，锁定 `pnpm-lock.yaml`；Node 20 LTS。
- 新增依赖须在对应 `02-design.md` 说明：用途、为什么不用已有依赖、维护活跃度。
- 安全：CI 中 `pip-audit` / `pnpm audit`，高危项阻断合并。
- 白名单基线：fastapi, uvicorn, sqlalchemy, alembic, pydantic(+settings), argon2-cffi, pyjwt, httpx, pytest 系 / vue, vue-router, pinia, vite, typescript, vitest, @vue/test-utils。

## 6. 自动化部署（Deployment）

链路：`git tag vX.Y.Z` → CI 构建（前端 dist + 后端镜像）→ 推送 NAS → compose 滚动更新 → 健康检查 → 失败自动回滚。

1. **构建**：CI 产出 `dist.tar.gz`（前端）+ Docker 镜像（后端），镜像 tag = git tag。
2. **推送**：NAS 上预装 fnOS Docker；`scripts/deploy.sh`（或 fnOS 计划任务）拉取产物。
3. **更新**：`docker compose pull && docker compose up -d`；Alembic 迁移在 api 容器启动前自动执行（`migrate && uvicorn` 入口脚本）。
4. **健康检查**：`GET /api/v1/healthz` 返回 db 连通 + 版本号；compose healthcheck 探活，失败 `--rollback`。
5. **回滚**：切回上一镜像 tag + `alembic downgrade -1`（迁移必须可逆，不可逆迁移须在设计文档中声明并要求人工确认）。
6. **数据备份**：部署前自动做一次 SQLite `.backup`，保留 14 份（与每日定时备份共用目录）。

## 7. 自省检查报告（Self-review Report）

产出：`docs/dev/{feature}/99-self-review.md`，Agent 在宣布完成前必须逐项自查并落盘：

| 类别 | 检查项 | 结果 |
|------|--------|------|
| 需求 | 需求清单每条 F-xx 是否都有对应实现与测试？ | ☐ |
| 设计 | 实际实现与 02-design.md 是否一致？偏差是否补记？ | ☐ |
| 代码 | lint（ruff/eslint）0 error？类型检查（mypy/vue-tsc）通过？ | ☐ |
| 代码 | 有无硬编码密钥/绝对路径/TODO 残留？ | ☐ |
| 测试 | 全部测试通过？核心算法覆盖 ≥ 90%？ | ☐ |
| 依赖 | 新增依赖是否走白名单审批？lock 文件已更新？ | ☐ |
| 数据 | schema 变更是否有 Alembic 迁移且可回滚？ | ☐ |
| 同步 | 是否触碰合并语义？如触碰，是否在设计中说明并获确认？ | ☐ |
| 部署 | healthz 通过？回滚脚本演练过？备份已执行？ | ☐ |
| 文档 | 阶段文档齐全（01/02/99）？README 更新？ | ☐ |

结论三选一：**PASS / PASS-with-notes（附遗留项）/ FAIL（附失败项与补救计划）**。FAIL 状态下 Agent 不得宣称任务完成。

## 8. Agent 会话工作模板

每次被指派功能开发时按此顺序执行并留痕：

```
1. 读 docs/01-需求清单.md + 02-技术架构.md，确认影响面
2. 写 docs/dev/{feature}/01-requirements.md   → 用户确认
3. 写 docs/dev/{feature}/02-design.md         → 用户确认（涉及红线时必须确认）
4. 实现 + 测试 + lock 更新
5. 写 docs/dev/{feature}/99-self-review.md    → 结论 PASS 才交付
6. 更新 README 变更记录
```
