import React, { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { CockpitBar } from './components/CockpitBar';
import { TabTopology } from './components/TabTopology';
import { TabAIOps } from './components/TabAIOps';
import { TabAutomation } from './components/TabAutomation';
import { CommandPalette } from './components/CommandPalette';
import { LoginModal } from './components/LoginModal';
import { ClusterData, CockpitItem } from './types';
import { checkAuth, fetchClusterData, fetchApprovals, logout } from './api';
import { Server, Shield, Zap, AlertCircle } from 'lucide-react';

export const App: React.FC = () => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(true);
  const [isCheckingAuth, setIsCheckingAuth] = useState<boolean>(true);

  const [clusterData, setClusterData] = useState<ClusterData | null>(null);
  const [activeTab, setActiveTab] = useState<'topology' | 'ai-ops' | 'automation'>('topology');
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState<number>(0);

  const [isPaletteOpen, setIsPaletteOpen] = useState(false);
  const [isDark, setIsDark] = useState<boolean>(() => {
    return localStorage.getItem('ops_theme') !== 'light';
  });

  const [refreshCountdown, setRefreshCountdown] = useState<number>(30);
  const [isAutoRefreshPaused, setIsAutoRefreshPaused] = useState<boolean>(false);

  // Dynamic cockpit items from backend injection or fallback
  const cockpitItems: CockpitItem[] = (window as any).__OPS_COCKPIT_ITEMS__ || [];

  // Theme Sync
  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('ops_theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('ops_theme', 'light');
    }
  }, [isDark]);

  // Auth Check on load
  const verifyAuth = useCallback(async () => {
    setIsCheckingAuth(true);
    const authed = await checkAuth();
    setIsAuthenticated(authed);
    setIsCheckingAuth(false);
  }, []);

  useEffect(() => {
    verifyAuth();
  }, [verifyAuth]);

  // Load Data
  const loadClusterData = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      const data = await fetchClusterData();
      setClusterData(data);
    } catch (e: any) {
      if (e?.message === 'UNAUTHORIZED') {
        setIsAuthenticated(false);
      }
    }
  }, [isAuthenticated]);

  const loadPendingApprovals = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      const pending = await fetchApprovals('pending');
      setPendingApprovalsCount(pending.length);
    } catch {
      // ignore
    }
  }, [isAuthenticated]);

  const refreshAll = useCallback(() => {
    loadClusterData();
    loadPendingApprovals();
    setRefreshCountdown(30);
  }, [loadClusterData, loadPendingApprovals]);

  useEffect(() => {
    if (isAuthenticated) {
      refreshAll();
    }
  }, [isAuthenticated, refreshAll]);

  // Auto-refresh countdown timer
  useEffect(() => {
    if (!isAuthenticated || isAutoRefreshPaused) return;

    const timer = setInterval(() => {
      setRefreshCountdown(prev => {
        if (prev <= 1) {
          refreshAll();
          return 30;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [isAuthenticated, isAutoRefreshPaused, refreshAll]);

  // Global Keyboard Shortcuts (Cmd+K / Ctrl+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        setIsPaletteOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleLogout = async () => {
    await logout();
    setIsAuthenticated(false);
  };

  if (isCheckingAuth) {
    return (
      <div className="h-screen w-screen bg-zinc-950 flex items-center justify-center text-zinc-400 font-mono text-xs select-none">
        <div className="flex flex-col items-center gap-3">
          <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <span>正在连接 Cluster Ops 控制台...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginModal onSuccess={() => { setIsAuthenticated(true); refreshAll(); }} />;
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-[#09090b] text-zinc-900 dark:text-zinc-100 flex flex-col transition-colors selection:bg-indigo-500 selection:text-white relative">
      {/* Ambient background aura */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0" aria-hidden="true">
        <div className="absolute top-[-100px] left-[-100px] w-96 h-96 bg-indigo-500/10 dark:bg-indigo-600/15 rounded-full blur-3xl" />
        <div className="absolute top-[20%] right-[-100px] w-80 h-80 bg-sky-500/10 dark:bg-sky-600/15 rounded-full blur-3xl" />
        <div className="absolute bottom-[-100px] left-[30%] w-96 h-96 bg-emerald-500/10 dark:bg-emerald-600/15 rounded-full blur-3xl" />
      </div>

      {/* 1. Header */}
      <Header
        summary={clusterData?.summary || null}
        pendingApprovalsCount={pendingApprovalsCount}
        onOpenPalette={() => setIsPaletteOpen(true)}
        onRefresh={refreshAll}
        onToggleTheme={() => setIsDark(!isDark)}
        onLogout={handleLogout}
        isDark={isDark}
        refreshSeconds={refreshCountdown}
        isAutoRefreshPaused={isAutoRefreshPaused}
        onToggleAutoRefresh={() => setIsAutoRefreshPaused(!isAutoRefreshPaused)}
        onSelectTab={setActiveTab}
        activeTab={activeTab}
      />

      {/* 2. Cockpit Navigation Bar */}
      <CockpitBar items={cockpitItems} />

      {/* 3. Main Container & Tab Navigation */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 flex-1 w-full space-y-6 z-10">
        {/* Navigation Tabs Header */}
        <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-800 pb-3">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab('topology')}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                activeTab === 'topology'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white hover:bg-zinc-100 dark:hover:bg-zinc-800/60'
              }`}
            >
              <Server className="w-4 h-4" />
              <span>节点与拓扑全景</span>
              <span className={`text-[10px] font-mono px-1.5 py-0.2 rounded-full ${
                activeTab === 'topology' ? 'bg-white/20 text-white' : 'bg-zinc-200 dark:bg-zinc-800 text-zinc-500'
              }`}>
                {clusterData?.routes.length || 0}
              </span>
            </button>

            <button
              onClick={() => setActiveTab('ai-ops')}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer relative ${
                activeTab === 'ai-ops'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white hover:bg-zinc-100 dark:hover:bg-zinc-800/60'
              }`}
            >
              <Shield className="w-4 h-4" />
              <span>AI 运维与审批中心</span>
              {pendingApprovalsCount > 0 && (
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-amber-500 text-white font-bold animate-pulse">
                  {pendingApprovalsCount}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('automation')}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                activeTab === 'automation'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white hover:bg-zinc-100 dark:hover:bg-zinc-800/60'
              }`}
            >
              <Zap className="w-4 h-4" />
              <span>自动化管线与宿主守护</span>
            </button>
          </div>

          <div className="hidden sm:flex items-center gap-2 text-xs font-mono text-zinc-400">
            <span>Traefik v3 Swarm Ingress</span>
          </div>
        </div>

        {/* Tab Content Views */}
        {activeTab === 'topology' && (
          <TabTopology
            nodes={clusterData?.nodes || []}
            routes={clusterData?.routes || []}
            summary={clusterData?.summary || null}
          />
        )}

        {activeTab === 'ai-ops' && (
          <TabAIOps />
        )}

        {activeTab === 'automation' && (
          <TabAutomation
            automation={clusterData?.automation || { backups: [], guard: { last_run: '-', issues: 0, ok: true }, timers: [], systemd_daemons: {} }}
            standalones={clusterData?.standalones || {}}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-200 dark:border-zinc-800 py-6 text-center text-xs text-zinc-400 font-mono">
        跨国双向自愈 Mesh 架构 · Traefik v3 Swarm 动态服务发现 · 多方 AI 协同受控管治 · 自动健康巡检
      </footer>

      {/* Command Palette Modal (Cmd+K) */}
      <CommandPalette
        isOpen={isPaletteOpen}
        onClose={() => setIsPaletteOpen(false)}
        routes={clusterData?.routes || []}
        cockpitItems={cockpitItems}
        onSelectTab={setActiveTab}
        onRefresh={refreshAll}
        onToggleTheme={() => setIsDark(!isDark)}
        onLogout={handleLogout}
        isDark={isDark}
      />
    </div>
  );
};
