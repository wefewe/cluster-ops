"""HTML frontend template."""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Cluster Ops · 跨国高可用集群控制台</title>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 24 24%22 fill=%22none%22 stroke=%22%236366f1%22 stroke-width=%222%22 stroke-linecap=%22round%22 stroke-linejoin=%22round%22><path d=%22M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z%22/></svg>">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          fontFamily: {
            sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
            mono: ['JetBrains Mono', 'Menlo', 'Monaco', 'monospace'],
          },
          colors: {
            zinc: {
              850: '#202023',
              900: '#18181b',
              950: '#09090b',
            }
          }
        }
      }
    }
  </script>
  <style>
    @keyframes pulse-subtle { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }
    .animate-pulse-subtle { animation: pulse-subtle 3s infinite; }
    @keyframes floaty { 0%,100% { transform: translate3d(0,0,0) scale(1); } 50% { transform: translate3d(0,-16px,0) scale(1.04); } }
    @keyframes fadeUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    .fade-up { animation: fadeUp .45s cubic-bezier(.22,1,.36,1) both; }
    .hover-lift { transition: transform .25s cubic-bezier(.22,1,.36,1), box-shadow .25s ease, border-color .25s ease; }
    .hover-lift:hover { transform: translateY(-3px); box-shadow: 0 14px 34px -16px rgba(24,24,27,.4); }
    .dark .hover-lift:hover { box-shadow: 0 18px 44px -16px rgba(99,102,241,.4); border-color: rgba(99,102,241,.35); }
    #bg-aura { position: fixed; inset: 0; z-index: -1; pointer-events: none; overflow: hidden; }
    #bg-aura .blob { position: absolute; border-radius: 9999px; filter: blur(90px); opacity: .5; animation: floaty 18s ease-in-out infinite; }
    .dark #bg-aura .blob { opacity: .34; }
    .grid-veil { position: absolute; inset: 0;
      background-image: linear-gradient(to right, rgba(120,120,140,.06) 1px, transparent 1px), linear-gradient(to bottom, rgba(120,120,140,.06) 1px, transparent 1px);
      background-size: 44px 44px;
      mask-image: radial-gradient(ellipse 85% 55% at 50% 0%, #000 35%, transparent 100%);
      -webkit-mask-image: radial-gradient(ellipse 85% 55% at 50% 0%, #000 35%, transparent 100%);
    }
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: linear-gradient(180deg, rgba(99,102,241,.38), rgba(99,102,241,.16)); border-radius: 9999px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(99,102,241,.6); }
  </style>
</head>
<body class="bg-zinc-50 text-zinc-900 dark:bg-[#09090b] dark:text-zinc-100 min-h-screen font-sans antialiased selection:bg-indigo-500 selection:text-white transition-colors duration-200">

  <!-- AMBIENT BACKGROUND (subtle aurora + grid veil) -->
  <div id="bg-aura" aria-hidden="true">
    <div class="grid-veil"></div>
    <div class="blob" style="width:420px;height:420px;left:-90px;top:-120px;background:#6366f1;animation-delay:0s"></div>
    <div class="blob" style="width:360px;height:360px;right:-70px;top:60px;background:#0ea5e9;animation-delay:2.5s"></div>
    <div class="blob" style="width:340px;height:340px;left:38%;bottom:-150px;background:#10b981;animation-delay:5s"></div>
  </div>

  <!-- TOAST NOTIFICATION -->
  <div id="toast" class="fixed bottom-6 right-6 z-50 transform translate-y-20 opacity-0 transition-all duration-300 pointer-events-none">
    <div class="px-4 py-2.5 rounded-xl bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 shadow-2xl border border-zinc-700 dark:border-zinc-300 text-xs font-semibold flex items-center space-x-2">
      <span id="toast-icon"></span>
      <span id="toast-msg">已复制到剪贴板</span>
    </div>
  </div>

  <!-- LOGIN MODAL -->
  <div id="login-modal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-zinc-950/80 backdrop-blur-md transition-all duration-300">
    <div class="w-full max-w-md p-8 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-2xl relative overflow-hidden">
      <div class="absolute -top-24 -left-24 w-48 h-48 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>
      <div class="absolute -bottom-24 -right-24 w-48 h-48 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>

      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-xl bg-zinc-900 dark:bg-zinc-800 border border-zinc-800 dark:border-zinc-700/80 flex items-center justify-center text-indigo-500 shadow-inner">
          <span id="login-logo-icon"></span>
        </div>
        <div>
          <h2 class="text-lg font-bold tracking-tight text-zinc-900 dark:text-white">Cluster Ops Console</h2>
          <p class="text-xs text-zinc-500 dark:text-zinc-400">跨国三节点高可用集群全景中枢</p>
        </div>
      </div>

      <form id="login-form" class="space-y-4">
        <div>
          <label class="block text-xs font-semibold text-zinc-600 dark:text-zinc-300 uppercase tracking-wider mb-2">管理员专属密码</label>
          <input id="login-password" type="password" required autofocus placeholder="••••••••••••••••••••••••" 
            class="w-full px-4 py-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-zinc-900 dark:text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition text-sm font-mono">
        </div>
        <p id="login-error" class="text-rose-500 text-xs hidden flex items-center gap-1.5 font-medium">密码错误，请核对后重试</p>
        <button type="submit" id="login-btn"
          class="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm shadow-md transition transform active:scale-95 flex items-center justify-center space-x-2">
          <span>进入集群控制台</span>
          <span id="login-btn-arrow"></span>
        </button>
      </form>
    </div>
  </div>

  <!-- MAIN APP CONTAINER -->
  <div id="app-container" class="hidden min-h-screen flex flex-col">
    <!-- TOP NAVIGATION -->
    <header class="sticky top-0 z-40 border-b border-zinc-200 dark:border-zinc-800/80 bg-white/80 dark:bg-[#09090b]/80 backdrop-blur-md px-6 py-3 transition-colors">
      <div class="max-w-7xl mx-auto flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <div class="w-9 h-9 rounded-xl bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 flex items-center justify-center text-indigo-500 dark:text-indigo-400 shadow-sm">
            <span id="nav-logo-icon"></span>
          </div>
          <div>
            <div class="flex items-center space-x-2">
              <h1 class="text-sm sm:text-base font-bold tracking-tight text-zinc-900 dark:text-zinc-100">Cluster Ops</h1>
              <span class="px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">3-Manager Quorum</span>
            </div>
            <p class="text-[11px] text-zinc-500 dark:text-zinc-400">Docker Swarm · Traefik v3 · WireGuard Mesh</p>
          </div>
        </div>

        <div class="flex items-center space-x-2 sm:space-x-3">
          <!-- THEME TOGGLE BUTTON -->
          <button id="theme-btn" class="px-2.5 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-xs font-medium transition flex items-center space-x-1.5 text-zinc-700 dark:text-zinc-300 shadow-xs">
            <span id="theme-icon"></span>
            <span id="theme-text" class="hidden sm:inline">深色</span>
          </button>

          <!-- AUTO REFRESH COUNTDOWN BADGE -->
          <button id="autorefresh-btn" class="px-3 py-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-xs font-medium text-emerald-700 dark:text-emerald-400 hover:bg-emerald-500/20 transition flex items-center space-x-1.5 shadow-xs">
            <span class="relative flex h-2 w-2">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span id="autorefresh-label">自动刷新: <strong id="countdown-text" class="font-mono">30s</strong></span>
          </button>

          <!-- MANUAL REFRESH -->
          <button id="refresh-btn" title="立即刷新" class="p-2 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-xs font-medium transition text-zinc-700 dark:text-zinc-300">
            <span id="refresh-icon" class="inline-block"></span>
          </button>

          <!-- LOGOUT -->
          <button id="logout-btn" class="px-3 py-1.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs font-medium hover:bg-rose-500/20 text-rose-600 dark:text-rose-400 transition flex items-center space-x-1.5">
            <span id="logout-icon"></span>
            <span class="hidden sm:inline">退出</span>
          </button>
        </div>
      </div>
    </header>

    <!-- QUICK COCKPIT BAR (FEATURE 4) -->
    <div class="border-b border-zinc-200 dark:border-zinc-800/80 bg-zinc-50 dark:bg-zinc-950/60 px-6 py-2">
      <div id="cockpit-bar" class="max-w-7xl mx-auto flex flex-wrap items-center gap-x-2 gap-y-1.5 text-xs">
        <!-- Dynamic Cockpit Pills with SVG Icons -->
      </div>
    </div>

    <!-- CONTENT BODY -->
    <main class="max-w-7xl mx-auto px-6 py-8 flex-1 w-full space-y-8">

      <!-- SECTION 1: PHYSICAL NODES & REAL-TIME TELEMETRY (RESTRUCTURED) -->
      <section class="space-y-5">
        <!-- 核心云端高可用生产环 (3-Manager Cloud Quorum) -->
        <div>
          <div class="flex items-center justify-between mb-3">
            <h2 class="text-xs sm:text-sm font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 flex items-center space-x-2">
              <span id="sec1-icon"></span>
              <span>核心云端生产拓扑环 (3-Manager Quorum · 100% 高可用)</span>
            </h2>
            <span class="text-xs text-emerald-600 dark:text-emerald-400 font-mono flex items-center gap-1.5 font-medium">
              <span class="relative flex h-2 w-2">
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              JP · US · RN 跨洋骨干 Mesh
            </span>
          </div>
          <div id="core-nodes-grid" class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <!-- 3 核心云端生产节点卡片 -->
          </div>
        </div>

        <!-- 边缘混合内网接入节点 (Edge Worker Mesh, 仅在存在边缘节点时显示) -->
        <div id="edge-section" class="pt-1 hidden">
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center space-x-2">
              <span class="text-amber-500 text-sm">🏠</span>
              <span class="text-xs sm:text-sm font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">边缘混合接入节点 (Edge Worker Mesh)</span>
            </div>
            <span class="text-[11px] text-zinc-400 font-mono">WireGuard 专线接入</span>
          </div>
          <div id="edge-nodes-grid">
            <!-- 边缘节点卡片 -->
          </div>
        </div>
      </section>

      <!-- SECTION 2: TOP METRICS -->
      <section id="summary-cards" class="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <!-- Dynamic Summary Cards -->
      </section>

      <!-- ═══ SECTION 3: 自动化自愈与 AI 智能中枢 (AUTOMATION & AI CO-PILOT) ═══ -->
      <section id="automation-section" class="rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/60 p-6 shadow-sm relative transition-colors">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
          <div>
            <h2 class="text-base font-bold text-zinc-900 dark:text-white flex items-center space-x-2">
              <span id="sec5-icon"></span>
              <span>自动化自愈与 AI 智能中枢 (Automation & AI Co-Pilot)</span>
            </h2>
            <p class="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">三流水线异地冷备互备环 · cluster-guard 6h 闭环巡检 · 月度恢复演练 · OpenClaw 运维管家 · 全集群定时调度</p>
          </div>
          <div class="flex items-center space-x-2">
            <span id="auto-overall-badge" class="px-2.5 py-1 rounded-lg text-[11px] font-mono font-bold border">…</span>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <!-- Col 1: Backups -->
          <div class="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/70 dark:bg-zinc-950/50 p-4 flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between pb-2 mb-3 border-b border-zinc-200 dark:border-zinc-800">
                <span class="text-xs font-bold text-zinc-800 dark:text-zinc-200 uppercase tracking-wider flex items-center gap-1.5">
                  <span class="text-emerald-500">📦</span> 异地容灾冷备流水线
                </span>
                <span class="text-[10px] text-zinc-400 font-mono">25h 阈值 · 3机互备环</span>
              </div>
              <div id="auto-backups" class="space-y-2 text-xs font-mono"></div>
            </div>
            <div class="pt-3 mt-3 border-t border-zinc-200 dark:border-zinc-800/80 text-[11px] text-zinc-400 flex items-center justify-between">
              <span>每日错峰: 03:30 / 04:00 / 04:30</span>
              <span class="text-emerald-500 font-medium">TG 告警闭环</span>
            </div>
          </div>

          <!-- Col 2: Guard & Drill & Snapshots -->
          <div class="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/70 dark:bg-zinc-950/50 p-4 flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between pb-2 mb-3 border-b border-zinc-200 dark:border-zinc-800">
                <span class="text-xs font-bold text-zinc-800 dark:text-zinc-200 uppercase tracking-wider flex items-center gap-1.5">
                  <span class="text-amber-500">🛡️</span> 巡检哨兵与自愈验证
                </span>
                <span class="text-[10px] text-zinc-400 font-mono">只读探针 · 异常报警</span>
              </div>
              <div id="auto-guard" class="space-y-2 text-xs"></div>
            </div>
            <div class="pt-3 mt-3 border-t border-zinc-200 dark:border-zinc-800/80 text-[11px] text-zinc-400 flex items-center justify-between">
              <span>周日 05:00 清理 · 周一 06:00 快照</span>
              <span class="text-indigo-400 font-medium">机器实测仲裁</span>
            </div>
          </div>

          <!-- Col 3: Dedicated OpenClaw Co-Pilot Card -->
          <div class="rounded-xl border border-indigo-200/80 dark:border-indigo-900/50 bg-gradient-to-b from-indigo-50/50 to-white dark:from-indigo-950/30 dark:to-zinc-950/60 p-4 flex flex-col justify-between shadow-xs">
            <div>
              <div class="flex items-center justify-between pb-2 mb-3 border-b border-zinc-200 dark:border-zinc-800">
                <span class="text-xs font-bold text-zinc-900 dark:text-white uppercase tracking-wider flex items-center gap-1.5">
                  <span>🤖</span> AI 智能运维管家 (OpenClaw)
                </span>
                <span id="agent-active-badge" class="px-2 py-0.5 rounded-full text-[10px] font-medium border font-mono">…</span>
              </div>
              <div id="auto-agent-card" class="space-y-1.5 text-xs"></div>
            </div>
            <div class="pt-3 mt-3 border-t border-zinc-200 dark:border-zinc-800/80 flex items-center justify-between gap-2">
              <a href="https://agent.cwsub.indevs.in" target="_blank" class="flex-1 text-center py-1.5 px-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-[11px] shadow-xs transition flex items-center justify-center gap-1">
                <span>直达 Web 控制台</span> <span>↗</span>
              </a>
              <a href="https://t.me/cwsub_cluster_agent_bot" target="_blank" class="py-1.5 px-2.5 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 hover:border-indigo-400 text-zinc-700 dark:text-zinc-300 font-medium text-[11px] transition flex items-center gap-1">
                <span>💬 Telegram</span>
              </a>
            </div>
          </div>
        </div>

        <!-- Timers Sub-Bar -->
        <div class="mt-5 pt-4 border-t border-zinc-200 dark:border-zinc-800">
          <div class="flex items-center justify-between mb-2.5">
            <span class="text-[11px] font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
              <span>⏱️</span> 全集群定时任务调度矩阵 (Systemd Timers)
            </span>
            <span class="text-[10px] text-zinc-400 font-mono">9 个全局定时器运行中</span>
          </div>
          <div id="auto-timers" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 text-xs font-mono"></div>
        </div>
      </section>

      <!-- ═══ SECTION 3B: AI 操作审计时间线 (AUDIT TIMELINE) ═══ -->
      <section class="rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/60 p-6 shadow-sm relative transition-colors">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
          <div>
            <h2 class="text-base font-bold text-zinc-900 dark:text-white flex items-center space-x-2">
              <span>🧾</span>
              <span>AI 操作审计时间线</span>
            </h2>
            <p class="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">三方 AI 的 L1/L2 写操作自动记账（5 分钟内上报），失败与驳回标红</p>
          </div>
          <div class="flex flex-wrap items-center gap-2 text-xs">
            <div class="flex rounded-xl bg-zinc-100 dark:bg-zinc-950 p-1 border border-zinc-200 dark:border-zinc-800">
              <button onclick="setAuditFilter('actor','')" data-af="actor:" class="audit-filter px-2.5 py-1 rounded-lg font-medium text-white bg-indigo-600 transition">全部</button>
              <button onclick="setAuditFilter('actor','openclaw')" data-af="actor:openclaw" class="audit-filter px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 transition">openclaw</button>
              <button onclick="setAuditFilter('actor','opencode')" data-af="actor:opencode" class="audit-filter px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 transition">opencode</button>
              <button onclick="setAuditFilter('actor','muse-spark')" data-af="actor:muse-spark" class="audit-filter px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 transition">muse-spark</button>
            </div>
            <div class="flex rounded-xl bg-zinc-100 dark:bg-zinc-950 p-1 border border-zinc-200 dark:border-zinc-800">
              <button onclick="setAuditFilter('level','')" data-af="level:" class="audit-filter px-2.5 py-1 rounded-lg font-medium text-white bg-indigo-600 transition">L1+L2</button>
              <button onclick="setAuditFilter('level','L1')" data-af="level:L1" class="audit-filter px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 transition">L1</button>
              <button onclick="setAuditFilter('level','L2')" data-af="level:L2" class="audit-filter px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 transition">L2</button>
            </div>
          </div>
        </div>
        <div id="audit-list" class="space-y-2 text-sm max-h-96 overflow-y-auto pr-1">
          <div class="text-xs text-zinc-400 py-4 text-center">加载中…</div>
        </div>
      </section>

      <!-- ═══ SECTION 3C: L2 审批队列 (APPROVAL QUEUE) ═══ -->
      <section class="rounded-2xl border border-amber-200 dark:border-amber-900/60 bg-white dark:bg-zinc-900/60 p-6 shadow-sm relative transition-colors">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
          <div>
            <h2 class="text-base font-bold text-zinc-900 dark:text-white flex items-center space-x-2">
              <span id="sec3c-icon"></span>
              <span>L2 审批队列</span>
              <span id="approval-pending-badge" class="hidden text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300"></span>
            </h2>
            <p class="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">AI 发起的 L2 高风险操作需在此批准；24 小时未处理自动驳回</p>
          </div>
          <div class="flex rounded-xl bg-zinc-100 dark:bg-zinc-950 p-1 border border-zinc-200 dark:border-zinc-800 text-xs">
            <button onclick="setApprovalFilter('pending')" data-apf="pending" class="approval-filter px-2.5 py-1 rounded-lg font-medium text-white bg-indigo-600 transition">待处理</button>
            <button onclick="setApprovalFilter('')" data-apf="" class="approval-filter px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 transition">全部</button>
          </div>
        </div>
        <div id="approval-list" class="space-y-2 text-sm max-h-96 overflow-y-auto pr-1">
          <div class="text-xs text-zinc-400 py-4 text-center">加载中…</div>
        </div>
      </section>

      <!-- SECTION 4: DOMAIN & ROUTING MATRIX (SWARM MANAGED) -->
      <section class="rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/60 p-6 shadow-sm relative transition-colors">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <h2 class="text-base font-bold text-zinc-900 dark:text-white flex items-center space-x-2">
              <span id="sec3-icon"></span>
              <span>全域微服务与域名拓扑矩阵 (Traefik v3 动态发现)</span>
            </h2>
            <p class="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">自动汇聚 Traefik 与 Docker Swarm，显示实时网络延时与内部端口</p>
          </div>

          <!-- CONTROLS -->
          <div class="flex flex-wrap items-center gap-2">
            <!-- VIEW MODE TOGGLE -->
            <div class="flex rounded-xl bg-zinc-100 dark:bg-zinc-950 p-1 border border-zinc-200 dark:border-zinc-800 text-xs">
              <button id="view-accordion-btn" onclick="setRouteView('accordion')" class="px-2.5 py-1 rounded-lg font-medium text-white bg-indigo-600 transition shadow-xs">📑 堆栈手风琴</button>
              <button id="view-flat-btn" onclick="setRouteView('flat')" class="px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition">📋 全景大表</button>
            </div>

            <!-- EXPAND/COLLAPSE (Accordion only) -->
            <div id="accordion-controls" class="flex rounded-xl bg-zinc-100 dark:bg-zinc-950 p-1 border border-zinc-200 dark:border-zinc-800 text-xs">
              <button id="expand-all-btn" class="px-2.5 py-1 rounded-lg text-zinc-600 dark:text-zinc-300 hover:text-indigo-600 dark:hover:text-indigo-400 transition font-medium">全部展开</button>
              <button id="collapse-all-btn" class="px-2.5 py-1 rounded-lg text-zinc-600 dark:text-zinc-300 hover:text-indigo-600 dark:hover:text-indigo-400 transition font-medium">全部折叠</button>
            </div>

            <div class="relative">
              <input id="search-input" type="text" placeholder="搜索 Stack、域名、服务..." 
                class="w-36 sm:w-48 pl-8 pr-3 py-1.5 rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs text-zinc-800 dark:text-zinc-200 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition">
              <span id="search-icon" class="absolute left-2.5 top-2 text-zinc-400"></span>
            </div>

            <div id="filter-tabs" class="flex rounded-xl bg-zinc-100 dark:bg-zinc-950 p-1 border border-zinc-200 dark:border-zinc-800 text-xs">
              <button data-filter="all" class="filter-tab px-2.5 py-1 rounded-lg font-medium text-white bg-indigo-600 transition shadow-xs">全部</button>
              <button data-filter="jp-oracle" class="filter-tab px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition">🇯🇵 jp-oracle</button>
              <button data-filter="us-oracle" class="filter-tab px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition">🇺🇸 us-oracle</button>
              <button data-filter="us-racknerd" class="filter-tab px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition">🟣 us-racknerd</button>
            </div>
          </div>
        </div>

        <!-- STACKS ACCORDION OR FLAT TABLE CONTAINER -->
        <div id="routes-wrapper">
          <div id="stacks-accordion" class="space-y-3">
            <!-- Dynamic Accordion Items -->
          </div>
        </div>
      </section>

      <!-- SECTION 5: STANDALONE DAEMONS & HOST SYSTEMD (FEATURE 2) -->
      <section class="rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/60 p-6 shadow-sm relative transition-colors">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div>
            <h2 class="text-base font-bold text-zinc-900 dark:text-white flex items-center space-x-2">
              <span id="sec4-icon"></span>
              <span>单机宿主守护进程专区 (Standalone Daemons & Host Systemd)</span>
            </h2>
            <p class="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">三台物理节点的基础单机服务，按标准槽位严格横向对齐（硬件探针、出海网格、每小时更新与节点特化）</p>
          </div>
          <div class="flex items-center space-x-2">
            <!-- VIEW TOGGLE (Matrix vs Cards) -->
            <div class="flex rounded-xl bg-zinc-100 dark:bg-zinc-950 p-1 border border-zinc-200 dark:border-zinc-800 text-xs">
              <button id="view-matrix-btn" onclick="setDaemonView('matrix')" class="px-2.5 py-1 rounded-lg font-medium text-white bg-indigo-600 transition shadow-xs">📊 横向矩阵</button>
              <button id="view-cards-btn" onclick="setDaemonView('cards')" class="px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition">📋 对齐卡片</button>
            </div>
            <button onclick="toggleStandaloneAccordion()" class="text-xs text-zinc-500 hover:text-indigo-500 transition font-medium flex items-center gap-1">
              <span id="standalone-toggle-arrow">▼</span>
              <span id="standalone-toggle-text">折叠</span>
            </button>
          </div>
        </div>

        <div id="standalone-wrapper">
          <!-- Dynamic Standalone Content (Matrix or Aligned Cards) -->
        </div>

        <!-- Host Systemd Daemons Bar -->
        <div id="host-systemd-container" class="mt-4 pt-3.5 border-t border-zinc-200 dark:border-zinc-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <div class="flex items-center gap-2 text-zinc-500 dark:text-zinc-400">
            <span class="font-semibold text-[11px] uppercase tracking-wider">宿主系统守护底座 (Systemd):</span>
            <span class="text-[10px] text-zinc-400 font-mono hidden sm:inline">(无容器原生守护 · 与 Docker 容器严格分层)</span>
          </div>
          <div id="host-systemd-badges" class="flex flex-wrap items-center gap-2 text-[11px] font-mono"></div>
        </div>
      </section>

    </main>

    <!-- FOOTER -->
    <footer class="border-t border-zinc-200 dark:border-zinc-800 py-6 text-center text-xs text-zinc-500 dark:text-zinc-400 transition-colors">
      跨国双向自愈 Mesh 架构 · Traefik v3 Swarm 动态服务发现 · 本地 GitOps 受控 · 自动健康巡检
    </footer>
  </div>

  <script>
    // --- LUCIDE SVG ICON SYSTEM ---
    const ICONS = {
      shield: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`,
      server: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="8" x="2" y="2" rx="2" ry="2"/><rect width="20" height="8" x="2" y="14" rx="2" ry="2"/><line x1="6" x2="6.01" y1="6" y2="6"/><line x1="6" x2="6.01" y1="18" y2="18"/></svg>`,
      cpu: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect width="16" height="16" x="4" y="4" rx="2"/><rect width="6" height="6" x="9" y="9" rx="1"/><path d="M15 2v2"/><path d="M15 20v2"/><path d="M2 15h2"/><path d="M2 9h2"/><path d="M20 15h2"/><path d="M20 9h2"/><path d="M9 2v2"/><path d="M9 20v2"/></svg>`,
      harddrive: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><line x1="22" x2="2" y1="12" y2="12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/><line x1="6" x2="6.01" y1="16" y2="16"/><line x1="10" x2="10.01" y1="16" y2="16"/></svg>`,
      layers: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>`,
      globe: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" x2="22" y1="12" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>`,
      lock: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>`,
      copy: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>`,
      check: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`,
      search: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" x2="16.65" y1="21" y2="16.65"/></svg>`,
      refresh: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M3 21v-5h5"/></svg>`,
      moon: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>`,
      sun: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>`,
      logout: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/></svg>`,
      external: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" x2="21" y1="14" y2="3"/></svg>`,
      chevronDown: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>`,
      chevronRight: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>`,
      arrowRight: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>`,
      brain: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-2.04z"/><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-4.44-2.04z"/></svg>`,
      bot: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="12" x="3" y="6" rx="2"/><circle cx="9" cy="12" r="1"/><circle cx="15" cy="12" r="1"/><path d="M12 2v4"/><path d="M2 12h1"/><path d="M21 12h1"/></svg>`,
      chart: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><line x1="18" x2="18" y1="20" y2="10"/><line x1="12" x2="12" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="14"/></svg>`,
      clock: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,
      zap: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`,
      folder: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>`,
      box: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/></svg>`,
      radio: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="2"/><path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49m11.31-2.82a10 10 0 0 1 0 14.14m-14.14 0a10 10 0 0 1 0-14.14"/></svg>`,
      activity: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>`,
      settings: `<svg class="CLASS" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>`
    };

    function icon(name, cls = "w-4 h-4") {
      const template = ICONS[name] || ICONS.box;
      return template.replace('CLASS', cls);
    }

    let currentData = null;
    let activeFilter = 'all';
    let expandedStacks = new Set();
    let standaloneExpanded = true;
    let routeView = localStorage.getItem('ops_route_view') || 'accordion';
    let daemonView = localStorage.getItem('ops_daemon_view') || 'matrix';
    let refreshSeconds = 30;
    let countdown = 30;
    let timerId = null;

    // Static Icon Injections
    document.getElementById('toast-icon').innerHTML = icon('copy', 'w-4 h-4 text-zinc-400');
    document.getElementById('login-logo-icon').innerHTML = icon('shield', 'w-5 h-5 text-indigo-400');
    document.getElementById('login-btn-arrow').innerHTML = icon('arrowRight', 'w-4 h-4');
    document.getElementById('nav-logo-icon').innerHTML = icon('shield', 'w-4 h-4 text-indigo-400');
    document.getElementById('refresh-icon').innerHTML = icon('refresh', 'w-3.5 h-3.5');
    document.getElementById('logout-icon').innerHTML = icon('logout', 'w-3.5 h-3.5');
    document.getElementById('sec1-icon').innerHTML = icon('server', 'w-4 h-4 text-indigo-500');
    document.getElementById('sec3-icon').innerHTML = icon('globe', 'w-4 h-4 text-indigo-500');
      document.getElementById('sec4-icon').innerHTML = icon('settings', 'w-4 h-4 text-indigo-500');
      document.getElementById('sec5-icon').innerHTML = icon('zap', 'w-4 h-4 text-indigo-500');
    document.getElementById('search-icon').innerHTML = icon('search', 'w-3.5 h-3.5');

    // Quick Cockpit Bar Renderer (Environment Configurable or Generic Defaults)
    const COCKPIT_ITEMS = window.__OPS_COCKPIT_ITEMS__ || [
      { name: 'Portainer', url: 'https://portainer.cwsub.indevs.in', icon: 'box', color: 'text-blue-400' },
      { name: 'AI 管家', url: 'https://agent.cwsub.indevs.in', icon: 'zap', color: 'text-emerald-400' },
      { name: 'AxonHub', url: 'https://axonhub.cwsub.indevs.in', icon: 'brain', color: 'text-indigo-400' },
      { name: 'CLIProxy', url: 'https://cliproxy.cwsub.indevs.in', icon: 'bot', color: 'text-purple-400' },
      { name: 'Vaultwarden', url: 'https://vault.cjwmf.eu.org', icon: 'shield', color: 'text-emerald-400' },
      { name: 'Beszel', url: 'https://beszel.cjwmf.eu.org', icon: 'chart', color: 'text-cyan-400' },
      { name: 'Uptime-Kuma', url: 'https://uptime.cjwmf.eu.org/dashboard', icon: 'clock', color: 'text-amber-400' },
      { name: 'WorkBuddy', url: 'https://workapi.cwsub.indevs.in/dashboard/', icon: 'zap', color: 'text-yellow-400' },
      { name: 'OpenList', url: 'https://openlist.cwsub.indevs.in', icon: 'folder', color: 'text-sky-400' },
      { name: 'Sub-Store', url: 'https://substore.cwsub.indevs.in', icon: 'radio', color: 'text-rose-400' },
      { name: 'FreeLLMAPI', url: 'https://freellmapi.cwsub.indevs.in', icon: 'zap', color: 'text-violet-400' },
      { name: 'Cline2API', url: 'https://cline.cwsub.indevs.in', icon: 'bot', color: 'text-teal-400' }
    ];

    document.getElementById('cockpit-bar').innerHTML = `
      <span class="w-full text-zinc-400 dark:text-zinc-500 font-semibold text-[11px] uppercase tracking-wider whitespace-nowrap">极速直达:</span>
      ${COCKPIT_ITEMS.map(item => `
        <a href="${item.url}" target="_blank" class="px-2.5 py-1 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 hover:border-zinc-400 dark:hover:border-zinc-600 text-zinc-700 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-white transition duration-200 hover:-translate-y-0.5 hover:shadow-md hover:shadow-indigo-500/10 flex items-center space-x-1.5 whitespace-nowrap shadow-2xs group">
          <span class="${item.color} transition group-hover:scale-110 inline-block">${icon(item.icon, 'w-3.5 h-3.5')}</span>
          <span class="font-medium">${item.name}</span>
        </a>
      `).join('')}
    `;

    // Toast helper
    function showToast(msg) {
      const t = document.getElementById('toast');
      const m = document.getElementById('toast-msg');
      m.textContent = msg;
      t.classList.remove('translate-y-20', 'opacity-0');
      setTimeout(() => t.classList.add('translate-y-20', 'opacity-0'), 2000);
    }

    // Copy to clipboard helper
    window.copyText = function(text, label) {
      navigator.clipboard.writeText(text).then(() => {
        showToast(`已复制 ${label}: ${text}`);
      }).catch(() => {
        showToast(`复制成功: ${text}`);
      });
    };

    // Theme Engine (Zinc Style)
    function initTheme() {
      const savedTheme = localStorage.getItem('ops_theme') || 'dark';
      applyTheme(savedTheme);
    }

    function applyTheme(theme) {
      const html = document.documentElement;
      const iconSpan = document.getElementById('theme-icon');
      const textSpan = document.getElementById('theme-text');
      if (theme === 'light') {
        html.classList.remove('dark');
        iconSpan.innerHTML = icon('sun', 'w-3.5 h-3.5 text-amber-500');
        textSpan.textContent = '浅色';
        localStorage.setItem('ops_theme', 'light');
      } else {
        html.classList.add('dark');
        iconSpan.innerHTML = icon('moon', 'w-3.5 h-3.5 text-indigo-400');
        textSpan.textContent = '深色';
        localStorage.setItem('ops_theme', 'dark');
      }
    }

    document.getElementById('theme-btn').addEventListener('click', () => {
      const isDark = document.documentElement.classList.contains('dark');
      applyTheme(isDark ? 'light' : 'dark');
    });

    // Auto Refresh Countdown Engine
    function startCountdown() {
      if (timerId) clearInterval(timerId);
      timerId = setInterval(() => {
        if (refreshSeconds <= 0) return;
        countdown--;
        const cdElem = document.getElementById('countdown-text');
        if (cdElem) cdElem.textContent = countdown + 's';

        if (countdown <= 0) {
          silentRefresh();
          countdown = refreshSeconds;
        }
      }, 1000);
    }

    async function silentRefresh() {
      try {
        const res = await fetch('/api/data');
        if (res.status === 200) {
          currentData = await res.json();
          renderDashboard(currentData);
        }
      } catch (e) {}
    }

    document.getElementById('autorefresh-btn').addEventListener('click', () => {
      if (refreshSeconds === 30) {
        refreshSeconds = 15;
      } else if (refreshSeconds === 15) {
        refreshSeconds = 60;
      } else if (refreshSeconds === 60) {
        refreshSeconds = 0; // pause
      } else {
        refreshSeconds = 30;
      }
      countdown = refreshSeconds;
      const label = document.getElementById('autorefresh-label');
      if (refreshSeconds === 0) {
        label.innerHTML = '自动刷新: <strong class="text-zinc-400">已暂停</strong>';
      } else {
        label.innerHTML = `自动刷新: <strong id="countdown-text" class="font-mono">${countdown}s</strong>`;
      }
    });

    // Auth Check
    async function checkAuth() {
      try {
        const res = await fetch('/api/auth-check');
        const data = await res.json();
        if (data.authenticated) {
          document.getElementById('login-modal').classList.add('hidden');
          document.getElementById('app-container').classList.remove('hidden');
          loadData();
          startCountdown();
        } else {
          document.getElementById('login-modal').classList.remove('hidden');
          document.getElementById('app-container').classList.add('hidden');
        }
      } catch (e) {
        document.getElementById('login-modal').classList.remove('hidden');
      }
    }

    async function loadData() {
      try {
        const res = await fetch('/api/data');
        if (res.status === 401) {
          checkAuth();
          return;
        }
        currentData = await res.json();
        renderDashboard(currentData);
      } catch (e) {}
    }

    document.getElementById('login-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const pwd = document.getElementById('login-password').value;
      const err = document.getElementById('login-error');
      try {
        const res = await fetch('/api/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ password: pwd })
        });
        if (res.status === 200) {
          err.classList.add('hidden');
          document.getElementById('login-modal').classList.add('hidden');
          document.getElementById('app-container').classList.remove('hidden');
          loadData();
          startCountdown();
        } else {
          err.classList.remove('hidden');
        }
      } catch (e) {
        err.classList.remove('hidden');
      }
    });

    document.getElementById('logout-btn').addEventListener('click', async () => {
      await fetch('/api/logout', { method: 'POST' });
      location.reload();
    });

    document.getElementById('refresh-btn').addEventListener('click', async () => {
      const iconSpan = document.getElementById('refresh-icon');
      iconSpan.classList.add('animate-spin');
      countdown = refreshSeconds;
      await silentRefresh();
      setTimeout(() => iconSpan.classList.remove('animate-spin'), 600);
    });

    // Better Stack Heartbeat Live Response Badge
    function renderProbeBadge(code, ms) {
      const isSuccess = code >= 200 && code < 400;
      const dotClass = isSuccess ? 'bg-emerald-500' : 'bg-rose-500';
      const pingClass = isSuccess ? 'bg-emerald-400' : 'bg-rose-400';
      const badgeClass = isSuccess 
        ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20' 
        : 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20';

      return `
        <span class="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-[10px] font-mono font-medium border ${badgeClass}">
          <span class="relative flex h-1.5 w-1.5">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full ${pingClass} opacity-75"></span>
            <span class="relative inline-flex rounded-full h-1.5 w-1.5 ${dotClass}"></span>
          </span>
          <span>${code}</span>
          <span class="text-zinc-400 dark:text-zinc-600">·</span>
          <span class="font-semibold text-zinc-700 dark:text-zinc-200">${ms}ms</span>
        </span>
      `;
    }

    // Dashboard Renderer
    function renderDashboard(data) {
      if (!data) return;

      const coreNodes = data.nodes.filter(n => n.role === 'Leader' || n.role === 'Manager');
      const edgeNodes = data.nodes.filter(n => n.role !== 'Leader' && n.role !== 'Manager');

      // Toggle edge section: only show when edge nodes exist
      const edgeSection = document.getElementById('edge-section');
      if (edgeSection) edgeSection.classList.toggle('hidden', edgeNodes.length === 0);

      // 1. Render Core Cloud Quorum Nodes (3 Columns)
      const coreContainer = document.getElementById('core-nodes-grid');
      if (coreContainer) {
        coreContainer.innerHTML = coreNodes.map(n => {
          const hw = n.hardware || {};
          const cpu = hw.cpu_pct !== undefined ? hw.cpu_pct : 0;
          const mem_pct = hw.mem_pct !== undefined ? hw.mem_pct : 0;
          const disk_pct = hw.disk_pct !== undefined ? hw.disk_pct : 0;
          const mem_used_gb = hw.mem_used_mb ? (hw.mem_used_mb / 1024).toFixed(1) : '-';
          const mem_total_gb = hw.mem_total_mb ? (hw.mem_total_mb / 1024).toFixed(1) : '-';
          const disk_used = hw.disk_used_gb !== undefined ? hw.disk_used_gb : '-';
          const disk_total = hw.disk_total_gb !== undefined ? hw.disk_total_gb : '-';

          return `
            <div class="hover-lift p-5 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-900/60 shadow-xs relative overflow-hidden flex flex-col justify-between space-y-4">
              <div class="flex items-start justify-between">
                <div>
                  <div class="flex items-center space-x-2">
                    <span class="font-bold text-sm text-zinc-900 dark:text-white">${n.name}</span>
                  </div>
                  <p class="text-xs text-zinc-500 dark:text-zinc-400 font-mono mt-0.5">${n.ip} · ${n.arch}</p>
                </div>
                <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
                  n.role === 'Leader' ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20' : 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20'
                }">${n.role}</span>
              </div>

              <!-- Hardware Telemetry -->
              <div class="space-y-3 pt-1 text-xs">
                <div>
                  <div class="flex justify-between text-[11px] mb-1">
                    <span class="text-zinc-500 dark:text-zinc-400 flex items-center gap-1">${icon('cpu', 'w-3 h-3')} CPU 负载</span>
                    <span class="font-mono font-semibold text-zinc-800 dark:text-zinc-200">${cpu}%</span>
                  </div>
                  <div class="w-full bg-zinc-100 dark:bg-zinc-800 rounded-full h-1.5 overflow-hidden">
                    <div class="bg-indigo-500 h-1.5 rounded-full transition-all duration-500" style="width: ${Math.min(cpu, 100)}%"></div>
                  </div>
                </div>

                <div>
                  <div class="flex justify-between text-[11px] mb-1">
                    <span class="text-zinc-500 dark:text-zinc-400 flex items-center gap-1">${icon('layers', 'w-3 h-3')} 内存占用 (${mem_pct}%)</span>
                    <span class="font-mono text-[10px] text-zinc-700 dark:text-zinc-300">${mem_used_gb}G / ${mem_total_gb}G</span>
                  </div>
                  <div class="w-full bg-zinc-100 dark:bg-zinc-800 rounded-full h-1.5 overflow-hidden">
                    <div class="${mem_pct > 80 ? 'bg-rose-500' : 'bg-emerald-500'} h-1.5 rounded-full transition-all duration-500" style="width: ${Math.min(mem_pct, 100)}%"></div>
                  </div>
                </div>

                <div>
                  <div class="flex justify-between text-[11px] mb-1">
                    <span class="text-zinc-500 dark:text-zinc-400 flex items-center gap-1">${icon('harddrive', 'w-3 h-3')} 系统固态 (${disk_pct}%)</span>
                    <span class="font-mono text-[10px] text-zinc-700 dark:text-zinc-300">${disk_used}G / ${disk_total}G</span>
                  </div>
                  <div class="w-full bg-zinc-100 dark:bg-zinc-800 rounded-full h-1.5 overflow-hidden">
                    <div class="${disk_pct > 80 ? 'bg-amber-500' : 'bg-sky-500'} h-1.5 rounded-full transition-all duration-500" style="width: ${Math.min(disk_pct, 100)}%"></div>
                  </div>
                </div>
              </div>

              <!-- Footer info -->
              <div class="grid grid-cols-2 gap-2 pt-2.5 border-t border-zinc-200 dark:border-zinc-800/80 text-xs">
                <div>
                  <span class="text-zinc-400 dark:text-zinc-500 block text-[10px] uppercase">节点状态</span>
                  <span class="text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1.5 mt-0.5">
                    <span class="relative flex h-1.5 w-1.5">
                      <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                      <span class="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
                    </span>
                    <span>${n.status}</span>
                  </span>
                </div>
                <div>
                  <span class="text-zinc-400 dark:text-zinc-500 block text-[10px] uppercase">Swarm 任务</span>
                  <span class="text-zinc-800 dark:text-white font-semibold font-mono mt-0.5 block">${n.tasks_count} 个微服务</span>
                </div>
              </div>
            </div>
          `;
        }).join('');
      }

      // 2. Render Edge Worker Nodes (if any)
      const edgeContainer = document.getElementById('edge-nodes-grid');
      if (edgeContainer && edgeNodes.length > 0) {
        edgeContainer.innerHTML = edgeNodes.map(n => {
          const hw = n.hardware || {};
          const isOnline = hw.status === 'online' || n.status === 'ready';
          const cpu = hw.cpu_pct !== undefined ? hw.cpu_pct : 0;
          const mem_pct = hw.mem_pct !== undefined ? hw.mem_pct : 0;
          const disk_pct = hw.disk_pct !== undefined ? hw.disk_pct : 0;
          const mem_used_gb = hw.mem_used_mb ? (hw.mem_used_mb / 1024).toFixed(1) : '-';
          const mem_total_gb = hw.mem_total_mb ? (hw.mem_total_mb / 1024).toFixed(1) : '5.2';
          const disk_used = hw.disk_used_gb !== undefined ? hw.disk_used_gb : '-';
          const disk_total = hw.disk_total_gb !== undefined ? hw.disk_total_gb : '-';

          return `
            <div class="hover-lift p-5 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-900/60 shadow-xs relative overflow-hidden">
              <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-zinc-200 dark:border-zinc-800/80">
                <div class="flex items-center space-x-3">
                  <div class="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-500 text-lg flex-shrink-0">
                    🏠
                  </div>
                  <div>
                    <div class="flex items-center space-x-2">
                      <span class="font-bold text-sm text-zinc-900 dark:text-white">${n.name}</span>
                      <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">${n.role}</span>
                      <span class="px-2 py-0.5 rounded-full text-[10px] font-mono text-zinc-500 bg-zinc-100 dark:bg-zinc-800">WireGuard Mesh</span>
                    </div>
                    <p class="text-xs text-zinc-500 dark:text-zinc-400 font-mono mt-0.5">${n.ip} · ${n.arch} · 中继节点: US-RackNerd (10.10.0.3)</p>
                  </div>
                </div>

                <div class="flex items-center gap-4 text-xs font-mono">
                  <div class="flex items-center gap-1.5">
                    <span class="relative flex h-2 w-2">
                      <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                      <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                    </span>
                    <span class="text-emerald-600 dark:text-emerald-400 font-semibold">Swarm: ${n.status}</span>
                  </div>
                  <span class="text-zinc-300 dark:text-zinc-700">|</span>
                  <span class="text-zinc-500">调度任务: <strong class="text-zinc-800 dark:text-zinc-200">${n.tasks_count} 容器</strong></span>
                </div>
              </div>

              <!-- Edge Hardware Meters -->
              <div class="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4 text-xs">
                <div>
                  <div class="flex justify-between text-[11px] mb-1">
                    <span class="text-zinc-500 dark:text-zinc-400 flex items-center gap-1">${icon('cpu', 'w-3 h-3')} CPU 算力占用</span>
                    <span class="font-mono font-semibold text-zinc-800 dark:text-zinc-200">${cpu}%</span>
                  </div>
                  <div class="w-full bg-zinc-100 dark:bg-zinc-800 rounded-full h-1.5 overflow-hidden">
                    <div class="bg-amber-500 h-1.5 rounded-full transition-all duration-500" style="width: ${Math.min(cpu, 100)}%"></div>
                  </div>
                </div>

                <div>
                  <div class="flex justify-between text-[11px] mb-1">
                    <span class="text-zinc-500 dark:text-zinc-400 flex items-center gap-1">${icon('layers', 'w-3 h-3')} 内存负载 (${mem_pct}%)</span>
                    <span class="font-mono text-[10px] text-zinc-700 dark:text-zinc-300">${mem_used_gb}G / ${mem_total_gb}G</span>
                  </div>
                  <div class="w-full bg-zinc-100 dark:bg-zinc-800 rounded-full h-1.5 overflow-hidden">
                    <div class="bg-amber-500 h-1.5 rounded-full transition-all duration-500" style="width: ${Math.min(mem_pct, 100)}%"></div>
                  </div>
                </div>

                <div>
                  <div class="flex justify-between text-[11px] mb-1">
                    <span class="text-zinc-500 dark:text-zinc-400 flex items-center gap-1">${icon('harddrive', 'w-3 h-3')} 宿主固态 (${disk_pct}%)</span>
                    <span class="font-mono text-[10px] text-zinc-700 dark:text-zinc-300">${disk_used}G / ${disk_total}G</span>
                  </div>
                  <div class="w-full bg-zinc-100 dark:bg-zinc-800 rounded-full h-1.5 overflow-hidden">
                    <div class="bg-amber-500 h-1.5 rounded-full transition-all duration-500" style="width: ${Math.min(disk_pct, 100)}%"></div>
                  </div>
                </div>
              </div>
            </div>
          `;
        }).join('');
      }

      // 2. Summary Cards (Cloudflare / Linear Style - 4 Rich Cards)
      const sum = data.summary;
      const isAutoHealthy = sum.auto_healthy;
      document.getElementById('summary-cards').innerHTML = `
        <div class="hover-lift fade-up p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-900/60 text-xs shadow-xs relative overflow-hidden">
          <div class="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-emerald-400/80 via-emerald-500/30 to-transparent"></div>
          <div class="flex items-center justify-between">
            <span class="text-zinc-500 dark:text-zinc-400">Swarm 管理仲裁</span>
            <span class="w-6 h-6 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-500">${icon('shield', 'w-3.5 h-3.5')}</span>
          </div>
          <p class="text-base font-bold text-emerald-600 dark:text-emerald-400 mt-1">${sum.nodes_online}</p>
          <span class="text-[10px] text-zinc-400 dark:text-zinc-500 font-mono">${sum.quorum_status}</span>
        </div>
        <div class="hover-lift fade-up p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-900/60 text-xs shadow-xs relative overflow-hidden" style="animation-delay:.06s">
          <div class="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-indigo-400/80 via-indigo-500/30 to-transparent"></div>
          <div class="flex items-center justify-between">
            <span class="text-zinc-500 dark:text-zinc-400">活跃微服务</span>
            <span class="w-6 h-6 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-500">${icon('server', 'w-3.5 h-3.5')}</span>
          </div>
          <p class="text-base font-bold text-zinc-900 dark:text-white mt-1">${sum.services_count} 个微服务</p>
          <span class="text-[10px] text-zinc-400 dark:text-zinc-500 font-mono">${sum.stacks_count} 个 Swarm 业务栈</span>
        </div>
        <div class="hover-lift fade-up p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-900/60 text-xs shadow-xs relative overflow-hidden" style="animation-delay:.12s">
          <div class="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-amber-400/80 via-amber-500/30 to-transparent"></div>
          <div class="flex items-center justify-between">
            <span class="text-zinc-500 dark:text-zinc-400">自动化与容灾中枢</span>
            <span class="flex items-center gap-1.5">
              <span class="w-6 h-6 rounded-lg bg-zinc-500/10 border border-zinc-500/20 flex items-center justify-center text-zinc-500">${icon('zap', 'w-3.5 h-3.5')}</span>
              <span class="w-1.5 h-1.5 rounded-full ${isAutoHealthy ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}"></span>
            </span>
          </div>
          <p class="text-base font-bold ${isAutoHealthy ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'} mt-1">${isAutoHealthy ? '全链路健康' : '需注意'}</p>
          <span class="text-[10px] text-zinc-400 dark:text-zinc-500">6/6 备份鲜活 · 巡检全绿 · AI管家</span>
        </div>
        <div class="hover-lift fade-up p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-900/60 text-xs shadow-xs relative overflow-hidden" style="animation-delay:.18s">
          <div class="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-sky-400/80 via-sky-500/30 to-transparent"></div>
          <div class="flex items-center justify-between">
            <span class="text-zinc-500 dark:text-zinc-400">公网服务路由</span>
            <span class="w-6 h-6 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-500">${icon('globe', 'w-3.5 h-3.5')}</span>
          </div>
          <p class="text-base font-bold text-blue-600 dark:text-blue-400 mt-1">${sum.routes_count} 个域名映射</p>
          <span class="text-[10px] text-zinc-400 dark:text-zinc-500 font-mono">${sum.ssl_validity}</span>
        </div>
      `;

      // Header auto badge update
      const navBadge = document.getElementById('nav-auto-badge');
      if (navBadge) {
        navBadge.className = isAutoHealthy
          ? 'hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
          : 'hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20';
        navBadge.innerHTML = `<span class="w-1.5 h-1.5 rounded-full ${isAutoHealthy ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}"></span>${isAutoHealthy ? '自愈闭环在线' : '自动化存在异常'}`;
      }

      // Sync view buttons styling with stored state
      const accBtn = document.getElementById('view-accordion-btn');
      const flatBtn = document.getElementById('view-flat-btn');
      const accControls = document.getElementById('accordion-controls');
      if (accBtn && flatBtn) {
        if (routeView === 'accordion') {
          accBtn.className = "px-2.5 py-1 rounded-lg font-medium text-white bg-indigo-600 transition shadow-xs";
          flatBtn.className = "px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition";
          if (accControls) accControls.classList.remove('hidden');
        } else {
          flatBtn.className = "px-2.5 py-1 rounded-lg font-medium text-white bg-indigo-600 transition shadow-xs";
          accBtn.className = "px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition";
          if (accControls) accControls.classList.add('hidden');
        }
      }
      const matrixBtn = document.getElementById('view-matrix-btn');
      const cardsBtn = document.getElementById('view-cards-btn');
      if (matrixBtn && cardsBtn) {
        if (daemonView === 'matrix') {
          matrixBtn.className = "px-2.5 py-1 rounded-lg font-medium text-white bg-indigo-600 transition shadow-xs";
          cardsBtn.className = "px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition";
        } else {
          cardsBtn.className = "px-2.5 py-1 rounded-lg font-medium text-white bg-indigo-600 transition shadow-xs";
          matrixBtn.className = "px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition";
        }
      }

      renderRoutes();
      renderStandalone();
      renderAutomation(currentData.automation);
      loadAudit();
      loadApprovals();
    }

    // View Mode Switchers
    window.setRouteView = function(mode) {
      routeView = mode;
      localStorage.setItem('ops_route_view', mode);
      const accBtn = document.getElementById('view-accordion-btn');
      const flatBtn = document.getElementById('view-flat-btn');
      const accControls = document.getElementById('accordion-controls');
      if (accBtn && flatBtn) {
        if (mode === 'accordion') {
          accBtn.className = "px-2.5 py-1 rounded-lg font-medium text-white bg-indigo-600 transition shadow-xs";
          flatBtn.className = "px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition";
          if (accControls) accControls.classList.remove('hidden');
        } else {
          flatBtn.className = "px-2.5 py-1 rounded-lg font-medium text-white bg-indigo-600 transition shadow-xs";
          accBtn.className = "px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition";
          if (accControls) accControls.classList.add('hidden');
        }
      }
      renderRoutes();
    };

    window.setDaemonView = function(mode) {
      daemonView = mode;
      localStorage.setItem('ops_daemon_view', mode);
      const matrixBtn = document.getElementById('view-matrix-btn');
      const cardsBtn = document.getElementById('view-cards-btn');
      if (matrixBtn && cardsBtn) {
        if (mode === 'matrix') {
          matrixBtn.className = "px-2.5 py-1 rounded-lg font-medium text-white bg-indigo-600 transition shadow-xs";
          cardsBtn.className = "px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition";
        } else {
          cardsBtn.className = "px-2.5 py-1 rounded-lg font-medium text-white bg-indigo-600 transition shadow-xs";
          matrixBtn.className = "px-2.5 py-1 rounded-lg font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition";
        }
      }
      renderStandalone();
    };

    // Stacks & Routes Renderer (Fixed-layout Accordion & Unified Flat Table)
    function renderRoutes() {
      if (!currentData) return;
      const search = document.getElementById('search-input').value.toLowerCase();
      const wrapper = document.getElementById('routes-wrapper');

      const filtered = currentData.routes.filter(r => {
        const matchesFilter = (activeFilter === 'all') || (r.node === activeFilter);
        const matchesSearch = !search || 
          r.domain.toLowerCase().includes(search) || 
          r.stack.toLowerCase().includes(search) || 
          r.service.toLowerCase().includes(search) ||
          r.node_name.toLowerCase().includes(search) ||
          (r.ip_port && r.ip_port.toLowerCase().includes(search));
        return matchesFilter && matchesSearch;
      });

      if (filtered.length === 0) {
        wrapper.innerHTML = `<div class="text-center py-12 text-zinc-400 dark:text-zinc-500 text-xs">未找到匹配的堆栈或域名记录</div>`;
        return;
      }

      if (routeView === 'flat') {
        // UNIFIED FLAT ALL-IN-ONE TABLE
        wrapper.innerHTML = `
          <div class="overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/60 shadow-xs">
            <table class="w-full text-left border-collapse text-xs table-fixed min-w-[820px]">
              <colgroup>
                <col class="w-[30%] min-w-[220px]">
                <col class="w-[22%] min-w-[170px]">
                <col class="w-[18%] min-w-[140px]">
                <col class="w-[15%] min-w-[120px]">
                <col class="w-[15%] min-w-[130px]">
              </colgroup>
              <thead>
                <tr class="bg-zinc-100/90 dark:bg-zinc-950/80 text-zinc-500 dark:text-zinc-400 border-b border-zinc-200 dark:border-zinc-800 text-[11px]">
                  <th class="py-3 px-4 font-semibold">公网访问域名 (点击直达 ↗)</th>
                  <th class="py-3 px-4 font-semibold">所属堆栈与微服务</th>
                  <th class="py-3 px-4 font-semibold">容器内部 IP:端口</th>
                  <th class="py-3 px-4 font-semibold">物理部署节点</th>
                  <th class="py-3 px-4 text-center font-semibold">网关响应与延时</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-zinc-100 dark:divide-zinc-800/60">
                ${filtered.map(r => `
                  <tr class="hover:bg-zinc-50/80 dark:hover:bg-zinc-850/40 transition">
                    <td class="py-2.5 px-4 min-w-0">
                      <div class="flex items-center space-x-1.5 min-w-0">
                        <a href="${r.url}" target="_blank" title="${r.domain} (点击直达)" class="text-indigo-600 dark:text-indigo-400 hover:underline font-semibold flex items-center space-x-1 truncate min-w-0">
                          <span class="truncate">${r.domain}</span>
                          <span class="opacity-60 flex-shrink-0">${icon('external', 'w-3 h-3')}</span>
                        </a>
                        <button onclick="copyText('${r.url}', '域名')" title="复制域名链接" class="flex-shrink-0 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition text-[10px] p-0.5 rounded hover:bg-zinc-200 dark:hover:bg-zinc-800">
                          ${icon('copy', 'w-3 h-3')}
                        </button>
                      </div>
                    </td>
                    <td class="py-2.5 px-4 min-w-0">
                      <div class="flex items-center space-x-1.5 min-w-0">
                        <span class="px-1.5 py-0.2 rounded-sm text-[10px] font-mono bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700/80 flex-shrink-0">${r.stack}</span>
                        <span class="truncate text-zinc-700 dark:text-zinc-300 font-mono text-[11px]" title="${r.service}">${r.service}</span>
                      </div>
                    </td>
                    <td class="py-2.5 px-4 min-w-0 font-mono">
                      <div class="flex items-center space-x-1 min-w-0">
                        <span class="truncate text-indigo-600 dark:text-indigo-400 text-[11px] cursor-pointer hover:underline" onclick="copyText('${r.ip_port}', '内部IP')" title="${r.ip_port || '-'} (点击复制)">
                          ${r.ip_port || '-'}
                        </span>
                      </div>
                    </td>
                    <td class="py-2.5 px-4 min-w-0">
                      <span class="px-2 py-0.5 rounded-full text-[10px] font-medium ${
                        r.node === 'jp-oracle' ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20' :
                        r.node === 'us-oracle' ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20' :
                        r.node === 'us-racknerd' ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20' :
                        'bg-zinc-500/10 text-zinc-600 dark:text-zinc-400'
                      } truncate inline-block max-w-full">${r.node_name}</span>
                    </td>
                    <td class="py-2.5 px-4 text-center whitespace-nowrap min-w-0">
                      ${renderProbeBadge(r.probe_code, r.probe_ms)}
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        `;
        return;
      }

      // GROUP BY STACK (ACCORDION VIEW WITH STRICT UNIFORM FIXED COLUMNS)
      const stackGroups = {};
      filtered.forEach(r => {
        if (!stackGroups[r.stack]) {
          stackGroups[r.stack] = {
            stack: r.stack,
            node_name: r.node_name,
            node: r.node,
            color: r.color,
            arch: r.arch,
            routes: []
          };
        }
        stackGroups[r.stack].routes.push(r);
      });

      wrapper.innerHTML = `
        <div id="stacks-accordion" class="space-y-3">
          ${Object.values(stackGroups).map(g => {
            const isExpanded = expandedStacks.has(g.stack);
            return `
              <div class="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/70 dark:bg-zinc-950/60 overflow-hidden transition shadow-xs">
                <!-- STACK HEADER -->
                <div onclick="toggleStack('${g.stack}')" class="p-3.5 px-4 cursor-pointer flex items-center justify-between hover:bg-zinc-100/80 dark:hover:bg-zinc-900/60 transition select-none">
                  <div class="flex items-center space-x-3">
                    <span class="text-zinc-400 dark:text-zinc-500 transform transition-transform duration-200 ${isExpanded ? 'rotate-90' : 'rotate-0'} inline-block">
                      ${icon('chevronRight', 'w-3.5 h-3.5')}
                    </span>
                    <div class="flex items-center space-x-2">
                      <span class="font-mono font-bold text-sm text-zinc-900 dark:text-white">${g.stack}</span>
                      <span class="px-2 py-0.5 rounded-full text-[10px] font-medium ${
                        g.node === 'jp-oracle' ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20' :
                        g.node === 'us-oracle' ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20' :
                        g.node === 'us-racknerd' ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20' :
                        'bg-zinc-500/10 text-zinc-600 dark:text-zinc-400'
                      }">${g.node_name}</span>
                    </div>
                  </div>

                  <div class="flex items-center space-x-2">
                    <span class="px-2 py-0.5 rounded-md bg-zinc-200/80 dark:bg-zinc-800 text-[11px] font-mono text-zinc-700 dark:text-zinc-300">
                      ${g.routes.length} 个域名
                    </span>
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                  </div>
                </div>

                <!-- STACK BODY WITH STRICT FIXED TABLE COLUMNS -->
                <div class="${isExpanded ? 'block' : 'hidden'} border-t border-zinc-200 dark:border-zinc-800/80 overflow-x-auto bg-white dark:bg-zinc-900/90">
                  <table class="w-full text-left border-collapse text-xs table-fixed min-w-[760px]">
                    <colgroup>
                      <col class="w-[30%] min-w-[210px]">
                      <col class="w-[22%] min-w-[170px]">
                      <col class="w-[18%] min-w-[140px]">
                      <col class="w-[15%] min-w-[120px]">
                      <col class="w-[15%] min-w-[120px]">
                    </colgroup>
                    <thead>
                      <tr class="bg-zinc-100/90 dark:bg-zinc-950/80 text-zinc-500 dark:text-zinc-400 border-b border-zinc-200 dark:border-zinc-800 text-[11px]">
                        <th class="py-2.5 px-4 font-semibold">公网访问域名 (点击直达 ↗)</th>
                        <th class="py-2.5 px-4 font-semibold">微服务名</th>
                        <th class="py-2.5 px-4 font-semibold">内部网络与端口</th>
                        <th class="py-2.5 px-4 font-semibold">SSL 加密证书</th>
                        <th class="py-2.5 px-4 text-center font-semibold">网关响应与延时</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-zinc-100 dark:divide-zinc-800/60">
                      ${g.routes.map(r => `
                        <tr class="hover:bg-zinc-50/80 dark:hover:bg-zinc-800/40 transition">
                          <td class="py-2.5 px-4 min-w-0">
                            <div class="flex items-center space-x-1.5 min-w-0">
                              <a href="${r.url}" target="_blank" title="${r.domain} (点击直达)" class="text-indigo-600 dark:text-indigo-400 hover:underline font-semibold flex items-center space-x-1 truncate min-w-0">
                                <span class="truncate">${r.domain}</span>
                                <span class="opacity-60 flex-shrink-0">${icon('external', 'w-3 h-3')}</span>
                              </a>
                              <button onclick="copyText('${r.url}', '域名')" title="复制域名链接" class="flex-shrink-0 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition text-[10px] p-0.5 rounded hover:bg-zinc-200 dark:hover:bg-zinc-800">
                                ${icon('copy', 'w-3 h-3')}
                              </button>
                            </div>
                          </td>
                          <td class="py-2.5 px-4 min-w-0">
                            <div class="truncate text-zinc-700 dark:text-zinc-300 font-mono text-[11px]" title="${r.service}">
                              ${r.service}
                            </div>
                          </td>
                          <td class="py-2.5 px-4 min-w-0 font-mono">
                            <div class="flex items-center space-x-1 min-w-0">
                              <span class="truncate text-indigo-600 dark:text-indigo-400 text-[11px] cursor-pointer hover:underline" onclick="copyText('${r.ip_port}', '内部IP')" title="${r.ip_port || '-'} (点击复制)">
                                ${r.ip_port || '-'}
                              </span>
                            </div>
                          </td>
                          <td class="py-2.5 px-4 min-w-0">
                            <div class="truncate text-zinc-500 dark:text-zinc-400 text-[11px] font-sans flex items-center gap-1.5" title="${r.tls}">
                              <span class="flex-shrink-0 text-zinc-400">${icon('lock', 'w-3 h-3')}</span>
                              <span class="truncate">${r.tls}</span>
                            </div>
                          </td>
                          <td class="py-2.5 px-4 text-center whitespace-nowrap min-w-0">
                            ${renderProbeBadge(r.probe_code, r.probe_ms)}
                          </td>
                        </tr>
                      `).join('')}
                    </tbody>
                  </table>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      `;
    }

    const STANDARD_SLOTS = [
      { key: 'beszel', name: '系统硬件性能探针', subtitle: 'Beszel Telemetry Agent', icon: 'chart', tag: '探针' },
      { key: 'singbox', name: '核心出海网格网络', subtitle: 'Sing-box Mesh Network', icon: 'radio', tag: '网络' },
      { key: 'watchtower', name: '镜像自动巡检守护', subtitle: 'Hourly Auto Updater', icon: 'refresh', tag: '巡检' },
      { key: 'portainer', name: '集群管控运行基座', subtitle: 'Portainer CE / Agent', icon: 'box', tag: '管控' },
      { key: 'dedicated', name: '节点专属特化设施', subtitle: 'Node Dedicated Infras', icon: 'shield', tag: '专属' }
    ];

    function findSlotContainer(nodeList, slotKey) {
      if (!nodeList || !nodeList.length) return null;
      if (slotKey === 'beszel') return nodeList.find(c => c.name.includes('beszel')) || null;
      if (slotKey === 'singbox') return nodeList.find(c => c.name.includes('sing-box')) || null;
      if (slotKey === 'watchtower') return nodeList.find(c => c.name.includes('watchtower')) || null;
      if (slotKey === 'portainer') return nodeList.find(c => c.name === 'portainer_agent' || c.name === 'portainer') || null;
      if (slotKey === 'dedicated') return nodeList.find(c => c.slot_key === 'dedicated' || c.name.includes('warp') || c.name.includes('mcp') || c.name.includes('gateway')) || null;
      return null;
    }

    // Standalone Daemons Renderer (Cross-Node Matrix & Aligned Cards)
    function renderStandalone() {
      if (!currentData || !currentData.standalones) return;
      const wrapper = document.getElementById('standalone-wrapper');
      const st = currentData.standalones;

      // Render Host Systemd Daemons Bar
      const sysBox = document.getElementById('host-systemd-badges');
      const daemons = (currentData && currentData.automation && currentData.automation.systemd_daemons) || {};
      if (sysBox) {
        const nodesDef = [
          { key: 'jp-oracle', label: '🇯🇵 日本', color: 'emerald' },
          { key: 'us-oracle', label: '🇺🇸 美国', color: 'blue' },
          { key: 'us-racknerd', label: '🟣 圣何塞', color: 'purple' }
        ];
        sysBox.innerHTML = nodesDef.map(n => {
          const list = daemons[n.key] || [];
          return `
            <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-zinc-100 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-[10px]">
              <span class="font-bold text-${n.color}-600 dark:text-${n.color}-400 mr-0.5">${n.label}:</span>
              ${list.length > 0 ? list.map(d => `
                <span class="inline-flex items-center gap-1 text-zinc-700 dark:text-zinc-300">
                  <span class="w-1.5 h-1.5 rounded-full ${d.active ? 'bg-emerald-500' : 'bg-rose-500'}"></span>
                  <span>${d.label}</span>
                </span>
              `).join('<span class="text-zinc-300 dark:text-zinc-700 mx-0.5">·</span>') : '<span class="text-zinc-400">无额外服务</span>'}
            </div>
          `;
        }).join('');
      }

      if (daemonView === 'matrix') {
        // CROSS-NODE COMPARISON MATRIX TABLE
        wrapper.innerHTML = `
          <div class="overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/60 shadow-xs">
            <table class="w-full text-left border-collapse text-xs table-fixed min-w-[780px]">
              <colgroup>
                <col class="w-[22%] min-w-[170px]">
                <col class="w-[26%] min-w-[200px]">
                <col class="w-[26%] min-w-[200px]">
                <col class="w-[26%] min-w-[200px]">
              </colgroup>
              <thead>
                <tr class="bg-zinc-100/90 dark:bg-zinc-950/80 text-zinc-500 dark:text-zinc-400 border-b border-zinc-200 dark:border-zinc-800 text-[11px]">
                  <th class="py-3 px-4 font-semibold">守护服务职责与角色</th>
                  <th class="py-3 px-4 font-semibold text-emerald-600 dark:text-emerald-400">🇯🇵 日本主控 (jp-oracle)</th>
                  <th class="py-3 px-4 font-semibold text-blue-600 dark:text-blue-400">🇺🇸 美国算力 (us-oracle)</th>
                  <th class="py-3 px-4 font-semibold text-purple-600 dark:text-purple-400">🟣 圣何塞哨兵 (us-racknerd)</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-zinc-100 dark:divide-zinc-800/60">
                ${STANDARD_SLOTS.map(slot => {
                  const c_jp = findSlotContainer(st['jp-oracle'], slot.key);
                  const c_us = findSlotContainer(st['us-oracle'], slot.key);
                  const c_rn = findSlotContainer(st['us-racknerd'], slot.key);

                  const renderCell = (c, nodeKey) => {
                    if (!c) {
                      if (slot.key === 'portainer' && nodeKey === 'jp-oracle') {
                        return `
                          <div class="p-2.5 rounded-lg bg-emerald-50/70 dark:bg-emerald-950/40 border border-emerald-300/80 dark:border-emerald-800/80 flex items-center justify-between min-w-0">
                            <div class="truncate mr-2 min-w-0">
                              <div class="flex items-center space-x-1.5 min-w-0">
                                <span class="font-mono font-bold text-xs text-zinc-900 dark:text-white truncate">portainer</span>
                                <span class="px-1.5 py-0.2 rounded-sm text-[9px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 flex-shrink-0">Swarm 主控</span>
                              </div>
                              <div class="text-[10px] text-zinc-400 font-mono truncate mt-0.5" title="portainer/portainer-ce:latest">portainer/portainer-ce:latest</div>
                            </div>
                            <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 whitespace-nowrap flex-shrink-0">
                              <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1 animate-pulse"></span>
                              Swarm 原生
                            </span>
                          </div>
                        `;
                      }
                      return `
                        <div class="p-2.5 rounded-lg bg-zinc-50/50 dark:bg-zinc-950/40 border border-dashed border-zinc-200 dark:border-zinc-800 text-center">
                          <span class="text-[11px] text-zinc-400 font-medium">✨ 纯净宿主 (业务全纳管)</span>
                        </div>
                      `;
                    }
                    return `
                      <div class="p-2.5 rounded-lg bg-zinc-50/70 dark:bg-zinc-950/60 border border-zinc-200/80 dark:border-zinc-800/80 flex items-center justify-between min-w-0">
                        <div class="truncate mr-2 min-w-0">
                          <div class="flex items-center space-x-1.5 min-w-0">
                            <span class="font-mono font-bold text-xs text-zinc-900 dark:text-white truncate">${c.name}</span>
                            <span class="px-1.5 py-0.2 rounded-sm text-[9px] bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20 flex-shrink-0">${c.tag}</span>
                          </div>
                          <div class="text-[10px] text-zinc-400 font-mono truncate mt-0.5" title="${c.image}">${c.image}</div>
                        </div>
                        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 whitespace-nowrap flex-shrink-0">
                          <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1 animate-pulse"></span>
                          运行中
                        </span>
                      </div>
                    `;
                  };

                  return `
                    <tr class="hover:bg-zinc-50/50 dark:hover:bg-zinc-850/40 transition">
                      <td class="py-3 px-4 min-w-0">
                        <div class="flex items-start space-x-2.5">
                          <span class="text-zinc-500 dark:text-zinc-400 flex-shrink-0 mt-0.5">${icon(slot.icon, 'w-4 h-4')}</span>
                          <div class="min-w-0">
                            <div class="font-bold text-zinc-900 dark:text-white text-xs truncate">${slot.name}</div>
                            <div class="text-[10px] text-zinc-400 truncate">${slot.subtitle}</div>
                          </div>
                        </div>
                      </td>
                      <td class="py-3 px-4 min-w-0">${renderCell(c_jp, 'jp-oracle')}</td>
                      <td class="py-3 px-4 min-w-0">${renderCell(c_us, 'us-oracle')}</td>
                      <td class="py-3 px-4 min-w-0">${renderCell(c_rn, 'us-racknerd')}</td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>
        `;
        return;
      }

      // ALIGNED 3-COLUMN CARDS VIEW
      const nodesDef = [
        { key: 'jp-oracle', name: '🇯🇵 日本主控 (jp-oracle)', color: 'emerald' },
        { key: 'us-oracle', name: '🇺🇸 美国算力 (us-oracle)', color: 'blue' },
        { key: 'us-racknerd', name: '🟣 圣何塞哨兵 (us-racknerd)', color: 'purple' }
      ];

      wrapper.innerHTML = `
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          ${nodesDef.map(n => {
            const list = st[n.key] || [];
            return `
              <div class="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/70 dark:bg-zinc-950/60 p-4 space-y-3 shadow-xs">
                <div class="flex items-center justify-between pb-2 border-b border-zinc-200 dark:border-zinc-800">
                  <span class="font-bold text-xs text-zinc-900 dark:text-white">${n.name}</span>
                  <span class="text-[10px] px-2 py-0.5 rounded-full bg-zinc-200 dark:bg-zinc-800 font-mono">${list.length} 个守护</span>
                </div>
                <div class="space-y-2">
                  ${STANDARD_SLOTS.map(slot => {
                    const c = findSlotContainer(list, slot.key);
                    if (!c) {
                      if (slot.key === 'portainer' && n.key === 'jp-oracle') {
                        return `
                          <div class="h-14 p-2.5 rounded-lg bg-emerald-50/70 dark:bg-emerald-950/40 border border-emerald-300/80 dark:border-emerald-800/80 flex items-center justify-between text-xs min-w-0">
                            <div class="truncate mr-2 min-w-0">
                              <div class="flex items-center space-x-1.5 min-w-0">
                                <span class="text-zinc-500 flex-shrink-0">${icon('box', 'w-3.5 h-3.5')}</span>
                                <span class="font-mono font-semibold text-zinc-900 dark:text-white text-xs truncate">portainer</span>
                                <span class="px-1.5 py-0.2 rounded-sm text-[9px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 flex-shrink-0">Swarm 主控</span>
                              </div>
                              <p class="text-[10px] text-zinc-400 font-mono truncate mt-0.5" title="portainer/portainer-ce:latest">portainer/portainer-ce:latest</p>
                            </div>
                            <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 whitespace-nowrap flex-shrink-0">
                              <span class="w-1 h-1 rounded-full bg-emerald-500 mr-1 animate-pulse"></span>
                              Swarm 原生
                            </span>
                          </div>
                        `;
                      }
                      return `
                        <div class="h-14 p-2.5 rounded-lg bg-zinc-100/50 dark:bg-zinc-900/40 border border-dashed border-zinc-200 dark:border-zinc-800 flex items-center justify-center text-center">
                          <span class="text-[11px] text-zinc-400 font-medium">✨ 纯净宿主 (业务全纳管)</span>
                        </div>
                      `;
                    }
                    return `
                      <div class="h-14 p-2.5 rounded-lg bg-white dark:bg-zinc-900/80 border border-zinc-200 dark:border-zinc-800/80 flex items-center justify-between text-xs min-w-0">
                        <div class="truncate mr-2 min-w-0">
                          <div class="flex items-center space-x-1.5 min-w-0">
                            <span class="text-zinc-500 flex-shrink-0">${icon(slot.icon, 'w-3.5 h-3.5')}</span>
                            <span class="font-mono font-semibold text-zinc-900 dark:text-white text-xs truncate">${c.name}</span>
                            <span class="px-1.5 py-0.2 rounded-sm text-[9px] bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20 flex-shrink-0">${c.tag}</span>
                          </div>
                          <p class="text-[10px] text-zinc-400 font-mono truncate mt-0.5" title="${c.image}">${c.image}</p>
                        </div>
                        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 whitespace-nowrap flex-shrink-0">
                          <span class="w-1 h-1 rounded-full bg-emerald-500 mr-1 animate-pulse"></span>
                          运行中
                        </span>
                      </div>
                    `;
                  }).join('')}
                </div>
              </div>
            `;
          }).join('')}
        </div>
      `;
    }

    window.toggleStandaloneAccordion = function() {
      const c = document.getElementById('standalone-wrapper');
      const arrow = document.getElementById('standalone-toggle-arrow');
      const text = document.getElementById('standalone-toggle-text');
      standaloneExpanded = !standaloneExpanded;
      if (standaloneExpanded) {
        c.classList.remove('hidden');
        if (arrow) arrow.textContent = '▼';
        if (text) text.textContent = '折叠';
      } else {
        c.classList.add('hidden');
        if (arrow) arrow.textContent = '▶';
        if (text) text.textContent = '展开';
      }
    };

    // Toggle individual stack
    window.toggleStack = function(stackName) {
      if (expandedStacks.has(stackName)) {
        expandedStacks.delete(stackName);
      } else {
        expandedStacks.add(stackName);
      }
      renderRoutes();
    };

    // Expand All
    document.getElementById('expand-all-btn').addEventListener('click', () => {
      if (currentData) {
        currentData.routes.forEach(r => expandedStacks.add(r.stack));
        renderRoutes();
      }
    });

    // Collapse All
    document.getElementById('collapse-all-btn').addEventListener('click', () => {
      expandedStacks.clear();
      renderRoutes();
    });

    // Search input
    document.getElementById('search-input').addEventListener('input', renderRoutes);

    // Node filter tabs
    document.querySelectorAll('.filter-tab').forEach(tab => {
      tab.addEventListener('click', (e) => {
        document.querySelectorAll('.filter-tab').forEach(t => {
          t.classList.remove('bg-indigo-600', 'text-white', 'shadow-xs');
          t.classList.add('text-zinc-600', 'dark:text-zinc-400');
        });
        e.target.classList.add('bg-indigo-600', 'text-white', 'shadow-xs');
        e.target.classList.remove('text-zinc-600', 'dark:text-zinc-400');
        activeFilter = e.target.getAttribute('data-filter');
        renderRoutes();
      });
    });

    // Initialize
    initTheme();
    checkAuth();

    // ── Automation Section Renderer (2026-09-23) ──
    function renderAutomation(auto) {
      if (!auto || !auto.backups) return;
      // Overall badge
      const bakOk = auto.backups.length > 0 && auto.backups.every(b => b.ok);
      const guardOk = auto.guard && auto.guard.ok;
      const agentOk = auto.agent && auto.agent.active;
      const allOk = bakOk && guardOk && agentOk;
      const badge = document.getElementById('auto-overall-badge');
      if (badge) {
        badge.textContent = allOk ? '● 全链路正常' : '● 存在异常';
        badge.className = allOk
          ? 'px-2.5 py-1 rounded-lg text-[11px] font-mono font-bold border bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30'
          : 'px-2.5 py-1 rounded-lg text-[11px] font-mono font-bold border bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/30';
      }

      // 1. Backups
      const bk = document.getElementById('auto-backups');
      if (bk) {
        bk.innerHTML = auto.backups.map(b => `
          <div class="flex items-center justify-between gap-2 p-1 rounded-lg hover:bg-zinc-100/50 dark:hover:bg-zinc-900/50 transition">
            <div class="flex items-center gap-1.5 min-w-0 truncate">
              <span class="${b.ok ? 'text-emerald-500' : 'text-rose-500'} font-bold flex-shrink-0">${b.ok ? '✓' : '✗'}</span>
              <span class="text-zinc-700 dark:text-zinc-300 font-medium truncate" title="${b.host}">${b.host}</span>
            </div>
            <div class="flex items-center gap-2 flex-shrink-0 text-right font-mono text-[11px]">
              <span class="${b.ok ? 'text-zinc-600 dark:text-zinc-400' : 'text-rose-500'}">${b.age_h === null ? '无档案' : b.age_h + 'h 前'}</span>
              <span class="text-zinc-400 dark:text-zinc-500 min-w-[48px]">${b.size_mb !== null ? b.size_mb + 'MB' : '-'}</span>
            </div>
          </div>`).join('');
      }

      // 2. Guard / Drill / Prune / Snapshot
      const gd = document.getElementById('auto-guard');
      const g = auto.guard || {};
      const d = auto.drill || {};
      if (gd) {
        gd.innerHTML = `
          <div class="flex items-center justify-between p-1">
            <span class="text-zinc-700 dark:text-zinc-300 font-medium">cluster-guard 6h 巡检</span>
            <span class="${g.ok ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'} font-semibold font-mono text-[11px]">${g.ok ? '● 全绿通过' : (g.issues > 0 ? '● ' + g.issues + ' 异常' : '● 待检')}</span>
          </div>
          <div class="flex items-center justify-between text-[11px] px-1 text-zinc-500">
            <span>上次巡检时间戳</span>
            <span class="font-mono text-zinc-700 dark:text-zinc-300">${g.last_run || '-'}</span>
          </div>
          <div class="flex items-center justify-between p-1 pt-1.5 border-t border-zinc-200/60 dark:border-zinc-800/60">
            <span class="text-zinc-700 dark:text-zinc-300 font-medium">月度自动恢复演练</span>
            <span class="${d.ok ? 'text-emerald-600 dark:text-emerald-400' : 'text-zinc-400'} font-semibold font-mono text-[11px]">${d.ok ? '● 校验通过' : '● 待执行'}</span>
          </div>
          <div class="flex items-center justify-between text-[11px] px-1 text-zinc-500">
            <span>最新演练存证</span>
            <span class="font-mono text-zinc-700 dark:text-zinc-300 text-[10px] truncate max-w-[140px]" title="${d.last}">${d.last || '-'}</span>
          </div>
          <div class="flex items-center justify-between text-[11px] px-1 pt-1.5 border-t border-zinc-200/60 dark:border-zinc-800/60 text-zinc-500">
            <span>周度安全清理 (Prune)</span>
            <span class="font-mono text-zinc-600 dark:text-zinc-400">周日 05:00 · until=168h</span>
          </div>
          <div class="flex items-center justify-between text-[11px] px-1 text-zinc-500">
            <span>每周机器实测快照</span>
            <span class="font-mono text-zinc-600 dark:text-zinc-400">周一 06:00 · SNAPSHOT.md</span>
          </div>
        `;
      }

      // 3. OpenClaw Dedicated Co-Pilot Card
      const ac = document.getElementById('auto-agent-card');
      const a = auto.agent || {};
      const agentBadge = document.getElementById('agent-active-badge');
      if (agentBadge) {
        agentBadge.textContent = a.active ? '● 在线运行中' : '● 离线停止';
        agentBadge.className = a.active
          ? 'px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
          : 'px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20';
      }
      if (ac) {
        ac.innerHTML = `
          <div class="flex items-center justify-between text-[11px] px-1">
            <span class="text-zinc-500">运行形态</span>
            <span class="font-mono text-zinc-700 dark:text-zinc-300">${a.mode || 'Systemd'} · ${a.version || 'v2026.9.5'}</span>
          </div>
          <div class="flex items-center justify-between text-[11px] px-1">
            <span class="text-zinc-500">通讯渠道</span>
            <span class="font-mono text-zinc-700 dark:text-zinc-300 flex items-center gap-1">
              <span class="text-sky-500">💬</span> ${a.tg_bot || '-'}
            </span>
          </div>
          <div class="flex items-center justify-between text-[11px] px-1">
            <span class="text-zinc-500">权限绑定</span>
            <span class="font-mono text-emerald-600 dark:text-emerald-400 font-medium">Owner (${a.owner || 'mcnikicm'})</span>
          </div>
          <div class="flex items-center justify-between text-[11px] px-1">
            <span class="text-zinc-500">模型路由</span>
            <span class="font-mono text-indigo-600 dark:text-indigo-400 font-medium truncate max-w-[140px]" title="${a.model}">${a.model || 'AxonHub'}</span>
          </div>
          <div class="flex items-center justify-between text-[11px] px-1">
            <span class="text-zinc-500">管控工具</span>
            <span class="font-mono text-zinc-700 dark:text-zinc-300">${a.mcp_tools || '119 个只读工具 (Portainer MCP)'}</span>
          </div>
          <div class="flex items-center justify-between text-[11px] px-1 pt-0.5">
            <span class="text-zinc-500">安全基线</span>
            <span class="text-emerald-600 dark:text-emerald-400 font-medium text-[10px] bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">严格只读 · 审批拦截</span>
          </div>
        `;
      }

      // 4. Timers Matrix (Full Width Sub-card)
      const tm = document.getElementById('auto-timers');
      if (tm) {
        tm.innerHTML = (auto.timers || []).map(t => {
          const dot = t.active ? '<span class="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block"></span>' : '<span class="w-1.5 h-1.5 rounded-full bg-zinc-500 inline-block"></span>';
          const hostColor = t.host === 'jp' ? 'text-emerald-500' : (t.host === 'us' ? 'text-blue-500' : 'text-purple-500');
          return `
            <div class="p-2 rounded-lg bg-zinc-50/80 dark:bg-zinc-950/70 border border-zinc-200/80 dark:border-zinc-800/80 flex items-center justify-between min-w-0 shadow-2xs">
              <div class="truncate mr-1 min-w-0">
                <div class="flex items-center gap-1.5">
                  ${dot}
                  <span class="font-semibold text-zinc-800 dark:text-zinc-200 truncate text-[11px]">${t.unit.replace('.timer','')}</span>
                </div>
                <div class="text-[10px] text-zinc-400 font-mono truncate mt-0.5">${t.next || '-'}</div>
              </div>
              <span class="text-[9px] px-1 py-0.2 rounded font-mono ${hostColor} bg-zinc-100 dark:bg-zinc-900 border border-zinc-200/60 dark:border-zinc-800/60 flex-shrink-0">${t.host}</span>
            </div>
          `;
        }).join('');
      }
    }

    // ═══ AUDIT TIMELINE ═══
    let auditFilter = { actor: '', level: '' };

    window.setAuditFilter = function(kind, value) {
      auditFilter[kind] = value;
      document.querySelectorAll('.audit-filter').forEach(btn => {
        const parts = btn.getAttribute('data-af').split(':');
        const k = parts[0], v = parts.slice(1).join(':');
        const active = auditFilter[k] === v;
        btn.className = 'audit-filter px-2.5 py-1 rounded-lg font-medium transition ' +
          (active ? 'text-white bg-indigo-600' : 'text-zinc-600 dark:text-zinc-400');
      });
      loadAudit();
    };

    function escHtml(s) {
      return String(s == null ? '' : s).replace(/[&<>"']/g, c =>
        ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    }

    function fmtTs(ts) {
      try {
        return new Date(ts * 1000).toLocaleString('zh-CN', {hour12: false});
      } catch (e) { return '-'; }
    }

    async function loadAudit() {
      const box = document.getElementById('audit-list');
      if (!box) return;
      try {
        const q = new URLSearchParams({limit: '50'});
        if (auditFilter.actor) q.set('actor', auditFilter.actor);
        if (auditFilter.level) q.set('level', auditFilter.level);
        const res = await fetch('/api/audit?' + q.toString());
        if (res.status === 401) { checkAuth(); return; }
        const data = await res.json();
        renderAudit(data.items || []);
      } catch (e) {
        box.innerHTML = '<div class="text-xs text-zinc-400 py-4 text-center">审计数据加载失败</div>';
      }
    }

    function renderAudit(items) {
      const box = document.getElementById('audit-list');
      if (!box) return;
      if (!items.length) {
        box.innerHTML = '<div class="text-xs text-zinc-400 py-4 text-center">暂无审计记录</div>';
        return;
      }
      const levelColor = l => l === 'L2'
        ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
        : 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300';
      const resultDot = r => r === 'ok'
        ? '<span class="text-emerald-500">●</span>'
        : '<span class="text-red-500">●</span>';
      box.innerHTML = items.map(it => `
        <div class="flex items-start gap-3 px-3 py-2 rounded-xl border border-zinc-200/70 dark:border-zinc-800/70 bg-zinc-50/60 dark:bg-zinc-900/40">
          <div class="mt-0.5 flex-shrink-0">${resultDot(it.result)}</div>
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2 text-xs">
              <span class="font-mono text-zinc-500 dark:text-zinc-400">${escHtml(fmtTs(it.ts))}</span>
              <span class="font-semibold text-zinc-800 dark:text-zinc-200">${escHtml(it.actor)}</span>
              <span class="px-1.5 py-0.5 rounded text-[10px] font-mono ${levelColor(it.level)}">${escHtml(it.level)}</span>
              <span class="font-mono text-zinc-600 dark:text-zinc-300">${escHtml(it.action)}</span>
              ${it.target ? `<span class="text-zinc-500 dark:text-zinc-400 truncate">→ ${escHtml(it.target)}</span>` : ''}
            </div>
            ${it.detail ? `<div class="text-xs text-zinc-500 dark:text-zinc-400 mt-1 truncate">${escHtml(it.detail)}</div>` : ''}
          </div>
          <span class="text-[10px] font-mono px-1.5 py-0.5 rounded ${it.result === 'ok' ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}">${escHtml(it.result)}</span>
        </div>
      `).join('');
    }

    // ═══ APPROVAL QUEUE ═══
    let approvalFilter = 'pending';

    window.setApprovalFilter = function(status) {
      approvalFilter = status;
      document.querySelectorAll('.approval-filter').forEach(btn => {
        const active = btn.getAttribute('data-apf') === status;
        btn.className = 'approval-filter px-2.5 py-1 rounded-lg font-medium transition ' +
          (active ? 'text-white bg-indigo-600' : 'text-zinc-600 dark:text-zinc-400');
      });
      loadApprovals();
    };

    async function loadApprovals() {
      const box = document.getElementById('approval-list');
      if (!box) return;
      try {
        const q = new URLSearchParams({limit: '50'});
        if (approvalFilter) q.set('status', approvalFilter);
        const res = await fetch('/api/approvals?' + q.toString());
        if (res.status === 401) { checkAuth(); return; }
        const data = await res.json();
        renderApprovals(data.items || []);
      } catch (e) {
        box.innerHTML = '<div class="text-xs text-zinc-400 py-4 text-center">审批队列加载失败</div>';
      }
    }

    window.decideApproval = async function(id, decision) {
      const verb = decision === 'approved' ? '批准' : '驳回';
      if (!confirm(verb + ' #' + id + ' 的 L2 操作？此操作不可撤销。')) return;
      try {
        const res = await fetch('/api/approvals/' + id + '/decide', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({decision: decision})
        });
        if (res.status === 401) { checkAuth(); return; }
        const data = await res.json();
        if (!res.ok) { alert('失败：' + (data.error || res.status)); return; }
        loadApprovals();
      } catch (e) {
        alert('请求失败：' + e);
      }
    };

    function renderApprovals(items) {
      const box = document.getElementById('approval-list');
      if (!box) return;
      const badge = document.getElementById('approval-pending-badge');
      const pendingCount = items.filter(i => i.status === 'pending').length;
      if (badge) {
        if (pendingCount > 0) {
          badge.textContent = pendingCount + ' 待处理';
          badge.classList.remove('hidden');
        } else {
          badge.classList.add('hidden');
        }
      }
      if (!items.length) {
        box.innerHTML = '<div class="text-xs text-zinc-400 py-4 text-center">暂无审批单</div>';
        return;
      }
      const statusStyle = s => ({
        pending: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
        approved: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
        rejected: 'bg-zinc-200 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400',
        executed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
        failed: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
      })[s] || '';
      box.innerHTML = items.map(it => `
        <div class="px-3 py-2 rounded-xl border border-zinc-200/70 dark:border-zinc-800/70 bg-zinc-50/60 dark:bg-zinc-900/40">
          <div class="flex flex-wrap items-center gap-2 text-xs">
            <span class="font-mono text-zinc-400">#${it.id}</span>
            <span class="px-1.5 py-0.5 rounded text-[10px] font-mono ${statusStyle(it.status)}">${it.status}</span>
            <span class="font-semibold text-zinc-800 dark:text-zinc-200">${escHtml(it.requester)}</span>
            <span class="font-mono text-zinc-600 dark:text-zinc-300">${escHtml(it.action)}</span>
            <span class="text-zinc-500 dark:text-zinc-400 truncate">→ ${escHtml(it.target)}</span>
            <span class="font-mono text-zinc-500 dark:text-zinc-400">${escHtml(fmtTs(it.ts))}</span>
          </div>
          <div class="text-xs text-zinc-500 dark:text-zinc-400 mt-1">理由：${escHtml(it.reason)}</div>
          ${(it.params && Object.keys(it.params).length) ? `<div class="text-[11px] font-mono text-zinc-400 mt-0.5 truncate">params: ${escHtml(JSON.stringify(it.params))}</div>` : ''}
          ${it.decision_note ? `<div class="text-[11px] text-zinc-500 mt-0.5">决定备注：${escHtml(it.decision_note)}</div>` : ''}
          ${it.execute_detail ? `<div class="text-[11px] text-zinc-500 mt-0.5">执行结果：${escHtml(it.execute_detail)}</div>` : ''}
          ${it.status === 'pending' ? `
          <div class="flex gap-2 mt-2">
            <button onclick="decideApproval(${it.id}, 'approved')" class="px-3 py-1 rounded-lg text-xs font-medium text-white bg-emerald-600 hover:bg-emerald-700 transition">✓ 批准</button>
            <button onclick="decideApproval(${it.id}, 'rejected')" class="px-3 py-1 rounded-lg text-xs font-medium text-white bg-red-600 hover:bg-red-700 transition">✕ 驳回</button>
          </div>` : ''}
        </div>
      `).join('');
    }
  </script>
</body>
</html>
"""

