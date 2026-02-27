import {
  BarChart3,
  Check,
  ChevronLeft,
  ChevronRight,
  GitMerge,
  Loader2,
  RefreshCw,
  Search,
  X,
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import {
  fetchMatchingRuns,
  fetchPendingMatches,
  fetchMatchingStats,
  fetchSuppliers,
  MatchingCandidate,
  MatchingRunItem,
  MatchingStatsData,
  PendingMatchItem,
  rejectMatch,
  validateMatch,
} from '../api';
import { useNotification } from './NotificationProvider';

const statusLabels: Record<string, string> = {
  pending: 'Matchs en attente',
  validated: 'Matchs valides',
  rejected: 'Matchs rejetes',
  created: 'Matchs crees',
};

const CHART_COLORS = ['#B8860B', '#38bdf8', '#22c55e', '#e879f9', '#facc15', '#f43f5e'];

interface ChartPoint { label: string; value: number }

function MultiLineChart({ series, yLabel }: { series: { name: string; data: ChartPoint[] }[]; yLabel?: string }) {
  const width = 700, height = 280, padding = 50;
  const all = series.flatMap(s => s.data);
  if (!all.length) return <div className="h-40 flex items-center justify-center text-sm text-[var(--color-text-muted)]">Aucune donnée</div>;

  const maxVal = Math.max(...all.map(d => d.value)) * 1.15 || 1;
  const labels = Array.from(new Set(all.map(d => d.label)));
  const stepX = (width - padding * 2) / Math.max(1, labels.length - 1);
  const ticks = 4;
  const stepY = (height - padding * 2) / ticks;

  const paths = series.map((s, idx) => {
    const pts = labels.map((l, i) => {
      const found = s.data.find(d => d.label === l);
      return found ? { x: padding + i * stepX, y: height - padding - (found.value / maxVal) * (height - padding * 2) } : null;
    }).filter(Boolean) as { x: number; y: number }[];
    return { name: s.name, color: CHART_COLORS[idx % CHART_COLORS.length], points: pts, path: pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ') };
  });

  return (
    <div>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full" preserveAspectRatio="xMidYMid meet">
        {Array.from({ length: ticks + 1 }).map((_, i) => (
          <line key={i} x1={padding} y1={height - padding - i * stepY} x2={width - padding} y2={height - padding - i * stepY} stroke="var(--color-chart-grid, rgba(255,255,255,0.06))" />
        ))}
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="var(--color-chart-axis, rgba(255,255,255,0.2))" />
        <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="var(--color-chart-axis, rgba(255,255,255,0.2))" />
        {labels.map((l, i) => (
          <text key={l} x={padding + i * stepX} y={height - padding + 16} fontSize="9" textAnchor="middle" fill="var(--color-chart-text, rgba(255,255,255,0.5))">{l}</text>
        ))}
        {Array.from({ length: ticks + 1 }).map((_, i) => (
          <text key={i} x={padding - 6} y={height - padding - i * stepY + 3} fontSize="9" textAnchor="end" fill="var(--color-chart-text, rgba(255,255,255,0.5))">{((maxVal / ticks) * i).toFixed(maxVal < 1 ? 4 : 0)}</text>
        ))}
        {yLabel && <text x={12} y={height / 2} fontSize="10" fill="var(--color-chart-text, rgba(255,255,255,0.5))" transform={`rotate(-90, 12, ${height / 2})`} textAnchor="middle">{yLabel}</text>}
        {paths.map(s => (
          <g key={s.name}>
            <path d={s.path} fill="none" stroke={s.color} strokeWidth="2" />
            {s.points.map((p, i) => <circle key={i} cx={p.x} cy={p.y} r={3} fill={s.color} />)}
          </g>
        ))}
      </svg>
      <div className="flex gap-4 justify-center mt-1">
        {paths.map(s => (
          <div key={s.name} className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)]">
            <span className="w-3 h-0.5 rounded" style={{ background: s.color }} />
            {s.name}
          </div>
        ))}
      </div>
    </div>
  );
}

function StackedBarChart({ series, labels }: { series: { name: string; color: string; values: number[] }[]; labels: string[] }) {
  const width = 700, height = 280, padding = 50;
  if (!labels.length) return <div className="h-40 flex items-center justify-center text-sm text-[var(--color-text-muted)]">Aucune donnée</div>;

  const totals = labels.map((_, i) => series.reduce((sum, s) => sum + (s.values[i] || 0), 0));
  const maxVal = Math.max(...totals) * 1.15 || 1;
  const barW = Math.min(30, (width - padding * 2) / labels.length - 4);
  const stepX = (width - padding * 2) / labels.length;
  const ticks = 4;
  const stepY = (height - padding * 2) / ticks;

  return (
    <div>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full" preserveAspectRatio="xMidYMid meet">
        {Array.from({ length: ticks + 1 }).map((_, i) => (
          <line key={i} x1={padding} y1={height - padding - i * stepY} x2={width - padding} y2={height - padding - i * stepY} stroke="var(--color-chart-grid, rgba(255,255,255,0.06))" />
        ))}
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="var(--color-chart-axis, rgba(255,255,255,0.2))" />
        <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="var(--color-chart-axis, rgba(255,255,255,0.2))" />
        {labels.map((l, i) => {
          const cx = padding + i * stepX + stepX / 2;
          let cumY = 0;
          return (
            <g key={i}>
              {series.map(s => {
                const val = s.values[i] || 0;
                const barH = (val / maxVal) * (height - padding * 2);
                const y = height - padding - cumY - barH;
                cumY += barH;
                return <rect key={s.name} x={cx - barW / 2} y={y} width={barW} height={barH} fill={s.color} rx={1} />;
              })}
              <text x={cx} y={height - padding + 16} fontSize="9" textAnchor="middle" fill="var(--color-chart-text, rgba(255,255,255,0.5))">{l}</text>
            </g>
          );
        })}
        {Array.from({ length: ticks + 1 }).map((_, i) => (
          <text key={i} x={padding - 6} y={height - padding - i * stepY + 3} fontSize="9" textAnchor="end" fill="var(--color-chart-text, rgba(255,255,255,0.5))">{((maxVal / ticks) * i).toFixed(0)}</text>
        ))}
      </svg>
      <div className="flex gap-4 justify-center mt-1">
        {series.map(s => (
          <div key={s.name} className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)]">
            <span className="w-3 h-3 rounded-sm" style={{ background: s.color }} />
            {s.name}
          </div>
        ))}
      </div>
    </div>
  );
}

function MatchingPanel() {
  const notify = useNotification();

  // Tab
  const [activeTab, setActiveTab] = useState<'validation' | 'rapport'>('validation');

  // Suppliers
  const [suppliers, setSuppliers] = useState<{ id: number; name: string }[]>([]);
  const [selectedSupplier, setSelectedSupplier] = useState<number | undefined>();


  // Pending matches
  const [pending, setPending] = useState<PendingMatchItem[]>([]);
  const [pendingTotal, setPendingTotal] = useState(0);
  const [pendingPage, setPendingPage] = useState(1);
  const perPage = 10;

  // Filters
  const [statusFilter, setStatusFilter] = useState('pending');
  const [modelFilter, setModelFilter] = useState('');
  const [modelInput, setModelInput] = useState('');
  const modelTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Stats
  const [stats, setStats] = useState<MatchingStatsData | null>(null);

  // Rapport — matching runs history
  const [runs, setRuns] = useState<MatchingRunItem[]>([]);
  const [loadingRuns, setLoadingRuns] = useState(false);

  // Loading
  const [loadingPending, setLoadingPending] = useState(false);

  useEffect(() => {
    fetchSuppliers()
      .then((data) => setSuppliers(data))
      .catch(() => {});
    loadStats();
  }, []);

  useEffect(() => {
    if (activeTab === 'rapport' && runs.length === 0) loadRuns();
  }, [activeTab]);

  useEffect(() => {
    loadPending();
  }, [pendingPage, selectedSupplier, statusFilter, modelFilter]);

  function loadPending() {
    setLoadingPending(true);
    return fetchPendingMatches({
      supplier_id: selectedSupplier,
      page: pendingPage,
      per_page: perPage,
      status: statusFilter,
      model: modelFilter || undefined,
    })
      .then((data) => {
        setPending(data.items);
        setPendingTotal(data.total);
      })
      .catch(() => notify('Erreur lors du chargement des matchs', 'error'))
      .finally(() => setLoadingPending(false));
  }

  function loadStats() {
    return fetchMatchingStats()
      .then((data) => { setStats(data); return data; })
      .catch(() => undefined);
  }

  function loadRuns() {
    setLoadingRuns(true);
    fetchMatchingRuns(30)
      .then(setRuns)
      .catch(() => notify('Erreur lors du chargement des runs', 'error'))
      .finally(() => setLoadingRuns(false));
  }

  function handleModelInputChange(value: string) {
    setModelInput(value);
    if (modelTimerRef.current) clearTimeout(modelTimerRef.current);
    modelTimerRef.current = setTimeout(() => {
      setModelFilter(value);
      setPendingPage(1);
    }, 400);
  }

  async function handleValidate(pm: PendingMatchItem, candidate: MatchingCandidate) {
    const scrollY = window.scrollY;
    try {
      await validateMatch(pm.id, candidate.product_id);
      notify(`Match valide : ${pm.source_label}`, 'success');
      await loadPending();
      loadStats();
      requestAnimationFrame(() => window.scrollTo(0, scrollY));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Erreur';
      notify(msg, 'error');
    }
  }

  async function handleReject(pm: PendingMatchItem) {
    const scrollY = window.scrollY;
    try {
      await rejectMatch(pm.id, false);
      notify(`Match rejete : ${pm.source_label}`, 'success');
      await loadPending();
      loadStats();
      requestAnimationFrame(() => window.scrollTo(0, scrollY));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Erreur';
      notify(msg, 'error');
    }
  }

  const totalPages = Math.ceil(pendingTotal / perPage);
  const canValidate = statusFilter === 'pending' || statusFilter === 'rejected';
  const showActions = statusFilter === 'pending';

  const paginationControls = totalPages > 1 ? (
    <div className="flex items-center gap-2 text-sm text-[var(--color-text-muted)]">
      <button
        type="button"
        disabled={pendingPage <= 1}
        onClick={() => setPendingPage((p) => p - 1)}
        className="p-1 rounded hover:bg-[var(--color-bg-elevated)] disabled:opacity-30"
      >
        <ChevronLeft className="w-4 h-4" />
      </button>
      <span>
        {pendingPage} / {totalPages}
      </span>
      <button
        type="button"
        disabled={pendingPage >= totalPages}
        onClick={() => setPendingPage((p) => p + 1)}
        className="p-1 rounded hover:bg-[var(--color-bg-elevated)] disabled:opacity-30"
      >
        <ChevronRight className="w-4 h-4" />
      </button>
    </div>
  ) : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-[var(--color-text-heading)] flex items-center gap-3">
            <GitMerge className="w-8 h-8 text-[#B8860B]" />
            Rapprochement LLM
          </h1>
          <p className="text-[var(--color-text-muted)] mt-1">
            Mise en correspondance automatique des produits fournisseurs au référentiel.
          </p>
        </div>
      </div>

      {/* KPI cards */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="card p-4 text-center">
            <div className="text-2xl font-bold text-[#B8860B]">{stats.coverage_pct}%</div>
            <div className="text-xs text-[var(--color-text-muted)] mt-1">Couverture</div>
          </div>
          <div className="card p-4 text-center">
            <div className="text-2xl font-bold text-emerald-400">{stats.total_auto_matched}</div>
            <div className="text-xs text-[var(--color-text-muted)] mt-1">Auto-matchés</div>
          </div>
          <div className="card p-4 text-center">
            <div className="text-2xl font-bold text-amber-400">{stats.total_pending}</div>
            <div className="text-xs text-[var(--color-text-muted)] mt-1">À valider</div>
          </div>
          <div className="card p-4 text-center">
            <div className="text-2xl font-bold text-[var(--color-text-heading)]">{stats.total_validated}</div>
            <div className="text-xs text-[var(--color-text-muted)] mt-1">Validés</div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-[var(--color-border-subtle)] flex gap-0">
        <button
          type="button"
          onClick={() => setActiveTab('validation')}
          className={`px-4 py-2 text-sm font-medium -mb-px ${activeTab === 'validation' ? 'border-b-2 border-[#B8860B] text-[#B8860B]' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'}`}
        >
          <Check className="w-4 h-4 inline -mt-0.5 mr-1.5" />
          Validation
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('rapport')}
          className={`px-4 py-2 text-sm font-medium -mb-px ${activeTab === 'rapport' ? 'border-b-2 border-[#B8860B] text-[#B8860B]' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'}`}
        >
          <BarChart3 className="w-4 h-4 inline -mt-0.5 mr-1.5" />
          Rapport
        </button>
      </div>

      {activeTab === 'validation' && (
        <>
          {/* Produits Odoo sans correspondance fournisseur */}
          {stats && stats.total_odoo_unmatched > 0 && (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 space-y-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-amber-400/70">
                Produits Odoo sans correspondance fournisseur
              </p>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-amber-500/10 rounded-md px-3 py-2">
                  <div className="text-xl font-bold text-amber-400">
                    {stats.total_odoo_never_submitted}
                  </div>
                  <div className="text-xs text-[var(--color-text-muted)] mt-0.5">
                    jamais soumis au LLM
                  </div>
                  {stats.total_odoo_never_submitted > 0 && (
                    <div className="text-xs text-amber-400/60 mt-1">
                      → lancez le rapprochement
                    </div>
                  )}
                </div>
                <div className="bg-[var(--color-bg-elevated)] rounded-md px-3 py-2">
                  <div className="text-xl font-bold text-[var(--color-text-primary)]">
                    {stats.total_pending}
                  </div>
                  <div className="text-xs text-[var(--color-text-muted)] mt-0.5">
                    en attente de validation
                  </div>
                  {stats.total_pending > 0 && (
                    <div className="text-xs text-[var(--color-text-muted)]/60 mt-1">
                      → validez les matchs ci-dessous
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Section Validation — PRIMARY */}
          <div className="card overflow-hidden">
            <div className="p-4 flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-3 flex-wrap">
                <h3 className="text-sm font-semibold text-[var(--color-text-heading)]">
                  {statusLabels[statusFilter]} ({pendingTotal})
                </h3>
                <select
                  value={selectedSupplier ?? ''}
                  onChange={(e) => {
                    const val = e.target.value;
                    setSelectedSupplier(val ? Number(val) : undefined);
                    setPendingPage(1);
                  }}
                  className="rounded-md border border-[var(--color-border-default)] bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)] px-2 py-1 text-xs"
                  data-testid="supplier-filter"
                >
                  <option value="">Tous les fournisseurs</option>
                  {suppliers.map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
                <select
                  value={statusFilter}
                  onChange={(e) => {
                    setStatusFilter(e.target.value);
                    setPendingPage(1);
                  }}
                  className="rounded-md border border-[var(--color-border-default)] bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)] px-2 py-1 text-xs"
                  data-testid="status-filter"
                >
                  <option value="pending">En attente</option>
                  <option value="validated">Valides</option>
                  <option value="rejected">Rejetes</option>
                  <option value="created">Crees</option>
                </select>
                <div className="relative">
                  <Search className="w-3.5 h-3.5 absolute left-2 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
                  <input
                    type="text"
                    value={modelInput}
                    onChange={(e) => handleModelInputChange(e.target.value)}
                    placeholder="Filtrer par modèle..."
                    className="rounded-md border border-[var(--color-border-default)] bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)] pl-7 pr-2 py-1 text-xs w-44"
                    data-testid="model-filter"
                  />
                </div>
              </div>
              {paginationControls}
            </div>

            {loadingPending ? (
              <div className="p-8 flex justify-center">
                <Loader2 className="w-6 h-6 animate-spin text-[var(--color-text-muted)]" />
              </div>
            ) : pending.length === 0 ? (
              <div className="p-8 text-center text-sm text-[var(--color-text-muted)]">
                Aucun match a afficher.
              </div>
            ) : (
              <div className="divide-y divide-[var(--color-border-subtle)]">
                {pending.map((pm) => (
                  <PendingMatchRow
                    key={pm.id}
                    pm={pm}
                    canValidate={canValidate}
                    showActions={showActions}
                    onValidate={handleValidate}
                    onReject={handleReject}
                  />
                ))}
              </div>
            )}

            {paginationControls && (
              <div className="p-4 border-t border-[var(--color-border-subtle)] flex justify-end">
                {paginationControls}
              </div>
            )}
          </div>
        </>
      )}

      {activeTab === 'rapport' && <RapportTab runs={runs} loading={loadingRuns} onRefresh={loadRuns} stats={stats} />}

    </div>
  );
}


function RapportTab({ runs, loading, onRefresh, stats }: { runs: MatchingRunItem[]; loading: boolean; onRefresh: () => void; stats: MatchingStatsData | null }) {
  // Reverse to show oldest → newest (left to right) and limit to 15
  const sorted = [...runs].filter(r => r.status === 'completed').reverse().slice(-15);
  const dateLabels = sorted.map(r => r.ran_at ? new Date(r.ran_at).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' }) : '?');

  // Chart 1: Cost & Cache
  const costData: ChartPoint[] = sorted.map((r, i) => ({ label: dateLabels[i], value: r.cost_estimate ?? 0 }));
  const cacheData: ChartPoint[] = sorted.map((r, i) => {
    const total = (r.from_cache ?? 0) + (r.llm_calls ?? 0) * 25; // approximate total labels
    const pct = total > 0 ? ((r.from_cache ?? 0) / total) * 100 : 0;
    return { label: dateLabels[i], value: Math.round(pct) };
  });

  // Chart 2: Stacked results
  const stackedSeries = [
    { name: 'Auto-matchés', color: '#22c55e', values: sorted.map(r => r.auto_matched ?? 0) },
    { name: 'À valider', color: '#f59e0b', values: sorted.map(r => r.pending_review ?? 0) },
    { name: 'Rejetés', color: '#ef4444', values: sorted.map(r => r.auto_rejected ?? 0) },
    { name: 'Non trouvés', color: '#6b7280', values: sorted.map(r => r.not_found ?? 0) },
  ];

  // Chart 3: Products processed
  const productsData: ChartPoint[] = sorted.map((r, i) => ({ label: dateLabels[i], value: r.total_products ?? 0 }));
  const autoData: ChartPoint[] = sorted.map((r, i) => ({ label: dateLabels[i], value: r.auto_matched ?? 0 }));

  // Coverage KPI: live from stats endpoint
  const coveragePct = stats ? stats.coverage_pct : null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-[var(--color-text-heading)]">
          Historique des runs ({runs.length})
        </h3>
        <button type="button" onClick={onRefresh} disabled={loading} className="btn btn-secondary text-xs py-1 px-2 flex items-center gap-1.5">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Rafraîchir
        </button>
      </div>

      {loading ? (
        <div className="p-8 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-[var(--color-text-muted)]" /></div>
      ) : sorted.length === 0 ? (
        <div className="p-8 text-center text-sm text-[var(--color-text-muted)]">Aucun run complété.</div>
      ) : (
        <>
          {/* Chart 1: Cost & Cache */}
          <div className="card p-4 space-y-2">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">Coût LLM & Taux de cache</h4>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-[var(--color-text-muted)] mb-1">Coût estimé (€)</p>
                <MultiLineChart series={[{ name: 'Coût (€)', data: costData }]} yLabel="€" />
              </div>
              <div>
                <p className="text-xs text-[var(--color-text-muted)] mb-1">Taux de cache (%)</p>
                <MultiLineChart series={[{ name: 'Cache %', data: cacheData }]} yLabel="%" />
              </div>
            </div>
          </div>

          {/* Chart 2: Stacked results */}
          <div className="card p-4 space-y-2">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">Répartition des résultats</h4>
            <StackedBarChart series={stackedSeries} labels={dateLabels} />
          </div>

          {/* Coverage KPI + Chart 3 */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Coverage gauge */}
            <div className="card p-4 flex flex-col items-center justify-center">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)] mb-3">Couverture TCP</h4>
              {coveragePct !== null && stats ? (
                <>
                  <CoverageGauge percent={coveragePct} />
                  <p className="text-sm font-semibold text-[var(--color-text-primary)] mt-2">
                    {stats.total_odoo_matched} <span className="text-[var(--color-text-muted)] font-normal">/ {stats.total_odoo_products}</span>
                  </p>
                  <p className="text-xs text-[var(--color-text-muted)]">produits dans TCP / référentiel Odoo</p>
                </>
              ) : (
                <p className="text-xs text-[var(--color-text-muted)]">Chargement…</p>
              )}
            </div>

            {/* Products processed chart */}
            <div className="card p-4 space-y-2 lg:col-span-2">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">Produits traités par run</h4>
              <MultiLineChart series={[{ name: 'Produits traités', data: productsData }, { name: 'Auto-matchés', data: autoData }]} />
            </div>
          </div>

          {/* History table */}
          <div className="card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-[var(--color-border-subtle)]">
                    {['Date', 'Durée', 'Coût', 'Couverture', 'Produits', 'Cache', 'Auto', 'Pending', 'Rejetés', 'Not found', 'LLM calls'].map(h => (
                      <th key={h} className="px-3 py-2 text-left font-medium text-[var(--color-text-muted)] whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--color-border-subtle)]">
                  {[...sorted].reverse().map(r => (
                    <tr key={r.id} className="hover:bg-[var(--color-bg-elevated)]">
                      <td className="px-3 py-2 whitespace-nowrap text-[var(--color-text-primary)]">
                        {r.ran_at ? new Date(r.ran_at).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'}
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap text-[var(--color-text-muted)]">{r.duration_seconds ? `${r.duration_seconds.toFixed(1)}s` : '—'}</td>
                      <td className="px-3 py-2 whitespace-nowrap text-[var(--color-text-muted)]">{r.cost_estimate ? `${r.cost_estimate.toFixed(4)}€` : '—'}</td>
                      <td className="px-3 py-2 whitespace-nowrap text-[#B8860B] font-medium">
                        {r.total_odoo_products != null && r.matched_products != null
                          ? `${r.matched_products}/${r.total_odoo_products} (${((r.matched_products / r.total_odoo_products) * 100).toFixed(1)}%)`
                          : '—'}
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap font-medium text-[var(--color-text-primary)]">{r.total_products ?? '—'}</td>
                      <td className="px-3 py-2 whitespace-nowrap text-[#B8860B]">{r.from_cache ?? '—'}</td>
                      <td className="px-3 py-2 whitespace-nowrap text-emerald-400">{r.auto_matched ?? '—'}</td>
                      <td className="px-3 py-2 whitespace-nowrap text-amber-400">{r.pending_review ?? '—'}</td>
                      <td className="px-3 py-2 whitespace-nowrap text-red-400">{r.auto_rejected ?? '—'}</td>
                      <td className="px-3 py-2 whitespace-nowrap text-[var(--color-text-muted)]">{r.not_found ?? '—'}</td>
                      <td className="px-3 py-2 whitespace-nowrap text-[var(--color-text-muted)]">{r.llm_calls ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}


const SCORE_LABELS: Record<string, string> = {
  brand: 'Marque',
  storage: 'Stockage',
  model_family: 'Modèle',
  color: 'Couleur',
  region: 'Région',
  label_similarity: 'Nomenclature',
};

function CoverageGauge({ percent }: { percent: number }) {
  const size = 120;
  const stroke = 10;
  const radius = (size - stroke) / 2;
  const circumference = Math.PI * radius; // half circle
  const offset = circumference - (Math.min(percent, 100) / 100) * circumference;

  return (
    <svg width={size} height={size / 2 + 10} viewBox={`0 0 ${size} ${size / 2 + 10}`}>
      {/* Background arc */}
      <path
        d={`M ${stroke / 2} ${size / 2} A ${radius} ${radius} 0 0 1 ${size - stroke / 2} ${size / 2}`}
        fill="none"
        stroke="var(--color-border-subtle)"
        strokeWidth={stroke}
        strokeLinecap="round"
      />
      {/* Filled arc */}
      <path
        d={`M ${stroke / 2} ${size / 2} A ${radius} ${radius} 0 0 1 ${size - stroke / 2} ${size / 2}`}
        fill="none"
        stroke="#B8860B"
        strokeWidth={stroke}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        className="transition-all duration-700"
      />
      {/* Percentage text */}
      <text x={size / 2} y={size / 2 - 2} textAnchor="middle" className="text-xl font-bold" fill="var(--color-text-primary)" fontSize="22">
        {percent.toFixed(1)}%
      </text>
    </svg>
  );
}


function ScoreDetails({ details }: { details: Record<string, number> }) {
  const entries = Object.entries(details).filter(
    ([k]) => k !== 'disqualified' && k in SCORE_LABELS
  );
  if (entries.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1.5 mt-1">
      {entries.map(([key, val]) => {
        const color =
          val > 0
            ? 'text-emerald-400 border-emerald-500/30'
            : val < 0
            ? 'text-red-400 border-red-500/30'
            : 'text-[var(--color-text-muted)] border-[var(--color-border-subtle)]';
        return (
          <span
            key={key}
            className={`inline-flex items-center gap-1 px-1.5 py-0 rounded text-[10px] border ${color}`}
          >
            {SCORE_LABELS[key]}
            <strong>{val > 0 ? `+${val}` : val}</strong>
          </span>
        );
      })}
    </div>
  );
}

function PendingMatchRow({
  pm,
  canValidate,
  showActions,
  onValidate,
  onReject,
}: {
  pm: PendingMatchItem;
  canValidate: boolean;
  showActions: boolean;
  onValidate: (pm: PendingMatchItem, candidate: MatchingCandidate) => void;
  onReject: (pm: PendingMatchItem) => void;
}) {
  const attrs = pm.extracted_attributes;
  const badges = [
    attrs.brand,
    attrs.model_family,
    attrs.storage,
    attrs.color,
    attrs.region,
  ].filter(Boolean) as string[];

  return (
    <div className="p-4 space-y-3">
      {/* Label + supplier */}
      <div>
        <div className="text-sm font-medium text-[var(--color-text-primary)]">
          {pm.source_label}
        </div>
        {pm.supplier_name && (
          <div className="text-xs text-[var(--color-text-muted)]">
            {pm.supplier_name}
          </div>
        )}
      </div>

      {/* Extracted attributes */}
      <div className="flex flex-wrap gap-1.5">
        {badges.map((badge, i) => (
          <span
            key={i}
            className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] border border-[var(--color-border-subtle)]"
          >
            {badge}
          </span>
        ))}
      </div>

      {/* Candidates */}
      {pm.candidates.length > 0 && (
        <div className="space-y-1.5">
          {pm.candidates.map((c, i) => (
            <div key={i} className="flex items-start gap-3 text-sm">
              {/* Score bar */}
              <div className="flex items-center gap-2 min-w-[120px] pt-0.5">
                <div className="w-16 h-2 rounded-full bg-[var(--color-bg-elevated)] overflow-hidden">
                  <div
                    className="h-full rounded-full bg-[#B8860B]"
                    style={{ width: `${c.score}%` }}
                  />
                </div>
                <span className="text-xs text-[var(--color-text-muted)] w-8">
                  {c.score}%
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline gap-2">
                  <span className="text-[var(--color-text-primary)] truncate">
                    {c.product_name}
                  </span>
                  <span className="text-[10px] text-[var(--color-text-muted)] shrink-0">
                    #{c.product_id}
                  </span>
                </div>
                <ScoreDetails details={c.details} />
              </div>
              {canValidate && (
                <button
                  type="button"
                  onClick={() => onValidate(pm, c)}
                  className="btn btn-primary text-xs py-1 px-2 flex items-center gap-1 shrink-0"
                  title="Valider ce match"
                >
                  <Check className="w-3 h-3" />
                  Valider
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
      {showActions && (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => onReject(pm)}
            className="btn btn-secondary text-xs py-1 px-2 flex items-center gap-1"
          >
            <X className="w-3 h-3" />
            Ignorer
          </button>
        </div>
      )}
    </div>
  );
}

export default MatchingPanel;
