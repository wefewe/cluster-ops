import React, { useState } from 'react';
import { Zap, Archive, Shield, Bot, Clock, Server, CheckCircle2, AlertTriangle, Layers } from 'lucide-react';
import { AutomationData, StandaloneService } from '../types';

interface TabAutomationProps {
  automation: AutomationData;
  standalones: Record<string, StandaloneService[]>;
}

export const TabAutomation: React.FC<TabAutomationProps> = ({ automation, standalones }) => {
  const [daemonView, setDaemonView] = useState<'matrix' | 'cards'>('matrix');

  const { backups = [], guard = { last_run: '-', issues: 0, ok: true }, agent, timers = [], systemd_daemons = {} } = automation || {};

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* 1. TOP PIPELINE STATUS CARDS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Backups Pipeline Card */}
        <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 flex items-center gap-1.5">
              <Archive className="w-4 h-4 text-emerald-500" />
              <span>三机异地冷备流水线</span>
            </h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 font-bold">
              每日 03:30 / 04:30
            </span>
          </div>

          <div className="space-y-2 text-xs">
            {backups.map((b) => (
              <div key={b.name} className="flex items-center justify-between p-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-950/40 border border-zinc-200 dark:border-zinc-800/60 font-mono">
                <div>
                  <div className="font-semibold text-zinc-800 dark:text-zinc-200 flex items-center gap-1.5">
                    <span className={`w-2 h-2 rounded-full ${b.ok ? 'bg-emerald-500' : 'bg-red-500'}`} />
                    <span>{b.name}</span>
                  </div>
                  <div className="text-[10px] text-zinc-400">➔ {b.dest}</div>
                </div>
                <div className="text-right">
                  <div className="font-bold text-zinc-900 dark:text-zinc-100">{b.size}</div>
                  <div className="text-[10px] text-zinc-400">{b.age}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Cluster Guard Card */}
        <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 flex items-center gap-1.5">
              <Shield className="w-4 h-4 text-indigo-500" />
              <span>自动更新中枢 (Cluster-Guard)</span>
            </h3>
            <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-bold ${
              guard.ok ? 'bg-emerald-500/10 text-emerald-500' : 'bg-red-500/10 text-red-500'
            }`}>
              {guard.ok ? '自愈就绪' : '异常告警'}
            </span>
          </div>

          <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-950/40 border border-zinc-200 dark:border-zinc-800/60 space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-zinc-500">最近巡检时间:</span>
              <span className="font-mono font-medium text-zinc-800 dark:text-zinc-200">{guard.last_run}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">发现异常项:</span>
              <span className="font-mono font-bold text-emerald-500">{guard.issues} 项</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">巡检运行周期:</span>
              <span className="font-mono text-zinc-700 dark:text-zinc-300">每 2 小时自愈比对</span>
            </div>
          </div>
        </div>

        {/* AI Agent (OpenClaw) Card */}
        <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 flex items-center gap-1.5">
              <Bot className="w-4 h-4 text-pink-500" />
              <span>7×24 值守智能体 (openclaw)</span>
            </h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 font-bold">
              {agent?.mode || 'Systemd 原生'}
            </span>
          </div>

          <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-950/40 border border-zinc-200 dark:border-zinc-800/60 space-y-1.5 text-xs">
            <div className="flex justify-between">
              <span className="text-zinc-500">Telegram Bot:</span>
              <span className="font-mono text-indigo-500 font-semibold">{agent?.tg_bot}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">核心思考模型:</span>
              <span className="font-mono text-zinc-800 dark:text-zinc-200">{agent?.model}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">MCP 只读工具集:</span>
              <span className="font-mono text-zinc-800 dark:text-zinc-200">{agent?.mcp_tools}</span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. SYSTEM TIMERS GRID */}
      {timers.length > 0 && (
        <section className="p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-4">
          <h2 className="text-base font-bold text-zinc-900 dark:text-white flex items-center gap-2">
            <Clock className="w-4 h-4 text-indigo-500" />
            <span>集群自动化定时器流水线 ({timers.length} 个)</span>
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {timers.map((t) => (
              <div key={t.name} className="p-3.5 rounded-xl bg-zinc-50 dark:bg-zinc-950/40 border border-zinc-200 dark:border-zinc-800 space-y-1 text-xs font-mono">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-zinc-800 dark:text-zinc-200 truncate">{t.name}</span>
                  <span className={`w-2 h-2 rounded-full ${t.active ? 'bg-emerald-500' : 'bg-zinc-400'}`} />
                </div>
                <div className="text-[11px] text-zinc-500 truncate">计划: {t.schedule}</div>
                <div className="text-[10px] text-zinc-400">下次: {t.next}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 3. STANDALONE SERVICES & SYSTEMD DAEMONS */}
      <section className="p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-zinc-900 dark:text-white flex items-center gap-2">
              <Server className="w-4 h-4 text-indigo-500" />
              <span>单机宿主守护进程专区 (Standalone & Host Systemd)</span>
            </h2>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
              各物理节点的基础单机服务与特化守护，与 Swarm 分布式业务栈严格解耦
            </p>
          </div>

          <div className="flex rounded-xl bg-zinc-100 dark:bg-zinc-950 p-1 border border-zinc-200 dark:border-zinc-800 text-xs">
            <button
              onClick={() => setDaemonView('matrix')}
              className={`px-3 py-1 rounded-lg font-medium transition ${
                daemonView === 'matrix' ? 'bg-indigo-600 text-white shadow-xs' : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-white'
              }`}
            >
              横向矩阵
            </button>
            <button
              onClick={() => setDaemonView('cards')}
              className={`px-3 py-1 rounded-lg font-medium transition ${
                daemonView === 'cards' ? 'bg-indigo-600 text-white shadow-xs' : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-white'
              }`}
            >
              对齐卡片
            </button>
          </div>
        </div>

        {/* Daemons Matrix View */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Object.entries(standalones).map(([nodeName, sList]) => (
            <div key={nodeName} className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-950/40 border border-zinc-200 dark:border-zinc-800 space-y-3">
              <h3 className="font-bold text-xs text-zinc-900 dark:text-zinc-100 uppercase font-mono tracking-wider border-b border-zinc-200 dark:border-zinc-800 pb-2">
                {nodeName} ({sList.length})
              </h3>
              <div className="space-y-2">
                {sList.map((s, idx) => (
                  <div key={idx} className="p-2.5 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800/80 flex items-center justify-between text-xs">
                    <div>
                      <div className="font-semibold text-zinc-800 dark:text-zinc-200">{s.name}</div>
                      <div className="text-[10px] text-zinc-400 font-mono">{s.type} {s.port ? `:${s.port}` : ''}</div>
                    </div>
                    <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-emerald-500/10 text-emerald-500 font-bold">
                      {s.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Host Systemd Badges footer */}
        {Object.keys(systemd_daemons).length > 0 && (
          <div className="pt-4 border-t border-zinc-200 dark:border-zinc-800 space-y-2 text-xs">
            <span className="font-bold text-zinc-500 text-[11px] uppercase tracking-wider">
              宿主底层守护底座 (Systemd Services):
            </span>
            <div className="flex flex-wrap gap-2">
              {Object.entries(systemd_daemons).flatMap(([node, daemons]) => 
                daemons.map(d => (
                  <span
                    key={`${node}-${d.name}`}
                    className="px-2.5 py-1 rounded-lg bg-zinc-100 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-[11px] font-mono text-zinc-700 dark:text-zinc-300 flex items-center gap-1.5"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                    <strong>{node.split('-')[0]}:</strong> {d.name}
                  </span>
                ))
              )}
            </div>
          </div>
        )}
      </section>
    </div>
  );
};
