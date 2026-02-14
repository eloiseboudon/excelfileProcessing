import {
  AlertTriangle,
  Check,
  ChevronLeft,
  ChevronRight,
  Link,
  Loader2,
  Play,
  Plus,
  X,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import {
  fetchPendingMatches,
  fetchMatchingStats,
  fetchSuppliers,
  MatchingCandidate,
  MatchingReport,
  MatchingStatsData,
  PendingMatchItem,
  rejectMatch,
  runMatching,
  validateMatch,
} from '../api';
import { useNotification } from './NotificationProvider';

function MatchingPanel() {
  const notify = useNotification();

  // Suppliers
  const [suppliers, setSuppliers] = useState<{ id: number; name: string }[]>([]);
  const [selectedSupplier, setSelectedSupplier] = useState<number | undefined>();

  // Run state
  const [running, setRunning] = useState(false);
  const [report, setReport] = useState<MatchingReport | null>(null);

  // Pending matches
  const [pending, setPending] = useState<PendingMatchItem[]>([]);
  const [pendingTotal, setPendingTotal] = useState(0);
  const [pendingPage, setPendingPage] = useState(1);
  const perPage = 10;

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
  }, [pendingPage, selectedSupplier]);

  function loadPending() {
    setLoadingPending(true);
    fetchPendingMatches({
      supplier_id: selectedSupplier,
      page: pendingPage,
      per_page: perPage,
    })
      .then((data) => {
        setPending(data.items);
        setPendingTotal(data.total);
      })
      .catch(() => notify('Erreur lors du chargement des matchs en attente', 'error'))
      .finally(() => setLoadingPending(false));
  }

  function loadStats() {
    fetchMatchingStats()
      .then(setStats)
      .catch(() => {});
  }

  async function handleRun() {
    setRunning(true);
    setReport(null);
    setError(null);
    try {
      const result = await runMatching(selectedSupplier);
      setReport(result);
      notify(
        `Rapprochement termine : ${result.auto_matched} matches, ${result.pending_review} en attente, ${result.auto_created} crees`,
        'success'
      );
      loadPending();
      loadStats();
    } catch (err: unknown) {
      let msg: string;
      if (err instanceof DOMException && err.name === 'AbortError') {
        msg = 'Le rapprochement a pris trop de temps (timeout). Essayez avec un seul fournisseur.';
      } else if (err instanceof TypeError && err.message === 'Failed to fetch') {
        msg = 'Impossible de contacter le serveur. Verifiez votre connexion ou que le backend est demarre.';
      } else if (err instanceof Error) {
        msg = err.message;
      } else {
        msg = 'Erreur inconnue lors du rapprochement';
      }
      setError(msg);
      notify(msg, 'error');
    } finally {
      setRunning(false);
    }
  }

  async function handleValidate(pm: PendingMatchItem, candidate: MatchingCandidate) {
    try {
      await validateMatch(pm.id, candidate.product_id);
      notify(`Match valide : ${pm.source_label}`, 'success');
      loadPending();
      loadStats();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Erreur';
      notify(msg, 'error');
    }
  }

  async function handleReject(pm: PendingMatchItem, createProduct: boolean) {
    try {
      await rejectMatch(pm.id, createProduct);
      notify(
        createProduct
          ? `Nouveau produit cree depuis : ${pm.source_label}`
          : `Match rejete : ${pm.source_label}`,
        'success'
      );
      loadPending();
      loadStats();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Erreur';
      notify(msg, 'error');
    }
  }

  const totalPages = Math.ceil(pendingTotal / perPage);

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
          <button
            type="button"
            onClick={handleRun}
            disabled={running}
            className="btn btn-primary flex items-center gap-2"
          >
            {running ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            {running ? 'Rapprochement en cours...' : 'Lancer le rapprochement'}
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

        {/* Rapport */}
        {report && (
          <>
            <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
              <ReportCard label="Matches auto" value={report.auto_matched} />
              <ReportCard label="En attente" value={report.pending_review} />
              <ReportCard label="Crees" value={report.auto_created} />
              <ReportCard label="Depuis cache" value={report.from_cache} />
              <ReportCard label="Erreurs" value={report.errors} />
              <ReportCard
                label="Cout estime"
                value={`${report.cost_estimate.toFixed(4)} €`}
              />
            </div>
            {report.errors > 0 && report.error_message && (
              <div className="mt-3 flex items-start gap-2 p-3 rounded-md bg-[var(--color-bg-elevated)] border border-red-500/30">
                <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
                <p className="text-sm text-red-400">
                  {report.error_message}
                </p>
              </div>
            )}
          </>
        )}
      </div>

      {/* Stats */}
      {stats && (
        <div className="card">
          <h3 className="text-sm font-semibold text-[var(--color-text-heading)] mb-3">
            Statistiques
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <ReportCard label="En cache" value={stats.total_cached} />
            <ReportCard label="En attente" value={stats.total_pending} />
            <ReportCard label="Auto-matches" value={stats.total_auto_matched} />
            <ReportCard
              label="Taux de cache"
              value={`${stats.cache_hit_rate}%`}
            />
          </div>
        </div>
      )}

      {/* Section 2 — Matchs en attente */}
      <div className="card overflow-hidden">
        <div className="p-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[var(--color-text-heading)]">
            Matchs en attente ({pendingTotal})
          </h3>
          {totalPages > 1 && (
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
          )}
        </div>

        {loadingPending ? (
          <div className="p-8 flex justify-center">
            <Loader2 className="w-6 h-6 animate-spin text-[var(--color-text-muted)]" />
          </div>
        ) : pending.length === 0 ? (
          <div className="p-8 text-center text-sm text-[var(--color-text-muted)]">
            Aucun match en attente de validation.
          </div>
        ) : (
          <div className="divide-y divide-[var(--color-border-subtle)]">
            {pending.map((pm) => (
              <PendingMatchRow
                key={pm.id}
                pm={pm}
                onValidate={handleValidate}
                onReject={handleReject}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ReportCard({
  label,
  value,
}: {
  label: string;
  value: number | string;
}) {
  return (
    <div className="bg-[var(--color-bg-elevated)] rounded-md p-3 text-center">
      <div className="text-lg font-bold text-[var(--color-text-heading)]">
        {value}
      </div>
      <div className="text-xs text-[var(--color-text-muted)]">{label}</div>
    </div>
  );
}

function PendingMatchRow({
  pm,
  onValidate,
  onReject,
}: {
  pm: PendingMatchItem;
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
            <div
              key={i}
              className="flex items-center gap-3 text-sm"
            >
              {/* Score bar */}
              <div className="flex items-center gap-2 min-w-[120px]">
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
              <span className="text-[var(--color-text-primary)] flex-1 truncate">
                {c.product_name}
              </span>
              <button
                type="button"
                onClick={() => onValidate(pm, c)}
                className="btn btn-primary text-xs py-1 px-2 flex items-center gap-1"
                title="Valider ce match"
              >
                <Check className="w-3 h-3" />
                Valider
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
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
    </div>
  );
}

export default MatchingPanel;
