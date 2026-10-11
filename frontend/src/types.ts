export interface NodeStat {
  node: string;
  name: string;
  role: string;
  status: string;
  arch: string;
  color: string;
  cpu_pct: number | null;
  mem_used_mb: number | null;
  mem_total_mb: number | null;
  mem_pct: number | null;
  disk_used_gb: number | null;
  disk_total_gb: number | null;
  disk_pct: number | null;
}

export interface RouteItem {
  domain: string;
  url: string;
  router: string;
  service: string;
  stack: string;
  ip_port: string;
  node_name: string;
  node: string;
  color: string;
  arch: string;
  tls: string;
  status: string;
  probe_code: number;
  probe_ms: number;
}

export interface StandaloneService {
  name: string;
  type?: string;
  icon?: string;
  port?: string;
  status: string;
  version?: string;
  autoupdate?: string;
  subdomain?: string;
}

export interface BackupItem {
  name: string;
  dest: string;
  size: string;
  age: string;
  ok: boolean;
}

export interface TimerItem {
  name: string;
  schedule: string;
  next: string;
  active: boolean;
  triggered?: string;
  missed?: string;
}

export interface SystemdDaemon {
  name: string;
  status: string;
  desc?: string;
  pid?: number;
}

export interface AutomationData {
  backups: BackupItem[];
  timers: TimerItem[];
  guard: {
    last_run: string;
    issues: number;
    ok: boolean;
  };
  drill?: {
    last: string;
    ok: boolean;
  };
  agent?: {
    active: boolean;
    version: string;
    mode: string;
    tg_bot: string;
    owner: string;
    model: string;
    mcp_tools: string;
    panel: string;
  };
  systemd_daemons: Record<string, SystemdDaemon[]>;
}

export interface ClusterSummary {
  nodes_online: string;
  quorum_status: string;
  stacks_count: number;
  services_count: number;
  standalone_count: number;
  routes_count: number;
  ssl_validity: string;
  auto_healthy: boolean;
}

export interface ClusterData {
  nodes: NodeStat[];
  routes: RouteItem[];
  standalones: Record<string, StandaloneService[]>;
  automation: AutomationData;
  summary: ClusterSummary;
}

export interface AuditItem {
  id: number;
  ts: number;
  actor: string;
  level: string;
  action: string;
  target: string;
  result: string;
  detail: string;
  rollback_hint?: string;
}

export interface ApprovalItem {
  id: number;
  created_at: number;
  expires_at: number;
  status: 'pending' | 'approved' | 'rejected' | 'executed' | 'failed';
  requester: string;
  action: string;
  target: string;
  reason: string;
  payload?: any;
  decision?: string;
  decided_by?: string;
  decided_at?: number;
  decision_note?: string;
  execution_result?: string;
  executed_at?: number;
  result_detail?: string;
}

export interface TokenMetadata {
  name: string;
  purpose: string;
  scopes: string[];
  holders: string;
  configured_in: string;
  last_used: number;
}

export interface CockpitItem {
  name: string;
  url: string;
  icon: string;
  color?: string;
}
