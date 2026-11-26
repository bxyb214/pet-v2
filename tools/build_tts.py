"""本地 TTS 预生成：把词库/阅读/口语固定文本灌进 data/tts 缓存。

只依赖标准库；通过 HTTP 调生产 API，走与前端完全相同的规范化与缓存键。
建议用管理员账号（跳过每用户限流），在低峰期串行执行。

用法：
  python tools/build_tts.py --base http://192.168.1.10:8088 \
      --user admin --password-env PET_ADMIN_PASS --tier A
  python tools/build_tts.py --base ... --check        # 只查命中率，不合成
  python tools/build_tts.py --base ... --dry          # 只打印统计
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "frontend" / "public" / "data"
WORK = ROOT / "_work"
CJK = re.compile(r"[㐀-䶿一-鿿豈-﫿]")
SPACE = re.compile(r"\s+")

MAX_TEXT = 300


def english_only(text: object) -> str:
    if not isinstance(text, str):
        return ""
    m = CJK.search(text)
    s = (text[: m.start()] if m else text).strip()
    return SPACE.sub(" ", s)


def add(target: list[str], seen: set[str], text: object, max_chars: int, skipped: list[str]) -> None:
    s = english_only(text)
    if len(s) < 3:
        return
    if len(s) > max_chars:
        skipped.append(s)
        return
    if s in seen:
        return
    seen.add(s)
    target.append(s)


def load_json(name: str):
    with (DATA / name).open(encoding="utf-8") as fh:
        return json.load(fh)


def collect(max_chars: int, skipped: list[str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {
        "words": [],
        "examples": [],
        "reading": [],
        "speak_core": [],
        "speak_extra": [],
    }
    seen: dict[str, set[str]] = {k: set() for k in groups}

    banks = load_json("banks.json")
    for items in (banks.get("banks") or {}).values():
        for w in items or []:
            add(groups["words"], seen["words"], w.get("en"), max_chars, skipped)
            add(groups["examples"], seen["examples"], w.get("example"), max_chars, skipped)

    reading = load_json("reading.json")
    for test in reading.get("tests") or []:
        for part in test.get("parts") or []:
            for sent in part.get("sentences") or []:
                add(groups["reading"], seen["reading"], sent.get("en"), max_chars, skipped)

    speak = load_json("speak.json")
    for item in speak.get("shadow") or []:
        add(groups["speak_core"], seen["speak_core"], item.get("en"), max_chars, skipped)
    for item in speak.get("free") or []:
        add(groups["speak_core"], seen["speak_core"], item.get("en"), max_chars, skipped)

    for scene in speak.get("scenes") or []:
        for opener in scene.get("openers") or []:
            text = opener.get("en") if isinstance(opener, dict) else opener
            add(groups["speak_extra"], seen["speak_extra"], text, max_chars, skipped)
        for make in scene.get("make") or []:
            if isinstance(make, dict):
                add(groups["speak_extra"], seen["speak_extra"], make.get("answer"), max_chars, skipped)
    for pattern in speak.get("patterns") or []:
        for item in pattern.get("items") or []:
            add(groups["speak_extra"], seen["speak_extra"], item.get("en"), max_chars, skipped)
    for item in speak.get("part1bank") or []:
        add(groups["speak_extra"], seen["speak_extra"], item.get("ans"), max_chars, skipped)
    for item in speak.get("essays") or []:
        add(groups["speak_extra"], seen["speak_extra"], item.get("ans"), max_chars, skipped)
    return groups


def request(
    method: str, url: str, token: str = "", payload: dict | None = None, timeout: float = 90.0
) -> tuple[int, bytes]:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        return 0, str(exc).encode()


class Client:
    def __init__(self, base: str, timeout: float) -> None:
        self.base = base.rstrip("/")
        self.timeout = timeout
        self.token = ""
        self.refresh = ""

    def login(self, user: str, password: str) -> None:
        status, body = request(
            "POST",
            f"{self.base}/api/v1/auth/login",
            payload={"username": user, "password": password},
            timeout=self.timeout,
        )
        if status != 200:
            raise SystemExit(f"登录失败（HTTP {status}）：{body[:200].decode(errors='replace')}")
        data = json.loads(body)
        self.token = data["access_token"]
        self.refresh = data.get("refresh_token", "")
        if not data.get("is_admin"):
            print("警告：该账号不是管理员，POST 会受每用户 30 次/分钟限流。", file=sys.stderr)

    def _refresh(self) -> bool:
        if not self.refresh:
            return False
        status, body = request(
            "POST",
            f"{self.base}/api/v1/auth/refresh",
            payload={"refresh_token": self.refresh},
            timeout=self.timeout,
        )
        if status != 200:
            return False
        data = json.loads(body)
        self.token = data["access_token"]
        self.refresh = data.get("refresh_token", self.refresh)
        return True

    def call(self, method: str, path: str, payload: dict | None = None) -> tuple[int, bytes]:
        status, body = request(method, f"{self.base}{path}", self.token, payload, self.timeout)
        if status == 401 and self._refresh():
            status, body = request(method, f"{self.base}{path}", self.token, payload, self.timeout)
        return status, body


def config(c: Client) -> dict:
    status, body = request("GET", f"{c.base}/api/v1/speak/tts/config", timeout=c.timeout)
    if status != 200:
        raise SystemExit(f"读取 /speak/tts/config 失败（HTTP {status}）")
    return json.loads(body)


def main() -> int:
    ap = argparse.ArgumentParser(description="预生成本地 TTS 缓存")
    ap.add_argument("--base", default="http://127.0.0.1:8088")
    ap.add_argument("--user", default="")
    ap.add_argument("--password", default="")
    ap.add_argument("--password-env", default="PET_ADMIN_PASS")
    ap.add_argument("--tier", choices=["A", "B", "all"], default="A")
    ap.add_argument(
        "--only",
        default="",
        help="只处理指定组：words,examples,reading,speak_core,speak_extra（逗号分隔）",
    )
    ap.add_argument("--check", action="store_true", help="只 GET 检查命中率，不合成")
    ap.add_argument("--dry", action="store_true", help="只打印统计，不发请求")
    ap.add_argument("--concurrency", type=int, default=1, help="保留参数；sidecar 串行，建议 1")
    ap.add_argument("--delay", type=float, default=0.12, help="每条之间的间隔秒数（避开 nginx 限流）")
    ap.add_argument("--timeout", type=float, default=90.0)
    args = ap.parse_args()

    c = Client(args.base, args.timeout)
    try:
        cfg = config(c)
    except SystemExit as exc:
        if not args.dry:
            raise
        cfg = {}
        print(f"提示：服务不可用（{exc}），按默认 300 字统计。", file=sys.stderr)
    if cfg and not cfg.get("enabled"):
        print("提示：speak.local.enabled=false。预生成仍会失败；请先在管理页开启。", file=sys.stderr)
    max_chars = int(cfg.get("max_chars", MAX_TEXT))
    skipped: list[str] = []
    groups = collect(max_chars, skipped)

    if args.only:
        wanted = [x.strip() for x in args.only.split(",") if x.strip()]
    elif args.tier == "A":
        wanted = ["words", "reading", "speak_core"]
    elif args.tier == "B":
        wanted = ["words", "reading", "speak_core", "examples"]
    else:
        wanted = list(groups)

    unknown = [x for x in wanted if x not in groups]
    if unknown:
        raise SystemExit(f"未知分组：{', '.join(unknown)}")
    texts: list[str] = []
    seen: set[str] = set()
    for name in wanted:
        for text in groups[name]:
            if text not in seen:
                seen.add(text)
                texts.append(text)

    chars = sum(len(t) for t in texts)
    estimate_mb = chars * 2940 / 1e6
    print(
        f"分组：{', '.join(wanted)} | {len(texts)} 条 / {chars} 字符 "
        f"| 约 {estimate_mb:.0f} MB WAV | 跳过超长 {len(skipped)} 条"
    )
    if args.dry:
        return 0

    if not args.check:
        password = args.password or os.environ.get(args.password_env, "")
        if not args.user or not password:
            raise SystemExit("需要 --user 与 --password/--password-env 才能合成")
        c.login(args.user, password)

    path = cfg.get("path", "/api/v1/speak/tts/local")
    version = cfg.get("cache_version", "")
    ok = fail = hit = 0
    failures: list[str] = []
    started = time.monotonic()
    for i, text in enumerate(texts, 1):
        if args.check:
            q = urllib.parse.urlencode({"text": text, "v": version})
            status, _ = request("GET", f"{c.base}{path}?{q}", timeout=args.timeout)
            if status == 200:
                hit += 1
            elif status == 404:
                fail += 1
            else:
                failures.append(f"HTTP {status}: {text[:60]}")
                fail += 1
        else:
            status, body = c.call("POST", path, {"text": text})
            if status == 200:
                ok += 1
            elif status == 429:
                time.sleep(2.0)
                status, body = c.call("POST", path, {"text": text})
                if status == 200:
                    ok += 1
                else:
                    fail += 1
                    failures.append(f"HTTP {status}: {text[:60]}")
            else:
                fail += 1
                failures.append(f"HTTP {status}: {text[:60]}")
        if i % 25 == 0 or i == len(texts):
            print(f"  {i}/{len(texts)}  ok={ok} hit={hit} fail={fail}", flush=True)
        if args.delay:
            time.sleep(args.delay)

    elapsed = time.monotonic() - started
    report = {
        "base": c.base,
        "tier": args.tier,
        "only": wanted,
        "count": len(texts),
        "chars": chars,
        "ok": ok,
        "hit": hit,
        "fail": fail,
        "skipped_too_long": len(skipped),
        "elapsed_sec": round(elapsed, 1),
        "failures": failures[:50],
    }
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "tts_warm_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"完成：{'命中' if args.check else '合成'} {ok + hit}，失败 {fail}，耗时 {elapsed:.0f}s")
    print(f"报告：{WORK / 'tts_warm_report.json'}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
