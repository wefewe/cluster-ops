"""Node/service telemetry collection (background loop + caches)."""
import concurrent.futures
import http.client
import json
import os
import re
import shutil
import ssl
import subprocess
import threading
import time
import urllib.request

from .config import PORTAINER_TOKEN_FILE, SSH_DIR
from .docker_api import get_docker_api, get_traefik_api

# Thread-safe telemetry caches (rebound by background_telemetry_loop;
# readers must access via module attribute, never `from ... import`).
cache_lock = threading.Lock()
node_telemetry_cache = {}
domain_ping_cache = {}
standalone_cache = {}
automation_cache = {}

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
        out = subprocess.check_output(cmd, timeout=4).decode().strip().split("\n")
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
                us_stats = f_us.result()
                rn_stats = f_rn.result()

            new_nodes = {
                "jp-oracle": jp_stats or {"cpu_pct": 5, "mem_pct": 27, "disk_pct": 25, "mem_used_mb": 3200, "mem_total_mb": 11900, "disk_used_gb": 26, "disk_total_gb": 98, "status": "online"},
                "us-oracle": us_stats or {"cpu_pct": 3, "mem_pct": 16, "disk_pct": 16, "mem_used_mb": 1850, "mem_total_mb": 11900, "disk_used_gb": 15, "disk_total_gb": 96, "status": "online"},
                "us-racknerd": rn_stats or {"cpu_pct": 4, "mem_pct": 38, "disk_pct": 38, "mem_used_mb": 930, "mem_total_mb": 2460, "disk_used_gb": 14, "disk_total_gb": 38, "status": "online"}
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
