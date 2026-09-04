# -*- coding: utf-8 -*-
"""一次性：上传带 /updates 路由的 app.py 到服务器并重启 personal-site。

用法:
    python scripts/deploy_updates_route.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# aliyun 目录在 PycharmProjects/ 下（computerAPP 的上级）
PROJECTS_DIR = os.path.dirname(os.path.dirname(ROOT))
ALIYUN_DIR = os.path.join(PROJECTS_DIR, "aliyun-118.178.193.189")
HOST = "118.178.193.189"
USER = "root"
REMOTE_APP = "/opt/personal-site/app.py"


def _load_password():
    env = os.environ.get("ROOT_PASSWORD")
    if env:
        return env
    env_file = os.path.join(ALIYUN_DIR, "secrets.env")
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("ROOT_PASSWORD="):
                    return line.split("=", 1)[1].strip()
    return None


def main():
    import hashlib
    import paramiko

    local_app = os.path.join(ALIYUN_DIR, "backend", "app.py")
    if not os.path.exists(local_app):
        print("找不到本地 backend/app.py", file=sys.stderr)
        sys.exit(2)

    password = _load_password()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"连接 {HOST} …")
    client.connect(HOST, username=USER, password=password, timeout=30, banner_timeout=30)
    sftp = client.open_sftp()

    def run(cmd):
        _, stdout, stderr = client.exec_command(cmd, timeout=120)
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
        if out.strip():
            print(out.rstrip())
        if err.strip():
            print("  (stderr) " + err.strip()[:400])
        return stdout.channel.recv_exit_status()

    # 上传并校验
    print(f"[sftp] app.py -> {REMOTE_APP}")
    sftp.put(local_app, REMOTE_APP)
    local_sha = hashlib.sha256(open(local_app, "rb").read()).hexdigest()
    print(f"本地 SHA  {local_sha}")
    print(run(f"sha256sum {REMOTE_APP}"))

    # 服务器上建 updates 目录 + 初步 health 检查
    run("mkdir -p /opt/personal-site/updates")
    run("chown site:site /opt/personal-site/updates")

    # 重启
    print("重启 personal-site …")
    run("systemctl restart personal-site")
    run("sleep 2 && systemctl is-active personal-site")

    # 自测
    run("curl -s -o /dev/null -w 'health HTTP %{http_code}\\n' http://127.0.0.1/health")
    run("curl -s -o /dev/null -w 'updates HTTP %{http_code}\\n' http://127.0.0.1/updates/update.json")
    # 测试更新路由是否连通（应 404，因为还没有文件，但路由生效说明 404 而非 500）
    run("curl -s -o /dev/null -w 'updates-route HTTP %{http_code} (404=路由生效)\\n' http://127.0.0.1/updates/nonexist.txt")

    sftp.close()
    client.close()
    print("\n部署完成")


if __name__ == "__main__":
    main()