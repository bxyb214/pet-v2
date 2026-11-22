# vocab-v2 / 99 自省检查报告

日期：2026-11-22 · 范围：docs/dev/vocab-v2（计划切分 / 自加词 / app_cfg / Alembic / 三个页面）

| 类别 | 检查项 | 结果 |
|------|--------|------|
| 需求 | F-1 计划切分 / F-2 计划存取 / F-3 自加词 CRUD+同步 / F-4 AI 补全 / F-5 app_cfg / F-6 三页面 / F-7 Alembic — 全部实现 | ✅ |
| 设计 | 与 02-design 一致：切分语义、custom_words 合并（word 小写键、服务端优先）、LLM 调用参数 | ✅ |
| 代码 | 后端 pytest 25 passed；前端 vitest 23 passed；vue-tsc + vite build 通过；uvicorn 冒烟 healthz OK、未登录 401 正确 | ✅ |
| 代码 | Key 零硬编码（app_cfg 存库 + 管理页）；enrich 无 Key → 503 | ✅ |
| 测试 | 计划切分不变量：validatePlan 属性校验（30/45/3 天）+ 篡改检测；非法天数抛错 | ✅ |
| 测试 | custom_words 合并双侧同语义测试；CRUD + 404/503 场景；admin cfg 脱敏（尾 4 位） | ✅ |
| 数据 | Alembic 初始迁移 upgrade→downgrade→upgrade 演练通过；Dockerfile 改为 alembic 先行 | ✅ |
| 同步 | SyncData 扩展第五类 custom_words，merge.py/merge.ts 双侧同步实现 | ✅ |
| 文档 | 01/02/99 齐全 | ✅ |

## 结论：PASS-with-notes

### 遗留项

1. **词库静态数据未迁移**：`/data/banks.json` 尚无产物（browse/plan 页面空态已处理），下一步 `tools/build_data.py` 从旧站 `js/data.js` 迁移四库。
2. **测验题型 UI（V2–V4）未做**：recordMastery/recordWrong/recordRight 已就绪待接线。
3. **登录后 learning.connect() 自动化 + 路由守卫**仍未接（第三次顺延，务必随测验迭代完成）。
4. LLM enrich 为同步阻塞调用（15s 超时），并发高时可换后台任务——家庭规模可接受。
5. TTS（V8）、随机测试（V10）后续迭代。
