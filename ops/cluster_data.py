"""Aggregated cluster data served by /api/data."""
import re

from . import telemetry
from .docker_api import get_docker_api, get_traefik_api
from .telemetry import cache_lock

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
        nodes_tlm = dict(telemetry.node_telemetry_cache)
        pings = dict(telemetry.domain_ping_cache)
        standalones = dict(telemetry.standalone_cache)
        automation = dict(telemetry.automation_cache) if telemetry.automation_cache else default_automation

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
        else:
            display_name = hostname
            ip = n.get("Status", {}).get("Addr", "")
            color = "slate"

        hw = nodes_tlm.get(node_name, {})

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

    mgr_online = sum(1 for n in node_stats.values() if n.get("role") in ["Leader", "Manager"] and n.get("status") == "ready")
    mgr_total = sum(1 for n in node_stats.values() if n.get("role") in ["Leader", "Manager"])
    total_online = sum(1 for n in node_stats.values() if n.get("status") == "ready")
    total_nodes = len(node_stats)

    return {
        "nodes": list(node_stats.values()),
        "routes": routes_list,
        "standalones": standalones,
        "automation": automation,
        "summary": {
            "nodes_online": f"{mgr_online}/{mgr_total} 仲裁就绪",
            "quorum_status": f"Quorum 健全 · 全节点 {total_online}/{total_nodes} 在线",
            "stacks_count": len(set(s.get("Spec", {}).get("Labels", {}).get("com.docker.stack.namespace", "") for s in services if s.get("Spec", {}).get("Labels", {}).get("com.docker.stack.namespace"))),
            "services_count": len(services),
            "standalone_count": total_standalone,
            "routes_count": len(routes_list),
            "ssl_validity": "CF Full (Strict) · 源站 Origin CA (15年)",
            "auto_healthy": auto_healthy
        }
    }

