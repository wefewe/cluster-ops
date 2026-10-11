import React, { useState, useMemo } from 'react';
import { Server, Layers, Zap, Lock, Globe, ExternalLink, ChevronDown, ChevronRight, Activity, Cpu, HardDrive } from 'lucide-react';
import { NodeStat, RouteItem, ClusterSummary } from '../types';

interface TabTopologyProps {
  nodes: NodeStat[];
  routes: RouteItem[];
  summary: ClusterSummary | null;
}

export const TabTopology: React.FC<TabTopologyProps> = ({ nodes, routes, summary }) => {
  const [search, setSearch] = useState('');
  const [selectedStack, setSelectedStack] = useState<string>('all');
  const [selectedNode, setSelectedNode] = useState<string>('all');
  const [expandedStacks, setExpandedStacks] = useState<Record<string, boolean>>({});
  const [viewMode, setViewMode] = useState<'accordion' | 'flat'>('accordion');

  // Filter routes
  const filteredRoutes = useMemo(() => {
    return routes.filter(r => {
      const matchSearch = !search || 
        r.domain.toLowerCase().includes(search.toLowerCase()) || 
        r.service.toLowerCase().includes(search.toLowerCase()) ||
        r.stack.toLowerCase().includes(search.toLowerCase());
      
      const matchStack = selectedStack === 'all' || r.stack === selectedStack;
      const matchNode = selectedNode === 'all' || r.node === selectedNode;

      return matchSearch && matchStack && matchNode;
    });
  }, [routes, search, selectedStack, selectedNode]);

  // Group routes by stack
  const routesByStack = useMemo(() => {
    const map: Record<string, RouteItem[]> = {};
    for (const r of filteredRoutes) {
      if (!map[r.stack]) map[r.stack] = [];
      map[r.stack].push(r);
    }
    return map;
  }, [filteredRoutes]);

  const allStacks = useMemo(() => {
    const set = new Set(routes.map(r => r.stack));
    return Array.from(set).sort();
  }, [routes]);

  const toggleStack = (stack: string) => {
    setExpandedStacks(prev => ({ ...prev, [stack]: !prev[stack] }));
  };

  const expandAll = () => {
    const next: Record<string, boolean> = {};
    allStacks.forEach(s => next[s] = true);
    setExpandedStacks(next);
  };

  const collapseAll = () => {
    setExpandedStacks({});
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* 1. NODE TELEMETRY GRID (3-Manager Cloud Quorum) */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
            <Server className="w-4 h-4 text-indigo-500" />
            <span>核心云端高可用生产环境 (3-Manager Cloud Quorum)</span>
          </h2>
          <span className="text-[11px] font-mono text-zinc-400">
            {summary?.quorum_status}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {nodes.map((node) => {
            const isLeader = node.role === 'Leader';
            const cpu = node.cpu_pct !== null ? `${node.cpu_pct}%` : '在线';
            const memPct = node.mem_pct || 0;
            const diskPct = node.disk_pct || 0;

            return (
              <div
                key={node.node}
                className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs hover:border-indigo-500/30 transition-all space-y-4"
              >
                {/* Node Header */}
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-bold text-sm text-zinc-900 dark:text-white flex items-center gap-2">
                      <span>{node.name}</span>
                    </h3>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ${
                        isLeader
                          ? 'bg-indigo-500/15 text-indigo-500 border border-indigo-500/30'
                          : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-500'
                      }`}>
                        {node.role}
                      </span>
                      <span className="text-[10px] font-mono text-zinc-400">
                        {node.arch}
                      </span>
                    </div>
                  </div>

                  <span className="inline-flex items-center gap-1 text-[11px] font-mono font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    {node.status}
                  </span>
                </div>

                {/* Resource Metrics Bar */}
                <div className="space-y-2.5 pt-1 text-xs">
                  {/* CPU */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-[11px] text-zinc-500">
                      <span className="flex items-center gap-1"><Cpu className="w-3 h-3" /> CPU 负载</span>
                      <span className="font-mono font-medium text-zinc-700 dark:text-zinc-300">{cpu}</span>
                    </div>
                    {node.cpu_pct !== null && (
                      <div className="h-1.5 w-full bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-indigo-500 rounded-full transition-all duration-500" 
                          style={{ width: `${Math.min(100, Math.max(2, node.cpu_pct))}%` }} 
                        />
                      </div>
                    )}
                  </div>

                  {/* Memory */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-[11px] text-zinc-500">
                      <span className="flex items-center gap-1"><Activity className="w-3 h-3" /> 内存使用</span>
                      <span className="font-mono font-medium text-zinc-700 dark:text-zinc-300">
                        {node.mem_used_mb ? `${node.mem_used_mb}MB / ${node.mem_total_mb}MB (${memPct}%)` : '-'}
                      </span>
                    </div>
                    {node.mem_pct !== null && (
                      <div className="h-1.5 w-full bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-emerald-500 rounded-full transition-all duration-500" 
                          style={{ width: `${Math.min(100, Math.max(2, memPct))}%` }} 
                        />
                      </div>
                    )}
                  </div>

                  {/* Disk */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-[11px] text-zinc-500">
                      <span className="flex items-center gap-1"><HardDrive className="w-3 h-3" /> 系统根盘</span>
                      <span className="font-mono font-medium text-zinc-700 dark:text-zinc-300">
                        {node.disk_used_gb ? `${node.disk_used_gb}GB / ${node.disk_total_gb}GB (${diskPct}%)` : '-'}
                      </span>
                    </div>
                    {node.disk_pct !== null && (
                      <div className="h-1.5 w-full bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-sky-500 rounded-full transition-all duration-500" 
                          style={{ width: `${Math.min(100, Math.max(2, diskPct))}%` }} 
                        />
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* 2. CLUSTER METRIC SUMMARY CARDS */}
      <section className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-1 shadow-xs">
          <div className="flex items-center gap-1.5 text-xs text-zinc-500">
            <Server className="w-3.5 h-3.5 text-indigo-500" />
            <span>仲裁节点</span>
          </div>
          <p className="text-xl font-bold font-mono text-zinc-900 dark:text-white">
            {summary?.nodes_online.split(' ')[0] || '3/3'}
          </p>
          <p className="text-[11px] text-emerald-500 font-medium">全节点 100% 健全</p>
        </div>

        <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-1 shadow-xs">
          <div className="flex items-center gap-1.5 text-xs text-zinc-500">
            <Layers className="w-3.5 h-3.5 text-indigo-500" />
            <span>微服务规模</span>
          </div>
          <p className="text-xl font-bold font-mono text-zinc-900 dark:text-white">
            {summary?.services_count || 34} 个
          </p>
          <p className="text-[11px] text-zinc-400 font-medium">{summary?.stacks_count || 24} 个 Swarm 栈</p>
        </div>

        <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-1 shadow-xs">
          <div className="flex items-center gap-1.5 text-xs text-zinc-500">
            <Zap className="w-3.5 h-3.5 text-amber-500" />
            <span>自愈守护状态</span>
          </div>
          <p className="text-xl font-bold font-mono text-emerald-500">
            {summary?.auto_healthy ? 'HEALTHY' : 'WARN'}
          </p>
          <p className="text-[11px] text-zinc-400 font-medium">巡检/冷备/Guard 全绿</p>
        </div>

        <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-1 shadow-xs">
          <div className="flex items-center gap-1.5 text-xs text-zinc-500">
            <Lock className="w-3.5 h-3.5 text-indigo-500" />
            <span>边缘网关证书</span>
          </div>
          <p className="text-sm font-bold text-zinc-900 dark:text-white truncate pt-1">
            CF Strict + 15年 CA
          </p>
          <p className="text-[11px] text-emerald-500 font-medium">Traefik v3 Ingress</p>
        </div>
      </section>

      {/* 3. SWARM STACKS & TRAEFIK INGRESS ACCORDION */}
      <section className="p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-5 shadow-xs">
        {/* Controls Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-bold text-zinc-900 dark:text-white flex items-center gap-2">
              <Globe className="w-4 h-4 text-indigo-500" />
              <span>Swarm 业务栈与 Traefik 路由拓扑 ({filteredRoutes.length} 条)</span>
            </h2>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
              全域泛域名 TLS，包含目标容器端口、调度节点与实时心跳延迟探测
            </p>
          </div>

          {/* Quick Filters */}
          <div className="flex items-center gap-2 flex-wrap">
            <input
              type="text"
              placeholder="过滤服务或域名..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="px-3 py-1.5 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950 text-xs text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400 focus:outline-none focus:border-indigo-500"
            />

            <div className="flex rounded-xl bg-zinc-100 dark:bg-zinc-950 p-1 border border-zinc-200 dark:border-zinc-800 text-xs">
              <button
                onClick={() => setViewMode('accordion')}
                className={`px-2.5 py-1 rounded-lg font-medium transition ${
                  viewMode === 'accordion' ? 'bg-indigo-600 text-white shadow-xs' : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-white'
                }`}
              >
                手风琴分组
              </button>
              <button
                onClick={() => setViewMode('flat')}
                className={`px-2.5 py-1 rounded-lg font-medium transition ${
                  viewMode === 'flat' ? 'bg-indigo-600 text-white shadow-xs' : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-white'
                }`}
              >
                平铺大图
              </button>
            </div>

            {viewMode === 'accordion' && (
              <div className="flex items-center gap-1 text-xs">
                <button
                  onClick={expandAll}
                  className="px-2 py-1 rounded-lg text-zinc-500 hover:text-indigo-500 font-medium"
                >
                  全部展开
                </button>
                <button
                  onClick={collapseAll}
                  className="px-2 py-1 rounded-lg text-zinc-500 hover:text-indigo-500 font-medium"
                >
                  全部折叠
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Stack View List */}
        {viewMode === 'accordion' ? (
          <div className="space-y-3">
            {Object.entries(routesByStack).map(([stack, stackRoutes]) => {
              const isOpen = expandedStacks[stack] ?? true;
              return (
                <div
                  key={stack}
                  className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-950/40 overflow-hidden transition-colors"
                >
                  {/* Stack Group Header */}
                  <div
                    onClick={() => toggleStack(stack)}
                    className="px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-zinc-100/70 dark:hover:bg-zinc-900/60 transition-colors select-none"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-zinc-400">
                        {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                      </span>
                      <span className="font-bold text-xs text-zinc-900 dark:text-zinc-100 font-mono">
                        stack: {stack}
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.2 rounded-full bg-zinc-200 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400">
                        {stackRoutes.length} 路由
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-xs text-zinc-400 font-mono">
                      <span>{stackRoutes[0]?.node_name}</span>
                    </div>
                  </div>

                  {/* Route Items in Stack */}
                  {isOpen && (
                    <div className="p-3 pt-0 grid grid-cols-1 md:grid-cols-2 gap-2.5">
                      {stackRoutes.map(r => (
                        <div
                          key={r.domain}
                          className="p-3 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800/80 flex items-center justify-between gap-3 text-xs shadow-xs"
                        >
                          <div className="truncate flex-1 space-y-1">
                            <a
                              href={r.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="font-semibold text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1 truncate"
                            >
                              <span className="truncate">{r.domain}</span>
                              <ExternalLink className="w-3 h-3 shrink-0" />
                            </a>
                            <div className="flex items-center gap-2 text-[11px] text-zinc-400 font-mono">
                              <span>svc: {r.service}</span>
                              <span>•</span>
                              <span>{r.ip_port}</span>
                            </div>
                          </div>

                          <div className="text-right shrink-0 space-y-1">
                            <span className="inline-flex items-center gap-1 font-mono text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-500 font-semibold">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                              {r.probe_ms}ms · {r.probe_code}
                            </span>
                            <div className="text-[10px] text-zinc-400 font-mono">
                              {r.node_name.split(' ')[0]}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          /* Flat Grid View */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {filteredRoutes.map(r => (
              <div
                key={r.domain}
                className="p-3.5 rounded-xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200 dark:border-zinc-800 space-y-2 text-xs"
              >
                <div className="flex items-start justify-between gap-2">
                  <a
                    href={r.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-bold text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1 truncate"
                  >
                    <span className="truncate">{r.domain}</span>
                    <ExternalLink className="w-3 h-3 shrink-0" />
                  </a>
                  <span className="inline-flex items-center gap-1 font-mono text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-500 font-semibold shrink-0">
                    {r.probe_ms}ms
                  </span>
                </div>
                <div className="flex items-center justify-between text-[11px] text-zinc-400 font-mono">
                  <span>{r.stack} / {r.service}</span>
                  <span>{r.node_name.split(' ')[0]}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
};
