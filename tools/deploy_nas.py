#!/usr/bin/env python3
"""飞牛 NAS 一键部署（paramiko over SSH）

用法（在 pet-v2 根目录执行）：

    # 生产（默认 profile=prod，8088，/vol1/1000/docker/pet-v2）
    python tools/deploy_nas.py check   --host <NAS-IP>
    python tools/deploy_nas.py deploy  --host <NAS-IP>
    python tools/deploy_nas.py ps      --host <NAS-IP>
    python tools/deploy_nas.py restart --host <NAS-IP>
    python tools/deploy_nas.py logs    --host <NAS-IP> -n 200

    # 开发/预发布（8089，/vol1/1000/docker/pet-v2-dev，PET_DEV_MODE=1）
    python tools/deploy_nas.py deploy  --host <NAS-IP> --profile dev
    python tools/deploy_nas.py ps      --host <NAS-IP> --profile dev

密码来源优先级：--password > 环境变量 NAS_PASS > 交互输入（不回显）。
凭据绝不写进本文件、也不进 git；本机存在 ../nas-credentials.md（仓库外）。

实测环境（2026-11-22）：fnOS / Debian 12，Docker 28.5.2 + compose v2.40.3；
admin 访问 docker.sock 需要 sudo（不在 docker 组），/vol1/1000/docker 可直接写。
"""

from __future__ import annotations

import argparse
import getpass
import os
import secrets
import shlex
import sys
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # pet-v2/
DEFAULT_REMOTE = "/vol1/1000/docker/pet-v2"
DEFAULT_REMOTE_DEV = "/vol1/1000/docker/pet-v2-dev"
DEFAULT_PORT = 8088
DEFAULT_PORT_DEV = 8089

EXCLUDE_DIRS = {
    ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", "node_modules", ".git", "htmlcov", ".idea", ".vscode",
}
EXCLUDE_SUFFIX = {".pyc", ".pyo", ".db", ".db-shm", ".db-wal", ".log"}
# .env 含 JWT secret，绝不随包上传（远端已有 .env 时保留原文件）
EXCLUDE_NAMES = {".DS_Store", "Thumbs.db", ".coverage", "smoke.db", ".env"}

PACK_INCLUDE = ["backend", "frontend/dist", "deploy"]

# fnOS 上 admin 没有 /home/admin，每条命令都会带这行噪音
NOISE = ("Could not chdir to home directory",)


def die(msg: str) -> None:
    print(f"\n[×] {msg}", file=sys.stderr)
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"[✓] {msg}")


def info(msg: str) -> None:
    print(f"[·] {msg}")


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def clean(text: str) -> str:
    lines = [ln for ln in text.splitlines() if not any(n in ln for n in NOISE)]
    return "\n".join(lines).strip()


# ---------------------------------------------------------------- runner
class Runner:
    """封装远端执行：普通命令 / sudo / docker（自动判定是否需要 sudo）。"""

    def __init__(self, cli, password: str):
        self.cli = cli
        self.password = password
        self.remote = DEFAULT_REMOTE
        self.compose_file = "docker-compose.yml"
        self.docker_as_sudo = False
        self._docker_checked = False

    def _say(self, line: str) -> None:
        if not line or any(n in line for n in NOISE):
            return
        if self.password and self.password in line:
            line = line.replace(self.password, "******")
        print("   " + line)

    def _exec(self, cmd: str, timeout: int, sudo: bool, stream: bool) -> tuple[int, str]:
        if sudo:
            cmd = f"sudo -S -p '' sh -c {shlex.quote(cmd)}"
        # 不用 pty：docker 退化成 plain 输出，密码也不会被回显
        stdin, stdout, stderr = self.cli.exec_command(cmd, timeout=timeout, get_pty=False)
        chan = stdout.channel
        if sudo and self.password:
            try:
                stdin.write(self.password + "\n")
                stdin.flush()
            except Exception:  # noqa: BLE001
                pass

        # 非流式：先等退出码，再读缓冲（实测这样读最可靠，直接 recv 轮询会漏数据）
        if not stream:
            code = chan.recv_exit_status()
            # 必须用换行拼接：stdout 末尾常常没有 \n，直接相连会把两段粘成一行，
            # 于是整行都命中 NOISE 被过滤掉（曾经的“返回空”事故）
            text = clean(stdout.read().decode("utf-8", "replace")
                         + "\n" + stderr.read().decode("utf-8", "replace"))
            if self.password:
                text = text.replace(self.password, "******")
            return code, text

        # 流式：边收边打；exit_status 可能比输出先到，留 0.4s 宽限再收尾
        out_buf: list[bytes] = []
        err_buf: list[bytes] = []
        pending = ""
        deadline = time.time() + timeout
        exited_at: float | None = None

        while True:
            got = False
            while chan.recv_ready():
                data = chan.recv(65536)
                out_buf.append(data)
                got = True
                pending += data.decode("utf-8", "replace")
                *lines, pending = pending.split("\n")
                for ln in lines:
                    self._say(ln)
            while chan.recv_stderr_ready():
                err_buf.append(chan.recv_stderr(65536))
                got = True
            if chan.exit_status_ready():
                if exited_at is None:
                    exited_at = time.time()
                elif time.time() - exited_at > 0.4 and not chan.recv_ready():
                    break
            if time.time() > deadline:
                break
            if not got:
                time.sleep(0.03)

        # 收尾：把可能还在缓冲里的尾巴读干净
        tail = stdout.read().decode("utf-8", "replace")
        if tail:
            pending += tail
            *lines, pending = pending.split("\n")
            for ln in lines:
                self._say(ln)
        if pending:
            self._say(pending)
        leftover_err = stderr.read().decode("utf-8", "replace")
        code = chan.recv_exit_status()
        text = clean(
            b"".join(out_buf).decode("utf-8", "replace") + tail
            + "\n" + b"".join(err_buf).decode("utf-8", "replace") + leftover_err
        )
        if self.password:
            text = text.replace(self.password, "******")
        return code, text

    def sh(self, cmd: str, timeout: int = 180, stream: bool = False) -> tuple[int, str]:
        return self._exec(cmd, timeout, False, stream)

    def sudo(self, cmd: str, timeout: int = 900, stream: bool = False) -> tuple[int, str]:
        return self._exec(cmd, timeout, True, stream)

    def docker(self, sub: str, timeout: int = 900, stream: bool = False) -> tuple[int, str]:
        if self.docker_as_sudo:
            return self.sudo(f"docker {sub}", timeout, stream)
        return self.sh(f"docker {sub}", timeout, stream)

    def compose(self, sub: str, timeout: int = 1800, stream: bool = True) -> tuple[int, str]:
        self.detect_docker()
        remote = shlex.quote(getattr(self, "remote", DEFAULT_REMOTE))
        inner = f"cd {remote}/deploy && docker compose -f {self.compose_file} {sub}"
        # sudo() 内部已用 sh -c 包了一层，cd 这类内建命令可以直接用
        if self.docker_as_sudo:
            return self.sudo(inner, timeout, stream)
        return self.sh(inner, timeout, stream)

    def detect_docker(self) -> None:
        if self._docker_checked:
            return
        self._docker_checked = True
        code, _ = self.sh("docker info >/dev/null 2>&1 && echo DIRECT_OK")
        if code == 0:
            self.docker_as_sudo = False
            ok("docker 免 sudo 可访问")
            return
        code, _ = self.sudo("docker info >/dev/null 2>&1 && echo SUDO_OK")
        if code == 0:
            self.docker_as_sudo = True
            ok("docker 需 sudo（admin 不在 docker 组，sudo 已确认可用）")
        else:
            die("docker 守护进程不可访问（sudo 也不行），检查 Docker 服务是否启动")


# ---------------------------------------------------------------- connect
def connect(args):
    try:
        import paramiko
    except ImportError:
        die("缺少 paramiko：pip install paramiko")

    password = args.password or os.environ.get("NAS_PASS")
    if not password and not args.key:
        password = getpass.getpass(f"{args.user}@{args.host} 的 SSH 密码：")

    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    info(f"连接 {args.user}@{args.host}:{args.port} …")
    try:
        cli.connect(
            hostname=args.host, port=args.port, username=args.user,
            password=password, key_filename=args.key,
            timeout=15, banner_timeout=20, auth_timeout=20,
            look_for_keys=False, allow_agent=False,
        )
    except Exception as exc:  # noqa: BLE001
        die(f"SSH 连接失败：{exc}")
    ok("SSH 已连接")
    return cli, (password or "")


# ---------------------------------------------------------------- check
def cmd_check(args, R: Runner) -> None:
    checks: list[tuple[str, bool, str]] = []

    code, out = R.sh("uname -r && . /etc/os-release && echo $PRETTY_NAME")
    checks.append(("系统", code == 0, out.replace("\n", " · ")))

    code, out = R.sh("docker --version")
    checks.append(("Docker", code == 0, out or "未安装"))

    code, out = R.sh("docker compose version")
    checks.append(("compose", code == 0, out or "未安装"))

    R.detect_docker()
    checks.append(("docker.sock", True, "需 sudo" if R.docker_as_sudo else "免 sudo"))

    code, out = R.sh("id")
    checks.append(("用户", code == 0, out))

    probe = f"{args.remote}/.probe"
    code, out = R.sh(f"mkdir -p {shlex.quote(args.remote)} && touch {probe} && rm -f {probe} && echo WRITABLE")
    writable = code == 0 and "WRITABLE" in out
    checks.append(("目标目录", writable, args.remote + ("" if writable else "（不可写，将用 sudo）")))

    code, out = R.sh(f"df -h {shlex.quote(args.remote)} 2>/dev/null | tail -1 | awk '{{print $4\" 可用 / \"$6}}'")
    checks.append(("磁盘", code == 0, out))

    code, out = R.sh("date '+%F %T %Z'")
    checks.append(("时区", code == 0, out))

    code, out = R.sh("free -m | awk 'NR==2{print $2\"MB 总 / \"$7\"MB 可用\"}'")
    checks.append(("内存", code == 0, out))

    print("\n" + "=" * 72)
    for name, good, detail in checks:
        print(f"{'✓' if good else '×'} {name:<12} {detail}")
    print("=" * 72)
    if all(g for _, g, _ in checks):
        print(f"全部就绪 → python tools/deploy_nas.py deploy --host {args.host} --profile {args.profile}")
    else:
        print("有未通过项，先补齐再 deploy。")


# ---------------------------------------------------------------- pack
def pack(dest: Path) -> Path:
    info("打包 backend + frontend/dist + deploy …")
    for rel in PACK_INCLUDE:
        if not (ROOT / rel).exists():
            die(f"缺少 {rel}（前端未构建？先 cd frontend && npm run build）")

    def filt(ti: tarfile.TarInfo):
        p = Path(ti.name)
        if any(part in EXCLUDE_DIRS for part in p.parts):
            return None
        if p.suffix in EXCLUDE_SUFFIX or p.name in EXCLUDE_NAMES:
            return None
        return ti

    with tarfile.open(dest, "w:gz", compresslevel=6) as tf:
        for rel in PACK_INCLUDE:
            tf.add(ROOT / rel, arcname=rel, filter=filt)
    ok(f"打包完成 {dest.name}  {human(dest.stat().st_size)}")
    return dest


def upload(cli, local: Path, remote_tmp: str) -> None:
    info(f"上传 → {remote_tmp}")
    sftp = cli.open_sftp()
    total = local.stat().st_size
    state = {"t": 0.0}

    def cb(done: int, _total: int) -> None:
        now = time.time()
        if now - state["t"] >= 2 or done >= total:
            state["t"] = now
            print(f"   {done * 100 / total:5.1f}%  {human(done)} / {human(total)}")

    sftp.put(str(local), remote_tmp, callback=cb)
    sftp.close()
    ok(f"上传完成（{human(total)}）")


# ---------------------------------------------------------------- deploy
def cmd_deploy(args, R: Runner, cli) -> None:
    R.remote = args.remote
    code, _ = R.sh("docker --version")
    if code != 0:
        die("NAS 上 Docker 不可用，先在飞牛应用中心安装 Docker")
    R.detect_docker()

    remote_q = shlex.quote(args.remote)
    code, _ = R.sh(f"mkdir -p {remote_q} && touch {remote_q}/.probe && rm -f {remote_q}/.probe")
    dir_sudo = code != 0
    if dir_sudo:
        info(f"{args.remote} 需 sudo 写入")

    # 1. 打包 + 上传 + 解包（--skip-upload 时跳过，用于只重启/重建镜像）
    profile_tag = "" if args.profile == "prod" else f"-{args.profile}"
    if args.skip_upload:
        info("--skip-upload：跳过打包上传，直接用 NAS 上已有代码")
    else:
        tar_local = ROOT / "_work" / f"pet-v2-deploy{profile_tag}.tar.gz"
        tar_local.parent.mkdir(parents=True, exist_ok=True)
        pack(tar_local)
        remote_tar = f"/tmp/pet-v2-deploy{profile_tag}.tar.gz"
        upload(cli, tar_local, remote_tar)

        info("远端解包 …")
        # Windows 打包的条目 mode 常为 000，nginx(worker) 需要 r/x：统一 a+rX（目录加 x）
        extract = (f"tar xzf {remote_tar} -C {remote_q} && rm -f {remote_tar}"
                   f" && mkdir -p {remote_q}/data"
                   f" && chmod -R a+rX {remote_q}/frontend/dist")
        code, out = R.sudo(extract) if dir_sudo else R.sh(extract)
        if code != 0:
            die(f"解包失败：{out[:400]}")
        ok("解包完成")
    R.sh(f"mkdir -p {remote_q}/data")

    # 3. deploy/.env —— 只生成一次，后续不覆盖（覆盖会导致已登录 token 全失效）
    env_path = f"{args.remote}/deploy/.env"
    _, out = R.sh(f"test -f {shlex.quote(env_path)} && echo EXISTS")
    if "EXISTS" not in out:
        secret = secrets.token_urlsafe(48)
        if args.profile == "dev":
            content = (f"PET_JWT_SECRET={secret}\n"
                       "PET_DEV_MODE=1\n"
                       f"PET_DEV_PORT={args.http_port}\n")
            backup = ROOT / "_work" / "nas-dev-jwt-secret.txt"
        else:
            content = f"PET_JWT_SECRET={secret}\n"
            backup = ROOT / "_work" / "nas-jwt-secret.txt"
        py = ("import pathlib,sys;"
              f"p=pathlib.Path({env_path!r});"
              "p.write_text(sys.argv[1]);p.chmod(0o600)")
        writer = R.sudo if dir_sudo else R.sh
        code, out = writer(f"python3 -c {shlex.quote(py)} {shlex.quote(content)}")
        if code != 0:
            die(f"写 deploy/.env 失败：{out[:300]}")
        backup.write_text(content, encoding="utf-8")
        ok(f"已生成 deploy/.env（chmod 600），secret 备份于 _work/{backup.name}")
    else:
        ok("deploy/.env 已存在，保持不变")

    # 4. 构建 + 启动
    info(f"docker compose -f {args.compose_file} up -d --build（首次 3~8 分钟）…")
    code, _ = R.compose("up -d --build", timeout=2400, stream=True)
    if code != 0:
        die("compose 构建/启动失败，看上面日志")
    ok("容器已启动")

    # 5. 健康检查
    info(f"等待健康检查（:{args.http_port}）…")
    healthy = False
    for _ in range(40):
        _, out = R.sh(f"curl -fsS http://127.0.0.1:{args.http_port}/api/v1/healthz 2>/dev/null || true")
        if "ok" in out.lower():
            ok(f"健康检查通过：{out.strip()}")
            healthy = True
            break
        time.sleep(3)
    if not healthy:
        R.compose("ps", timeout=60, stream=True)
        R.compose("logs --tail 60 api", timeout=120, stream=True)
        die("健康检查超时，看上面日志")

    _, out = R.compose("ps", timeout=60, stream=False)
    print("\n容器状态：\n" + out)
    env_label = "开发环境" if args.profile == "dev" else "生产环境"
    print(f"\n{env_label}（{args.profile}）局域网访问：http://{args.host}:{args.http_port}")
    print(f"管理页：    http://{args.host}:{args.http_port}/admin")


def cmd_ps(args, R: Runner) -> None:
    R.remote = args.remote
    _, out = R.compose("ps", timeout=60, stream=False)
    print(out)
    _, out = R.sh(f"curl -fsS http://127.0.0.1:{args.http_port}/api/v1/healthz || echo 'healthz FAIL'")
    print("healthz:", out)


def cmd_restart(args, R: Runner) -> None:
    R.remote = args.remote
    code, out = R.compose("restart", timeout=300, stream=True)
    ok("已重启") if code == 0 else die(out[:300])


def cmd_logs(args, R: Runner) -> None:
    R.remote = args.remote
    try:
        R.compose(f"logs --tail {args.n} -f", timeout=3600, stream=True)
    except KeyboardInterrupt:
        print("\n已断开会话")


# ---------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(description="飞牛 NAS 部署工具")
    ap.add_argument("action", choices=["check", "deploy", "ps", "restart", "logs"])
    ap.add_argument("--host", required=True, help="NAS 内网 IP")
    ap.add_argument("--port", type=int, default=22, help="SSH 端口")
    ap.add_argument("--user", default="admin")
    ap.add_argument("--password", help="不推荐明文；优先 NAS_PASS 环境变量或交互输入")
    ap.add_argument("--key", help="改用私钥登录")
    ap.add_argument("--profile", choices=["prod", "dev"], default="prod",
                    help="prod=生产（8088，目录 pet-v2）；dev=开发（8089，目录 pet-v2-dev）")
    ap.add_argument("--remote", default=None, help="远端项目目录（默认按 profile 推断）")
    ap.add_argument("--http-port", type=int, default=None,
                    help="宿主机 HTTP 端口（默认 prod=8088 / dev=8089）")
    ap.add_argument("--skip-upload", action="store_true",
                    help="跳过打包上传解包（NAS 上代码已就位，只重建/重启容器）")
    ap.add_argument("-n", type=int, default=200, help="logs 行数")
    args = ap.parse_args()

    # profile 决定目录、compose 文件、端口；显式参数优先
    if args.profile == "dev":
        args.remote = args.remote or DEFAULT_REMOTE_DEV
        args.compose_file = "docker-compose.dev.yml"
        args.http_port = args.http_port or DEFAULT_PORT_DEV
    else:
        args.remote = args.remote or DEFAULT_REMOTE
        args.compose_file = "docker-compose.yml"
        args.http_port = args.http_port or DEFAULT_PORT

    cli, password = connect(args)
    R = Runner(cli, password)
    R.remote = args.remote
    R.compose_file = args.compose_file
    try:
        {"check": lambda: cmd_check(args, R),
         "deploy": lambda: cmd_deploy(args, R, cli),
         "ps": lambda: cmd_ps(args, R),
         "restart": lambda: cmd_restart(args, R),
         "logs": lambda: cmd_logs(args, R)}[args.action]()
    finally:
        cli.close()


if __name__ == "__main__":
    main()
