# 功能开发记录

每个功能按 [03 技术规范](../03-Agent技术规范.md) 的七阶段落盘：`01-requirements.md` → `02-design.md` → `99-self-review.md`。
多步迭代加 `-step2` 后缀；完成后的文档保留，不删除。

| 功能目录 | 范围 | 主要文档 |
|---|---|---|
| [vocab-v2](vocab-v2/) | 词库迁移、计划切分、自加词、测验 | [需求](vocab-v2/01-requirements.md) · [设计](vocab-v2/02-design.md) · [自省](vocab-v2/99-self-review.md) · [第二步自省](vocab-v2/99-self-review-step2.md) |
| [reading-v2](reading-v2/) | 阅读迁移、精读进度、错题、计划、加句 | [需求](reading-v2/01-requirements.md) · [设计](reading-v2/02-design.md) · [自省](reading-v2/99-self-review.md) · [第二步需求](reading-v2/01-requirements-step2.md) / [设计](reading-v2/02-design-step2.md) / [自省](reading-v2/99-self-review-step2.md) |
| [listening-v2](listening-v2/) | 听力迁移、题目/原文/错题/进度 | [需求](listening-v2/01-requirements.md) · [设计](listening-v2/02-design.md) · [自省](listening-v2/99-self-review.md) |
| [listening-player](listening-player/) | Part 页改纯播放器、字幕、倍速、路由修复 | [需求](listening-player/01-requirements.md) · [设计](listening-player/02-design.md) · [自省](listening-player/99-self-review.md) |
| [speak-v2](speak-v2/) | 口语迁移、Realtime、WebRTC、90 天计划 | [自省](speak-v2/99-self-review.md) |
| [speak-15-15](speak-15-15/) | 口语 5+10+15、手动计划、场景题库、服务端时长、返回按钮 | [需求](speak-15-15/01-requirements.md) · [设计](speak-15-15/02-design.md) · [自省](speak-15-15/99-self-review.md) · [第二步需求](speak-15-15/01-requirements-step2.md) / [设计](speak-15-15/02-design-step2.md) / [自省](speak-15-15/99-self-review-step2.md) |
| [sync-v2](sync-v2/) | 同步引擎、合并语义、409 重试 | [需求](sync-v2/01-requirements.md) · [设计](sync-v2/02-design.md) · [自省](sync-v2/99-self-review.md) · [第二步自省](sync-v2/99-self-review-step2.md) |
| [dev-mode](dev-mode/) | 开发/测试模式：DEV 标识、AI 模拟、无外部调用 | [需求](dev-mode/01-requirements.md) · [设计](dev-mode/02-design.md) · [自省](dev-mode/99-self-review.md) |
| [auth-guard](auth-guard/) | 会话失效守卫：无 token/过期/401 全站回登录 | [需求](auth-guard/01-requirements.md) · [设计](auth-guard/02-design.md) · [自省](auth-guard/99-self-review.md) |
| [vocab-plan-fix](vocab-plan-fix/) | 词汇计划预览校验、按总数切分（每天差 ≤1） | [需求](vocab-plan-fix/01-requirements.md) · [设计](vocab-plan-fix/02-design.md) · [自省](vocab-plan-fix/99-self-review.md) |
| [mic-companion](mic-companion/) | 麦克风占用时的数字人面板与一键关闭麦克风 | [需求](mic-companion/01-requirements.md) · [设计](mic-companion/02-design.md) · [自省](mic-companion/99-self-review.md) |
| [speak-plan-select](speak-plan-select/) | 口语计划日历选日、入口与今日开口上移 | [需求](speak-plan-select/01-requirements.md) · [设计](speak-plan-select/02-design.md) · [自省](speak-plan-select/99-self-review.md) |
| [speak-free-mode](speak-free-mode/) | 无计划：隐藏 5/10/15 与计时，三个子页从题库自由练习 | [需求](speak-free-mode/01-requirements.md) · [设计](speak-free-mode/02-design.md) · [自省](speak-free-mode/99-self-review.md) |
| [user-menu](user-menu/) | 顶栏设置/管理/退出整合为下拉；首字母折叠与 DEV 保留 | [需求](user-menu/01-requirements.md) · [设计](user-menu/02-design.md) · [自省](user-menu/99-self-review.md) · [第二步自省](user-menu/99-self-review-step2.md) |
| [delete-plan-prominent](delete-plan-prominent/) | 词汇/阅读/口语「删除计划」改填充红按钮 | [需求](delete-plan-prominent/01-requirements.md) · [设计](delete-plan-prominent/02-design.md) · [自省](delete-plan-prominent/99-self-review.md) |
| [vocab-plan-quiz](vocab-plan-quiz/) | 词汇计划删除不复活；创建即生成四库题型、按天直接开练 | [需求](vocab-plan-quiz/01-requirements.md) · [设计](vocab-plan-quiz/02-design.md) · [自省](vocab-plan-quiz/99-self-review.md) |
| [vocab-quiz-resume](vocab-quiz-resume/) | 单词测验每题保存，刷新后从下一道未答题续做 | [需求](vocab-quiz-resume/01-requirements.md) · [设计](vocab-quiz-resume/02-design.md) · [自省](vocab-quiz-resume/99-self-review.md) |
| [vocab-plan-learn-test](vocab-plan-learn-test/) | 计划学习/测试分库；必默三型、其他两型；种子确定性出题；四库全完打勾 | [需求](vocab-plan-learn-test/01-requirements.md) · [设计](vocab-plan-learn-test/02-design.md) · [自省](vocab-plan-learn-test/99-self-review.md) |
| [vocab-random-learning](vocab-random-learning/) | 学习页签随机学习、自选考核方式；词库掌握度三类比例 | [需求](vocab-random-learning/01-requirements.md) · [设计](vocab-random-learning/02-design.md) · [自省](vocab-random-learning/99-self-review.md) |
| [vocab-plan-split-migration](vocab-plan-split-migration/) | 计划切分改回每库平均分到各天；felix 迁移数据核对 | [需求](vocab-plan-split-migration/01-requirements.md) · [设计](vocab-plan-split-migration/02-design.md) · [自省](vocab-plan-split-migration/99-self-review.md) |

> 当前产品能力以 [04 功能清单](../04-功能清单.md) 为准；这些目录记录「当时为什么这样做」。

## 会话交接

跨功能的收尾记录（本轮改了什么、验证结果、遗留项、环境备忘）放在
[2026-11-23-handoff.md](2026-11-23-handoff.md)。单项功能仍以上表目录为准。
