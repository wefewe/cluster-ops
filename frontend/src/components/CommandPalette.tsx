import React, { useState, useEffect, useRef } from 'react';
import { Search, ExternalLink, ArrowRight, Server, Globe, Cpu, Zap, Shield, Moon, Sun, RefreshCw, LogOut } from 'lucide-react';
import { RouteItem, CockpitItem } from '../types';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  routes: RouteItem[];
  cockpitItems: CockpitItem[];
  onSelectTab: (tab: 'topology' | 'ai-ops' | 'automation') => void;
  onRefresh: () => void;
  onToggleTheme: () => void;
  onLogout: () => void;
  isDark: boolean;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  routes,
  cockpitItems,
  onSelectTab,
  onRefresh,
  onToggleTheme,
  onLogout,
  isDark,
}) => {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Combine items into a searchable list
  const searchResults = React.useMemo(() => {
    const q = query.toLowerCase().trim();

    const actions = [
      {
        id: 'action-tab-topology',
        type: 'action',
        title: '切换到：节点与拓扑全景',
        subtitle: '查看 Swarm 集群节点硬件与微服务路由',
        icon: <Server className="w-4 h-4 text-indigo-400" />,
        action: () => { onSelectTab('topology'); onClose(); },
      },
      {
        id: 'action-tab-ai-ops',
        type: 'action',
        title: '切换到：AI 运维与审批中心',
        subtitle: 'L2 待审批队列、四方 AI 审计流水与密钥管家',
        icon: <Shield className="w-4 h-4 text-amber-400" />,
        action: () => { onSelectTab('ai-ops'); onClose(); },
      },
      {
        id: 'action-tab-automation',
        type: 'action',
        title: '切换到：自动化管线与宿主守护',
        subtitle: '容灾冷备、巡检中枢、看门狗与 Systemd 矩阵',
        icon: <Zap className="w-4 h-4 text-emerald-400" />,
        action: () => { onSelectTab('automation'); onClose(); },
      },
      {
        id: 'action-refresh',
        type: 'action',
        title: '立即刷新集群数据',
        subtitle: '重新拉取节点负载与微服务状态',
        icon: <RefreshCw className="w-4 h-4 text-blue-400" />,
        action: () => { onRefresh(); onClose(); },
      },
      {
        id: 'action-theme',
        type: 'action',
        title: `切换为${isDark ? '亮色' : '暗色'}主题`,
        subtitle: '切换控制台视觉外观',
        icon: isDark ? <Sun className="w-4 h-4 text-amber-500" /> : <Moon className="w-4 h-4 text-indigo-400" />,
        action: () => { onToggleTheme(); onClose(); },
      },
      {
        id: 'action-logout',
        type: 'action',
        title: '退出登录',
        subtitle: '清除当前会话凭证',
        icon: <LogOut className="w-4 h-4 text-red-400" />,
        action: () => { onLogout(); onClose(); },
      },
    ];

    const cockpit = cockpitItems.map(item => ({
      id: `cockpit-${item.name}`,
      type: 'cockpit',
      title: item.name,
      subtitle: `直达应用 · ${item.url}`,
      icon: <ExternalLink className="w-4 h-4 text-sky-400" />,
      action: () => { window.open(item.url, '_blank', 'noopener,noreferrer'); onClose(); },
    }));

    const routeItems = routes.map(r => ({
      id: `route-${r.domain}`,
      type: 'route',
      title: r.domain,
      subtitle: `微服务 · ${r.stack} / ${r.service} (${r.node_name})`,
      icon: <Globe className="w-4 h-4 text-emerald-400" />,
      action: () => { window.open(r.url, '_blank', 'noopener,noreferrer'); onClose(); },
    }));

    const all = [...actions, ...cockpit, ...routeItems];
    if (!q) return all.slice(0, 10);

    return all.filter(it => 
      it.title.toLowerCase().includes(q) || it.subtitle.toLowerCase().includes(q)
    ).slice(0, 12);
  }, [query, routes, cockpitItems, isDark, onSelectTab, onRefresh, onToggleTheme, onLogout, onClose]);

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(prev => (prev + 1) % (searchResults.length || 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(prev => (prev - 1 + searchResults.length) % (searchResults.length || 1));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (searchResults[selectedIndex]) {
          searchResults[selectedIndex].action();
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, searchResults, selectedIndex, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-start justify-center pt-20 p-4">
      <div 
        className="w-full max-w-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-150"
        onClick={e => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-950/30">
          <Search className="w-5 h-5 text-zinc-400 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            placeholder="搜索微服务、域名、导航应用或控制台操作..."
            value={query}
            onChange={e => { setQuery(e.target.value); setSelectedIndex(0); }}
            className="flex-1 bg-transparent text-sm text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400 focus:outline-none"
          />
          <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono text-zinc-400 border border-zinc-200 dark:border-zinc-700 rounded-md">
            ESC
          </kbd>
        </div>

        {/* Results List */}
        <div className="max-h-96 overflow-y-auto p-2 space-y-1">
          {searchResults.length === 0 ? (
            <div className="py-12 text-center text-xs text-zinc-400">
              未找到匹配的微服务或操作
            </div>
          ) : (
            searchResults.map((it, idx) => (
              <div
                key={it.id}
                onClick={it.action}
                onMouseEnter={() => setSelectedIndex(idx)}
                className={`flex items-center justify-between px-3 py-2.5 rounded-xl text-xs cursor-pointer transition-colors ${
                  idx === selectedIndex
                    ? 'bg-indigo-600 text-white'
                    : 'text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800/60'
                }`}
              >
                <div className="flex items-center gap-2.5 truncate flex-1 pr-2">
                  <div className={`p-1.5 rounded-lg shrink-0 ${idx === selectedIndex ? 'bg-white/20 text-white' : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-400'}`}>
                    {it.icon}
                  </div>
                  <div className="truncate">
                    <p className={`font-medium truncate ${idx === selectedIndex ? 'text-white' : 'text-zinc-900 dark:text-zinc-100'}`}>
                      {it.title}
                    </p>
                    <p className={`text-[11px] truncate ${idx === selectedIndex ? 'text-indigo-100' : 'text-zinc-400'}`}>
                      {it.subtitle}
                    </p>
                  </div>
                </div>
                <ArrowRight className={`w-3.5 h-3.5 shrink-0 ${idx === selectedIndex ? 'text-white' : 'text-zinc-400'}`} />
              </div>
            ))
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="px-4 py-2 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-950/40 flex items-center justify-between text-[11px] text-zinc-400 font-mono">
          <span>↑↓ 切换 • Enter 确认</span>
          <span>Cmd/Ctrl + K 随时呼出</span>
        </div>
      </div>
    </div>
  );
};
