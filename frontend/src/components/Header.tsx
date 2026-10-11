import React from 'react';
import { Shield, RefreshCw, Moon, Sun, LogOut, Search, Clock, AlertCircle } from 'lucide-react';
import { ClusterSummary } from '../types';

interface HeaderProps {
  summary: ClusterSummary | null;
  pendingApprovalsCount: number;
  onOpenPalette: () => void;
  onRefresh: () => void;
  onToggleTheme: () => void;
  onLogout: () => void;
  isDark: boolean;
  refreshSeconds: number;
  isAutoRefreshPaused: boolean;
  onToggleAutoRefresh: () => void;
  onSelectTab: (tab: 'topology' | 'ai-ops' | 'automation') => void;
  activeTab: 'topology' | 'ai-ops' | 'automation';
}

export const Header: React.FC<HeaderProps> = ({
  summary,
  pendingApprovalsCount,
  onOpenPalette,
  onRefresh,
  onToggleTheme,
  onLogout,
  isDark,
  refreshSeconds,
  isAutoRefreshPaused,
  onToggleAutoRefresh,
  onSelectTab,
  activeTab,
}) => {
  return (
    <header className="sticky top-0 z-40 border-b border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-900/80 backdrop-blur-md transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        {/* Brand & Quorum Indicator */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-500 flex items-center justify-center shrink-0">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-bold text-sm tracking-tight text-zinc-900 dark:text-white">
                Cluster Ops
              </h1>
              <span className="hidden md:inline-flex text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 font-semibold">
                {summary?.nodes_online || '3/3 仲裁就绪'}
              </span>
            </div>
            <p className="text-[11px] text-zinc-500 dark:text-zinc-400 font-mono hidden sm:block">
              {summary?.quorum_status || 'Quorum 健全 · 全节点 3/3 在线'}
            </p>
          </div>
        </div>

        {/* Center Search / Command Palette Shortcut */}
        <button
          onClick={onOpenPalette}
          className="flex-1 max-w-sm hidden md:flex items-center justify-between px-3 py-1.5 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950/40 text-xs text-zinc-400 hover:border-zinc-300 dark:hover:border-zinc-700 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors"
        >
          <div className="flex items-center gap-2 truncate">
            <Search className="w-3.5 h-3.5" />
            <span className="truncate">搜索微服务、域名或动作...</span>
          </div>
          <kbd className="px-1.5 py-0.5 text-[10px] font-mono border border-zinc-200 dark:border-zinc-800 rounded bg-white dark:bg-zinc-900 shadow-xs">
            ⌘K
          </kbd>
        </button>

        {/* Right Action Tools */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* L2 Pending Approvals Quick Alert Button */}
          {pendingApprovalsCount > 0 && (
            <button
              onClick={() => onSelectTab('ai-ops')}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-semibold bg-amber-500/15 border border-amber-500/30 text-amber-500 animate-pulse hover:bg-amber-500/25 transition-colors cursor-pointer"
              title="有待审批单需要处理"
            >
              <AlertCircle className="w-3.5 h-3.5" />
              <span>{pendingApprovalsCount} 待审批</span>
            </button>
          )}

          {/* Auto Refresh Toggle & Timer */}
          <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-[11px] font-mono text-zinc-500">
            <button
              onClick={onToggleAutoRefresh}
              className="hover:text-indigo-500 transition-colors"
              title={isAutoRefreshPaused ? '点击恢复自动刷新' : '点击暂停自动刷新'}
            >
              {isAutoRefreshPaused ? '已暂停' : `${refreshSeconds}s`}
            </button>
          </div>

          <button
            onClick={onRefresh}
            className="p-2 rounded-xl text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
            title="立即刷新"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          <button
            onClick={onToggleTheme}
            className="p-2 rounded-xl text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
            title={isDark ? '切换亮色' : '切换暗色'}
          >
            {isDark ? <Sun className="w-4 h-4 text-amber-500" /> : <Moon className="w-4 h-4 text-indigo-500" />}
          </button>

          <button
            onClick={onLogout}
            className="p-2 rounded-xl text-zinc-500 hover:text-red-500 hover:bg-red-500/10 transition-colors"
            title="退出登录"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
