import { ClusterData, AuditItem, ApprovalItem, TokenMetadata } from './types';

export async function checkAuth(): Promise<boolean> {
  try {
    const res = await fetch('/api/auth-check');
    return res.status === 200;
  } catch {
    return false;
  }
}

export async function login(password: string): Promise<boolean> {
  const res = await fetch('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  });
  return res.ok;
}

export async function logout(): Promise<void> {
  await fetch('/api/logout', { method: 'POST' });
}

export async function fetchClusterData(): Promise<ClusterData> {
  const res = await fetch('/api/data');
  if (res.status === 401) {
    throw new Error('UNAUTHORIZED');
  }
  if (!res.ok) {
    throw new Error(`Failed to load cluster data: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchAuditLogs(params: { actor?: string; level?: string; limit?: number } = {}): Promise<AuditItem[]> {
  const q = new URLSearchParams();
  if (params.actor) q.set('actor', params.actor);
  if (params.level) q.set('level', params.level);
  q.set('limit', String(params.limit || 50));

  const res = await fetch('/api/audit?' + q.toString());
  if (res.status === 401) throw new Error('UNAUTHORIZED');
  if (!res.ok) throw new Error('Failed to load audit logs');
  const data = await res.json();
  return data.items || [];
}

export async function fetchApprovals(status?: string): Promise<ApprovalItem[]> {
  const q = new URLSearchParams();
  if (status) q.set('status', status);
  q.set('limit', '50');

  const res = await fetch('/api/approvals?' + q.toString());
  if (res.status === 401) throw new Error('UNAUTHORIZED');
  if (!res.ok) throw new Error('Failed to load approvals');
  const data = await res.json();
  return data.items || [];
}

export async function decideApproval(id: number, decision: 'approved' | 'rejected', note: string = ''): Promise<void> {
  const res = await fetch(`/api/approvals/${id}/decide`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision, note }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || 'Failed to submit decision');
  }
}

export async function fetchTokens(): Promise<TokenMetadata[]> {
  const res = await fetch('/api/tokens');
  if (!res.ok) return [];
  const data = await res.json();
  return data.tokens || [];
}
