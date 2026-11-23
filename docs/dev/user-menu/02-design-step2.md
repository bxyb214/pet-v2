# 顶栏用户菜单 · 第二步设计（首字母折叠）

## 1. 触发器结构

```text
[DEV] [头像 A]           ▾      开发环境（DEV 在左）
[头像 A] [admin]         ▾      正式环境 · 桌面
[头像 A]                 ▾      正式环境 · 手机（名称折叠）
[DEV] [头像 团]          ▾      中文名 + 开发环境 · 手机
```

- 头像永远存在，内容为 `initial`。
- 开发环境：**DEV 药丸在头像左侧** + 头像（不折叠）；不显示完整用户名；
  `gap: 10px`（手机 7px），保证两块不叠在一起。
- 正式环境：头像 + 完整名称；≤767px 时名称 `display:none`，头像即首字母。
- `title` 与 `aria-label` 使用完整 `userName`。

## 2. 首字母规则

```ts
const userName = computed(() => auth.displayName || auth.username || "学");
const initial = computed(() => {
  const ch = Array.from(userName.value)[0] ?? "学";
  return /^[a-z]$/.test(ch) ? ch.toUpperCase() : ch;
});
```

- `Array.from` 按 Unicode 码点取首字符，避免 emoji/代理对被截断。
- 英文小写转大写（felix → F）；中文保持首字（团小牛 → 团）。
- 空显示名/用户名回退「学」。

## 3. 响应式

| 视口 | 开发环境 | 正式环境 |
|---|---|---|
| ≥768px | DEV + A + ▾（约 150px，DEV/头像间距 10px） | A + 全名 + ▾（约 121px） |
| ≤767px | DEV + A + ▾（约 141px，间距 7px） | A + ▾（约 69px） |

- 旧规则 `.username { display:none }` 改名为 `.uname`，仅隐藏全名，不影响头像。
- DEV 药丸没有断点隐藏规则，任何宽度都完整保留。

## 4. 取舍

| 方案 | 结论 |
|---|---|
| 开发环境只显示 DEV | ❌ 看不出当前账号，且用户本次要求显示首字母 |
| 窄屏把名字截断成 `...` | ❌ 不如首字母可辨识 |
| 用 `name[0]` 取首字 | ❌ 代理对/emoji 会被截成半个字符 |
| **头像首字母 + DEV 保留（选定）** | ✅ 中英文都适用，窄屏最省空间 |

## 5. 测试

- `vue-tsc`、104 项单测、构建。
- 浏览器：开发/正式 × 桌面/手机 × 英文 admin/中文团小牛，检查 DEV 在头像左侧、间距 > 0（不重叠）、
  名称显隐、菜单与 title/aria 文案。
