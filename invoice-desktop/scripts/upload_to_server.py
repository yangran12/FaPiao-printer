# -*- coding: utf-8 -*-
"""把 server-payload/ 里的更新包上传到阿里云服务器 /opt/personal-site/updates/。

用法:
    python scripts/upload_to_server.py

依赖: paramiko（本机已装）；凭据从 ../../aliyun-118.178.193.189/secrets.env 读取。
"""
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECTS_DIR = os.path.dirname(os.path.dirname(ROOT))
SERVER_DIR = os.path.join(os.path.dirname(ROOT), "server-payload")   # computerAPP/server-payload
ALIYUN_DIR = os.path.join(PROJECTS_DIR, "aliyun-118.178.193.189")     # PycharmProjects/aliyun-...

HOST = "118.178.193.189"
USER = "root"
REMOTE_UPDATES_DIR = "/opt/personal-site/updates"


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
    import paramiko

    password = _load_password()
    if not password:
        print("缺少 ROOT_PASSWORD（secrets.env），无法连接服务器。", file=sys.stderr)
        sys.exit(2)

    if not os.path.isdir(SERVER_DIR):
        print(f"没有 {SERVER_DIR}，请先运行 make_update_manifest.py", file=sys.stderr)
        sys.exit(2)

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

    # 建目录
    run(f"mkdir -p {REMOTE_UPDATES_DIR}")

    # 上传所有文件（update.json + exe）
    for fname in sorted(os.listdir(SERVER_DIR)):
        local = os.path.join(SERVER_DIR, fname)
        if os.path.isfile(local):
            remote = f"{REMOTE_UPDATES_DIR}/{fname}"
            print(f"[sftp] {fname}")
            sftp.put(local, remote)

    # 设置属主 readable
    run(f"chown -R root:root {REMOTE_UPDATES_DIR}")
    run(f"chmod -R 644 {REMOTE_UPDATES_DIR}")

    # 自测（服务器本机走 80/443 相对路径无碍）
    run(f"ls -lh {REMOTE_UPDATES_DIR}")

    sftp.close()
    client.close()
    print("\n已上传到服务器 /opt/personal-site/updates/")


if __name__ == "__main__":
    main()