# NAS 开发环境 — 需求

> **已归档（2026-11-24）**：NAS `8089` 开发环境已删除，改由
> [本地开发环境](../../dev/local-dev-env/01-requirements.md)（`localhost:8088`，Windows 原生进程）替代。
>
> 功能编号：`nas-dev-env`；日期：2026-11-23；关联文档：[06 部署与运维](../../06-部署与运维.md)

## 1. 背景与目标

生产环境已稳定运行在飞牛 NAS 的 `8088`。每次发布都直接覆盖生产，无法先验证新构建。
目标：在同一台 NAS 上增加一套与生产并行的开发/预发布环境（`8089`），先验证再发布到生产。

## 2. 用户故事

- **US-01**：作为维护者，我希望在 NAS 上有一份与生产隔离的部署，以便先验证新版本再上线。
- **US-02**：作为发布者，我希望一条命令完成构建、上传、启动与健康检查，以便减少手工步骤。
- **US-03**：作为维护者，我希望两套环境的数据、镜像、端口互不影响，以便随时清理开发数据。

## 3. 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| F-01 | 新增 `deploy/docker-compose.dev.yml`：8089 端口、独立 compose 项目、镜像 tag `pet-api:dev` | P0 |
| F-02 | `tools/deploy_nas.py` 增加 `--profile dev`：目录 `pet-v2-dev`、compose 文件、端口自动切换 | P0 |
| F-03 | dev 首次部署自动生成独立 `.env`（独立 JWT secret、`PET_DEV_MODE=1`、`PET_DEV_PORT=8089`） | P0 |
| F-04 | 部署脚本解包后修正 `frontend/dist` 权限（`a+rX`），避免 nginx 403 | P0 |
| F-05 | 文档：`docs/06` 增加开发环境说明与发布顺序 | P1 |
| F-06 | `seed-db`：用生产库一致快照初始化/重置开发库（只对 dev 生效） | P0 |

## 4. 边界与非目标

- 不引入 CI/CD、自动回滚、镜像仓库。
- 开发库由生产一致快照复制（账号、密码哈希、学习数据、`app_cfg` 里的 AI 配置随库带入）；
  若切真实 AI 调用，建议在 dev 的 `/admin` 换成独立 Key。
- 不改变生产 compose、同步合并语义、错题本规则与任何业务代码。

## 5. 验收标准

- **AC-01**（F-01/F-02）：`deploy --profile dev` 后，`docker ps` 出现 `pet-v2-dev-*` 容器，`8089` 健康检查返回 `{"status":"ok",...,"dev_mode":true}`。
- **AC-02**（F-03）：dev 目录下 `.env` 含 `PET_DEV_MODE=1`、`PET_DEV_PORT=8089`，JWT secret 与生产不同。
- **AC-03**（F-01）：`8089/data/banks.json`、`8089/audio/listen/*.mp3`、SPA 路由均返回 200。
- **AC-04**（F-01/F-03）：dev 的 `data/pet.db` 与生产 `data/pet.db` 为不同文件；生产 `8088` 健康检查不受影响。
- **AC-05**（F-04）：重新执行 dev/prod 部署后，`frontend/dist` 权限为可读（nginx 无 403）。
- **AC-06**（F-05）：`docs/06` 能找到 dev 部署命令、端口、目录与发布顺序。
- **AC-07**（F-06）：`seed-db --profile dev` 后，dev 的 `users` / `mastery` / `plans` 数量与迁移版本同生产一致；生产 healthz 与数据不受影响。
- **AC-08**（F-06）：`seed-db` 只接受 `--profile dev`，对 prod 调用直接拒绝。

## 6. 影响面

| 类别 | 内容 |
|---|---|
| 脚本 | `tools/deploy_nas.py`（新增 profile、权限修正、`.env` 内容、`seed-db`） |
| 部署 | 新增 `deploy/docker-compose.dev.yml`；不修改生产 `docker-compose.yml` |
| 数据 | 新增 NAS 目录 `/vol1/1000/docker/pet-v2-dev/`（含独立 `data/`，可由生产快照初始化） |
| 业务代码 | 无 |
| 依赖 | 无新增 |
