# felix 第 24 天 50/56 排查与修复 — 自省报告（第 2 轮）

> 结论：**PASS**
>
> v1.21 修正切分后，felix 仍看到 50 词 / 56 题，原因不是计划长度（实际 length=30），
> 而是该账号 `users.exam` 被改成了 `ket`：页面按 KET 词库切分，
> 第 24 天自然是 50 词、核心词 56 题。已把考试级别恢复为 PET，并补齐
> 迁移显式级别、切换警告与审计工具。开发环境与生产环境均已核对。

## 1. 现象与真实根因

| 版本 | 第 24 天学习 | 必默题量 | 词库 |
|---|---|---|---|
| v1 | 57 词（24/14/9/10） | 72 题 | PET |
| v2（报障时） | 50 词（5 库合计） | 56 题（kword 28×2） | **KET** |
| v2（修复后） | 57 词（24/14/9/10） | 72 题 | PET |

核对线上库（只读 + 一致快照）：

- `plans.length = 30`、`days_done = [1..23]`，计划行本身没有损坏；
- `users.exam = 'ket'`，但 mastery 的 1285 个词 id 全部是 PET 前缀（`b/g/d/t`）；
- KET 30 天第 24 天 = 28+7+3+5+7 = **50 词**，kword 28 词 × 2 型 = **56 题**，
  与报障数字完全一致；PET 30 天第 24 天 = 57 词、必默 72 题。

结论：**旧站只有 PET 内容，迁移时用户默认就是 PET；`exam` 是迁移后在新站
设置页被切到 KET 的**。级别切换会立刻按新词库重切计划，而旧实现没有任何提示，
用户看到的就是「迁移把第 24 天搞坏了」。

## 2. 修复内容

| 编号 | 修复 | 位置 |
|---|---|---|
| F-08 | 线上 `felix.exam` 恢复为 `pet`，操作前做 SQLite 一致备份 | 生产 `data/backup/pet-2026-11-23-before-exam-fix.db` |
| F-09 | 迁移显式写 `exam="pet"`，不再依赖列默认值 | `tools/migrate_legacy.py` |
| F-10 | 迁移单测断言全部旧用户 `exam == "pet"` | `backend/tests/test_migration.py` |
| F-11 | 设置页切换级别前弹窗：说明计划会按新词库重切，打卡/掌握/错题不删 | `frontend/src/views/SettingsPage.vue` |
| F-12 | 级别审计工具：按 mastery 前缀推断应属级别，`--execute` 才写库 | `tools/check_user_exam.py` + `backend/tests/test_check_user_exam.py` |

不变式（未改动）：切换级别只影响「计划如何切词」，`days_done`、`mastery`、
`mistakes` 均保留；切回 PET 后第 24 天恢复 57 词 / 72 题。

## 3. 验证

### 3.1 单元/构建

- 后端：`pytest tests/ -q` **93 passed**（含迁移显式 exam、审计工具 5 例）。
- 前端：`vitest run` **18 文件 / 139 测试通过**；`vue-tsc --noEmit && vite build` 通过。
- 顺带修复 `tests/conftest.py`：先 `import app.main` 再建表，单文件运行
  （CLAUDE.md 记录的用法）不再因缺 `usages` 表报错。

### 3.2 开发环境（8089，数据库为修复后生产快照）

用 felix 真实 JWT 驱动 Playwright：

| 页面 | 结果 |
|---|---|
| `/english/words/study/day?day=24` | `第 24 天 · 学习 必默 24 · 高频 14 · 固搭 9 · 同义 10 共 57 词` |
| `/english/words/study?day=24` | `共 138 题`，必默 `0/72`（四库合计 138 = 72+28+18+20） |
| `/settings` 点击 KET | 弹窗「切换级别会重新切分进行中的计划……已打卡 23 天……确定切换吗？」 |

### 3.3 生产环境（8088）

- `/auth/me`（felix）返回 `exam: "pet"`；
- 第 24 天数据与开发环境一致（57 词 / 必默 72 题），设置页切换弹窗正常；
- 上线后对生产库重跑 `tools/check_user_exam.py`：4 个账号全部为 pet，
  无「级别与已学词库不一致」；felix 1285 个词均为 PET。

## 4. 对 v1.21 自省报告的更正

v1.21 曾推测「`plans.length=34` 导致第 24 天 49 词」。线上核对为 **length=30**，
该推测不成立；`map_plan` 的 30 天截断仍是正确的防御性修复，保留。
本轮真实根因是 **exam=ket**，与计划长度无关。

## 5. 遗留与建议

- 提示：若用户确实想学 KET，应新建 KET 计划；旧 PET 打卡记录保留在同步数据里。
- 迁移脚本已显式 `exam="pet"`，以后旧站新增用户不会再依赖默认值。
- 建议上线后跑一次 `python tools/check_user_exam.py --sqlite data/pet.db`，
  确认没有其他账号级别与已学词库矛盾。
