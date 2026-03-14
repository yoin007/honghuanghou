# -*- coding: utf-8 -*-
from netmiko import ConnectHandler
from datetime import datetime
import sys
from config.config import Config
from sendqueue import send_text


core_conf = Config().get_config("core", "network.yaml")
host = core_conf["host"]
user = core_conf["user"]
pwd = core_conf["pwd"]
en_pw = pwd

dev = {
    "device_type": "ruijie_os",
    "host": host,
    "username": user,
    "password": pwd,
    "secret": en_pw,
    "timeout": 10,
}

# 1. 命令列表：把可能不支持的放在可选组
MUST_CMDS = [
    "show cpu | include CPU utilization",
    "show memory | include Memory",
    "show interface status | include (err-disable|down)",
    "show ip dhcp pool",
]

OPTIONAL_CMDS = [
    "show environment | include (Temperature|Power|Fan)",
    "show power | include (PowerSupply|Current|Status)",   # 部分机型用这条
]

def run_cmd(conn, cmd: str, expect_string: str = r"#"):
    """返回 strip 后的回显；Invalid 返回空串"""
    out = conn.send_command(cmd, delay_factor=0.5, expect_string=expect_string)
    if "% Invalid" in out or "% Unrecognized" in out:
        return ""
    return out.strip()

def check_core():
    try:
        conn = ConnectHandler(**dev)
        conn.enable()
    except Exception as e:
        print("登录失败:", e); sys.exit(1)

    log = [f"# 锐捷快检 {host}  {datetime.now():%F %T}"]
    for cmd in MUST_CMDS:
        out = run_cmd(conn, cmd)
        log.append(f"\n# {cmd}")
        log.append(out if out else "无异常")

    for cmd in OPTIONAL_CMDS:
        out = run_cmd(conn, cmd)
        if out:                # 只有命令生效才记录
            log.append(f"\n# {cmd}")
            log.append(out)
    conn.disconnect()

    report = "\n".join(log)
    # print(repor/t)
    with open(f"quick_{host}.txt", "w", encoding="utf-8") as f:
        f.write(report)
    return report

async def core_status(record):
    tips = check_core()
    send_text(tips, record.roomid)

async def core_cmd(record):
    cmds = record.content.strip().replace("：", ":").replace("RJ:", "").split('\n')
    wxid = record.roomid
    try:
        conn = ConnectHandler(**dev)
        conn.enable()
        for cmd in cmds:
            out = run_cmd(conn, cmd)
            send_text(out if out else "无异常", wxid)
        conn.disconnect()
    except Exception as e:
        send_text(f"执行失败: {e}", wxid)

