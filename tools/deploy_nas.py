#!/usr/bin/env python3
"""飞牛 NAS 生产部署（paramiko over SSH）

用法（在 pet-v2 根目录执行）：

    python tools/deploy_nas.py check    --host <NAS-IP>
    python tools/deploy_nas.py deploy   --host <NAS-IP>              # 构建前端 → 上传 → 备份 → 启动
    python tools/deploy_nas.py deploy   --host <NAS-IP> --with-audio # 首次部署/新增素材（带 85MB 音频）
    python tools/deploy_nas.py deploy   --host <NAS-IP> --skip-build # 复用现有 frontend/dist
    python tools/deploy_nas.py backup   --host <NAS-IP> --download   # 在线备份并拉回本机
    python tools/deploy_nas.py rollback --host <NAS-IP>              # 回滚 api 到上一个镜像 tag
    python tools/deploy_nas.py ps       --host <NAS-IP>
    python tools/deploy_nas.py restart  --host <NAS-IP>
    python tools/deploy_nas.py logs     --host <NAS-IP> -n 200

只部署生产环境：8088，/vol1/1000/docker/pet-v2，deploy/docker-compose.yml。
本地开发统一用 Docker：`python tools/dev.py up`（热重载，:5173 / :8000）。

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
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # pet-v2/
FRONTEND = ROOT / "frontend"
DIST = FRONTEND / "dist"
DEFAULT_REMOTE = "/vol1/1000/docker/pet-v2"
DEFAULT_PORT = 8088

EXCLUDE_DIRS = {
    ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", "node_modules", ".git", "htmlcov", ".idea", ".vscode",
}
EXCLUDE_SUFFIX = {
    ".pyc", ".pyo", ".db", ".db-shm", ".db-wal", ".db-journal",
    ".sqlite", ".sqlite3", ".log",
}
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


def _find_node_bin(name: str) -> str | None:
    """优先 PATH；Windows 的 fnm/nvm 常没加进 PATH，再找 Node 22 安装目录。"""
    found = shutil.which(name)
    if found:
        return found
    homes: list[Path] = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        homes.append(Path(appdata) / "fnm" / "node-versions")
    homes += [
        Path.home() / ".fnm" / "node-versions",
        Path.home() / ".nvm" / "versions" / "node",
    ]
    candidates: list[Path] = []
    for home in homes:
        for pattern in (
            f"v22*/installation/{name}.cmd",
            f"v22*/installation/bin/{name}",
            f"v22*/{name}.cmd",
            f"v22*/bin/{name}",
        ):
            candidates += list(home.glob(pattern))
    candidates.sort(reverse=True)  # 版本目录倒序，新的优先
    return str(candidates[0]) if candidates else None


def _run_npm(args: list[str]) -> None:
    npm = _find_node_bin("npm")
    if not npm:
        die("找不到 npm：确认 Node.js 22 已安装（支持 PATH / nvm / fnm）")
    info(f"使用 npm：{npm}")
    cmd = [npm, *args]
    if os.name == "nt" and Path(npm).suffix.lower() in (".cmd", ".bat"):
        cmd = ["cmd.exe", "/c", *cmd]
    # npm 脚本内部还会调 node；把自动找到的 Node 目录补进 PATH
    env = os.environ.copy()
    env["PATH"] = str(Path(npm).parent) + os.pathsep + env.get("PATH", "")
    print(f"   $ {' '.join(cmd)}")
    code = subprocess.call(cmd, cwd=str(FRONTEND), env=env)
    if code != 0:
        die(f"命令失败（退出码 {code}）：{' '.join(cmd)}")


def build_frontend() -> None:
    """发布前本地构建前端：先 vue-tsc，再清理 dist/assets，避免带上历史哈希文件。"""
    node = _find_node_bin("node")
    if node:
        try:
            ver = subprocess.check_output([node, "-v"], text=True).strip()
            if not ver.startswith("v22."):
                info(f"提示：当前 Node {ver}，前端构建/测试建议 Node 22")
        except (OSError, subprocess.SubprocessError):
            pass
    if not (FRONTEND / "node_modules").is_dir():
        info("安装前端依赖（npm ci）…")
        _run_npm(["ci"])
    info("构建前端（npm run build，先清理 dist/assets）…")
    _run_npm(["run", "build"])


def release_tag() -> str:
    sha = "nogit"
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT), text=True
        ).strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return f"{time.strftime('%Y%m%d-%H%M%S')}-{sha}"


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
            except Exception:  # noqa: BLE001,S110 - 密码写入失败不阻断，后续命令会暴露问题
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

    def compose(
        self,
        sub: str,
        timeout: int = 1800,
        stream: bool = True,
        env: dict[str, str] | None = None,
    ) -> tuple[int, str]:
        self.detect_docker()
        remote = shlex.quote(getattr(self, "remote", DEFAULT_REMOTE))
        prefix = " ".join(f"{k}={shlex.quote(v)}" for k, v in (env or {}).items())
        if prefix:
            prefix += " "
        inner = f"cd {remote}/deploy && {prefix}docker compose -f {self.compose_file} {sub}"
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


# ---------------------------------------------------------------- health / images
def wait_health(R: Runner, port: int, timeout: int = 120) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        _, out = R.sh(
            f"curl -fsS http://127.0.0.1:{port}/api/v1/healthz 2>/dev/null || true",
            timeout=15,
        )
        if "ok" in out.lower():
            ok(f"健康检查通过：{out.strip()}")
            return True
        time.sleep(3)
    return False


def prune_images(R: Runner, keep: int, current: str) -> None:
    """保留 current/latest + 最近 keep 个 tag，其余删除。"""
    if keep <= 0:
        return
    code, out = R.docker("images pet-api --format '{{.Tag}}'", timeout=60, stream=False)
    if code != 0:
        return
    tags = [t for t in out.split() if t and t != "<none>"]
    keep_set = {current, "latest", *tags[:keep]}
    removed = 0
    for tag in tags:
        if tag in keep_set:
            continue
        code, _ = R.docker(f"rmi pet-api:{shlex.quote(tag)}", timeout=60, stream=False)
        if code == 0:
            removed += 1
    if removed:
        info(f"已清理 {removed} 个旧镜像 tag")


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
        print(f"全部就绪 → python tools/deploy_nas.py deploy --host {args.host}")
    else:
        print("有未通过项，先补齐再 deploy。")


# ---------------------------------------------------------------- pack
def pack(dest: Path, with_audio: bool = False) -> Path:
    scope = "backend + frontend/dist" + (" + audio" if with_audio else "") + " + deploy"
    info(f"打包 {scope} …")
    for rel in PACK_INCLUDE:
        if not (ROOT / rel).exists():
            die(f"缺少 {rel}（前端未构建？先 cd frontend && npm run build）")

    def filt(ti: tarfile.TarInfo):
        p = Path(ti.name)
        if any(part in EXCLUDE_DIRS for part in p.parts):
            return None
        # 音频只在首次部署/新增素材时上传，避免每次发布重复传 85MB
        if p.parts[:3] == ("frontend", "dist", "audio") and not with_audio:
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
def _backup_code(keep: int) -> str:
    """容器内执行的 SQLite 在线备份。

    不依赖 app.maintenance：部署前容器里可能还是旧镜像，没有这个模块。
    """
    return (
        "import os,sqlite3,pathlib,time\n"
        "src = pathlib.Path('/app/data/pet.db')\n"
        "out = src.parent / 'backups' / ('pet-' + time.strftime('%Y%m%d-%H%M%S') + '.db')\n"
        "out.parent.mkdir(parents=True, exist_ok=True)\n"
        "s = sqlite3.connect(str(src)); t = sqlite3.connect(str(out))\n"
        "s.backup(t); t.close(); s.close()\n"
        "os.chmod(out, 0o600)\n"
        f"keep = {int(keep)}\n"
        "files = sorted(out.parent.glob('pet-*.db'))\n"
        "for old in files[:-keep] if keep > 0 else []:\n"
        "    old.unlink(missing_ok=True)\n"
        "print(out)\n"
    )


def _compose_backup(R: Runner, keep: int, stream: bool = False) -> tuple[int, str]:
    return R.compose(
        f"exec -T api python -c {shlex.quote(_backup_code(keep))}",
        timeout=300,
        stream=stream,
    )


def run_backup(R: Runner, keep: int = 14) -> bool:
    """在 api 容器内做一次 SQLite 在线备份；容器未运行时返回 False（首次部署）。"""
    code, out = R.compose("ps -q api", timeout=60, stream=False)
    if code != 0 or not out.strip():
        info("api 容器未运行，跳过部署前备份")
        return False
    code, out = _compose_backup(R, keep)
    if code != 0:
        die(f"部署前备份失败：{out.strip()[:300]}\n"
            "    确认 api 容器与 data/ 可写；确需跳过加 --skip-backup")
    last = out.strip().splitlines()[-1] if out.strip() else "备份完成"
    ok(f"部署前备份：{last}")
    return True


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
    writer = R.sudo if dir_sudo else R.sh

    tag = args.tag or release_tag()

    # 1. 本地构建前端（vue-tsc → 清理 dist/assets → vite build）
    if args.skip_build:
        info("--skip-build：复用现有 frontend/dist")
        if not DIST.is_dir():
            die("frontend/dist 不存在，去掉 --skip-build 重新构建")
    else:
        build_frontend()

    # 2. 打包 + 上传 + 解包（--skip-upload 时跳过，用于只重建镜像/重启）
    if args.skip_upload:
        info("--skip-upload：跳过打包上传，直接用 NAS 上已有代码")
    else:
        tar_local = ROOT / "_work" / "pet-v2-deploy.tar.gz"
        tar_local.parent.mkdir(parents=True, exist_ok=True)
        pack(tar_local, with_audio=args.with_audio)
        remote_tar = "/tmp/pet-v2-deploy.tar.gz"
        upload(cli, tar_local, remote_tar)

        info("远端解包 …")
        # 先删旧 hashed assets：index.html 只引用新文件，旧的留着只会越积越多。
        # dist/audio 是 85MB 素材，默认不随包上传，因此这里也不能动 audio/。
        code, out = writer(f"rm -rf {remote_q}/frontend/dist/assets")
        if code != 0:
            die(f"清理旧 assets 失败：{out[:300]}")
        # Windows 打包的条目 mode 常为 000，nginx(worker) 需要 r/x：统一 a+rX（目录加 x）
        extract = (f"tar xzf {remote_tar} -C {remote_q} && rm -f {remote_tar}"
                   f" && mkdir -p {remote_q}/data"
                   f" && chmod -R a+rX {remote_q}/frontend/dist {remote_q}/deploy"
                   # 递归 chmod 会把 .env 放开；首次部署时文件还不存在，失败忽略
                   f" && (chmod 600 {remote_q}/deploy/.env 2>/dev/null || true)")
        code, out = writer(extract)
        if code != 0:
            die(f"解包失败：{out[:400]}")
        ok("解包完成")
    writer(f"mkdir -p {remote_q}/data")

    # 3. deploy/.env —— 只生成一次，后续不覆盖（覆盖会导致已登录 token 全失效）
    env_path = f"{args.remote}/deploy/.env"
    _, out = writer(f"test -f {shlex.quote(env_path)} && echo EXISTS")
    if "EXISTS" not in out:
        secret = secrets.token_urlsafe(48)
        content = f"PET_JWT_SECRET={secret}\n"
        backup = ROOT / "_work" / "nas-jwt-secret.txt"
        py = ("import pathlib,sys;"
              f"p=pathlib.Path({env_path!r});"
              "p.write_text(sys.argv[1]);p.chmod(0o600)")
        code, out = writer(f"python3 -c {shlex.quote(py)} {shlex.quote(content)}")
        if code != 0:
            die(f"写 deploy/.env 失败：{out[:300]}")
        backup.write_text(content, encoding="utf-8")
        ok(f"已生成 deploy/.env（chmod 600），secret 备份于 _work/{backup.name}")
    else:
        ok("deploy/.env 已存在，保持不变")

    # 4. 部署前备份（alembic 迁移前留一份可回退快照）
    if args.skip_backup:
        info("--skip-backup：跳过部署前备份")
    else:
        run_backup(R)

    # 5. 构建镜像 + 启动，镜像按发布 tag 打标，便于回滚
    info(f"docker compose up -d --build（PET_TAG={tag}，首次 3~8 分钟）…")
    code, _ = R.compose("up -d --build", timeout=2400, stream=True, env={"PET_TAG": tag})
    if code != 0:
        die("compose 构建/启动失败，看上面日志")
    ok("容器已启动")

    # 6. 健康检查
    info(f"等待健康检查（:{args.http_port}）…")
    if not wait_health(R, args.http_port, timeout=180):
        R.compose("ps", timeout=60, stream=True)
        R.compose("logs --tail 60 api", timeout=120, stream=True)
        die("健康检查超时，看上面日志")

    # 7. latest 指向本次发布 + 清理旧镜像
    code, out = R.docker(f"tag pet-api:{shlex.quote(tag)} pet-api:latest", timeout=60)
    if code != 0:
        info(f"打 latest 失败：{out[:200]}")
    prune_images(R, args.keep_images, tag)

    _, out = R.compose("ps", timeout=60, stream=False)
    print("\n容器状态：\n" + out)
    print(f"\n本次发布：pet-api:{tag}")
    print(f"生产环境局域网访问：http://{args.host}:{args.http_port}")
    print(f"管理页：    http://{args.host}:{args.http_port}/admin")


def cmd_backup(args, R: Runner, cli) -> None:
    R.remote = args.remote
    R.detect_docker()
    code, out = _compose_backup(R, args.keep, stream=True)
    if code != 0:
        die("备份失败，确认 api 容器在运行（python tools/deploy_nas.py ps --host …）")
    ok("备份完成")

    if not args.download:
        return
    remote_q = shlex.quote(args.remote)
    _, out = R.sh(f"ls -1t {remote_q}/data/backups/pet-*.db 2>/dev/null | head -1")
    remote_path = out.strip()
    if not remote_path:
        _, out = R.sudo(f"ls -1t {remote_q}/data/backups/pet-*.db 2>/dev/null | head -1")
        remote_path = out.strip()
    if not remote_path:
        die(f"在 {args.remote}/data/backups 找不到备份文件")

    dest_dir = ROOT / "_work" / "backups"
    dest_dir.mkdir(parents=True, exist_ok=True)
    local = dest_dir / Path(remote_path).name
    sftp = cli.open_sftp()
    try:
        try:
            sftp.get(remote_path, str(local))
        except Exception:  # noqa: BLE001 - 文件属 root 时先拷到 /tmp 再取
            tmp = f"/tmp/{local.name}"
            code, _ = R.sudo(f"cp {shlex.quote(remote_path)} {tmp} && chmod 644 {tmp}")
            if code != 0:
                die("读取备份文件失败（sudo cp 失败）")
            sftp.get(tmp, str(local))
            # cp 用了 sudo，文件属 root；/tmp 有 sticky bit，必须 sudo 才能删
            R.sudo(f"rm -f {tmp}")
    finally:
        sftp.close()
    ok(f"已下载 {local.relative_to(ROOT)}（{human(local.stat().st_size)}）")


def cmd_rollback(args, R: Runner, cli) -> None:
    R.remote = args.remote
    R.detect_docker()

    if args.tag:
        target = args.tag
    else:
        _, out = R.docker("images pet-api --format '{{.Tag}}'", timeout=60, stream=False)
        # docker images 默认按创建时间倒序；排除 latest / <none>
        tags = [t for t in out.split() if t and t not in ("<none>", "latest")]
        current = ""
        _, cid = R.compose("ps -q api", timeout=60, stream=False)
        if cid.strip():
            _, img = R.docker(
                f"inspect --format '{{{{.Config.Image}}}}' {shlex.quote(cid.strip())}",
                timeout=60, stream=False,
            )
            current = img.strip().split(":")[-1]
        if current:
            candidates = [t for t in tags if t != current]
        else:
            # 容器没跑时无法判断当前版本，最新 tag 视为当前发布，取上一个
            candidates = tags[1:]
        if not candidates:
            die("没有可回滚的旧镜像 tag（至少发布过两次）")
        target = candidates[0]

    code, _ = R.docker(f"tag pet-api:{shlex.quote(target)} pet-api:latest", timeout=60)
    if code != 0:
        die(f"镜像 pet-api:{target} 不存在")
    info(f"回滚 api → pet-api:{target}")
    code, _ = R.compose("up -d --no-build", timeout=600, stream=True)
    if code != 0:
        die("回滚启动失败，看上面日志")
    if not wait_health(R, args.http_port, timeout=180):
        R.compose("logs --tail 60 api", timeout=120, stream=True)
        die("回滚后健康检查失败，检查数据库迁移是否兼容旧镜像")
    ok(f"已回滚到 pet-api:{target}")
    print("注意：只回滚了 api 镜像；frontend/dist 是 nginx 直接挂载的共享目录。"
          "\n      如需回滚前端，从对应 git 版本重新 build 后 deploy。")


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
    ap = argparse.ArgumentParser(description="飞牛 NAS 生产部署工具")
    ap.add_argument("action",
                    choices=["check", "deploy", "backup", "rollback", "ps", "restart", "logs"])
    ap.add_argument("--host", required=True, help="NAS 内网 IP")
    ap.add_argument("--port", type=int, default=22, help="SSH 端口")
    ap.add_argument("--user", default="admin")
    ap.add_argument("--password", help="不推荐明文；优先 NAS_PASS 环境变量或交互输入")
    ap.add_argument("--key", help="改用私钥登录")
    ap.add_argument("--remote", default=DEFAULT_REMOTE, help="远端项目目录")
    ap.add_argument("--http-port", type=int, default=DEFAULT_PORT,
                    help="宿主机 HTTP 端口（默认 8088）")
    ap.add_argument("--skip-upload", action="store_true",
                    help="跳过打包上传解包（NAS 上代码已就位，只重建/重启容器）")
    ap.add_argument("--skip-build", action="store_true", help="deploy: 跳过本地 npm run build")
    ap.add_argument("--skip-backup", action="store_true", help="deploy: 跳过部署前 SQLite 备份")
    ap.add_argument("--with-audio", action="store_true",
                    help="deploy: 一并上传 frontend/dist/audio（首次部署/新增素材，约 85MB）")
    ap.add_argument("--tag", help="deploy: 发布 tag（默认 时间戳-gitsha）；rollback: 目标 tag")
    ap.add_argument("--keep-images", type=int, default=3,
                    help="deploy: 保留最近几个旧镜像 tag（0=不清理，默认 3）")
    ap.add_argument("--keep", type=int, default=14, help="backup: 保留份数（默认 14）")
    ap.add_argument("--download", action="store_true", help="backup: 下载最新备份到 _work/backups")
    ap.add_argument("-n", type=int, default=200, help="logs 行数")
    args = ap.parse_args()

    cli, password = connect(args)
    R = Runner(cli, password)
    R.remote = args.remote
    try:
        {"check": lambda: cmd_check(args, R),
         "deploy": lambda: cmd_deploy(args, R, cli),
         "backup": lambda: cmd_backup(args, R, cli),
         "rollback": lambda: cmd_rollback(args, R, cli),
         "ps": lambda: cmd_ps(args, R),
         "restart": lambda: cmd_restart(args, R),
         "logs": lambda: cmd_logs(args, R)}[args.action]()
    finally:
        cli.close()


if __name__ == "__main__":
    main()
