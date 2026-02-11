import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertCircle, FileText, Loader2, RefreshCcw } from 'lucide-react';
import {
  fetchSupplierApiReports,
  SupplierApiMappingSummary,
  SupplierApiReportEntry,
  SupplierApiReportEntryItem
} from '../api';

function describeMapping(mapping: SupplierApiMappingSummary | null | undefined): string {
  if (!mapping) {
    return 'Non renseigné';
  }
  const count = mapping.field_count ?? 0;
  const plural = count > 1 ? 'champs' : 'champ';
  const status = mapping.is_active ? '' : ' (inactif)';
  return `v${mapping.version} • ${count} ${plural}${status}`;
}

function formatDate(value: string | null): string {
  if (!value) {
    return '—';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '—';
  }
  return new Intl.DateTimeFormat('fr-FR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date);
}

function ReportList({
  title,
  items,
  emptyMessage,
  showPrice
}: {
  title: string;
  items: SupplierApiReportEntryItem[];
  emptyMessage: string;
  showPrice?: boolean;
}) {
  return (
    <div className="p-5 rounded-md bg-[var(--color-bg-subtle)] border border-[var(--color-border-subtle)]/60">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-sm font-semibold text-[var(--color-text-secondary)] uppercase tracking-wide">
          {title}
        </h4>
        <span className="text-xs text-[var(--color-text-muted)]">{items.length} élément{items.length > 1 ? 's' : ''}</span>
      </div>
      {items.length === 0 ? (
        <p className="text-sm text-[var(--color-text-muted)]">{emptyMessage}</p>
      ) : (
        <ul className="space-y-3 max-h-80 overflow-y-auto pr-2">
          {items.map((item, index) => {
            const key = item.product_id ?? `${item.ean || ''}-${item.part_number || ''}-${index}`;
            const label =
              item.product_name ||
              item.description ||
              item.part_number ||
              item.ean ||
              `Entrée ${index + 1}`;
            return (
              <li
                key={key || `entry-${index}`}
                className="flex items-start justify-between gap-4 border border-[var(--color-border-subtle)]/60 rounded-md px-3 py-2 bg-[var(--color-bg-faint)]"
              >
                <div className="flex-1">
                  <p className="text-sm font-medium text-[var(--color-text-heading)] truncate" title={label}>
                    {label}
                  </p>
                  <div className="text-xs text-[var(--color-text-muted)] space-x-2 mt-1">
                    {item.ean ? <span>EAN : {item.ean}</span> : null}
                    {item.part_number ? <span>Réf : {item.part_number}</span> : null}
                    {item.supplier_sku ? <span>SKU fournisseur : {item.supplier_sku}</span> : null}
                  </div>
                  {item.reason ? (
                    <p className="text-xs text-[var(--color-text-muted)] mt-2 leading-relaxed whitespace-pre-line">
                      {item.reason}
                    </p>
                  ) : null}
                </div>
                {showPrice && item.price != null ? (
                  <span className="text-sm font-semibold text-[var(--color-text-primary)] min-w-[80px] text-right">
                    {item.price.toLocaleString('fr-FR', {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2
                    })}{' '}
                    €
                  </span>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function RawDataPreview({ items }: { items: unknown[] | undefined }) {
  const [expanded, setExpanded] = useState(false);
  const entries = useMemo(() => (Array.isArray(items) ? items : []), [items]);

  const visibleEntries = useMemo(() => {
    if (expanded) {
      return entries;
    }
    return entries.slice(0, 3);
  }, [entries, expanded]);

  return (
    <div className="p-5 rounded-md bg-[var(--color-bg-subtle)] border border-[var(--color-border-subtle)]/60">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-sm font-semibold text-[var(--color-text-secondary)] uppercase tracking-wide">
          Données brutes de l'API
        </h4>
        <span className="text-xs text-[var(--color-text-muted)]">{entries.length} élément{entries.length > 1 ? 's' : ''}</span>
      </div>
      {entries.length === 0 ? (
        <p className="text-sm text-[var(--color-text-muted)]">
          Aucun échantillon de données brutes n'a été enregistré pour cette synchronisation.
        </p>
      ) : (
        <div className="space-y-3">
          <pre className="text-xs text-left text-[var(--color-text-secondary)] bg-[var(--color-bg-subtle)] border border-[var(--color-border-subtle)]/60 rounded-md p-4 overflow-x-auto whitespace-pre-wrap break-words max-h-80">
            {visibleEntries
              .map((entry) => JSON.stringify(entry, null, 2))
              .join('\n\n')}
          </pre>
          {entries.length > 3 ? (
            <button
              type="button"
              onClick={() => setExpanded((value) => !value)}
              className="text-xs font-medium text-[#B8860B] hover:underline"
            >
              {expanded ? 'Réduire l\'aperçu' : 'Afficher toutes les données brutes'}
            </button>
          ) : null}
        </div>
      )}
    </div>
  );
}

function SupplierApiReports() {
  const [reports, setReports] = useState<SupplierApiReportEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedReportIds, setExpandedReportIds] = useState<number[]>([]);

  const toggleReport = useCallback((jobId: number) => {
    setExpandedReportIds((current) =>
      current.includes(jobId) ? current.filter((id) => id !== jobId) : [...current, jobId]
    );
  }, []);

  const loadReports = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSupplierApiReports();
      setReports(Array.isArray(data) ? data : []);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Impossible de charger les rapports de synchronisation.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  const hasReports = reports.length > 0;
  const subtitle = useMemo(() => {
    if (!hasReports) {
      return "Consultez ici les résultats détaillés de chaque synchronisation effectuée.";
    }
    const [latest] = reports;
    if (!latest?.started_at) {
      return "Historique des synchronisations API fournisseurs.";
    }
    return `Dernière mise à jour : ${formatDate(latest.started_at)}`;
  }, [hasReports, reports]);

  return (
    <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="card">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
          <div>
            <h2 className="text-2xl font-semibold flex items-center gap-2">
              <FileText className="w-6 h-6 text-[#B8860B]" />
              Rapports de synchronisation
            </h2>
            <p className="text-sm text-[var(--color-text-muted)] mt-1">{subtitle}</p>
          </div>
          <button
            onClick={loadReports}
            disabled={loading}
            className={`btn btn-secondary flex items-center gap-2 ${loading ? 'opacity-70 cursor-wait' : ''}`}
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCcw className="w-4 h-4" />}
            Actualiser
          </button>
        </div>

        {error ? (
          <div className="p-4 rounded-md border border-red-500/30 bg-red-500/10 text-sm text-red-300 flex items-center gap-2 mb-6">
            <AlertCircle className="w-5 h-5" />
            <span>{error}</span>
          </div>
        ) : null}

        {loading && !hasReports ? (
          <div className="py-20 text-center text-sm text-[var(--color-text-muted)] flex flex-col items-center gap-3">
            <Loader2 className="w-5 h-5 animate-spin text-[#B8860B]" />
            <span>Chargement des rapports...</span>
          </div>
        ) : null}

        {!loading && !hasReports ? (
          <div className="py-20 text-center text-sm text-[var(--color-text-muted)]">
            Aucun rapport n'est disponible pour le moment. Lancez une synchronisation pour générer un premier rapport.
          </div>
        ) : null}

        <div className="space-y-6">
          {reports.map((report) => {
            const isExpanded = expandedReportIds.includes(report.job_id);
            const summaryItems = [
              {
                title: 'Produits mis à jour',
                count: report.updated_products.length,
                highlight: true
              },
              {
                title: 'Produits base non trouvés',
                count: report.database_missing_products.length
              },
              {
                title: 'Produits API non appairés',
                count: report.api_missing_products.length
              }
            ];

            return (
              <div
                key={report.job_id}
                className="border border-[var(--color-border-subtle)]/60 rounded-md bg-[var(--color-bg-subtle)] px-6 py-5"
              >
                <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                  <div>
                    <p className="text-xs text-zinc-500 uppercase tracking-wide">Fournisseur</p>
                    <h3 className="text-lg font-semibold text-[var(--color-text-heading)]">
                      {report.supplier || 'Fournisseur'}
                    </h3>
                    <div className="mt-3 grid gap-3 sm:grid-cols-3">
                      {summaryItems.map((item) => (
                        <div
                          key={item.title}
                          className="rounded-md border border-[var(--color-border-subtle)]/60 bg-[var(--color-bg-faint)] px-3 py-2"
                        >
                          <p className="text-[11px] uppercase tracking-wide text-zinc-500">{item.title}</p>
                          <p
                            className={`text-lg font-semibold ${
                              item.highlight ? 'text-[var(--color-text-heading)]' : 'text-[var(--color-text-secondary)]'
                            }`}
                          >
                            {item.count}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="flex flex-col items-start gap-4 md:items-end">
                    <div className="text-xs text-[var(--color-text-muted)] space-y-1 md:text-right">
                      <p>
                        Début :{' '}
                        <span className="font-medium text-[var(--color-text-secondary)]">{formatDate(report.started_at)}</span>
                      </p>
                      <p>
                        Fin :{' '}
                        <span className="font-medium text-[var(--color-text-secondary)]">{formatDate(report.ended_at)}</span>
                      </p>
                      <p>
                        Mapping :{' '}
                        <span className="font-medium text-[var(--color-text-secondary)]">
                          {describeMapping(report.mapping ?? null)}
                        </span>
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => toggleReport(report.job_id)}
                      aria-expanded={isExpanded}
                      className="btn btn-secondary text-xs"
                    >
                      {isExpanded ? 'Masquer le détail' : 'Afficher le détail'}
                    </button>
                  </div>
                </div>

                {isExpanded ? (
                  <div className="mt-6 space-y-5">
                    <div className="grid gap-4 md:grid-cols-3">
                      <ReportList
                        title="Produits mis à jour"
                        items={report.updated_products}
                        emptyMessage="Aucun produit mis à jour lors de cette synchronisation."
                        showPrice
                      />
                      <ReportList
                        title="Produits base non trouvés"
                        items={report.database_missing_products}
                        emptyMessage="Tous les produits liés ont été retrouvés dans l'API."
                      />
                      <ReportList
                        title="Produits API non appairés"
                        items={report.api_missing_products}
                        emptyMessage="Tous les articles de l'API ont été associés à la base produits."
                      />
                    </div>
                    <RawDataPreview items={report.api_raw_items} />
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

export default SupplierApiReports;
