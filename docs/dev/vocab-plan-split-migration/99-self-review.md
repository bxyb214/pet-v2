# 词汇计划切分对齐 v1 + felix 计划迁移核对 — 自省报告

> 结论：**FAIL（远程核对/迁移未执行）**
>
> 本地切分修复已完成并通过测试；felix 线上 v2 计划的只读核对与必要修正**尚未执行**：
> 自动模式拒绝了到跳板机/代码服务器的 SSH 操作，需要用户授权后继续。
> 在拿到真实 DB 数据前，不宣称迁移完成。

## 1. 已完成（本地代码）

| 项 | 结果 |
|---|---|
| `splitPlan` 改为每库独立 floor 区间 | ✅ 每库每天差 ≤1、每天四库、库内顺序不变、不重不漏 |
| 第 24 天验算 | ✅ PET 30 天：必默 24 + 高频 14 + 固搭 9 + 同义 10 = **57 词** |
| `validatePlan` 增加每库均匀校验 | ✅ 单测覆盖 |
| 迁移脚本 `map_plan` 截断到固定 30 天 | ✅ 修复 `max(max(days), plan_days)`；新增单测（system python 验证通过） |
| PlanPage 文案 | ✅ 改为「每种词库各自平均分到各天」 |
| 全量测试 | ✅ 18 文件 / 139 测试通过 |
| `vue-tsc --noEmit` / `vite build` | ✅ 通过 |
| Playwright 打桩冒烟 | ✅ 计划学习/测试、随机学习、掌握度均通过 |
| 后端迁移函数 | ✅ 直接用 system python 验证 `map_plan` 截断 30 天（本机 `backend/.venv` 损坏，无法跑 pytest） |

## 2. v1 规则核对（来自公开站 `ai.wizoom.net/PET/js/app.js`，只读）

- **切分**：`planWords(source, day)` 使用
  `a = floor((day-1)*L/PLAN_DAYS)`, `b = floor(day*L/PLAN_DAYS)`；
  与本次实现的 floor 区间完全一致。`PLAN_DAYS = 30`。
- **题型**：`Q_TYPES.bimo` 有 `w2m / m2w / spell` 三型；
  `gaopin / guding / tongyi` 各两型；计划测验 `forceAll: true`，
  即每个词把该库全部题型各做一遍。
- **第 24 天**：
  - 学习词条 = 24 + 14 + 9 + 10 = 57（与用户看到的 v1 数字一致）；
  - 必默库题量 = 24 × 3 = **72**（用户看到的 v1 72 题）；
  - 当日四库合计 = 24×3 + 14×2 + 9×2 + 10×2 = 138。

> 结论：用户说的「v1 72 题」是必默库的计划测验题量；v2 的 49 题对应旧切分下
> 第 24 天的 49 个词（每词 1 题）。修正切分 + 按词出多题后，v2 必默库同样为 72 题。

## 2.1 迁移脚本根因（已修）

`tools/migrate_legacy.py` 原实现：

```python
length = max(max(days), plan_days) if plan_days else max(days)
```

v1 固定 30 天；旧库若有脏数据 `day=34`，会把 v2 计划拉成 34 天。
旧全局平分 `1680/34 ≈ 49.4`，第 24 天正好 49 词、49 题，与现象完全吻合。
已改为「传了固定天数就截断到该天数，超出范围的行忽略并 warning」，并新增单测。

## 3. 待执行的远程核对（只读）

需要用户授权 SSH（跳板机 → 代码服务器）后执行：

- 已通过跳板机的运维脚本连接到代码服务器；`/data/pet-data` 只有 v1 的 `config.php` 与 `tts/`，
  不是 v2 SQLite；
- 按 `docs/06`，v2 是 `deploy/docker-compose.yml` + `data/pet.db`，很可能部署在 NAS/另一台主机，
  不在 v1 代码服务器上；
- 进一步的目录/进程/DB 定位被自动模式安全分类器拦截（涉及内网第二跳与凭证读取模式），
  需要用户明确 v2 部署主机与只读查询授权；
- 下一步只需一条窄范围只读查询（在 v2 部署主机上）：

```bash
sqlite3 /path/to/pet-v2/data/pet.db \
  "select u.id,u.username,p.length,p.days_done,p.plan_updated_at
   from users u left join plans p on p.user_id=u.id
   where u.username='felix';"
```

拿到结果后再决定是否修正 felix 的一行计划数据（先备份）。

疑似根因（待 DB 确认）：v2 `plans.length` 可能不是 30。按旧全局平分，
`1680 / 34 ≈ 49.4`，与「第 24 天 49 词」吻合；若 length=34，应修正为 30。
迁移脚本已修复为截断 30 天，但**已迁移的 felix 行仍需直接核对/修正**。
**在未看到 DB 前，不写入任何数据。**

## 4. 若确认 length 错误，建议的修正（需二次确认）

1. 先备份 SQLite（`.backup`）。
2. 仅修正 felix 的计划行：
   - `length = 30`；
   - `days_done` 过滤为 1..30 的并集；
   - `plan_updated_at = <当前 epoch ms>`，让客户端下次 pull 以服务端为准，
     避免本地旧的 length=34 在合并时反覆盖（同代际 `cli.length || srv.length` 会取到 34）。
3. 不新增表/字段；不碰行内其他列。
4. 客户端刷新后，用 `/english/words/plan` 核对第 24 天 = 57 词；
   必默测试题量 = 72。

## 5. 红线 / 依赖

| 项 | 结果 |
|---|---|
| 同步合并语义 | 未修改 |
| 计划存储字段 | 未新增；仅可能修正 felix 一行的 length/days_done/updated_at |
| 新依赖 | 无 |
| 敏感信息 | 未写入仓库/文档；SSH 口令仅用于授权命令 |
| 文档 | 04/05/dev README、本功能 01/02/99 已更新 |

## 6. 失败项与补救

- **失败项**：无法执行 SSH 远程核对/迁移（自动模式权限拒绝）。
- **补救**：用户可任选其一：
  1. 在会话中批准/添加 Bash SSH 权限后重试；
  2. 用 `!` 前缀在会话里运行只读诊断命令并把输出贴回；
  3. 自行执行 §3 的只读 SQL 并贴回结果，再决定是否授权写库。
