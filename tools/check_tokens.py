"""检查前端引用的 CSS 变量是否都有定义。

CSS 变量写错不会报错，浏览器只会静默忽略整条声明——曾经因此让口语页的
90 天日历、听力选项丢掉底色和圆角，肉眼很难定位。改动 tokens.css 后跑一遍：

    python tools/check_tokens.py

规则：
- 定义来源：frontend/src/tokens.css 的 :root 块；
- 允许「带兜底值」的引用（var(--x, #fff)）——兜底生效，不算错误，只提示；
- 其余未定义引用视为错误，退出码 1。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "frontend" / "src"
TOKENS = SRC / "tokens.css"

VAR_USE = re.compile(r"var\(\s*(--[a-zA-Z0-9-]+)\s*(,)?")
DEFINE = re.compile(r"^\s*(--[a-zA-Z0-9-]+)\s*:", re.M)


def defined() -> set[str]:
    text = TOKENS.read_text(encoding="utf-8")
    # 只取 :root 块，避免把组件里的局部变量误当成全局定义
    m = re.search(r":root\s*\{(.*?)\n\}", text, re.S)
    return set(DEFINE.findall(m.group(1) if m else text))


def main() -> int:
    known = defined()
    errors: list[str] = []
    soft: list[str] = []

    files = [*SRC.rglob("*.vue"), *SRC.rglob("*.css")]
    for f in files:
        rel = f.relative_to(ROOT)
        for lineno, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for name, has_fallback in VAR_USE.findall(line):
                if name in known:
                    continue
                msg = f"{rel}:{lineno}  var({name})"
                (soft if has_fallback else errors).append(msg)

    if soft:
        print(f"[提示] {len(soft)} 处引用了未定义变量但有兜底值：")
        for m in soft[:10]:
            print("   -", m)

    if errors:
        print(f"[错误] {len(errors)} 处引用了未定义变量且无兜底：")
        for m in errors:
            print("   -", m)
        return 1

    print(f"[OK] 变量引用全部有定义（检查 {len(files)} 个文件，{len(known)} 个 token）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
