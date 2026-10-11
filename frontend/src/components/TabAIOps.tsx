import React, { useState, useEffect } from 'react';
import { Shield, Check, X, Clock, Terminal, Bot, Sparkles, User, AlertTriangle, Key, Copy, RefreshCw } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { AuditItem, ApprovalItem, TokenMetadata } from '../types';
import { fetchAuditLogs, fetchApprovals, decideApproval, fetchTokens } from '../api';

const ACTOR_STYLES: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  opencode: { label: 'opencode 终端', color: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/30', icon: <Terminal className="w-3.5 h-3.5" /> },
  openclaw: { label: 'openclaw 值守', color: 'bg-indigo-500/10 text-indigo-500 border-indigo-500/30', icon: <Bot className="w-3.5 h-3.5" /> },
  'muse-spark': { label: 'muse-spark 对话', color: 'bg-pink-500/10 text-pink-500 border-pink-500/30', icon: <Sparkles className="w-3.5 h-3.5" /> },
  owner: { label: '集群 Owner', color: 'bg-amber-500/10 text-amber-500 border-amber-500/30', icon: <User className="w-3.5 h-3.5" /> },
};

export const TabAIOps: React.FC = () => {
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [approvalFilter, setApprovalFilter] = useState<'pending' | ''>('pending');
  const [isLoadingApprovals, setIsLoadingApprovals] = useState(false);

  const [audits, setAudits] = useState<AuditItem[]>([]);
  const [auditActor, setAuditActor] = useState<string>('');
  const [auditLevel, setAuditLevel] = useState<string>('');
  const [isLoadingAudit, setIsLoadingAudit] = useState(false);

  const [tokens, setTokens] = useState<TokenMetadata[]>([]);
  const [decidingId, setDecidingId] = useState<number | null>(null);

  const loadApprovals = async () => {
    setIsLoadingApprovals(true);
    try {
      const data = await fetchApprovals(approvalFilter);
      setApprovals(data);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoadingApprovals(false);
    }
  };

  const loadAudits = async () => {
    setIsLoadingAudit(true);
    try {
      const data = await fetchAuditLogs({ actor: auditActor, level: auditLevel });
      setAudits(data);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoadingAudit(false);
    }
  };

  const loadTokenList = async () => {
    try {
      const data = await fetchTokens();
      setTokens(data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadApprovals();
  }, [approvalFilter]);

  useEffect(() => {
    loadAudits();
  }, [auditActor, auditLevel]);

  useEffect(() => {
    loadTokenList();
  }, []);

  const handleDecision = async (id: number, decision: 'approved' | 'rejected') => {
    const note = prompt(`确认${decision === 'approved' ? '【批准】' : '【驳回】'}工单 #${id}？\n可输入批注理由（可选）：`, '');
    if (note === null) return; // Cancelled
    setDecidingId(id);
    try {
      await decideApproval(id, decision, note);
      await loadApprovals();
      await loadAudits();
    } catch (e: any) {
      alert(e.message || '操作失败');
    } finally {
      setDecidingId(null);
    }
  };

  const copyRotateCommand = () => {
    const cmd = 'sudo /usr/local/bin/ops-token-rotate.sh';
    navigator.clipboard.writeText(cmd).then(() => {
      alert('已复制轮换命令到剪贴板：' + cmd + '\n在服务器终端执行以安全轮换两个 Token（需持有维护锁）。');
    });
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* 1. L2 APPROVAL QUEUE */}
      <section className="p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-200 dark:border-zinc-800 pb-4">
          <div>
            <h2 className="text-base font-bold text-zinc-900 dark:text-white flex items-center gap-2">
              <Shield className="w-4 h-4 text-amber-500" />
              <span>L2 高风险操作待审批队列 (Approval Queue)</span>
            </h2>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
              高危写操作（数据库、WireGuard、证书、Docker Secrets 等）需经过 Owner 明确授权
            </p>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex rounded-xl bg-zinc-100 dark:bg-zinc-950 p-1 border border-zinc-200 dark:border-zinc-800 text-xs">
              <button
                onClick={() => setApprovalFilter('pending')}
                className={`px-3 py-1 rounded-lg font-medium transition ${
                  approvalFilter === 'pending' ? 'bg-amber-600 text-white shadow-xs' : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-white'
                }`}
              >
                待处理 ({approvals.filter(a => a.status === 'pending').length})
              </button>
              <button
                onClick={() => setApprovalFilter('')}
                className={`px-3 py-1 rounded-lg font-medium transition ${
                  approvalFilter === '' ? 'bg-indigo-600 text-white shadow-xs' : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-white'
                }`}
              >
                全部工单
              </button>
            </div>
            <button
              onClick={loadApprovals}
              className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition"
              title="刷新审批单"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoadingApprovals ? 'animate-spin text-indigo-400' : ''}`} />
            </button>
          </div>
        </div>

        {/* Approvals List */}
        <div className="space-y-3">
          {approvals.length === 0 ? (
            <div className="py-10 text-center text-xs text-zinc-400 space-y-1">
              <p>暂无待处理的 L2 审批工单</p>
              <p className="text-[11px] text-zinc-500">集群目前处于安全空闲态</p>
            </div>
          ) : (
            approvals.map((appr) => {
              const actorMeta = ACTOR_STYLES[appr.requester] || { label: appr.requester, color: 'bg-zinc-800 text-zinc-400', icon: <Bot className="w-3.5 h-3.5" /> };
              const isPending = appr.status === 'pending';

              return (
                <div
                  key={appr.id}
                  className={`p-4 rounded-xl border transition-all text-xs space-y-3 ${
                    isPending
                      ? 'bg-amber-500/5 dark:bg-amber-950/20 border-amber-500/30'
                      : 'bg-zinc-50 dark:bg-zinc-950/40 border-zinc-200 dark:border-zinc-800'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono font-bold text-zinc-900 dark:text-zinc-100">
                        #{appr.id}
                      </span>
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-[11px] font-semibold ${actorMeta.color}`}>
                        {actorMeta.icon}
                        <span>{actorMeta.label}</span>
                      </span>
                      <span className="font-mono text-zinc-400">
                        {appr.action} ➔ <strong className="text-zinc-700 dark:text-zinc-200">{appr.target}</strong>
                      </span>
                    </div>

                    <div className="flex items-center gap-2 font-mono text-[11px]">
                      <span className="text-zinc-400 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(appr.created_at * 1000).toLocaleString('zh-CN')}
                      </span>
                      <span className={`px-2 py-0.5 rounded-full font-bold uppercase text-[10px] ${
                        appr.status === 'pending'
                          ? 'bg-amber-500/20 text-amber-500'
                          : appr.status === 'approved'
                          ? 'bg-emerald-500/20 text-emerald-500'
                          : 'bg-red-500/20 text-red-500'
                      }`}>
                        {appr.status}
                      </span>
                    </div>
                  </div>

                  <p className="text-zinc-700 dark:text-zinc-300 leading-relaxed font-sans">
                    <strong>理由:</strong> {appr.reason}
                  </p>

                  {/* Decision Buttons for Pending */}
                  {isPending && (
                    <div className="flex items-center gap-2 pt-1 border-t border-amber-500/20">
                      <button
                        onClick={() => handleDecision(appr.id, 'approved')}
                        disabled={decidingId === appr.id}
                        className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium flex items-center gap-1.5 shadow-xs transition"
                      >
                        <Check className="w-3.5 h-3.5" />
                        <span>批准执行</span>
                      </button>
                      <button
                        onClick={() => handleDecision(appr.id, 'rejected')}
                        disabled={decidingId === appr.id}
                        className="px-3.5 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 text-white font-medium flex items-center gap-1.5 shadow-xs transition"
                      >
                        <X className="w-3.5 h-3.5" />
                        <span>驳回操作</span>
                      </button>
                    </div>
                  )}

                  {/* Resolution meta */}
                  {appr.decision && (
                    <div className="text-[11px] text-zinc-400 font-mono pt-1 border-t border-zinc-200 dark:border-zinc-800">
                      由 <strong>{appr.decided_by}</strong> 判定: {appr.decision} {appr.decision_note ? `(${appr.decision_note})` : ''}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </section>

      {/* 2. AI AUDIT TIMELINE */}
      <section className="p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-200 dark:border-zinc-800 pb-4">
          <div>
            <h2 className="text-base font-bold text-zinc-900 dark:text-white flex items-center gap-2">
              <Clock className="w-4 h-4 text-indigo-500" />
              <span>多方 AI 协同操作审计时间线 (Audit Timeline)</span>
            </h2>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
              所有 AI 智能体在集群执行写操作后 5 分钟内强制统一记账上报
            </p>
          </div>

          {/* Filters */}
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex rounded-xl bg-zinc-100 dark:bg-zinc-950 p-1 border border-zinc-200 dark:border-zinc-800 text-xs">
              <button
                onClick={() => setAuditActor('')}
                className={`px-2.5 py-1 rounded-lg font-medium transition ${!auditActor ? 'bg-indigo-600 text-white' : 'text-zinc-500'}`}
              >
                全部角色
              </button>
              <button
                onClick={() => setAuditActor('openclaw')}
                className={`px-2.5 py-1 rounded-lg font-medium transition ${auditActor === 'openclaw' ? 'bg-indigo-600 text-white' : 'text-zinc-500'}`}
              >
                openclaw
              </button>
              <button
                onClick={() => setAuditActor('opencode')}
                className={`px-2.5 py-1 rounded-lg font-medium transition ${auditActor === 'opencode' ? 'bg-indigo-600 text-white' : 'text-zinc-500'}`}
              >
                opencode
              </button>
              <button
                onClick={() => setAuditActor('muse-spark')}
                className={`px-2.5 py-1 rounded-lg font-medium transition ${auditActor === 'muse-spark' ? 'bg-indigo-600 text-white' : 'text-zinc-500'}`}
              >
                muse-spark
              </button>
            </div>

            <div className="flex rounded-xl bg-zinc-100 dark:bg-zinc-950 p-1 border border-zinc-200 dark:border-zinc-800 text-xs">
              <button
                onClick={() => setAuditLevel('')}
                className={`px-2.5 py-1 rounded-lg font-medium transition ${!auditLevel ? 'bg-indigo-600 text-white' : 'text-zinc-500'}`}
              >
                L1 + L2
              </button>
              <button
                onClick={() => setAuditLevel('L1')}
                className={`px-2.5 py-1 rounded-lg font-medium transition ${auditLevel === 'L1' ? 'bg-indigo-600 text-white' : 'text-zinc-500'}`}
              >
                L1
              </button>
              <button
                onClick={() => setAuditLevel('L2')}
                className={`px-2.5 py-1 rounded-lg font-medium transition ${auditLevel === 'L2' ? 'bg-indigo-600 text-white' : 'text-zinc-500'}`}
              >
                L2
              </button>
            </div>

            <button
              onClick={loadAudits}
              className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition"
              title="刷新审计日志"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoadingAudit ? 'animate-spin text-indigo-400' : ''}`} />
            </button>
          </div>
        </div>

        {/* Timeline Items */}
        <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-zinc-200 dark:before:bg-zinc-800">
          {audits.map((item) => {
            const actorMeta = ACTOR_STYLES[item.actor] || { label: item.actor, color: 'bg-zinc-800 text-zinc-400', icon: <Bot className="w-3.5 h-3.5" /> };
            const isOk = item.result === 'ok';

            return (
              <div key={item.id} className="relative group">
                {/* Timeline node dot */}
                <div className={`absolute -left-6 top-1.5 w-3 h-3 rounded-full border-2 bg-white dark:bg-zinc-900 ${
                  isOk ? 'border-emerald-500' : 'border-red-500'
                }`} />

                <div className="p-3.5 rounded-xl bg-zinc-50/70 dark:bg-zinc-950/40 border border-zinc-200 dark:border-zinc-800/80 space-y-1.5 text-xs hover:border-indigo-500/30 transition-colors">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div className="flex items-center gap-2">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-[10px] font-semibold ${actorMeta.color}`}>
                        {actorMeta.icon}
                        <span>{actorMeta.label}</span>
                      </span>
                      <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-zinc-200 dark:bg-zinc-800 text-zinc-500 font-bold">
                        {item.level}
                      </span>
                      <span className="font-mono text-zinc-500">
                        {item.action} ➔ <strong className="text-zinc-800 dark:text-zinc-200">{item.target}</strong>
                      </span>
                    </div>

                    <div className="flex items-center gap-2 font-mono text-[11px] text-zinc-400">
                      <span>{new Date(item.ts * 1000).toLocaleString('zh-CN')}</span>
                      <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                        isOk ? 'bg-emerald-500/10 text-emerald-500' : 'bg-red-500/10 text-red-500'
                      }`}>
                        {item.result}
                      </span>
                    </div>
                  </div>

                  <p className="text-zinc-800 dark:text-zinc-200 leading-relaxed">
                    {item.detail}
                  </p>

                  {item.rollback_hint && (
                    <p className="text-[11px] text-zinc-400 font-mono italic">
                      回滚依据: {item.rollback_hint}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* 3. TOKEN MANAGEMENT SECTION */}
      {tokens.length > 0 && (
        <section className="p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-800 pb-3">
            <h2 className="text-base font-bold text-zinc-900 dark:text-white flex items-center gap-2">
              <Key className="w-4 h-4 text-indigo-500" />
              <span>Agent API 凭证管家 (Token Catalog)</span>
            </h2>
            <button
              onClick={copyRotateCommand}
              className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1 font-medium"
            >
              <Copy className="w-3.5 h-3.5" />
              <span>复制轮换命令</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {tokens.map(t => (
              <div key={t.name} className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-950/40 border border-zinc-200 dark:border-zinc-800 space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-zinc-900 dark:text-zinc-100">{t.name}</span>
                  <span className="px-2 py-0.5 rounded bg-zinc-200 dark:bg-zinc-800 text-[10px] font-mono text-zinc-500">{t.purpose}</span>
                </div>
                <p className="text-zinc-500">持有方: <strong className="text-zinc-700 dark:text-zinc-300">{t.holders}</strong></p>
                <div className="text-[11px] text-zinc-400 font-mono">
                  最近活跃: {t.last_used ? new Date(t.last_used * 1000).toLocaleString('zh-CN') : '尚未记录'}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
};
