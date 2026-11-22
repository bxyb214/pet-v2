# vocab-v2 / 01 需求拆解

> 迭代范围：V1（计划生成）、V5/V6 后端支撑、V9（浏览自学）、V11（手动加词）。测验题型（V2–V4）UI 单独迭代。

## 用户故事
- US-1：作为学生，我选择任意天数（如 45 天），系统把四个词库不重不漏地切到每天，我完成当天四库后打勾（V1/P1）。
- US-2：作为学生，我删掉现有计划重新生成（P1）。
- US-3：作为学生，我学到不会的词，手动添加后系统自动给我例句、词性、释义（V11），我还能修改。
- US-4：作为学生，我可以翻卡/列表浏览词库自学习（V9）。

## 功能点
- F-1 (P0) 计划切分纯函数（前端）：输入四库词表 + 天数 N，输出每天四库条目，30 天不重不漏语义推广到任意 N。
- F-2 (P0) 计划存取：length/days_done 走现有 sync 通道；删除=清空（已实现 setPlan/deletePlan）。
- F-3 (P0) `custom_words` 表 + REST：`POST /words/custom`（手动添加）、`PUT /words/custom/{id}`（修正）、`GET /words/custom`（列表）。自加词随 sync 通道合并（新增 custom_words 进 SyncData）。
- F-4 (P0) AI 词条补全：`POST /words/custom/enrich {word}` → 调用文本 LLM（Key 从 `app_cfg` 读，S5/M2）返回 `{pos, definition, example_en, example_cn}`；未配 Key 返回 503 + 明确提示。
- F-5 (P1) `app_cfg` 表 + `GET/PUT /admin/cfg`：Key 类配置存库（值回显尾号），替代环境变量散配。
- F-6 (P1) 前端「加词」页面 + 词库浏览页（翻卡/列表，绿色系设计 token）。
- F-7 (P0) Alembic 接入：初始迁移生成，后续 schema 变更可逆（遗留项清偿）。

## 非目标（本迭代不做）
- 测验 UI（V2–V4）、TTS 音频生成（V8）、随机测试（V10）——后续迭代。

## 验收标准
- AC-1 (F-1)：给定四库条数与 N 天，任何一天的四库都是全库切片，拼接全部天数 = 全库且无重复（属性测试 + 抽样断言）。
- AC-2 (F-3/F-4)：添加自加词成功落库；enrich 无 Key → 503；配 Key 后 enrich 返回结构完整。
- AC-3 (F-3)：自加词经 push/pull 在另一端可见（扩展 merge 同步数据 + 双侧测试）。
- AC-4 (F-7)：alembic upgrade head 从空库建出全部表；downgrade 可回退。
