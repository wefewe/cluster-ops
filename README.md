# Cluster Ops Console

Lightweight, real-time multi-node Docker Swarm & Traefik v3 topology dashboard with automated telemetry, backup monitoring, and SRE operations pipelines.

## Features
- **Real-time Node Telemetry**: Hardware metrics (CPU, RAM, Disk) across physical nodes.
- **Traefik v3 Ingress Routing**: Automated discovery of Swarm microservices and domain mapping.
- **Automation Pipelines Matrix**: Live visibility of backup freshness, systemd timers, cluster-guard health audits, and AI agent status.
- **Zero-Dependency Core**: Standard Python library implementation with Lucide vector icons and dark/light mode UI.

## Quick Start
```bash
docker run -d -p 8080:8080 \
  -e ADMIN_PASSWORD=your_password \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  ghcr.io/wefewe/cluster-ops:latest
```
