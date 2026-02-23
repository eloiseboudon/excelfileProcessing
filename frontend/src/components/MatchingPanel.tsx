import {
  AlertTriangle,
  Check,
  ChevronLeft,
  ChevronRight,
  Link,
  Loader2,
  Play,
  Plus,
  Search,
  Tag,
  X,
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import {
  assignDeviceTypes,
  fetchPendingMatches,
  fetchMatchingStats,
  fetchSuppliers,
  MatchingCandidate,
  MatchingStatsData,
  PendingMatchItem,
  rejectMatch,
  runMatching,
  validateMatch,
} from '../api';
import { useNotification } from './NotificationProvider';

const statusLabels: Record<string, string> = {
  pending: 'Matchs en attente',
  validated: 'Matchs valides',
  rejected: 'Matchs rejetes',
  created: 'Matchs crees',
};

function MatchingPanel() {
  const notify = useNotification();

  // Suppliers
  const [suppliers, setSuppliers] = useState<{ id: number; name: string }[]>([]);
  const [selectedSupplier, setSelectedSupplier] = useState<number | undefined>();

  // Run state
  const [running, setRunning] = useState(false);
  const [matchLimit, setMatchLimit] = useState<number | undefined>(50);
  const [assigningTypes, setAssigningTypes] = useState(false);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

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

  // Error
  const [error, setError] = useState<string | null>(null);

  // Loading
  const [loadingPending, setLoadingPending] = useState(false);

  useEffect(() => {
    fetchSuppliers()
      .then((data) => setSuppliers(data))
      .catch(() => {});
    loadStats();
  }, []);

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
    fetchMatchingStats()
      .then(setStats)
      .catch(() => {});
  }

  function handleModelInputChange(value: string) {
    setModelInput(value);
    if (modelTimerRef.current) clearTimeout(modelTimerRef.current);
    modelTimerRef.current = setTimeout(() => {
      setModelFilter(value);
      setPendingPage(1);
    }, 400);
  }

  function stopPolling() {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    setRunning(false);
  }

  async function handleRun() {
    if (running) {
      stopPolling();
      return;
    }
    setRunning(true);
    setError(null);
    try {
      await runMatching(selectedSupplier, matchLimit);
      notify('Rapprochement lance en arriere-plan — les stats se mettent a jour automatiquement', 'success');

      // Poll stats + list every 5s for up to 10 minutes
      let elapsed = 0;
      const MAX_DURATION = 10 * 60 * 1000;
      const POLL_INTERVAL = 5000;
      pollIntervalRef.current = setInterval(() => {
        elapsed += POLL_INTERVAL;
        loadStats();
        loadPending();
        if (elapsed >= MAX_DURATION) {
          stopPolling();
        }
      }, POLL_INTERVAL);
    } catch (err: unknown) {
      let msg: string;
      if (err instanceof TypeError && err.message === 'Failed to fetch') {
        msg = 'Impossible de contacter le serveur. Verifiez votre connexion ou que le backend est demarre.';
      } else if (err instanceof Error) {
        msg = err.message;
      } else {
        msg = 'Erreur inconnue lors du rapprochement';
      }
      setError(msg);
      notify(msg, 'error');
      setRunning(false);
    }
  }

  async function handleAssignTypes() {
    setAssigningTypes(true);
    try {
      const result = await assignDeviceTypes(false);
      notify(
        `Types assignes : ${result.classified} produits classes, ${result.unclassified} non identifies`,
        'success'
      );
      loadStats();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Erreur';
      notify(msg, 'error');
    } finally {
      setAssigningTypes(false);
    }
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

  async function handleReject(pm: PendingMatchItem, createProduct: boolean) {
    const scrollY = window.scrollY;
    try {
      await rejectMatch(pm.id, createProduct);
      notify(
        createProduct
          ? `Nouveau produit cree depuis : ${pm.source_label}`
          : `Match rejete : ${pm.source_label}`,
        'success'
      );
      await loadPending();
      loadStats();
      requestAnimationFrame(() => window.scrollTo(0, scrollY));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Erreur';
      notify(msg, 'error');
    }
  }

  const totalPages = Math.ceil(pendingTotal / perPage);
  const readOnly = statusFilter !== 'pending';

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
      {/* Section 1 — Declenchement */}
      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <Link className="w-5 h-5 text-[#B8860B]" />
          <h2 className="text-lg font-semibold text-[var(--color-text-heading)]">
            Rapprochement LLM
          </h2>
        </div>
        <p className="text-sm text-[var(--color-text-muted)] mb-4">
          Associez automatiquement les produits fournisseurs au referentiel en
          utilisant l'extraction par IA.
        </p>

        <div className="flex items-center gap-3 flex-wrap">
          <select
            value={selectedSupplier ?? ''}
            onChange={(e) => {
              const val = e.target.value;
              setSelectedSupplier(val ? Number(val) : undefined);
              setPendingPage(1);
            }}
            className="rounded-md border border-[var(--color-border-default)] bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)] px-3 py-2 text-sm"
          >
            <option value="">Tous les fournisseurs</option>
            {suppliers.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
          <select
            value={matchLimit ?? ''}
            onChange={(e) => {
              const val = e.target.value;
              setMatchLimit(val ? Number(val) : undefined);
            }}
            className="rounded-md border border-[var(--color-border-default)] bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)] px-3 py-2 text-sm"
          >
            <option value="50">50 produits</option>
            <option value="100">100 produits</option>
            <option value="200">200 produits</option>
            <option value="">Tous</option>
          </select>
          <button
            type="button"
            onClick={handleRun}
            className={`btn flex items-center gap-2 ${running ? 'btn-secondary' : 'btn-primary'}`}
          >
            {running ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Arreter le suivi
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Lancer le rapprochement
              </>
            )}
          </button>
          <button
            type="button"
            onClick={handleAssignTypes}
            disabled={assigningTypes}
            className="btn btn-secondary flex items-center gap-2"
            title="Assigner automatiquement les types aux produits sans type (règles métier)"
          >
            {assigningTypes ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Tag className="w-4 h-4" />
            )}
            Assigner les types
          </button>
        </div>

        {/* Erreur inline */}
        {error && !running && (
          <div className="mt-4 flex items-start gap-2 p-3 rounded-md bg-[var(--color-bg-elevated)] border border-red-500/30">
            <AlertTriangle className="w-5 h-5 text-red-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium text-red-400">
                Echec du rapprochement
              </p>
              <p className="text-sm text-red-400/80 mt-1">{error}</p>
            </div>
          </div>
        )}

        {/* Bandeau "en cours" */}
        {running && (
          <div className="mt-4 flex items-center gap-2 p-3 rounded-md bg-[var(--color-bg-elevated)] border border-[var(--color-border-subtle)]">
            <Loader2 className="w-4 h-4 animate-spin text-[#B8860B] shrink-0" />
            <p className="text-sm text-[var(--color-text-primary)]">
              Rapprochement en cours — les statistiques se mettent a jour toutes les 5s.
            </p>
          </div>
        )}
      </div>

      {/* Produits Odoo sans correspondance fournisseur */}
      {stats && stats.total_odoo_unmatched > 0 && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-400/70">
            Produits Odoo sans correspondance fournisseur
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-amber-500/10 rounded-md px-3 py-2">
              <div className="text-xl font-bold text-amber-400">
                {stats.total_odoo_unmatched - stats.total_pending}
              </div>
              <div className="text-xs text-[var(--color-text-muted)] mt-0.5">
                jamais soumis au LLM
              </div>
              {(stats.total_odoo_unmatched - stats.total_pending) > 0 && (
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

      {/* Suivi de progression */}
      {stats && (
        <div className="card space-y-4">
          <h3 className="text-sm font-semibold text-[var(--color-text-heading)]">
            Couverture LLM
          </h3>

          {/* Produits Odoo matchés vs total */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-[var(--color-bg-elevated)] rounded-md p-4 text-center">
              <div className="text-3xl font-bold text-[#B8860B]">
                {stats.total_odoo_matched}
              </div>
              <div className="text-xs text-[var(--color-text-muted)] mt-1">produits Odoo matches</div>
            </div>
            <div className="bg-[var(--color-bg-elevated)] rounded-md p-4 text-center">
              <div className="text-3xl font-bold text-[var(--color-text-heading)]">
                {stats.total_odoo_products}
              </div>
              <div className="text-xs text-[var(--color-text-muted)] mt-1">produits Odoo en base</div>
            </div>
          </div>

          {/* Barre de couverture */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-[var(--color-text-muted)]">
              <span>Couverture catalogue</span>
              <span className="font-medium text-[var(--color-text-primary)]">{stats.coverage_pct}%</span>
            </div>
            <div className="w-full h-2 bg-[var(--color-bg-elevated)] rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${stats.coverage_pct}%`,
                  background: 'linear-gradient(to right, #B8860B, #DAA520)',
                }}
              />
            </div>
          </div>

          {/* Répartition des matchs */}
          <div className="pt-2 border-t border-[var(--color-border-subtle)] space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-[var(--color-text-heading)]">Repartition des matchs</span>
              <span className="text-xs text-[var(--color-text-muted)]">
                {stats.total_processed} traite{stats.total_processed > 1 ? 's' : ''} sur {stats.total_all} ({stats.progress_pct}%)
              </span>
            </div>

            {/* Barre de progression */}
            <div className="w-full h-2 bg-[var(--color-bg-elevated)] rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${stats.progress_pct}%`,
                  background: 'linear-gradient(to right, #B8860B, #DAA520)',
                }}
              />
            </div>

            {/* Compteurs par statut avec % */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <StatusCard
                label="En attente"
                value={stats.total_pending}
                color="text-amber-400"
                dot="bg-amber-400"
                pct={stats.total_all > 0 ? Math.round(stats.total_pending / stats.total_all * 100) : 0}
              />
              <StatusCard
                label="Valides"
                value={stats.total_validated}
                color="text-emerald-400"
                dot="bg-emerald-400"
                pct={stats.total_all > 0 ? Math.round(stats.total_validated / stats.total_all * 100) : 0}
              />
              <StatusCard
                label="Rejetes"
                value={stats.total_rejected}
                color="text-[var(--color-text-muted)]"
                dot="bg-[var(--color-border-default)]"
                pct={stats.total_all > 0 ? Math.round(stats.total_rejected / stats.total_all * 100) : 0}
              />
              <StatusCard
                label="Crees"
                value={stats.total_created}
                color="text-sky-400"
                dot="bg-sky-400"
                pct={stats.total_all > 0 ? Math.round(stats.total_created / stats.total_all * 100) : 0}
              />
            </div>
          </div>

          {/* Cache */}
          <div className="flex items-center gap-4 pt-1 border-t border-[var(--color-border-subtle)] text-xs text-[var(--color-text-muted)]">
            <span>Cache : <strong className="text-[var(--color-text-primary)]">{stats.total_cached}</strong> entrees</span>
            <span>Taux de cache : <strong className="text-[var(--color-text-primary)]">{stats.cache_hit_rate}%</strong></span>
            <span>Auto-matches : <strong className="text-[var(--color-text-primary)]">{stats.total_auto_matched}</strong></span>
          </div>
        </div>
      )}

      {/* Section 2 — Liste des matchs */}
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
                placeholder="Filtrer par modele..."
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
                readOnly={readOnly}
                onValidate={handleValidate}
                onReject={handleReject}
              />
            ))}
          </div>
        )}

        {/* Pagination bas */}
        {paginationControls && (
          <div className="p-4 border-t border-[var(--color-border-subtle)] flex justify-end">
            {paginationControls}
          </div>
        )}
      </div>
    </div>
  );
}


function StatusCard({
  label,
  value,
  color,
  dot,
  pct,
}: {
  label: string;
  value: number;
  color: string;
  dot: string;
  pct?: number;
}) {
  return (
    <div className="bg-[var(--color-bg-elevated)] rounded-md p-3 flex items-center gap-3">
      <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${dot}`} />
      <div>
        <div className={`text-lg font-bold ${color}`}>{value}</div>
        <div className="text-xs text-[var(--color-text-muted)]">{label}</div>
        {pct !== undefined && (
          <div className="text-xs font-medium text-[var(--color-text-secondary)]">{pct}%</div>
        )}
      </div>
    </div>
  );
}

const SCORE_LABELS: Record<string, string> = {
  brand: 'Marque',
  storage: 'Stockage',
  model_family: 'Modèle',
  color: 'Couleur',
  region: 'Région',
  label_similarity: 'Libellé',
};

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
  readOnly,
  onValidate,
  onReject,
}: {
  pm: PendingMatchItem;
  readOnly: boolean;
  onValidate: (pm: PendingMatchItem, candidate: MatchingCandidate) => void;
  onReject: (pm: PendingMatchItem, createProduct: boolean) => void;
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
              {!readOnly && (
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
      {!readOnly && (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => onReject(pm, true)}
            className="btn btn-secondary text-xs py-1 px-2 flex items-center gap-1"
          >
            <Plus className="w-3 h-3" />
            Creer produit
          </button>
          <button
            type="button"
            onClick={() => onReject(pm, false)}
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
