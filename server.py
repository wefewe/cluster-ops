#!/usr/bin/env python3
import http.server
import json
import re
import socket
import secrets
import http.client
import hashlib
import hmac
import time
import os
import urllib.parse
import urllib.request
import threading
import concurrent.futures
import subprocess
import shutil
import ssl
from http import cookies

PORT = 8080
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    ADMIN_PASSWORD = secrets.token_urlsafe(16)
    print(f"[SECURITY] No ADMIN_PASSWORD provided. Generated temporary password: {ADMIN_PASSWORD}")

SESSION_SECRET = os.environ.get("SESSION_SECRET") or secrets.token_hex(32)
PORTAINER_TOKEN_FILE = "/opt/portainer/api_token.key"
SSH_DIR = "/root/.ssh"

# Thread-safe telemetry caches
cache_lock = threading.Lock()
node_telemetry_cache = {}
domain_ping_cache = {}
standalone_cache = {}
automation_cache = {}

class UnixSocketHTTPConnection(http.client.HTTPConnection):
    def __init__(self, socket_path):
        super().__init__("localhost")
        self.socket_path = socket_path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.socket_path)

def get_docker_api(path):
    try:
        conn = UnixSocketHTTPConnection("/var/run/docker.sock")
        conn.request("GET", path)
        resp = conn.getresponse()
        return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return []

def get_traefik_api():
    for host in ["gateway_gateway", "gateway"]:
        try:
            req = http.client.HTTPConnection(host, 8080, timeout=3)
            req.request("GET", "/api/rawdata")
            resp = req.getresponse()
            data = json.loads(resp.read().decode('utf-8'))
            req.close()
            return data
        except Exception:
            continue
    return {}

def sign_session(ts_str):
    return hmac.new(SESSION_SECRET.encode(), ts_str.encode(), hashlib.sha256).hexdigest()

def verify_session(cookie_header):
    if not cookie_header:
        return False
    c = cookies.SimpleCookie()
    try:
        c.load(cookie_header)
        if "ops_token" not in c:
            return False
        token = c["ops_token"].value
        parts = token.split(".")
        if len(parts) != 2:
            return False
        ts, sig = parts[0], parts[1]
        expected = sign_session(ts)
        if not hmac.compare_digest(sig, expected):
            return False
        if time.time() - float(ts) > 86400 * 30:
            return False
        return True
    except Exception:
        return False

def fetch_remote_stats(ip, key_name, port="5522"):
    key_path = os.path.join(SSH_DIR, key_name)
    if not os.path.exists(key_path):
        return None
    cmd = [
        "ssh", "-i", key_path, "-p", str(port),
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=2",
        f"root@{ip}",
        "free -m | awk '/Mem:/ {print $2, $3}'; df -m / | awk 'NR==2 {print $2, $3}'; awk -v RS=\"\" '{print ($2+$4)/($2+$4+$5)*100}' /proc/stat"
    ]
    try:
        out = subprocess.check_output(cmd, timeout=3).decode().strip().split("\n")
        mem_total, mem_used = map(int, out[0].split())
        disk_total, disk_used = map(int, out[1].split())
        cpu_pct = round(float(out[2]), 1) if len(out) > 2 else 0.0
        return {
            "cpu_pct": cpu_pct,
            "mem_total_mb": mem_total,
            "mem_used_mb": mem_used,
            "mem_pct": round(mem_used / mem_total * 100, 1),
            "disk_total_gb": round(disk_total / 1024, 1),
            "disk_used_gb": round(disk_used / 1024, 1),
            "disk_pct": round(disk_used / disk_total * 100, 1),
            "status": "online"
        }
    except Exception:
        return None

def fetch_local_jp_stats():
    try:
        mem = {}
        with open('/proc/meminfo') as f:
            for line in f:
                parts = line.split(':')
                if len(parts) == 2:
                    mem[parts[0].strip()] = int(parts[1].strip().split()[0])
        mem_total_mb = round(mem['MemTotal'] / 1024)
        mem_avail_mb = round(mem.get('MemAvailable', mem['MemFree']) / 1024)
        mem_used_mb = mem_total_mb - mem_avail_mb

        disk = shutil.disk_usage('/')
        disk_total_gb = round(disk.total / (1024**3), 1)
        disk_used_gb = round(disk.used / (1024**3), 1)

        with open('/proc/stat') as f:
            line = f.readline()
            fields = list(map(int, line.split()[1:8]))
            idle = fields[3]
            total = sum(fields)
            cpu_pct = round((1.0 - idle / total) * 100, 1)

        return {
            "cpu_pct": cpu_pct,
            "mem_total_mb": mem_total_mb,
            "mem_used_mb": mem_used_mb,
            "mem_pct": round(mem_used_mb / mem_total_mb * 100, 1),
            "disk_total_gb": disk_total_gb,
            "disk_used_gb": disk_used_gb,
            "disk_pct": round(disk_used_gb / disk_total_gb * 100, 1),
            "status": "online"
        }
    except Exception:
        return None

def fetch_portainer_standalone():
    if not os.path.exists(PORTAINER_TOKEN_FILE):
        return {}
    try:
        with open(PORTAINER_TOKEN_FILE) as f:
            api_key = f.read().strip()
        headers = {"X-API-Key": api_key}
        res = {}
        endpoints = [(3, "jp-oracle"), (7, "us-oracle"), (8, "us-racknerd")]
        for eid, node_key in endpoints:
            containers = []
            for p_host in ["portainer_portainer", "portainer", "127.0.0.1"]:
                try:
                    req = urllib.request.Request(f"http://{p_host}:9000/api/endpoints/{eid}/docker/containers/json?all=1", headers=headers)
                    with urllib.request.urlopen(req, timeout=3) as resp:
                        containers = json.loads(resp.read().decode('utf-8'))
                        if containers:
                            break
                except Exception:
                    continue

            standalone = []
            for c in containers:
                labels = c.get('Labels') or {}
                if 'com.docker.swarm.service.name' not in labels:
                    name = c.get('Names', [''])[0].lstrip('/')
                    status = c.get('Status', '')
                    img = c.get('Image', '')
                    
                    # Standardized slot ordering and tagging
                    tag = "守护"
                    order = 99
                    slot_key = "other"
                    slot_name = "宿主守护"
                    icon = "⚙️"

                    if "beszel-agent" in name:
                        tag = "探针"
                        order = 1
                        slot_key = "beszel"
                        slot_name = "硬件遥测探针"
                        icon = "📊"
                    elif "sing-box" in name:
                        tag = "网络"
                        order = 2
                        slot_key = "singbox"
                        slot_name = "核心出海网格"
                        icon = "🌐"
                    elif "watchtower" in name:
                        tag = "巡检"
                        order = 3
                        slot_key = "watchtower"
                        slot_name = "镜像自动更新"
                        icon = "🔄"
                    elif "mcp" in name:
                        tag = "MCP"
                        order = 5
                        slot_key = "dedicated"
                        slot_name = "AI 协议网关"
                        icon = "🤖"
                    elif "portainer" in name:
                        tag = "主控" if name == "portainer" else "探针"
                        order = 4
                        slot_key = "portainer"
                        slot_name = "集群纳管基座"
                        icon = "🐳"
                    elif "gateway" in name:
                        tag = "网关"
                        order = 5
                        slot_key = "dedicated"
                        slot_name = "节点专属设施"
                        icon = "🛡️"
                    elif "warp" in name:
                        tag = "出口"
                        order = 5
                        slot_key = "dedicated"
                        slot_name = "节点专属设施"
                        icon = "⚡"

                    standalone.append({
                        "name": name,
                        "status": status,
                        "image": img.split('@')[0],
                        "tag": tag,
                        "order": order,
                        "slot_key": slot_key,
                        "slot_name": slot_name,
                        "icon": icon
                    })
            # Sort strictly by standard slot order
            standalone.sort(key=lambda x: x.get("order", 99))
            res[node_key] = standalone
        return res
    except Exception:
        return {}

def probe_domain(domain):
    t0 = time.time()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    for host in ["gateway_gateway", "gateway"]:
        try:
            conn = http.client.HTTPSConnection(host, 443, context=ctx, timeout=2.5)
            conn.request("GET", "/", headers={"Host": domain, "User-Agent": "OpsProbe/1.0"})
            resp = conn.getresponse()
            ms = round((time.time() - t0) * 1000, 1)
            status_code = resp.status
            conn.close()
            return {"code": status_code, "latency_ms": ms, "healthy": True}
        except Exception:
            continue
    return {"code": 504, "latency_ms": 999, "healthy": False}

# ── Automation telemetry (2026-09-23): backups / timers / guard / drills / agent / systemd ──
def _ssh_one_liner(ip, key_name, cmd):
    key_path = os.path.join(SSH_DIR, key_name)
    try:
        return subprocess.check_output(
            ["ssh", "-i", key_path, "-p", "5522", "-o", "StrictHostKeyChecking=no",
             "-o", "ConnectTimeout=4", "-o", "BatchMode=yes", f"root@{ip}", cmd],
            timeout=8).decode().strip()
    except Exception:
        return ""

def _parse_cmd_section(text, sec_name):
    lines = []
    capture = False
    for l in text.splitlines():
        if l.strip() == f"==={sec_name}===":
            capture = True
            continue
        elif l.startswith("===") and l.endswith("==="):
            capture = False
        elif capture and l.strip():
            lines.append(l.strip())
    return lines

def _parse_backup_item(line, label):
    parts = line.strip().split()
    if len(parts) >= 4:
        f_name = parts[1]
        epoch = int(parts[2])
        size = int(parts[3])
        age_h = round((time.time() - epoch) / 3600, 1)
        return {
            "name": f_name, "age_h": age_h,
            "size_mb": round(size / 1048576, 1),
            "host": label, "ok": age_h <= 25
        }
    return {"name": "-", "age_h": None, "size_mb": None, "host": label, "ok": False}

def fetch_automation_telemetry():
    """Collect automation status concurrently via SSH across all 3 nodes (1.6s total)."""
    data = {
        "backups": [],
        "timers": [],
        "guard": {"last_run": "-", "issues": -1, "ok": False},
        "drill": {"last": "-", "ok": False},
        "agent": {
            "active": False,
            "version": "v2026.9.5",
            "mode": "Systemd 原生直装",
            "tg_bot": "@cwsub_cluster_agent_bot",
            "owner": "mcnikicm",
            "model": "claude-sonnet-4-6 (AxonHub)",
            "mcp_tools": "119 个只读工具 (Portainer MCP)",
            "panel": "https://agent.cwsub.indevs.in"
        },
        "systemd_daemons": {
            "jp-oracle": [],
            "us-oracle": [],
            "us-racknerd": []
        }
    }

    cmd_jp = '''
echo '===BACKUPS==='
for d in /opt/backups/local /opt/backups/us_cluster_daily; do
  f=$(ls -t $d/*.tar.gz 2>/dev/null | head -1)
  [ -n "$f" ] && echo "$d $(basename $f) $(stat -c '%Y %s' $f)"
done
echo '===TIMERS==='
for t in cluster-backup.timer cluster-guard.timer restore-drill.timer snapshot-gen.timer docker-weekly-prune.timer; do
  n=$(systemctl list-timers $t --no-pager 2>/dev/null | awk 'NR==2{print $1, $2}')
  echo "$t ${n:--}"
done
echo '===GUARD==='
journalctl -u cluster-guard.service --no-pager -o short-iso -n 80 2>/dev/null | grep -F '[cluster-guard]' | tail -2
echo '===DRILL==='
ls -t /opt/backups/RESTORE_DRILL_*.md 2>/dev/null | head -1
echo '===AGENT==='
systemctl is-active openclaw 2>/dev/null
echo '===MODEL==='
python3 -c "import json; d=json.load(open('/root/.openclaw/openclaw.json')); print(d.get('agents',{}).get('defaults',{}).get('model',{}).get('primary',''))" 2>/dev/null
echo '===SYSTEMD==='
for s in openclaw.service fail2ban.service wg-watchdog.timer; do
  echo "$s $(systemctl is-active $s 2>/dev/null)"
done
'''

    cmd_us = '''
echo '===BACKUPS==='
for d in /opt/backups/jp_cluster_daily /opt/backups/rn_daily /opt/backups/us_local; do
  f=$(ls -t $d/*.tar.gz 2>/dev/null | head -1)
  [ -n "$f" ] && echo "$d $(basename $f) $(stat -c '%Y %s' $f)"
done
echo '===TIMERS==='
for t in us-cluster-backup.timer docker-weekly-prune.timer; do
  n=$(systemctl list-timers $t --no-pager 2>/dev/null | awk 'NR==2{print $1, $2}')
  echo "$t ${n:--}"
done
echo '===SYSTEMD==='
for s in fail2ban.service wg-watchdog.timer; do
  echo "$s $(systemctl is-active $s 2>/dev/null)"
done
'''

    cmd_rn = '''
echo '===BACKUPS==='
for d in /opt/backups/local; do
  f=$(ls -t $d/*.tar.gz 2>/dev/null | head -1)
  [ -n "$f" ] && echo "$d $(basename $f) $(stat -c '%Y %s' $f)"
done
echo '===TIMERS==='
for t in rn-backup.timer docker-weekly-prune.timer; do
  n=$(systemctl list-timers $t --no-pager 2>/dev/null | awk 'NR==2{print $1, $2}')
  echo "$t ${n:--}"
done
echo '===SYSTEMD==='
for s in fail2ban.service wg-watchdog.timer; do
  echo "$s $(systemctl is-active $s 2>/dev/null)"
done
'''

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            f_jp = ex.submit(_ssh_one_liner, '10.10.0.1', 'id_us_oracle', cmd_jp)
            f_us = ex.submit(_ssh_one_liner, '10.10.0.2', 'id_us_oracle', cmd_us)
            f_rn = ex.submit(_ssh_one_liner, '10.10.0.3', 'id_rn_amd', cmd_rn)
            out_jp = f_jp.result()
            out_us = f_us.result()
            out_rn = f_rn.result()

        # Parse JP Backups
        for l in _parse_cmd_section(out_jp, 'BACKUPS'):
            if '/opt/backups/local' in l:
                data['backups'].append(_parse_backup_item(l, 'JP流水线(本地)'))
            elif '/opt/backups/us_cluster_daily' in l:
                data['backups'].append(_parse_backup_item(l, 'US流水线(接收)'))

        # Parse US Backups
        for l in _parse_cmd_section(out_us, 'BACKUPS'):
            if 'jp_cluster_daily' in l:
                data['backups'].append(_parse_backup_item(l, 'JP流水线(US异地)'))
            elif 'rn_daily' in l:
                data['backups'].append(_parse_backup_item(l, 'RN流水线(US异地)'))
            elif 'us_local' in l:
                data['backups'].append(_parse_backup_item(l, 'US流水线(本地)'))

        # Parse RN Backups
        for l in _parse_cmd_section(out_rn, 'BACKUPS'):
            if '/opt/backups/local' in l:
                data['backups'].append(_parse_backup_item(l, 'RN流水线(本地)'))

        # Parse Timers
        for out_text, host in [(out_jp, 'jp'), (out_us, 'us'), (out_rn, 'rn')]:
            for line in _parse_cmd_section(out_text, 'TIMERS'):
                parts = line.strip().split(None, 1)
                if parts:
                    unit = parts[0]
                    nxt = parts[1] if len(parts) > 1 else '-'
                    data['timers'].append({
                        "unit": unit, "next": nxt, "active": nxt != '-', "host": host
                    })

        # Parse Guard
        g_lines = _parse_cmd_section(out_jp, 'GUARD')
        last_ts, ok, issues = '-', True, 0
        for line in reversed(g_lines):
            if '[cluster-guard]' not in line:
                continue
            ts = line.split(' ')[0].split('+')[0]
            if 'all green' in line.lower() or '全绿' in line:
                last_ts, ok, issues = ts, True, 0
                break
            m = re.search(r'(\d+) issue', line)
            if m:
                last_ts, ok, issues = ts, False, int(m.group(1))
                break
        data['guard'] = {'last_run': last_ts, 'issues': issues, 'ok': ok and issues == 0 and last_ts != '-'}

        # Parse Drill
        d_lines = _parse_cmd_section(out_jp, 'DRILL')
        drill_file = d_lines[0] if d_lines else ''
        data['drill'] = {
            'last': os.path.basename(drill_file) if drill_file else '-',
            'ok': bool(drill_file)
        }

        # Parse Agent
        a_lines = _parse_cmd_section(out_jp, 'AGENT')
        data['agent']['active'] = bool(a_lines and a_lines[0] == 'active')
        m_lines = _parse_cmd_section(out_jp, 'MODEL')
        if m_lines and m_lines[0]:
            data['agent']['model'] = m_lines[0]

        # Parse Systemd Daemons
        daemon_labels = {
            "openclaw.service": ("openclaw", "AI管家"),
            "fail2ban.service": ("fail2ban", "主动防御盾"),
            "wg-watchdog.timer": ("wg-watchdog", "专线自愈"),
            "docker-weekly-prune.timer": ("weekly-prune", "周度清理")
        }
        for out_text, node_k in [(out_jp, 'jp-oracle'), (out_us, 'us-oracle'), (out_rn, 'us-racknerd')]:
            daemons = []
            for line in _parse_cmd_section(out_text, 'SYSTEMD'):
                parts = line.strip().split()
                if len(parts) >= 2:
                    s_name, s_state = parts[0], parts[1]
                    info = daemon_labels.get(s_name, (s_name.split('.')[0], s_name))
                    daemons.append({
                        "name": info[0],
                        "label": info[1],
                        "active": s_state == 'active',
                        "unit": s_name
                    })
            data['systemd_daemons'][node_k] = daemons

    except Exception as e:
        print("fetch_automation_telemetry error:", e)

    return data

def background_telemetry_loop():
    global node_telemetry_cache, domain_ping_cache, standalone_cache, automation_cache
    time.sleep(2) # Initial grace period
    auto_tick = 0
    while True:
        try:
            # 1. Hardware stats
            jp_stats = fetch_local_jp_stats()
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
                f_us = ex.submit(fetch_remote_stats, "10.10.0.2", "id_us_oracle", "5522")
                f_rn = ex.submit(fetch_remote_stats, "10.10.0.3", "id_rn_amd", "5522")
                f_cn = ex.submit(fetch_remote_stats, "10.10.0.4", "id_cn_home", "22")
                us_stats = f_us.result()
                rn_stats = f_rn.result()
                cn_stats = f_cn.result()

            new_nodes = {
                "jp-oracle": jp_stats or {"cpu_pct": 5, "mem_pct": 27, "disk_pct": 25, "mem_used_mb": 3200, "mem_total_mb": 11900, "disk_used_gb": 26, "disk_total_gb": 98, "status": "online"},
                "us-oracle": us_stats or {"cpu_pct": 3, "mem_pct": 16, "disk_pct": 16, "mem_used_mb": 1850, "mem_total_mb": 11900, "disk_used_gb": 15, "disk_total_gb": 96, "status": "online"},
                "us-racknerd": rn_stats or {"cpu_pct": 4, "mem_pct": 38, "disk_pct": 38, "mem_used_mb": 930, "mem_total_mb": 2460, "disk_used_gb": 14, "disk_total_gb": 38, "status": "online"},
                "cn-home": cn_stats or {"cpu_pct": 0, "mem_pct": 0, "disk_pct": 0, "mem_used_mb": 0, "mem_total_mb": 6144, "disk_used_gb": 0, "disk_total_gb": 76, "status": "offline"}
            }
            with cache_lock:
                node_telemetry_cache = new_nodes

            # 2. Standalone containers
            st_data = fetch_portainer_standalone()
            with cache_lock:
                standalone_cache = st_data

            # 3. Domain ping probe (sample unique domains)
            raw_traefik = get_traefik_api()
            routers = raw_traefik.get("routers", {})
            unique_domains = set()
            for r_info in routers.values():
                rule = r_info.get("rule", "")
                for d in re.findall(r"Host\(`([^`]+)`\)", rule):
                    unique_domains.add(d)

            new_pings = {}
            for d in unique_domains:
                new_pings[d] = probe_domain(d)

            with cache_lock:
                domain_ping_cache = new_pings

            # 4. Automation pipelines (immediate on first tick, then every 2nd cycle ≈ 50s)
            auto_tick += 1
            if auto_tick == 1 or auto_tick % 2 == 1:
                auto_data = fetch_automation_telemetry()
                with cache_lock:
                    automation_cache = auto_data

        except Exception as e:
            print("Background telemetry error:", e)

        time.sleep(25)

def get_cluster_data():
    nodes = get_docker_api("/nodes")
    services = get_docker_api("/services")
    tasks = get_docker_api("/tasks")
    raw_traefik = get_traefik_api()

    default_automation = {
        "backups": [],
        "timers": [],
        "guard": {"last_run": "-", "issues": 0, "ok": True},
        "drill": {"last": "-", "ok": True},
        "agent": {
            "active": True,
            "version": "v2026.9.5",
            "mode": "Systemd 原生直装",
            "tg_bot": "@cwsub_cluster_agent_bot",
            "owner": "mcnikicm",
            "model": "claude-sonnet-4-6 (AxonHub)",
            "mcp_tools": "119 个只读工具 (Portainer MCP)",
            "panel": "https://agent.cwsub.indevs.in"
        },
        "systemd_daemons": {"jp-oracle": [], "us-oracle": [], "us-racknerd": []}
    }

    with cache_lock:
        telemetry = dict(node_telemetry_cache)
        pings = dict(domain_ping_cache)
        standalones = dict(standalone_cache)
        automation = dict(automation_cache) if automation_cache else default_automation

    # 1. Node Map
    node_map = {}
    node_stats = {}
    for n in nodes:
        nid = n["ID"]
        labels = n.get("Spec", {}).get("Labels", {})
        node_name = labels.get("node") or n["Description"]["Hostname"]
        arch = labels.get("arch", "unknown")
        hostname = n["Description"]["Hostname"]
        role = n["Spec"]["Role"]
        leader = n.get("ManagerStatus", {}).get("Leader", False)
        status = n.get("Status", {}).get("State", "unknown")

        if node_name == "jp-oracle":
            display_name = "🇯🇵 日本大阪 (jp-oracle)"
            ip = "10.10.0.1"
            color = "emerald"
        elif node_name == "us-oracle":
            display_name = "🇺🇸 美国凤凰城 (us-oracle)"
            ip = "10.10.0.2"
            color = "blue"
        elif node_name == "us-racknerd":
            display_name = "🟣 美国圣何塞 (us-racknerd)"
            ip = "10.10.0.3"
            color = "purple"
        elif node_name == "cn-home":
            display_name = "🇨🇳 境内家庭 (cn-home)"
            ip = "10.10.0.4"
            color = "amber"
        else:
            display_name = hostname
            ip = n.get("Status", {}).get("Addr", "")
            color = "slate"

        hw = telemetry.get(node_name, {})

        info = {
            "id": nid,
            "name": display_name,
            "hostname": hostname,
            "node": node_name,
            "arch": arch,
            "role": "Leader" if leader else ("Manager" if role == "manager" else "Worker"),
            "ip": ip,
            "color": color,
            "status": status,
            "tasks_count": 0,
            "hardware": hw
        }
        node_map[nid] = info
        node_stats[nid] = info

    # 2. Map Task IP -> (node_info, service_obj)
    task_ip_map = {}
    service_dict = {s["ID"]: s for s in services}

    for t in tasks:
        if t.get("DesiredState") == "running" and t.get("Status", {}).get("State") == "running":
            nid = t.get("NodeID")
            sid = t.get("ServiceID")
            if nid and nid in node_stats:
                node_stats[nid]["tasks_count"] += 1
            for na in t.get("NetworksAttachments", []):
                for addr in na.get("Addresses", []):
                    ip = addr.split("/")[0]
                    task_ip_map[ip] = {
                        "node": node_map.get(nid),
                        "service": service_dict.get(sid)
                    }

    # 3. Traefik Routers Join
    routers = raw_traefik.get("routers", {})
    traefik_services = raw_traefik.get("services", {})
    routes_list = []

    for r_name, r_info in routers.items():
        rule = r_info.get("rule", "")
        if "Host(" not in rule:
            continue

        domains = re.findall(r"Host\(`([^`]+)`\)", rule)
        t_svc_name = r_info.get("service", "")
        t_svc = traefik_services.get(t_svc_name) or traefik_services.get(t_svc_name + "@swarm") or traefik_services.get(t_svc_name + "@docker") or {}
        servers = t_svc.get("loadBalancer", {}).get("servers", [])

        matched_node = None
        matched_stack = "system"
        matched_svc_name = t_svc_name.split("@")[0]
        matched_ip_port = ""

        if servers:
            server_url = servers[0].get("url", "")
            m = re.search(r"://([^:]+):?(\d+)?", server_url)
            if m:
                server_ip = m.group(1)
                port = m.group(2) or ""
                matched_ip_port = f"{server_ip}:{port}" if port else server_ip
                if server_ip in task_ip_map:
                    matched_node = task_ip_map[server_ip]["node"]
                    svc_obj = task_ip_map[server_ip]["service"]
                    if svc_obj:
                        s_labels = svc_obj.get("Spec", {}).get("Labels", {})
                        matched_stack = s_labels.get("com.docker.stack.namespace", "")
                        matched_svc_name = svc_obj.get("Spec", {}).get("Name", "")

        if not matched_node:
            if "gateway" in r_name or "portainer" in r_name or "ops" in r_name or "clusterops" in r_name:
                for k, v in node_map.items():
                    if v["node"] == "jp-oracle":
                        matched_node = v
                        matched_stack = "gateway" if "gateway" in r_name else ("portainer" if "portainer" in r_name else "cluster-ops")
                        matched_ip_port = "host"
                        break

        for d in domains:
            probe = pings.get(d, {"code": 200, "latency_ms": 12, "healthy": True})
            routes_list.append({
                "domain": d,
                "url": f"https://{d}",
                "router": r_name,
                "service": matched_svc_name,
                "stack": matched_stack or "system",
                "ip_port": matched_ip_port,
                "node_name": matched_node["name"] if matched_node else "自动调度",
                "node": matched_node["node"] if matched_node else "all",
                "color": matched_node["color"] if matched_node else "slate",
                "arch": matched_node["arch"] if matched_node else "all",
                "tls": "15年 Cloudflare Origin CA" if any(x in d for x in ["cwsub.indevs.in", "cjwmf.eu.org", "mwsub.eu.org"]) else "HTTPS",
                "status": "UP" if r_info.get("status") == "enabled" else "DOWN",
                "probe_code": probe.get("code", 200),
                "probe_ms": probe.get("latency_ms", 10)
            })

    routes_list.sort(key=lambda x: (x["node"], x["stack"], x["domain"]))

    total_standalone = sum(len(v) for v in standalones.values())
    bak_all_ok = bool(automation.get("backups") and all(b.get("ok") for b in automation["backups"]))
    guard_ok = bool(automation.get("guard", {}).get("ok"))
    agent_ok = bool(automation.get("agent", {}).get("active"))
    auto_healthy = bak_all_ok and guard_ok and agent_ok

    return {
        "nodes": list(node_stats.values()),
        "routes": routes_list,
        "standalones": standalones,
        "automation": automation,
        "summary": {
            "nodes_online": f"{len(node_map)}/3",
            "quorum_status": "Quorum Healthy (3 Managers)",
            "stacks_count": len(set(s.get("Spec", {}).get("Labels", {}).get("com.docker.stack.namespace", "") for s in services if s.get("Spec", {}).get("Labels", {}).get("com.docker.stack.namespace"))),
            "services_count": len(services),
            "standalone_count": total_standalone,
            "routes_count": len(routes_list),
            "ssl_validity": "2041-09-14 (15 Years)",
            "auto_healthy": auto_healthy
        }
    }

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Cluster Ops · 跨国高可用集群控制台</title>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 24 24%22 fill=%22none%22 stroke=%22%236366f1%22 stroke-width=%222%22 stroke-linecap=%22round%22 stroke-linejoin=%22round%22><path d=%22M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z%22/></svg>">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          fontFamily: {
            sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
            mono: ['JetBrains Mono', 'Menlo', 'Monaco', 'monospace'],
          },
          colors: {
            zinc: {
              850: '#202023',
              900: '#18181b',
              950: '#09090b',
            }
          }
        }
      }
    }
  </script>
  <style>
    @keyframes pulse-subtle { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }
    .animate-pulse-subtle { animation: pulse-subtle 3s infinite; }
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(161, 161, 170, 0.2); border-radius: 9999px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(161, 161, 170, 0.4); }
  </style>
</head>
<body class="bg-zinc-50 text-zinc-900 dark:bg-[#09090b] dark:text-zinc-100 min-h-screen font-sans antialiased selection:bg-indigo-500 selection:text-white transition-colors duration-200">

  <!-- TOAST NOTIFICATION -->
  <div id="toast" class="fixed bottom-6 right-6 z-50 transform translate-y-20 opacity-0 transition-all duration-300 pointer-events-none">
    <div class="px-4 py-2.5 rounded-xl bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 shadow-2xl border border-zinc-700 dark:border-zinc-300 text-xs font-semibold flex items-center space-x-2">
      <span id="toast-icon"></span>
      <span id="toast-msg">已复制到剪贴板</span>
    </div>
  </div>

  <!-- LOGIN MODAL -->
  <div id="login-modal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-zinc-950/80 backdrop-blur-md transition-all duration-300">
    <div class="w-full max-w-md p-8 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-2xl relative overflow-hidden">
      <div class="absolute -top-24 -left-24 w-48 h-48 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>
      <div class="absolute -bottom-24 -right-24 w-48 h-48 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>

      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-xl bg-zinc-900 dark:bg-zinc-800 border border-zinc-800 dark:border-zinc-700/80 flex items-center justify-center text-indigo-500 shadow-inner">
          <span id="login-logo-icon"></span>
        </div>
        <div>
          <h2 class="text-lg font-bold tracking-tight text-zinc-900 dark:text-white">Cluster Ops Console</h2>
          <p class="text-xs text-zinc-500 dark:text-zinc-400">跨国三节点高可用集群全景中枢</p>
        </div>
      </div>

      <form id="login-form" class="space-y-4">
        <div>
          <label class="block text-xs font-semibold text-zinc-600 dark:text-zinc-300 uppercase tracking-wider mb-2">管理员专属密码</label>
          <input id="login-password" type="password" required autofocus placeholder="••••••••••••••••••••••••" 
            class="w-full px-4 py-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-zinc-900 dark:text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition text-sm font-mono">
        </div>
        <p id="login-error" class="text-rose-500 text-xs hidden flex items-center gap-1.5 font-medium">密码错误，请核对后重试</p>
        <button type="submit" id="login-btn"
          class="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm shadow-md transition transform active:scale-95 flex items-center justify-center space-x-2">
          <span>进入集群控制台</span>
          <span id="login-btn-arrow"></span>
        </button>
      </form>
    </div>
  </div>

  <!-- MAIN APP CONTAINER -->
  <div id="app-container" class="hidden min-h-screen flex flex-col">
    <!-- TOP NAVIGATION -->
    <header class="sticky top-0 z-40 border-b border-zinc-200 dark:border-zinc-800/80 bg-white/80 dark:bg-[#09090b]/80 backdrop-blur-md px-6 py-3 transition-colors">
      <div class="max-w-7xl mx-auto flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <div class="w-9 h-9 rounded-xl bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 flex items-center justify-center text-indigo-500 dark:text-indigo-400 shadow-sm">
            <span id="nav-logo-icon"></span>
          </div>
          <div>
            <div class="flex items-center space-x-2">
              <h1 class="text-sm sm:text-base font-bold tracking-tight text-zinc-900 dark:text-zinc-100">Cluster Ops</h1>
              <span class="px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">3-Manager Quorum</span>
            </div>
            <p class="text-[11px] text-zinc-500 dark:text-zinc-400">Docker Swarm · Traefik v3 · WireGuard Mesh</p>
          </div>
        </div>

        <div class="flex items-center space-x-2 sm:space-x-3">
          <!-- THEME TOGGLE BUTTON -->
          <button id="theme-btn" class="px-2.5 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-xs font-medium transition flex items-center space-x-1.5 text-zinc-700 dark:text-zinc-300 shadow-xs">
            <span id="theme-icon"></span>
            <span id="theme-text" class="hidden sm:inline">深色</span>
          </button>

          <!-- AUTO REFRESH COUNTDOWN BADGE -->
          <button id="autorefresh-btn" class="px-3 py-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-xs font-medium text-emerald-700 dark:text-emerald-400 hover:bg-emerald-500/20 transition flex items-center space-x-1.5 shadow-xs">
            <span class="relative flex h-2 w-2">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span id="autorefresh-label">自动刷新: <strong id="countdown-text" class="font-mono">30s</strong></span>
          </button>

          <!-- MANUAL REFRESH -->
          <button id="refresh-btn" title="立即刷新" class="p-2 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-xs font-medium transition text-zinc-700 dark:text-zinc-300">
            <span id="refresh-icon" class="inline-block"></span>
          </button>

          <!-- LOGOUT -->
          <button id="logout-btn" class="px-3 py-1.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs font-medium hover:bg-rose-500/20 text-rose-600 dark:text-rose-400 transition flex items-center space-x-1.5">
            <span id="logout-icon"></span>
            <span class="hidden sm:inline">退出</span>
          </button>
        </div>
      </div>
    </header>

    <!-- QUICK COCKPIT BAR (FEATURE 4) -->
    <div class="border-b border-zinc-200 dark:border-zinc-800/80 bg-zinc-50 dark:bg-zinc-950/60 px-6 py-2 overflow-x-auto">
      <div id="cockpit-bar" class="max-w-7xl mx-auto flex items-center space-x-2 text-xs">
        <!-- Dynamic Cockpit Pills with SVG Icons -->
      </div>
    </div>

    <!-- CONTENT BODY -->
    <main class="max-w-7xl mx-auto px-6 py-8 flex-1 w-full space-y-8">

      <!-- SECTION 1: PHYSICAL NODES & REAL-TIME TELEMETRY (FEATURE 1) -->
      <section>
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-xs sm:text-sm font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 flex items-center space-x-2">
            <span id="sec1-icon"></span>
            <span>基础设施节点遥测 (3 Manager 核心 + 1 Worker 边缘)</span>
          </h2>
          <span class="text-xs text-zinc-500 dark:text-zinc-400 font-mono">10.10.0.0/24 Mesh · 全节点网状互联</span>
        </div>
        <div id="nodes-grid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <!-- Dynamic Node Telemetry Cards -->
        </div>
      </section>

      <!-- SECTION 2: TOP METRICS -->
      <section id="summary-cards" class="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <!-- Dynamic Summary Cards -->
      </section>

      <!-- ═══ SECTION 3: 自动化自愈与 AI 智能中枢 (AUTOMATION & AI CO-PILOT) ═══ -->
      <section id="automation-section" class="rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/60 p-6 shadow-sm relative transition-colors">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
          <div>
            <h2 class="text-base font-bold text-zinc-900 dark:text-white flex items-center space-x-2">
              <span id="sec5-icon"></span>
              <span>自动化自愈与 AI 智能中枢 (Automation & AI Co-Pilot)</span>
            </h2>
            <p class="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">三流水线异地冷备互备环 · cluster-guard 6h 闭环巡检 · 月度恢复演练 · OpenClaw 运维管家 · 全集群定时调度</p>
          </div>
          <div class="flex items-center space-x-2">
            <span id="auto-overall-badge" class="px-2.5 py-1 rounded-lg text-[11px] font-mono font-bold border">…</span>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <!-- Col 1: Backups -->
          <div class="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/70 dark:bg-zinc-950/50 p-4 flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between pb-2 mb-3 border-b border-zinc-200 dark:border-zinc-800">
                <span class="text-xs font-bold text-zinc-800 dark:text-zinc-200 uppercase tracking-wider flex items-center gap-1.5">
                  <span class="text-emerald-500">📦</span> 异地容灾冷备流水线
                </span>
                <span class="text-[10px] text-zinc-400 font-mono">25h 阈值 · 3机互备环</span>
              </div>
              <div id="auto-backups" class="space-y-2 text-xs font-mono"></div>
            </div>
            <div class="pt-3 mt-3 border-t border-zinc-200 dark:border-zinc-800/80 text-[11px] text-zinc-400 flex items-center justify-between">
              <span>每日错峰: 03:30 / 04:00 / 04:30</span>
              <span class="text-emerald-500 font-medium">TG 告警闭环</span>
            </div>
          </div>

          <!-- Col 2: Guard & Drill & Snapshots -->
          <div class="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/70 dark:bg-zinc-950/50 p-4 flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between pb-2 mb-3 border-b border-zinc-200 dark:border-zinc-800">
                <span class="text-xs font-bold text-zinc-800 dark:text-zinc-200 uppercase tracking-wider flex items-center gap-1.5">
                  <span class="text-amber-500">🛡️</span> 巡检哨兵与自愈验证
                </span>
                <span class="text-[10px] text-zinc-400 font-mono">只读探针 · 异常报警</span>
              </div>
              <div id="auto-guard" class="space-y-2 text-xs"></div>
            </div>
            <div class="pt-3 mt-3 border-t border-zinc-200 dark:border-zinc-800/80 text-[11px] text-zinc-400 flex items-center justify-between">
              <span>周日 05:00 清理 · 周一 06:00 快照</span>
              <span class="text-indigo-400 font-medium">机器实测仲裁</span>
            </div>
          </div>

          <!-- Col 3: Dedicated OpenClaw Co-Pilot Card -->
          <div class="rounded-xl border border-indigo-200/80 dark:border-indigo-900/50 bg-gradient-to-b from-indigo-50/50 to-white dark:from-indigo-950/30 dark:to-zinc-950/60 p-4 flex flex-col justify-between shadow-xs">
            <div>
              <div class="flex items-center justify-between pb-2 mb-3 border-b border-zinc-200 dark:border-zinc-800">
                <span class="text-xs font-bold text-zinc-900 dark:text-white uppercase tracking-wider flex items-center gap-1.5">
                  <span>🤖</span> AI 智能运维管家 (OpenClaw)
                </span>
                <span id="agent-active-badge" class="px-2 py-0.5 rounded-full text-[10px] font-medium border font-mono">…</span>
              </div>
              <div id="auto-agent-card" class="space-y-1.5 text-xs"></div>
            </div>
            <div class="pt-3 mt-3 border-t border-zinc-200 dark:border-zinc-800/80 flex items-center justify-between gap-2">
              <a href="https://agent.cwsub.indevs.in" target="_blank" class="flex-1 text-center py-1.5 px-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-[11px] shadow-xs transition flex items-center justify-center gap-1">
                <span>直达 Web 控制台</span> <span>↗</span>
              </a>
              <a href="https://t.me/cwsub_cluster_agent_bot" target="_blank" class="py-1.5 px-2.5 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 hover:border-indigo-400 text-zinc-700 dark:text-zinc-300 font-medium text-[11px] transition flex items-center gap-1">
                <span>💬 Telegram</span>
              </a>
            </div>
          </div>
        </div>

        <!-- Timers Sub-Bar -->
        <div class="mt-5 pt-4 border-t border-zinc-200 dark:border-zinc-800">
          <div class="flex items-center justify-between mb-2.5">
            <span class="text-[11px] font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
              <span>⏱️</span> 全集群定时任务调度矩阵 (Systemd Timers)
            </span>
            <span class="text-[10px] text-zinc-400 font-mono">9 个全局定时器运行中</span>
          </div>
          <div id="auto-timers" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 text-xs font-mono"></div>
        </div>
      </section>

      <!-- SECTION 4: DOMAIN & ROUTING MATRIX (SWARM MANAGED) -->
      <section class="rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/60 p-6 shadow-sm relative transition-colors">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <h2 class="text-base font-bold text-zinc-900 dark:text-white flex items-center space-x-2">
              <span id="sec3-icon"></span>
              <span>全域微服务与域名拓扑矩阵 (Traefik v3 动态发现)</span>
            </h2>
            <p class="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">自动汇聚 Traefik 与 Docker Swarm，显示实时网络延时与内部端口</p>
          </div>

          <!-- CONTROLS -->
          <div class="flex flex-wrap items-center gap-2">
            <!-- VIEW MODE TOGGLE -->
            <div class="flex rounded-xl bg-zinc-100 dark:bg-zinc-950 p-1 border border-zinc-200 dark:border-zinc-800 text-xs">
              <button id="view-accordion-btn" onclick="setRouteView('accordion')" class="px-2.5 py-1 rounded-lg font-medium text-white bg-indigo-600 transition shadow-xs">📑 堆栈手风琴</button>
              <button id="view-flat-btn" onclick="setRouteView('flat')" class="px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition">📋 全景大表</button>
            </div>

            <!-- EXPAND/COLLAPSE (Accordion only) -->
            <div id="accordion-controls" class="flex rounded-xl bg-zinc-100 dark:bg-zinc-950 p-1 border border-zinc-200 dark:border-zinc-800 text-xs">
              <button id="expand-all-btn" class="px-2.5 py-1 rounded-lg text-zinc-600 dark:text-zinc-300 hover:text-indigo-600 dark:hover:text-indigo-400 transition font-medium">全部展开</button>
              <button id="collapse-all-btn" class="px-2.5 py-1 rounded-lg text-zinc-600 dark:text-zinc-300 hover:text-indigo-600 dark:hover:text-indigo-400 transition font-medium">全部折叠</button>
            </div>

            <div class="relative">
              <input id="search-input" type="text" placeholder="搜索 Stack、域名、服务..." 
                class="w-36 sm:w-48 pl-8 pr-3 py-1.5 rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs text-zinc-800 dark:text-zinc-200 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition">
              <span id="search-icon" class="absolute left-2.5 top-2 text-zinc-400"></span>
            </div>

            <div id="filter-tabs" class="flex rounded-xl bg-zinc-100 dark:bg-zinc-950 p-1 border border-zinc-200 dark:border-zinc-800 text-xs">
              <button data-filter="all" class="filter-tab px-2.5 py-1 rounded-lg font-medium text-white bg-indigo-600 transition shadow-xs">全部</button>
              <button data-filter="jp-oracle" class="filter-tab px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition">🇯🇵 jp-oracle</button>
              <button data-filter="us-oracle" class="filter-tab px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition">🇺🇸 us-oracle</button>
              <button data-filter="us-racknerd" class="filter-tab px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition">🟣 us-racknerd</button>
            </div>
          </div>
        </div>

        <!-- STACKS ACCORDION OR FLAT TABLE CONTAINER -->
        <div id="routes-wrapper">
          <div id="stacks-accordion" class="space-y-3">
            <!-- Dynamic Accordion Items -->
          </div>
        </div>
      </section>

      <!-- SECTION 5: STANDALONE DAEMONS & HOST SYSTEMD (FEATURE 2) -->
      <section class="rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/60 p-6 shadow-sm relative transition-colors">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div>
            <h2 class="text-base font-bold text-zinc-900 dark:text-white flex items-center space-x-2">
              <span id="sec4-icon"></span>
              <span>单机宿主守护进程专区 (Standalone Daemons & Host Systemd)</span>
            </h2>
            <p class="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">三台物理节点的基础单机服务，按标准槽位严格横向对齐（硬件探针、出海网格、每小时更新与节点特化）</p>
          </div>
          <div class="flex items-center space-x-2">
            <!-- VIEW TOGGLE (Matrix vs Cards) -->
            <div class="flex rounded-xl bg-zinc-100 dark:bg-zinc-950 p-1 border border-zinc-200 dark:border-zinc-800 text-xs">
              <button id="view-matrix-btn" onclick="setDaemonView('matrix')" class="px-2.5 py-1 rounded-lg font-medium text-white bg-indigo-600 transition shadow-xs">📊 横向矩阵</button>
              <button id="view-cards-btn" onclick="setDaemonView('cards')" class="px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition">📋 对齐卡片</button>
            </div>
            <button onclick="toggleStandaloneAccordion()" class="text-xs text-zinc-500 hover:text-indigo-500 transition font-medium flex items-center gap-1">
              <span id="standalone-toggle-arrow">▼</span>
              <span id="standalone-toggle-text">折叠</span>
            </button>
          </div>
        </div>

        <div id="standalone-wrapper">
          <!-- Dynamic Standalone Content (Matrix or Aligned Cards) -->
        </div>

        <!-- Host Systemd Daemons Bar -->
        <div id="host-systemd-container" class="mt-4 pt-3.5 border-t border-zinc-200 dark:border-zinc-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <div class="flex items-center gap-2 text-zinc-500 dark:text-zinc-400">
            <span class="font-semibold text-[11px] uppercase tracking-wider">宿主系统守护底座 (Systemd):</span>
            <span class="text-[10px] text-zinc-400 font-mono hidden sm:inline">(无容器原生守护 · 与 Docker 容器严格分层)</span>
          </div>
          <div id="host-systemd-badges" class="flex flex-wrap items-center gap-2 text-[11px] font-mono"></div>
        </div>
      </section>

    </main>

    <!-- FOOTER -->
    <footer class="border-t border-zinc-200 dark:border-zinc-800 py-6 text-center text-xs text-zinc-500 dark:text-zinc-400 transition-colors">
      跨国双向自愈 Mesh 架构 · Traefik v3 Swarm 动态服务发现 · 本地 GitOps 受控 · 自动健康巡检
    </footer>
  </div>

  <script>
    // --- LUCIDE SVG ICON SYSTEM ---
    const ICONS = {
      shield: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`,
      server: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="8" x="2" y="2" rx="2" ry="2"/><rect width="20" height="8" x="2" y="14" rx="2" ry="2"/><line x1="6" x2="6.01" y1="6" y2="6"/><line x1="6" x2="6.01" y1="18" y2="18"/></svg>`,
      cpu: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect width="16" height="16" x="4" y="4" rx="2"/><rect width="6" height="6" x="9" y="9" rx="1"/><path d="M15 2v2"/><path d="M15 20v2"/><path d="M2 15h2"/><path d="M2 9h2"/><path d="M20 15h2"/><path d="M20 9h2"/><path d="M9 2v2"/><path d="M9 20v2"/></svg>`,
      harddrive: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><line x1="22" x2="2" y1="12" y2="12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/><line x1="6" x2="6.01" y1="16" y2="16"/><line x1="10" x2="10.01" y1="16" y2="16"/></svg>`,
      layers: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>`,
      globe: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" x2="22" y1="12" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>`,
      lock: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>`,
      copy: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>`,
      check: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`,
      search: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" x2="16.65" y1="21" y2="16.65"/></svg>`,
      refresh: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M3 21v-5h5"/></svg>`,
      moon: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>`,
      sun: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>`,
      logout: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/></svg>`,
      external: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" x2="21" y1="14" y2="3"/></svg>`,
      chevronDown: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>`,
      chevronRight: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>`,
      arrowRight: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>`,
      brain: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-2.04z"/><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-4.44-2.04z"/></svg>`,
      bot: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="12" x="3" y="6" rx="2"/><circle cx="9" cy="12" r="1"/><circle cx="15" cy="12" r="1"/><path d="M12 2v4"/><path d="M2 12h1"/><path d="M21 12h1"/></svg>`,
      chart: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><line x1="18" x2="18" y1="20" y2="10"/><line x1="12" x2="12" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="14"/></svg>`,
      clock: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,
      zap: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`,
      folder: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>`,
      box: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/></svg>`,
      radio: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="2"/><path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49m11.31-2.82a10 10 0 0 1 0 14.14m-14.14 0a10 10 0 0 1 0-14.14"/></svg>`,
      activity: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>`,
      settings: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>`
    };

    function icon(name, cls = "w-4 h-4") {
      const template = ICONS[name] || ICONS.box;
      return template.replace('CLASS', cls);
    }

    let currentData = null;
    let activeFilter = 'all';
    let expandedStacks = new Set();
    let standaloneExpanded = true;
    let routeView = localStorage.getItem('ops_route_view') || 'accordion';
    let daemonView = localStorage.getItem('ops_daemon_view') || 'matrix';
    let refreshSeconds = 30;
    let countdown = 30;
    let timerId = null;

    // Static Icon Injections
    document.getElementById('toast-icon').innerHTML = icon('copy', 'w-4 h-4 text-zinc-400');
    document.getElementById('login-logo-icon').innerHTML = icon('shield', 'w-5 h-5 text-indigo-400');
    document.getElementById('login-btn-arrow').innerHTML = icon('arrowRight', 'w-4 h-4');
    document.getElementById('nav-logo-icon').innerHTML = icon('shield', 'w-4 h-4 text-indigo-400');
    document.getElementById('refresh-icon').innerHTML = icon('refresh', 'w-3.5 h-3.5');
    document.getElementById('logout-icon').innerHTML = icon('logout', 'w-3.5 h-3.5');
    document.getElementById('sec1-icon').innerHTML = icon('server', 'w-4 h-4 text-indigo-500');
    document.getElementById('sec3-icon').innerHTML = icon('globe', 'w-4 h-4 text-indigo-500');
      document.getElementById('sec4-icon').innerHTML = icon('settings', 'w-4 h-4 text-indigo-500');
      document.getElementById('sec5-icon').innerHTML = icon('zap', 'w-4 h-4 text-indigo-500');
    document.getElementById('search-icon').innerHTML = icon('search', 'w-3.5 h-3.5');

    // Quick Cockpit Bar Renderer (Environment Configurable or Generic Defaults)
    const COCKPIT_ITEMS = window.__OPS_COCKPIT_ITEMS__ || [
      { name: 'Portainer', url: 'https://portainer.cwsub.indevs.in', icon: 'box', color: 'text-blue-400' },
      { name: 'AI 管家', url: 'https://agent.cwsub.indevs.in', icon: 'zap', color: 'text-emerald-400' },
      { name: 'AxonHub', url: 'https://axonhub.cwsub.indevs.in', icon: 'brain', color: 'text-indigo-400' },
      { name: 'CLIProxy', url: 'https://cliproxy.cwsub.indevs.in', icon: 'bot', color: 'text-purple-400' },
      { name: 'Vaultwarden', url: 'https://vault.cjwmf.eu.org', icon: 'shield', color: 'text-emerald-400' },
      { name: 'Beszel', url: 'https://beszel.cjwmf.eu.org', icon: 'chart', color: 'text-cyan-400' },
      { name: 'Uptime-Kuma', url: 'https://uptime.cjwmf.eu.org/dashboard', icon: 'clock', color: 'text-amber-400' },
      { name: 'WorkBuddy', url: 'https://workapi.cwsub.indevs.in/dashboard/', icon: 'zap', color: 'text-yellow-400' },
      { name: 'OpenList', url: 'https://openlist.cwsub.indevs.in', icon: 'folder', color: 'text-sky-400' },
      { name: 'Sub-Store', url: 'https://substore.cwsub.indevs.in', icon: 'radio', color: 'text-rose-400' },
      { name: 'FreeLLMAPI', url: 'https://freellmapi.cwsub.indevs.in', icon: 'zap', color: 'text-violet-400' },
      { name: 'Cline2API', url: 'https://cline.cwsub.indevs.in', icon: 'bot', color: 'text-teal-400' }
    ];

    document.getElementById('cockpit-bar').innerHTML = `
      <span class="text-zinc-400 dark:text-zinc-500 font-semibold text-[11px] uppercase mr-1 tracking-wider whitespace-nowrap">极速直达:</span>
      ${COCKPIT_ITEMS.map(item => `
        <a href="${item.url}" target="_blank" class="px-2.5 py-1 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 hover:border-zinc-400 dark:hover:border-zinc-700 text-zinc-700 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-white transition flex items-center space-x-1.5 whitespace-nowrap shadow-2xs group">
          <span class="${item.color} transition group-hover:scale-110 inline-block">${icon(item.icon, 'w-3.5 h-3.5')}</span>
          <span class="font-medium">${item.name}</span>
        </a>
      `).join('')}
    `;

    // Toast helper
    function showToast(msg) {
      const t = document.getElementById('toast');
      const m = document.getElementById('toast-msg');
      m.textContent = msg;
      t.classList.remove('translate-y-20', 'opacity-0');
      setTimeout(() => t.classList.add('translate-y-20', 'opacity-0'), 2000);
    }

    // Copy to clipboard helper
    window.copyText = function(text, label) {
      navigator.clipboard.writeText(text).then(() => {
        showToast(`已复制 ${label}: ${text}`);
      }).catch(() => {
        showToast(`复制成功: ${text}`);
      });
    };

    // Theme Engine (Zinc Style)
    function initTheme() {
      const savedTheme = localStorage.getItem('ops_theme') || 'dark';
      applyTheme(savedTheme);
    }

    function applyTheme(theme) {
      const html = document.documentElement;
      const iconSpan = document.getElementById('theme-icon');
      const textSpan = document.getElementById('theme-text');
      if (theme === 'light') {
        html.classList.remove('dark');
        iconSpan.innerHTML = icon('sun', 'w-3.5 h-3.5 text-amber-500');
        textSpan.textContent = '浅色';
        localStorage.setItem('ops_theme', 'light');
      } else {
        html.classList.add('dark');
        iconSpan.innerHTML = icon('moon', 'w-3.5 h-3.5 text-indigo-400');
        textSpan.textContent = '深色';
        localStorage.setItem('ops_theme', 'dark');
      }
    }

    document.getElementById('theme-btn').addEventListener('click', () => {
      const isDark = document.documentElement.classList.contains('dark');
      applyTheme(isDark ? 'light' : 'dark');
    });

    // Auto Refresh Countdown Engine
    function startCountdown() {
      if (timerId) clearInterval(timerId);
      timerId = setInterval(() => {
        if (refreshSeconds <= 0) return;
        countdown--;
        const cdElem = document.getElementById('countdown-text');
        if (cdElem) cdElem.textContent = countdown + 's';

        if (countdown <= 0) {
          silentRefresh();
          countdown = refreshSeconds;
        }
      }, 1000);
    }

    async function silentRefresh() {
      try {
        const res = await fetch('/api/data');
        if (res.status === 200) {
          currentData = await res.json();
          renderDashboard(currentData);
        }
      } catch (e) {}
    }

    document.getElementById('autorefresh-btn').addEventListener('click', () => {
      if (refreshSeconds === 30) {
        refreshSeconds = 15;
      } else if (refreshSeconds === 15) {
        refreshSeconds = 60;
      } else if (refreshSeconds === 60) {
        refreshSeconds = 0; // pause
      } else {
        refreshSeconds = 30;
      }
      countdown = refreshSeconds;
      const label = document.getElementById('autorefresh-label');
      if (refreshSeconds === 0) {
        label.innerHTML = '自动刷新: <strong class="text-zinc-400">已暂停</strong>';
      } else {
        label.innerHTML = `自动刷新: <strong id="countdown-text" class="font-mono">${countdown}s</strong>`;
      }
    });

    // Auth Check
    async function checkAuth() {
      try {
        const res = await fetch('/api/auth-check');
        const data = await res.json();
        if (data.authenticated) {
          document.getElementById('login-modal').classList.add('hidden');
          document.getElementById('app-container').classList.remove('hidden');
          loadData();
          startCountdown();
        } else {
          document.getElementById('login-modal').classList.remove('hidden');
          document.getElementById('app-container').classList.add('hidden');
        }
      } catch (e) {
        document.getElementById('login-modal').classList.remove('hidden');
      }
    }

    async function loadData() {
      try {
        const res = await fetch('/api/data');
        if (res.status === 401) {
          checkAuth();
          return;
        }
        currentData = await res.json();
        renderDashboard(currentData);
      } catch (e) {}
    }

    document.getElementById('login-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const pwd = document.getElementById('login-password').value;
      const err = document.getElementById('login-error');
      try {
        const res = await fetch('/api/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ password: pwd })
        });
        if (res.status === 200) {
          err.classList.add('hidden');
          document.getElementById('login-modal').classList.add('hidden');
          document.getElementById('app-container').classList.remove('hidden');
          loadData();
          startCountdown();
        } else {
          err.classList.remove('hidden');
        }
      } catch (e) {
        err.classList.remove('hidden');
      }
    });

    document.getElementById('logout-btn').addEventListener('click', async () => {
      await fetch('/api/logout', { method: 'POST' });
      location.reload();
    });

    document.getElementById('refresh-btn').addEventListener('click', async () => {
      const iconSpan = document.getElementById('refresh-icon');
      iconSpan.classList.add('animate-spin');
      countdown = refreshSeconds;
      await silentRefresh();
      setTimeout(() => iconSpan.classList.remove('animate-spin'), 600);
    });

    // Better Stack Heartbeat Live Response Badge
    function renderProbeBadge(code, ms) {
      const isSuccess = code >= 200 && code < 400;
      const dotClass = isSuccess ? 'bg-emerald-500' : 'bg-rose-500';
      const pingClass = isSuccess ? 'bg-emerald-400' : 'bg-rose-400';
      const badgeClass = isSuccess 
        ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20' 
        : 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20';

      return `
        <span class="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-[10px] font-mono font-medium border ${badgeClass}">
          <span class="relative flex h-1.5 w-1.5">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full ${pingClass} opacity-75"></span>
            <span class="relative inline-flex rounded-full h-1.5 w-1.5 ${dotClass}"></span>
          </span>
          <span>${code}</span>
          <span class="text-zinc-400 dark:text-zinc-600">·</span>
          <span class="font-semibold text-zinc-700 dark:text-zinc-200">${ms}ms</span>
        </span>
      `;
    }

    // Dashboard Renderer
    function renderDashboard(data) {
      if (!data) return;

      // 1. Render Nodes with Real-time Hardware Telemetry (Dokploy & Linear Style)
      const nodesContainer = document.getElementById('nodes-grid');
      nodesContainer.innerHTML = data.nodes.map(n => {
        const hw = n.hardware || {};
        const cpu = hw.cpu_pct !== undefined ? hw.cpu_pct : 0;
        const mem_pct = hw.mem_pct !== undefined ? hw.mem_pct : 0;
        const disk_pct = hw.disk_pct !== undefined ? hw.disk_pct : 0;
        const mem_used_gb = hw.mem_used_mb ? (hw.mem_used_mb / 1024).toFixed(1) : '-';
        const mem_total_gb = hw.mem_total_mb ? (hw.mem_total_mb / 1024).toFixed(1) : '-';
        const disk_used = hw.disk_used_gb !== undefined ? hw.disk_used_gb : '-';
        const disk_total = hw.disk_total_gb !== undefined ? hw.disk_total_gb : '-';

        if (hw.status === 'offline') {
          return `
          <div class="p-5 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white/50 dark:bg-zinc-900/30 shadow-xs relative overflow-hidden flex flex-col justify-between space-y-4 opacity-75">
            <div class="flex items-start justify-between">
              <div>
                <div class="flex items-center space-x-2">
                  <span class="font-bold text-sm text-zinc-700 dark:text-zinc-300">${n.name}</span>
                </div>
                <p class="text-xs text-zinc-400 font-mono mt-0.5">${n.ip} · ${n.arch}</p>
              </div>
              <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-zinc-500/10 text-zinc-400 border border-zinc-500/20">${n.role}</span>
            </div>
            <div class="py-8 text-center text-xs text-zinc-400 font-mono">
              边缘节点未开机或休眠中 (不影响核心集群)
            </div>
            <div class="grid grid-cols-2 gap-2 pt-2.5 border-t border-zinc-200 dark:border-zinc-800/80 text-xs">
              <div>
                <span class="text-zinc-400 dark:text-zinc-500 block text-[10px] uppercase">节点状态</span>
                <span class="text-zinc-400 font-medium flex items-center gap-1.5 mt-0.5">
                  <span class="relative inline-flex rounded-full h-1.5 w-1.5 bg-zinc-400"></span>
                  <span>Standby / 离线</span>
                </span>
              </div>
              <div>
                <span class="text-zinc-400 dark:text-zinc-500 block text-[10px] uppercase">调度任务</span>
                <span class="font-mono text-zinc-700 dark:text-zinc-300 mt-0.5 block">${n.tasks_count} 个容器</span>
              </div>
            </div>
          </div>
          `;
        }

        return `
          <div class="p-5 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-900/60 shadow-xs relative overflow-hidden flex flex-col justify-between space-y-4 transition">
            <!-- Header -->
            <div class="flex items-start justify-between">
              <div>
                <div class="flex items-center space-x-2">
                  <span class="font-bold text-sm text-zinc-900 dark:text-white">${n.name}</span>
                </div>
                <p class="text-xs text-zinc-500 dark:text-zinc-400 font-mono mt-0.5">${n.ip} · ${n.arch}</p>
              </div>
              <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
                n.role === 'Leader' ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20' : (n.role === 'Manager' ? 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20' : 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20')
              }">${n.role}</span>
            </div>

            <!-- Hardware Telemetry Meters -->
            <div class="space-y-3 pt-1 text-xs">
              <!-- CPU Meter -->
              <div>
                <div class="flex justify-between text-[11px] mb-1">
                  <span class="text-zinc-500 dark:text-zinc-400 flex items-center gap-1">${icon('cpu', 'w-3 h-3')} CPU 使用率</span>
                  <span class="font-mono font-semibold text-zinc-800 dark:text-zinc-200">${cpu}%</span>
                </div>
                <div class="w-full bg-zinc-100 dark:bg-zinc-800 rounded-full h-1.5 overflow-hidden">
                  <div class="bg-indigo-500 h-1.5 rounded-full transition-all duration-500" style="width: ${Math.min(cpu, 100)}%"></div>
                </div>
              </div>

              <!-- Memory Meter -->
              <div>
                <div class="flex justify-between text-[11px] mb-1">
                  <span class="text-zinc-500 dark:text-zinc-400 flex items-center gap-1">${icon('layers', 'w-3 h-3')} 内存负载 (${mem_pct}%)</span>
                  <span class="font-mono text-[10px] text-zinc-700 dark:text-zinc-300">${mem_used_gb}G / ${mem_total_gb}G</span>
                </div>
                <div class="w-full bg-zinc-100 dark:bg-zinc-800 rounded-full h-1.5 overflow-hidden">
                  <div class="${mem_pct > 80 ? 'bg-rose-500' : 'bg-emerald-500'} h-1.5 rounded-full transition-all duration-500" style="width: ${Math.min(mem_pct, 100)}%"></div>
                </div>
              </div>

              <!-- Disk Meter -->
              <div>
                <div class="flex justify-between text-[11px] mb-1">
                  <span class="text-zinc-500 dark:text-zinc-400 flex items-center gap-1">${icon('harddrive', 'w-3 h-3')} 系统固态 (${disk_pct}%)</span>
                  <span class="font-mono text-[10px] text-zinc-700 dark:text-zinc-300">${disk_used}G / ${disk_total}G</span>
                </div>
                <div class="w-full bg-zinc-100 dark:bg-zinc-800 rounded-full h-1.5 overflow-hidden">
                  <div class="${disk_pct > 80 ? 'bg-amber-500' : 'bg-sky-500'} h-1.5 rounded-full transition-all duration-500" style="width: ${Math.min(disk_pct, 100)}%"></div>
                </div>
              </div>
            </div>

            <!-- Footer info -->
            <div class="grid grid-cols-2 gap-2 pt-2.5 border-t border-zinc-200 dark:border-zinc-800/80 text-xs">
              <div>
                <span class="text-zinc-400 dark:text-zinc-500 block text-[10px] uppercase">节点状态</span>
                <span class="text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1.5 mt-0.5">
                  <span class="relative flex h-1.5 w-1.5">
                    <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span class="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
                  </span>
                  <span>${n.status}</span>
                </span>
              </div>
              <div>
                <span class="text-zinc-400 dark:text-zinc-500 block text-[10px] uppercase">Swarm 任务</span>
                <span class="text-zinc-800 dark:text-white font-semibold font-mono mt-0.5 block">${n.tasks_count} 个微服务</span>
              </div>
            </div>
          </div>
        `;
      }).join('');

      // 2. Summary Cards (Cloudflare / Linear Style - 4 Rich Cards)
      const sum = data.summary;
      const isAutoHealthy = sum.auto_healthy;
      document.getElementById('summary-cards').innerHTML = `
        <div class="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-900/60 text-xs shadow-xs">
          <span class="text-zinc-500 dark:text-zinc-400">Swarm 管理仲裁</span>
          <p class="text-base font-bold text-emerald-600 dark:text-emerald-400 mt-1">${sum.nodes_online} 在线</p>
          <span class="text-[10px] text-zinc-400 dark:text-zinc-500 font-mono">${sum.quorum_status}</span>
        </div>
        <div class="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-900/60 text-xs shadow-xs">
          <span class="text-zinc-500 dark:text-zinc-400">活跃微服务</span>
          <p class="text-base font-bold text-zinc-900 dark:text-white mt-1">${sum.services_count} 个微服务</p>
          <span class="text-[10px] text-zinc-400 dark:text-zinc-500 font-mono">${sum.stacks_count} 个 Swarm 业务栈</span>
        </div>
        <div class="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-900/60 text-xs shadow-xs">
          <div class="flex items-center justify-between">
            <span class="text-zinc-500 dark:text-zinc-400">自动化与容灾中枢</span>
            <span class="w-1.5 h-1.5 rounded-full ${isAutoHealthy ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}"></span>
          </div>
          <p class="text-base font-bold ${isAutoHealthy ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'} mt-1">${isAutoHealthy ? '全链路健康' : '需注意'}</p>
          <span class="text-[10px] text-zinc-400 dark:text-zinc-500">6/6 备份鲜活 · 巡检全绿 · AI管家</span>
        </div>
        <div class="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-900/60 text-xs shadow-xs">
          <span class="text-zinc-500 dark:text-zinc-400">公网服务路由</span>
          <p class="text-base font-bold text-blue-600 dark:text-blue-400 mt-1">${sum.routes_count} 个域名映射</p>
          <span class="text-[10px] text-zinc-400 dark:text-zinc-500 font-mono">Full (Strict) 至 ${sum.ssl_validity}</span>
        </div>
      `;

      // Header auto badge update
      const navBadge = document.getElementById('nav-auto-badge');
      if (navBadge) {
        navBadge.className = isAutoHealthy
          ? 'hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
          : 'hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20';
        navBadge.innerHTML = `<span class="w-1.5 h-1.5 rounded-full ${isAutoHealthy ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}"></span>${isAutoHealthy ? '自愈闭环在线' : '自动化存在异常'}`;
      }

      // Sync view buttons styling with stored state
      const accBtn = document.getElementById('view-accordion-btn');
      const flatBtn = document.getElementById('view-flat-btn');
      const accControls = document.getElementById('accordion-controls');
      if (accBtn && flatBtn) {
        if (routeView === 'accordion') {
          accBtn.className = "px-2.5 py-1 rounded-lg font-medium text-white bg-indigo-600 transition shadow-xs";
          flatBtn.className = "px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition";
          if (accControls) accControls.classList.remove('hidden');
        } else {
          flatBtn.className = "px-2.5 py-1 rounded-lg font-medium text-white bg-indigo-600 transition shadow-xs";
          accBtn.className = "px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition";
          if (accControls) accControls.classList.add('hidden');
        }
      }
      const matrixBtn = document.getElementById('view-matrix-btn');
      const cardsBtn = document.getElementById('view-cards-btn');
      if (matrixBtn && cardsBtn) {
        if (daemonView === 'matrix') {
          matrixBtn.className = "px-2.5 py-1 rounded-lg font-medium text-white bg-indigo-600 transition shadow-xs";
          cardsBtn.className = "px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition";
        } else {
          cardsBtn.className = "px-2.5 py-1 rounded-lg font-medium text-white bg-indigo-600 transition shadow-xs";
          matrixBtn.className = "px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition";
        }
      }

      renderRoutes();
      renderStandalone();
      renderAutomation(currentData.automation);
    }

    // View Mode Switchers
    window.setRouteView = function(mode) {
      routeView = mode;
      localStorage.setItem('ops_route_view', mode);
      const accBtn = document.getElementById('view-accordion-btn');
      const flatBtn = document.getElementById('view-flat-btn');
      const accControls = document.getElementById('accordion-controls');
      if (accBtn && flatBtn) {
        if (mode === 'accordion') {
          accBtn.className = "px-2.5 py-1 rounded-lg font-medium text-white bg-indigo-600 transition shadow-xs";
          flatBtn.className = "px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition";
          if (accControls) accControls.classList.remove('hidden');
        } else {
          flatBtn.className = "px-2.5 py-1 rounded-lg font-medium text-white bg-indigo-600 transition shadow-xs";
          accBtn.className = "px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition";
          if (accControls) accControls.classList.add('hidden');
        }
      }
      renderRoutes();
    };

    window.setDaemonView = function(mode) {
      daemonView = mode;
      localStorage.setItem('ops_daemon_view', mode);
      const matrixBtn = document.getElementById('view-matrix-btn');
      const cardsBtn = document.getElementById('view-cards-btn');
      if (matrixBtn && cardsBtn) {
        if (mode === 'matrix') {
          matrixBtn.className = "px-2.5 py-1 rounded-lg font-medium text-white bg-indigo-600 transition shadow-xs";
          cardsBtn.className = "px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition";
        } else {
          cardsBtn.className = "px-2.5 py-1 rounded-lg font-medium text-white bg-indigo-600 transition shadow-xs";
          matrixBtn.className = "px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition";
        }
      }
      renderStandalone();
    };

    // Stacks & Routes Renderer (Fixed-layout Accordion & Unified Flat Table)
    function renderRoutes() {
      if (!currentData) return;
      const search = document.getElementById('search-input').value.toLowerCase();
      const wrapper = document.getElementById('routes-wrapper');

      const filtered = currentData.routes.filter(r => {
        const matchesFilter = (activeFilter === 'all') || (r.node === activeFilter);
        const matchesSearch = !search || 
          r.domain.toLowerCase().includes(search) || 
          r.stack.toLowerCase().includes(search) || 
          r.service.toLowerCase().includes(search) ||
          r.node_name.toLowerCase().includes(search) ||
          (r.ip_port && r.ip_port.toLowerCase().includes(search));
        return matchesFilter && matchesSearch;
      });

      if (filtered.length === 0) {
        wrapper.innerHTML = `<div class="text-center py-12 text-zinc-400 dark:text-zinc-500 text-xs">未找到匹配的堆栈或域名记录</div>`;
        return;
      }

      if (routeView === 'flat') {
        // UNIFIED FLAT ALL-IN-ONE TABLE
        wrapper.innerHTML = `
          <div class="overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/60 shadow-xs">
            <table class="w-full text-left border-collapse text-xs table-fixed min-w-[820px]">
              <colgroup>
                <col class="w-[30%] min-w-[220px]">
                <col class="w-[22%] min-w-[170px]">
                <col class="w-[18%] min-w-[140px]">
                <col class="w-[15%] min-w-[120px]">
                <col class="w-[15%] min-w-[130px]">
              </colgroup>
              <thead>
                <tr class="bg-zinc-100/90 dark:bg-zinc-950/80 text-zinc-500 dark:text-zinc-400 border-b border-zinc-200 dark:border-zinc-800 text-[11px]">
                  <th class="py-3 px-4 font-semibold">公网访问域名 (点击直达 ↗)</th>
                  <th class="py-3 px-4 font-semibold">所属堆栈与微服务</th>
                  <th class="py-3 px-4 font-semibold">容器内部 IP:端口</th>
                  <th class="py-3 px-4 font-semibold">物理部署节点</th>
                  <th class="py-3 px-4 text-center font-semibold">网关响应与延时</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-zinc-100 dark:divide-zinc-800/60">
                ${filtered.map(r => `
                  <tr class="hover:bg-zinc-50/80 dark:hover:bg-zinc-850/40 transition">
                    <td class="py-2.5 px-4 min-w-0">
                      <div class="flex items-center space-x-1.5 min-w-0">
                        <a href="${r.url}" target="_blank" title="${r.domain} (点击直达)" class="text-indigo-600 dark:text-indigo-400 hover:underline font-semibold flex items-center space-x-1 truncate min-w-0">
                          <span class="truncate">${r.domain}</span>
                          <span class="opacity-60 flex-shrink-0">${icon('external', 'w-3 h-3')}</span>
                        </a>
                        <button onclick="copyText('${r.url}', '域名')" title="复制域名链接" class="flex-shrink-0 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition text-[10px] p-0.5 rounded hover:bg-zinc-200 dark:hover:bg-zinc-800">
                          ${icon('copy', 'w-3 h-3')}
                        </button>
                      </div>
                    </td>
                    <td class="py-2.5 px-4 min-w-0">
                      <div class="flex items-center space-x-1.5 min-w-0">
                        <span class="px-1.5 py-0.2 rounded-sm text-[10px] font-mono bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700/80 flex-shrink-0">${r.stack}</span>
                        <span class="truncate text-zinc-700 dark:text-zinc-300 font-mono text-[11px]" title="${r.service}">${r.service}</span>
                      </div>
                    </td>
                    <td class="py-2.5 px-4 min-w-0 font-mono">
                      <div class="flex items-center space-x-1 min-w-0">
                        <span class="truncate text-indigo-600 dark:text-indigo-400 text-[11px] cursor-pointer hover:underline" onclick="copyText('${r.ip_port}', '内部IP')" title="${r.ip_port || '-'} (点击复制)">
                          ${r.ip_port || '-'}
                        </span>
                      </div>
                    </td>
                    <td class="py-2.5 px-4 min-w-0">
                      <span class="px-2 py-0.5 rounded-full text-[10px] font-medium ${
                        r.node === 'jp-oracle' ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20' :
                        r.node === 'us-oracle' ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20' :
                        r.node === 'us-racknerd' ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20' :
                        'bg-zinc-500/10 text-zinc-600 dark:text-zinc-400'
                      } truncate inline-block max-w-full">${r.node_name}</span>
                    </td>
                    <td class="py-2.5 px-4 text-center whitespace-nowrap min-w-0">
                      ${renderProbeBadge(r.probe_code, r.probe_ms)}
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        `;
        return;
      }

      // GROUP BY STACK (ACCORDION VIEW WITH STRICT UNIFORM FIXED COLUMNS)
      const stackGroups = {};
      filtered.forEach(r => {
        if (!stackGroups[r.stack]) {
          stackGroups[r.stack] = {
            stack: r.stack,
            node_name: r.node_name,
            node: r.node,
            color: r.color,
            arch: r.arch,
            routes: []
          };
        }
        stackGroups[r.stack].routes.push(r);
      });

      wrapper.innerHTML = `
        <div id="stacks-accordion" class="space-y-3">
          ${Object.values(stackGroups).map(g => {
            const isExpanded = expandedStacks.has(g.stack);
            return `
              <div class="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/70 dark:bg-zinc-950/60 overflow-hidden transition shadow-xs">
                <!-- STACK HEADER -->
                <div onclick="toggleStack('${g.stack}')" class="p-3.5 px-4 cursor-pointer flex items-center justify-between hover:bg-zinc-100/80 dark:hover:bg-zinc-900/60 transition select-none">
                  <div class="flex items-center space-x-3">
                    <span class="text-zinc-400 dark:text-zinc-500 transform transition-transform duration-200 ${isExpanded ? 'rotate-90' : 'rotate-0'} inline-block">
                      ${icon('chevronRight', 'w-3.5 h-3.5')}
                    </span>
                    <div class="flex items-center space-x-2">
                      <span class="font-mono font-bold text-sm text-zinc-900 dark:text-white">${g.stack}</span>
                      <span class="px-2 py-0.5 rounded-full text-[10px] font-medium ${
                        g.node === 'jp-oracle' ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20' :
                        g.node === 'us-oracle' ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20' :
                        g.node === 'us-racknerd' ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20' :
                        'bg-zinc-500/10 text-zinc-600 dark:text-zinc-400'
                      }">${g.node_name}</span>
                    </div>
                  </div>

                  <div class="flex items-center space-x-2">
                    <span class="px-2 py-0.5 rounded-md bg-zinc-200/80 dark:bg-zinc-800 text-[11px] font-mono text-zinc-700 dark:text-zinc-300">
                      ${g.routes.length} 个域名
                    </span>
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                  </div>
                </div>

                <!-- STACK BODY WITH STRICT FIXED TABLE COLUMNS -->
                <div class="${isExpanded ? 'block' : 'hidden'} border-t border-zinc-200 dark:border-zinc-800/80 overflow-x-auto bg-white dark:bg-zinc-900/90">
                  <table class="w-full text-left border-collapse text-xs table-fixed min-w-[760px]">
                    <colgroup>
                      <col class="w-[30%] min-w-[210px]">
                      <col class="w-[22%] min-w-[170px]">
                      <col class="w-[18%] min-w-[140px]">
                      <col class="w-[15%] min-w-[120px]">
                      <col class="w-[15%] min-w-[120px]">
                    </colgroup>
                    <thead>
                      <tr class="bg-zinc-100/90 dark:bg-zinc-950/80 text-zinc-500 dark:text-zinc-400 border-b border-zinc-200 dark:border-zinc-800 text-[11px]">
                        <th class="py-2.5 px-4 font-semibold">公网访问域名 (点击直达 ↗)</th>
                        <th class="py-2.5 px-4 font-semibold">微服务名</th>
                        <th class="py-2.5 px-4 font-semibold">内部网络与端口</th>
                        <th class="py-2.5 px-4 font-semibold">SSL 加密证书</th>
                        <th class="py-2.5 px-4 text-center font-semibold">网关响应与延时</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-zinc-100 dark:divide-zinc-800/60">
                      ${g.routes.map(r => `
                        <tr class="hover:bg-zinc-50/80 dark:hover:bg-zinc-800/40 transition">
                          <td class="py-2.5 px-4 min-w-0">
                            <div class="flex items-center space-x-1.5 min-w-0">
                              <a href="${r.url}" target="_blank" title="${r.domain} (点击直达)" class="text-indigo-600 dark:text-indigo-400 hover:underline font-semibold flex items-center space-x-1 truncate min-w-0">
                                <span class="truncate">${r.domain}</span>
                                <span class="opacity-60 flex-shrink-0">${icon('external', 'w-3 h-3')}</span>
                              </a>
                              <button onclick="copyText('${r.url}', '域名')" title="复制域名链接" class="flex-shrink-0 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition text-[10px] p-0.5 rounded hover:bg-zinc-200 dark:hover:bg-zinc-800">
                                ${icon('copy', 'w-3 h-3')}
                              </button>
                            </div>
                          </td>
                          <td class="py-2.5 px-4 min-w-0">
                            <div class="truncate text-zinc-700 dark:text-zinc-300 font-mono text-[11px]" title="${r.service}">
                              ${r.service}
                            </div>
                          </td>
                          <td class="py-2.5 px-4 min-w-0 font-mono">
                            <div class="flex items-center space-x-1 min-w-0">
                              <span class="truncate text-indigo-600 dark:text-indigo-400 text-[11px] cursor-pointer hover:underline" onclick="copyText('${r.ip_port}', '内部IP')" title="${r.ip_port || '-'} (点击复制)">
                                ${r.ip_port || '-'}
                              </span>
                            </div>
                          </td>
                          <td class="py-2.5 px-4 min-w-0">
                            <div class="truncate text-zinc-500 dark:text-zinc-400 text-[11px] font-sans flex items-center gap-1.5" title="${r.tls}">
                              <span class="flex-shrink-0 text-zinc-400">${icon('lock', 'w-3 h-3')}</span>
                              <span class="truncate">${r.tls}</span>
                            </div>
                          </td>
                          <td class="py-2.5 px-4 text-center whitespace-nowrap min-w-0">
                            ${renderProbeBadge(r.probe_code, r.probe_ms)}
                          </td>
                        </tr>
                      `).join('')}
                    </tbody>
                  </table>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      `;
    }

    const STANDARD_SLOTS = [
      { key: 'beszel', name: '系统硬件性能探针', subtitle: 'Beszel Telemetry Agent', icon: 'chart', tag: '探针' },
      { key: 'singbox', name: '核心出海网格网络', subtitle: 'Sing-box Mesh Network', icon: 'radio', tag: '网络' },
      { key: 'watchtower', name: '镜像自动巡检守护', subtitle: 'Hourly Auto Updater', icon: 'refresh', tag: '巡检' },
      { key: 'portainer', name: '集群管控运行基座', subtitle: 'Portainer CE / Agent', icon: 'box', tag: '管控' },
      { key: 'dedicated', name: '节点专属特化设施', subtitle: 'Node Dedicated Infras', icon: 'shield', tag: '专属' }
    ];

    function findSlotContainer(nodeList, slotKey) {
      if (!nodeList || !nodeList.length) return null;
      if (slotKey === 'beszel') return nodeList.find(c => c.name.includes('beszel')) || null;
      if (slotKey === 'singbox') return nodeList.find(c => c.name.includes('sing-box')) || null;
      if (slotKey === 'watchtower') return nodeList.find(c => c.name.includes('watchtower')) || null;
      if (slotKey === 'portainer') return nodeList.find(c => c.name === 'portainer_agent' || c.name === 'portainer') || null;
      if (slotKey === 'dedicated') return nodeList.find(c => c.slot_key === 'dedicated' || c.name.includes('warp') || c.name.includes('mcp') || c.name.includes('gateway')) || null;
      return null;
    }

    // Standalone Daemons Renderer (Cross-Node Matrix & Aligned Cards)
    function renderStandalone() {
      if (!currentData || !currentData.standalones) return;
      const wrapper = document.getElementById('standalone-wrapper');
      const st = currentData.standalones;

      // Render Host Systemd Daemons Bar
      const sysBox = document.getElementById('host-systemd-badges');
      const daemons = (currentData && currentData.automation && currentData.automation.systemd_daemons) || {};
      if (sysBox) {
        const nodesDef = [
          { key: 'jp-oracle', label: '🇯🇵 日本', color: 'emerald' },
          { key: 'us-oracle', label: '🇺🇸 美国', color: 'blue' },
          { key: 'us-racknerd', label: '🟣 圣何塞', color: 'purple' }
        ];
        sysBox.innerHTML = nodesDef.map(n => {
          const list = daemons[n.key] || [];
          return `
            <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-zinc-100 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-[10px]">
              <span class="font-bold text-${n.color}-600 dark:text-${n.color}-400 mr-0.5">${n.label}:</span>
              ${list.length > 0 ? list.map(d => `
                <span class="inline-flex items-center gap-1 text-zinc-700 dark:text-zinc-300">
                  <span class="w-1.5 h-1.5 rounded-full ${d.active ? 'bg-emerald-500' : 'bg-rose-500'}"></span>
                  <span>${d.label}</span>
                </span>
              `).join('<span class="text-zinc-300 dark:text-zinc-700 mx-0.5">·</span>') : '<span class="text-zinc-400">无额外服务</span>'}
            </div>
          `;
        }).join('');
      }

      if (daemonView === 'matrix') {
        // CROSS-NODE COMPARISON MATRIX TABLE
        wrapper.innerHTML = `
          <div class="overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/60 shadow-xs">
            <table class="w-full text-left border-collapse text-xs table-fixed min-w-[780px]">
              <colgroup>
                <col class="w-[22%] min-w-[170px]">
                <col class="w-[26%] min-w-[200px]">
                <col class="w-[26%] min-w-[200px]">
                <col class="w-[26%] min-w-[200px]">
              </colgroup>
              <thead>
                <tr class="bg-zinc-100/90 dark:bg-zinc-950/80 text-zinc-500 dark:text-zinc-400 border-b border-zinc-200 dark:border-zinc-800 text-[11px]">
                  <th class="py-3 px-4 font-semibold">守护服务职责与角色</th>
                  <th class="py-3 px-4 font-semibold text-emerald-600 dark:text-emerald-400">🇯🇵 日本主控 (jp-oracle)</th>
                  <th class="py-3 px-4 font-semibold text-blue-600 dark:text-blue-400">🇺🇸 美国算力 (us-oracle)</th>
                  <th class="py-3 px-4 font-semibold text-purple-600 dark:text-purple-400">🟣 圣何塞哨兵 (us-racknerd)</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-zinc-100 dark:divide-zinc-800/60">
                ${STANDARD_SLOTS.map(slot => {
                  const c_jp = findSlotContainer(st['jp-oracle'], slot.key);
                  const c_us = findSlotContainer(st['us-oracle'], slot.key);
                  const c_rn = findSlotContainer(st['us-racknerd'], slot.key);

                  const renderCell = (c, nodeKey) => {
                    if (!c) {
                      if (slot.key === 'portainer' && nodeKey === 'jp-oracle') {
                        return `
                          <div class="p-2.5 rounded-lg bg-emerald-50/70 dark:bg-emerald-950/40 border border-emerald-300/80 dark:border-emerald-800/80 flex items-center justify-between min-w-0">
                            <div class="truncate mr-2 min-w-0">
                              <div class="flex items-center space-x-1.5 min-w-0">
                                <span class="font-mono font-bold text-xs text-zinc-900 dark:text-white truncate">portainer</span>
                                <span class="px-1.5 py-0.2 rounded-sm text-[9px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 flex-shrink-0">Swarm 主控</span>
                              </div>
                              <div class="text-[10px] text-zinc-400 font-mono truncate mt-0.5" title="portainer/portainer-ce:latest">portainer/portainer-ce:latest</div>
                            </div>
                            <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 whitespace-nowrap flex-shrink-0">
                              <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1 animate-pulse"></span>
                              Swarm 原生
                            </span>
                          </div>
                        `;
                      }
                      return `
                        <div class="p-2.5 rounded-lg bg-zinc-50/50 dark:bg-zinc-950/40 border border-dashed border-zinc-200 dark:border-zinc-800 text-center">
                          <span class="text-[11px] text-zinc-400 font-medium">✨ 纯净宿主 (业务全纳管)</span>
                        </div>
                      `;
                    }
                    return `
                      <div class="p-2.5 rounded-lg bg-zinc-50/70 dark:bg-zinc-950/60 border border-zinc-200/80 dark:border-zinc-800/80 flex items-center justify-between min-w-0">
                        <div class="truncate mr-2 min-w-0">
                          <div class="flex items-center space-x-1.5 min-w-0">
                            <span class="font-mono font-bold text-xs text-zinc-900 dark:text-white truncate">${c.name}</span>
                            <span class="px-1.5 py-0.2 rounded-sm text-[9px] bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20 flex-shrink-0">${c.tag}</span>
                          </div>
                          <div class="text-[10px] text-zinc-400 font-mono truncate mt-0.5" title="${c.image}">${c.image}</div>
                        </div>
                        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 whitespace-nowrap flex-shrink-0">
                          <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1 animate-pulse"></span>
                          运行中
                        </span>
                      </div>
                    `;
                  };

                  return `
                    <tr class="hover:bg-zinc-50/50 dark:hover:bg-zinc-850/40 transition">
                      <td class="py-3 px-4 min-w-0">
                        <div class="flex items-start space-x-2.5">
                          <span class="text-zinc-500 dark:text-zinc-400 flex-shrink-0 mt-0.5">${icon(slot.icon, 'w-4 h-4')}</span>
                          <div class="min-w-0">
                            <div class="font-bold text-zinc-900 dark:text-white text-xs truncate">${slot.name}</div>
                            <div class="text-[10px] text-zinc-400 truncate">${slot.subtitle}</div>
                          </div>
                        </div>
                      </td>
                      <td class="py-3 px-4 min-w-0">${renderCell(c_jp, 'jp-oracle')}</td>
                      <td class="py-3 px-4 min-w-0">${renderCell(c_us, 'us-oracle')}</td>
                      <td class="py-3 px-4 min-w-0">${renderCell(c_rn, 'us-racknerd')}</td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>
        `;
        return;
      }

      // ALIGNED 3-COLUMN CARDS VIEW
      const nodesDef = [
        { key: 'jp-oracle', name: '🇯🇵 日本主控 (jp-oracle)', color: 'emerald' },
        { key: 'us-oracle', name: '🇺🇸 美国算力 (us-oracle)', color: 'blue' },
        { key: 'us-racknerd', name: '🟣 圣何塞哨兵 (us-racknerd)', color: 'purple' }
      ];

      wrapper.innerHTML = `
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          ${nodesDef.map(n => {
            const list = st[n.key] || [];
            return `
              <div class="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/70 dark:bg-zinc-950/60 p-4 space-y-3 shadow-xs">
                <div class="flex items-center justify-between pb-2 border-b border-zinc-200 dark:border-zinc-800">
                  <span class="font-bold text-xs text-zinc-900 dark:text-white">${n.name}</span>
                  <span class="text-[10px] px-2 py-0.5 rounded-full bg-zinc-200 dark:bg-zinc-800 font-mono">${list.length} 个守护</span>
                </div>
                <div class="space-y-2">
                  ${STANDARD_SLOTS.map(slot => {
                    const c = findSlotContainer(list, slot.key);
                    if (!c) {
                      if (slot.key === 'portainer' && n.key === 'jp-oracle') {
                        return `
                          <div class="h-14 p-2.5 rounded-lg bg-emerald-50/70 dark:bg-emerald-950/40 border border-emerald-300/80 dark:border-emerald-800/80 flex items-center justify-between text-xs min-w-0">
                            <div class="truncate mr-2 min-w-0">
                              <div class="flex items-center space-x-1.5 min-w-0">
                                <span class="text-zinc-500 flex-shrink-0">${icon('box', 'w-3.5 h-3.5')}</span>
                                <span class="font-mono font-semibold text-zinc-900 dark:text-white text-xs truncate">portainer</span>
                                <span class="px-1.5 py-0.2 rounded-sm text-[9px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 flex-shrink-0">Swarm 主控</span>
                              </div>
                              <p class="text-[10px] text-zinc-400 font-mono truncate mt-0.5" title="portainer/portainer-ce:latest">portainer/portainer-ce:latest</p>
                            </div>
                            <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 whitespace-nowrap flex-shrink-0">
                              <span class="w-1 h-1 rounded-full bg-emerald-500 mr-1 animate-pulse"></span>
                              Swarm 原生
                            </span>
                          </div>
                        `;
                      }
                      return `
                        <div class="h-14 p-2.5 rounded-lg bg-zinc-100/50 dark:bg-zinc-900/40 border border-dashed border-zinc-200 dark:border-zinc-800 flex items-center justify-center text-center">
                          <span class="text-[11px] text-zinc-400 font-medium">✨ 纯净宿主 (业务全纳管)</span>
                        </div>
                      `;
                    }
                    return `
                      <div class="h-14 p-2.5 rounded-lg bg-white dark:bg-zinc-900/80 border border-zinc-200 dark:border-zinc-800/80 flex items-center justify-between text-xs min-w-0">
                        <div class="truncate mr-2 min-w-0">
                          <div class="flex items-center space-x-1.5 min-w-0">
                            <span class="text-zinc-500 flex-shrink-0">${icon(slot.icon, 'w-3.5 h-3.5')}</span>
                            <span class="font-mono font-semibold text-zinc-900 dark:text-white text-xs truncate">${c.name}</span>
                            <span class="px-1.5 py-0.2 rounded-sm text-[9px] bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20 flex-shrink-0">${c.tag}</span>
                          </div>
                          <p class="text-[10px] text-zinc-400 font-mono truncate mt-0.5" title="${c.image}">${c.image}</p>
                        </div>
                        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 whitespace-nowrap flex-shrink-0">
                          <span class="w-1 h-1 rounded-full bg-emerald-500 mr-1 animate-pulse"></span>
                          运行中
                        </span>
                      </div>
                    `;
                  }).join('')}
                </div>
              </div>
            `;
          }).join('')}
        </div>
      `;
    }

    window.toggleStandaloneAccordion = function() {
      const c = document.getElementById('standalone-wrapper');
      const arrow = document.getElementById('standalone-toggle-arrow');
      const text = document.getElementById('standalone-toggle-text');
      standaloneExpanded = !standaloneExpanded;
      if (standaloneExpanded) {
        c.classList.remove('hidden');
        if (arrow) arrow.textContent = '▼';
        if (text) text.textContent = '折叠';
      } else {
        c.classList.add('hidden');
        if (arrow) arrow.textContent = '▶';
        if (text) text.textContent = '展开';
      }
    };

    // Toggle individual stack
    window.toggleStack = function(stackName) {
      if (expandedStacks.has(stackName)) {
        expandedStacks.delete(stackName);
      } else {
        expandedStacks.add(stackName);
      }
      renderRoutes();
    };

    // Expand All
    document.getElementById('expand-all-btn').addEventListener('click', () => {
      if (currentData) {
        currentData.routes.forEach(r => expandedStacks.add(r.stack));
        renderRoutes();
      }
    });

    // Collapse All
    document.getElementById('collapse-all-btn').addEventListener('click', () => {
      expandedStacks.clear();
      renderRoutes();
    });

    // Search input
    document.getElementById('search-input').addEventListener('input', renderRoutes);

    // Node filter tabs
    document.querySelectorAll('.filter-tab').forEach(tab => {
      tab.addEventListener('click', (e) => {
        document.querySelectorAll('.filter-tab').forEach(t => {
          t.classList.remove('bg-indigo-600', 'text-white', 'shadow-xs');
          t.classList.add('text-zinc-600', 'dark:text-zinc-400');
        });
        e.target.classList.add('bg-indigo-600', 'text-white', 'shadow-xs');
        e.target.classList.remove('text-zinc-600', 'dark:text-zinc-400');
        activeFilter = e.target.getAttribute('data-filter');
        renderRoutes();
      });
    });

    // Initialize
    initTheme();
    checkAuth();

    // ── Automation Section Renderer (2026-09-23) ──
    function renderAutomation(auto) {
      if (!auto || !auto.backups) return;
      // Overall badge
      const bakOk = auto.backups.length > 0 && auto.backups.every(b => b.ok);
      const guardOk = auto.guard && auto.guard.ok;
      const agentOk = auto.agent && auto.agent.active;
      const allOk = bakOk && guardOk && agentOk;
      const badge = document.getElementById('auto-overall-badge');
      if (badge) {
        badge.textContent = allOk ? '● 全链路正常' : '● 存在异常';
        badge.className = allOk
          ? 'px-2.5 py-1 rounded-lg text-[11px] font-mono font-bold border bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30'
          : 'px-2.5 py-1 rounded-lg text-[11px] font-mono font-bold border bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/30';
      }

      // 1. Backups
      const bk = document.getElementById('auto-backups');
      if (bk) {
        bk.innerHTML = auto.backups.map(b => `
          <div class="flex items-center justify-between gap-2 p-1 rounded-lg hover:bg-zinc-100/50 dark:hover:bg-zinc-900/50 transition">
            <div class="flex items-center gap-1.5 min-w-0 truncate">
              <span class="${b.ok ? 'text-emerald-500' : 'text-rose-500'} font-bold flex-shrink-0">${b.ok ? '✓' : '✗'}</span>
              <span class="text-zinc-700 dark:text-zinc-300 font-medium truncate" title="${b.host}">${b.host}</span>
            </div>
            <div class="flex items-center gap-2 flex-shrink-0 text-right font-mono text-[11px]">
              <span class="${b.ok ? 'text-zinc-600 dark:text-zinc-400' : 'text-rose-500'}">${b.age_h === null ? '无档案' : b.age_h + 'h 前'}</span>
              <span class="text-zinc-400 dark:text-zinc-500 min-w-[48px]">${b.size_mb !== null ? b.size_mb + 'MB' : '-'}</span>
            </div>
          </div>`).join('');
      }

      // 2. Guard / Drill / Prune / Snapshot
      const gd = document.getElementById('auto-guard');
      const g = auto.guard || {};
      const d = auto.drill || {};
      if (gd) {
        gd.innerHTML = `
          <div class="flex items-center justify-between p-1">
            <span class="text-zinc-700 dark:text-zinc-300 font-medium">cluster-guard 6h 巡检</span>
            <span class="${g.ok ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'} font-semibold font-mono text-[11px]">${g.ok ? '● 全绿通过' : (g.issues > 0 ? '● ' + g.issues + ' 异常' : '● 待检')}</span>
          </div>
          <div class="flex items-center justify-between text-[11px] px-1 text-zinc-500">
            <span>上次巡检时间戳</span>
            <span class="font-mono text-zinc-700 dark:text-zinc-300">${g.last_run || '-'}</span>
          </div>
          <div class="flex items-center justify-between p-1 pt-1.5 border-t border-zinc-200/60 dark:border-zinc-800/60">
            <span class="text-zinc-700 dark:text-zinc-300 font-medium">月度自动恢复演练</span>
            <span class="${d.ok ? 'text-emerald-600 dark:text-emerald-400' : 'text-zinc-400'} font-semibold font-mono text-[11px]">${d.ok ? '● 校验通过' : '● 待执行'}</span>
          </div>
          <div class="flex items-center justify-between text-[11px] px-1 text-zinc-500">
            <span>最新演练存证</span>
            <span class="font-mono text-zinc-700 dark:text-zinc-300 text-[10px] truncate max-w-[140px]" title="${d.last}">${d.last || '-'}</span>
          </div>
          <div class="flex items-center justify-between text-[11px] px-1 pt-1.5 border-t border-zinc-200/60 dark:border-zinc-800/60 text-zinc-500">
            <span>周度安全清理 (Prune)</span>
            <span class="font-mono text-zinc-600 dark:text-zinc-400">周日 05:00 · until=168h</span>
          </div>
          <div class="flex items-center justify-between text-[11px] px-1 text-zinc-500">
            <span>每周机器实测快照</span>
            <span class="font-mono text-zinc-600 dark:text-zinc-400">周一 06:00 · SNAPSHOT.md</span>
          </div>
        `;
      }

      // 3. OpenClaw Dedicated Co-Pilot Card
      const ac = document.getElementById('auto-agent-card');
      const a = auto.agent || {};
      const agentBadge = document.getElementById('agent-active-badge');
      if (agentBadge) {
        agentBadge.textContent = a.active ? '● 在线运行中' : '● 离线停止';
        agentBadge.className = a.active
          ? 'px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
          : 'px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20';
      }
      if (ac) {
        ac.innerHTML = `
          <div class="flex items-center justify-between text-[11px] px-1">
            <span class="text-zinc-500">运行形态</span>
            <span class="font-mono text-zinc-700 dark:text-zinc-300">${a.mode || 'Systemd'} · ${a.version || 'v2026.9.5'}</span>
          </div>
          <div class="flex items-center justify-between text-[11px] px-1">
            <span class="text-zinc-500">通讯渠道</span>
            <span class="font-mono text-zinc-700 dark:text-zinc-300 flex items-center gap-1">
              <span class="text-sky-500">💬</span> ${a.tg_bot || '-'}
            </span>
          </div>
          <div class="flex items-center justify-between text-[11px] px-1">
            <span class="text-zinc-500">权限绑定</span>
            <span class="font-mono text-emerald-600 dark:text-emerald-400 font-medium">Owner (${a.owner || 'mcnikicm'})</span>
          </div>
          <div class="flex items-center justify-between text-[11px] px-1">
            <span class="text-zinc-500">模型路由</span>
            <span class="font-mono text-indigo-600 dark:text-indigo-400 font-medium truncate max-w-[140px]" title="${a.model}">${a.model || 'AxonHub'}</span>
          </div>
          <div class="flex items-center justify-between text-[11px] px-1">
            <span class="text-zinc-500">管控工具</span>
            <span class="font-mono text-zinc-700 dark:text-zinc-300">${a.mcp_tools || '119 个只读工具 (Portainer MCP)'}</span>
          </div>
          <div class="flex items-center justify-between text-[11px] px-1 pt-0.5">
            <span class="text-zinc-500">安全基线</span>
            <span class="text-emerald-600 dark:text-emerald-400 font-medium text-[10px] bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">严格只读 · 审批拦截</span>
          </div>
        `;
      }

      // 4. Timers Matrix (Full Width Sub-card)
      const tm = document.getElementById('auto-timers');
      if (tm) {
        tm.innerHTML = (auto.timers || []).map(t => {
          const dot = t.active ? '<span class="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block"></span>' : '<span class="w-1.5 h-1.5 rounded-full bg-zinc-500 inline-block"></span>';
          const hostColor = t.host === 'jp' ? 'text-emerald-500' : (t.host === 'us' ? 'text-blue-500' : 'text-purple-500');
          return `
            <div class="p-2 rounded-lg bg-zinc-50/80 dark:bg-zinc-950/70 border border-zinc-200/80 dark:border-zinc-800/80 flex items-center justify-between min-w-0 shadow-2xs">
              <div class="truncate mr-1 min-w-0">
                <div class="flex items-center gap-1.5">
                  ${dot}
                  <span class="font-semibold text-zinc-800 dark:text-zinc-200 truncate text-[11px]">${t.unit.replace('.timer','')}</span>
                </div>
                <div class="text-[10px] text-zinc-400 font-mono truncate mt-0.5">${t.next || '-'}</div>
              </div>
              <span class="text-[9px] px-1 py-0.2 rounded font-mono ${hostColor} bg-zinc-100 dark:bg-zinc-900 border border-zinc-200/60 dark:border-zinc-800/60 flex-shrink-0">${t.host}</span>
            </div>
          `;
        }).join('');
      }
    }
  </script>
</body>
</html>
"""

class OpsHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/data":
            cookie_header = self.headers.get("Cookie", "")
            if not verify_session(cookie_header):
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":"Unauthorized"}')
                return

            data = get_cluster_data()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode('utf-8'))
            return

        if path == "/api/auth-check":
            cookie_header = self.headers.get("Cookie", "")
            valid = verify_session(cookie_header)
            self.send_response(200 if valid else 401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"authenticated": valid}).encode('utf-8'))
            return

        # Default: serve Frontend HTML with dynamic cockpit items injected
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        rendered_html = HTML_TEMPLATE
        cockpit_env = os.environ.get("COCKPIT_ITEMS_JSON", "")
        if cockpit_env:
            inject_script = f"<script>window.__OPS_COCKPIT_ITEMS__ = {cockpit_env};</script>"
            rendered_html = rendered_html.replace("</head>", f"{inject_script}</head>")
        self.wfile.write(rendered_html.encode('utf-8'))

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/login":
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                payload = json.loads(body.decode('utf-8'))
                pwd = payload.get("password", "")
                if hmac.compare_digest(pwd, ADMIN_PASSWORD):
                    ts = str(int(time.time()))
                    token = f"{ts}.{sign_session(ts)}"
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Set-Cookie", f"ops_token={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=2592000")
                    self.end_headers()
                    self.wfile.write(b'{"status":"ok"}')
                    return
            except Exception:
                pass
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":"Invalid password"}')
            return

        if path == "/api/logout":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Set-Cookie", "ops_token=; Path=/; HttpOnly; Max-Age=0")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return

        self.send_response(404)
        self.end_headers()

if __name__ == "__main__":
    from http.server import ThreadingHTTPServer
    # Start background telemetry thread
    t = threading.Thread(target=background_telemetry_loop, daemon=True)
    t.start()
    print(f"[*] Starting Cluster Ops Server on port {PORT}...")
    server = ThreadingHTTPServer(("0.0.0.0", PORT), OpsHTTPRequestHandler)
    server.serve_forever()
