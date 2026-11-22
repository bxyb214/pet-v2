# sync-v2 / 01 需求拆解

## 背景
现站同步：localStorage + PHP API + `data_rev` 乐观锁，合并逻辑散落前端。v2 重写为 FastAPI + 前端统一 sync 模块。

## 用户故事
- US-1：作为学生，我在 iPad 上做完题，回家打开电脑，两边进度都在（U4/U6）。
- US-2：作为学生，我断网也能做题，联网后自动补传（U6）。
- US-3：作为用户，我能在任意端看到一致的错题到期排期（V6 记忆曲线字段参与合并）。

## 功能点
- F-1 (P0) `GET /sync/pull`：返回该用户全部学习数据 + 当前 rev。
- F-2 (P0) `POST /sync/push`：携带本地基础 rev + 变更数据；rev 不匹配 → 409 + 服务端最新数据；匹配 → 合并落库、rev+1。
- F-3 (P0) 合并语义：mastery 并集；mistakes 取「欠得多」（dims 并集、stage 取小、due 取早）；progress seen 并集 + idx 取大；plan 完成并集。
- F-4 (P1) 前端合并模块 `core/merge.ts`：与服务端同语义（前端先合并再重试 push）。
- F-5 (P1) 数据范围：mastery / mistakes / progress / plan 四类。

## 非目标
- 不做增量 delta 同步（家庭规模全量足够）；不做多课程隔离（首版单英语）。

## 验收标准
- AC-1 (F-1/F-2)：登录后 pull 得到空数据 rev=1；push mastery → pull 可见；旧 rev push → 409 + 最新数据。
- AC-2 (F-3)：给定冲突样本（见 02-design §3 表），合并结果与规则逐条吻合（pytest + vitest 双侧断言同一批用例）。
- AC-3 (F-2)：push 合并是叠加而非覆盖——push 半量数据不丢另一半。
