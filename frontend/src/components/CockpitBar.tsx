import React from 'react';
import { ExternalLink, Box, Zap, Book, Brain, Search, Bot, BarChart3, Shield, Clock, Folder, Radio, Activity } from 'lucide-react';
import { CockpitItem } from '../types';

interface CockpitBarProps {
  items: CockpitItem[];
}

const ICON_MAP: Record<string, React.ReactNode> = {
  box: <Box className="w-3.5 h-3.5" />,
  zap: <Zap className="w-3.5 h-3.5" />,
  book: <Book className="w-3.5 h-3.5" />,
  brain: <Brain className="w-3.5 h-3.5" />,
  search: <Search className="w-3.5 h-3.5" />,
  bot: <Bot className="w-3.5 h-3.5" />,
  chart: <BarChart3 className="w-3.5 h-3.5" />,
  shield: <Shield className="w-3.5 h-3.5" />,
  clock: <Clock className="w-3.5 h-3.5" />,
  folder: <Folder className="w-3.5 h-3.5" />,
  radio: <Radio className="w-3.5 h-3.5" />,
  activity: <Activity className="w-3.5 h-3.5" />,
};

export const CockpitBar: React.FC<CockpitBarProps> = ({ items }) => {
  if (!items || items.length === 0) return null;

  return (
    <div className="border-b border-zinc-200 dark:border-zinc-800/80 bg-zinc-100/60 dark:bg-zinc-950/40 py-2.5 px-4 sm:px-6 transition-colors">
      <div className="max-w-7xl mx-auto flex items-center gap-2 overflow-x-auto no-scrollbar py-0.5">
        <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider shrink-0 mr-1 hidden sm:inline">
          控制台直达:
        </span>
        <div className="flex items-center gap-2 flex-nowrap">
          {items.map((item) => (
            <a
              key={item.name}
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-xs font-medium text-zinc-700 dark:text-zinc-300 hover:text-indigo-500 dark:hover:text-indigo-400 hover:border-indigo-400/30 transition-all shrink-0 shadow-xs hover:-translate-y-0.5"
            >
              <span className={item.color || 'text-indigo-400'}>
                {ICON_MAP[item.icon] || <ExternalLink className="w-3.5 h-3.5" />}
              </span>
              <span>{item.name}</span>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
};
