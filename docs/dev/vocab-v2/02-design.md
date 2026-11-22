# vocab-v2 / 02 设计方案

## 1. 计划切分（F-1，前端纯函数 `core/plan.ts`）

沿用现站语义推广到任意 N 天：四库各按 `ceil(库长 / N)` 每天配额顺序切片，第 N 天吸收余量。

```ts
splitPlan(banks: {bimo: Word[]; gaopin: Word[]; guding: Word[]; tongyi: Word[]}, days: number)
  → Array<{ day: number; bimo: Word[]; gaopin: Word[]; guding: Word[]; tongyi: Word[]; total: number }>
```

不变量：各库全量拼回 = 原库顺序不变、无重复；days > 库长时允许空日。`planSig(days)` 用于检测计划变更需重生成。

## 2. custom_words（F-3/F-4，后端）

表 `custom_words(user_id PK/FK, id PK autoincr, word, pos, definition, example_en, example_cn, source, created_at)`，`source ∈ manual`。

API（`/api/v1/words/custom`）：
- `GET /` → 列表
- `POST /` body `{word, pos?, definition?, example_en?, example_cn?}` → 创建；若四项全空且配置了 LLM Key，服务端自动 enrich
- `PUT /{id}` → 人工修正
- `DELETE /{id}` → 删除自加词（用户自建数据，允许删；区别于错题本）
- `POST /enrich` body `{word}` → 调 LLM 补全，返回四项；无 Key → `503 {"detail": "未配置 AI Key"}`

LLM 调用：`services/ai_enrich.py`，HTTP 调 OpenAI 兼容接口（dashscope compatible-mode），Key/模型名从 `app_cfg` 读（key: `llm.api_key`, `llm.base_url`, `llm.model`）。超时 15s，失败返回 502。

## 3. SyncData 扩展（AC-3）

`SyncData` 增 `custom_words: [{id, word, pos, definition, example_en, example_cn}]`。
合并规则：按 `word` 小写去重取并集（id 冲突以服务端为准）；双侧同词内容不同 → **服务端优先**（人工修正场景少，避免复杂三方合并）。`merge.py` / `merge.ts` 双侧同步实现 + 测试。

## 4. app_cfg 与 admin（F-5）

表 `app_cfg(key TEXT PK, value TEXT)`。端点：`GET /admin/cfg`（llm.api_key 回显尾 4 位）、`PUT /admin/cfg`（admin 权限）。

## 5. Alembic（F-7）

- `alembic init alembic`；`env.py` 用 `app.core.config` 的 database_url + `Base.metadata`。
- 初始迁移 `upgrade head` 从现状 create_all 等价生成（手写 or autogenerate）。
- Dockerfile CMD 改为 `alembic upgrade head && uvicorn ...`。

## 6. 前端页面（F-6）

- `/plan`：天数输入 + 生成预览（每天四库条数）→ 确认写入 store；已有计划显示进度条与删除按钮。
- `/words/browse`：词库选择 tab + 翻卡（点击翻面）。
- `/words/add`：输入单词 → enrich 自动填充（可编辑）→ 保存。
均遵守 05 设计 token（绿系、圆角卡、大触控目标）。

## 7. 风险

- LLM 生成质量：允许人工修正（PUT）；prompt 里限定小学生可读释义。
- custom_words 与 sync 合并的 id 漂移：以 word 小写为业务键，id 仅本地列表 key 用。
