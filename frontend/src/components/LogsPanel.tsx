import { Activity, FileText, RefreshCw } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import {
  fetchActivityLogs,
  fetchAppLogs,
  type ActivityLogEntry,
  type AppLogsResponse,
} from '../api';

type LogTab = 'activity' | 'app';

const CATEGORIES = [
  { value: '', label: 'Toutes' },
  { value: 'auth', label: 'Authentification' },
  { value: 'matching', label: 'Rapprochement' },
  { value: 'import', label: 'Import' },
  { value: 'calculation', label: 'Calculs' },
  { value: 'odoo', label: 'Odoo' },
  { value: 'product', label: 'Produits' },
];

const CATEGORY_COLORS: Record<string, string> = {
  auth: 'bg-blue-500/20 text-blue-400',
  matching: 'bg-purple-500/20 text-purple-400',
  import: 'bg-green-500/20 text-green-400',
  calculation: 'bg-yellow-500/20 text-yellow-400',
  odoo: 'bg-orange-500/20 text-orange-400',
  product: 'bg-red-500/20 text-red-400',
};

function formatTimestamp(ts: string | null): string {
  if (!ts) return '—';
  const d = new Date(ts);
  return d.toLocaleString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function LogsPanel() {
  const [tab, setTab] = useState<LogTab>('activity');

  return (
    <div>
      <div className="border-b border-[var(--color-border-subtle)] mb-6">
        <nav className="flex gap-4">
          <button
            type="button"
            onClick={() => setTab('activity')}
            className={`px-2 pb-3 text-sm font-medium transition-colors border-b-2 flex items-center gap-2 ${
              tab === 'activity'
                ? 'border-[#B8860B] text-[var(--color-text-heading)]'
                : 'border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
            }`}
          >
            <Activity className="w-4 h-4" />
            Historique d'activité
          </button>
          <button
            type="button"
            onClick={() => setTab('app')}
            className={`px-2 pb-3 text-sm font-medium transition-colors border-b-2 flex items-center gap-2 ${
              tab === 'app'
                ? 'border-[#B8860B] text-[var(--color-text-heading)]'
                : 'border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
            }`}
          >
            <FileText className="w-4 h-4" />
            Logs application
          </button>
        </nav>
      </div>

      {tab === 'activity' && <ActivityLogsTab />}
      {tab === 'app' && <AppLogsTab />}
    </div>
  );
}

function ActivityLogsTab() {
  const [logs, setLogs] = useState<ActivityLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState('');
  const [loading, setLoading] = useState(false);
  const perPage = 20;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchActivityLogs({
        page,
        per_page: perPage,
        category: category || undefined,
      });
      setLogs(data.items);
      setTotal(data.total);
    } catch {
      // silently handled
    } finally {
      setLoading(false);
    }
  }, [page, category]);

  useEffect(() => {
    load();
  }, [load]);

  const totalPages = Math.ceil(total / perPage);

  return (
    <div>
      <div className="card mb-4">
        <div className="flex items-center gap-3">
          <label className="text-sm text-[var(--color-text-muted)]">Catégorie :</label>
          <select
            value={category}
            onChange={(e) => {
              setCategory(e.target.value);
              setPage(1);
            }}
            className="rounded-md bg-[var(--color-bg-elevated)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)] text-sm px-2 py-1"
          >
            {CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={load}
            className="btn btn-secondary flex items-center gap-1 text-sm"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Rafraîchir
          </button>
          <span className="text-sm text-[var(--color-text-muted)] ml-auto">
            {total} entrée{total !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      <div className="card overflow-hidden">
        {loading ? (
          <div className="p-6 text-center text-[var(--color-text-muted)]">Chargement…</div>
        ) : logs.length === 0 ? (
          <div className="p-6 text-center text-[var(--color-text-muted)]">Aucune activité enregistrée.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border-subtle)]">
                  <th className="text-left px-4 py-3 text-[var(--color-text-muted)] font-medium">Date</th>
                  <th className="text-left px-4 py-3 text-[var(--color-text-muted)] font-medium">Catégorie</th>
                  <th className="text-left px-4 py-3 text-[var(--color-text-muted)] font-medium">Action</th>
                  <th className="text-left px-4 py-3 text-[var(--color-text-muted)] font-medium">Utilisateur</th>
                  <th className="text-left px-4 py-3 text-[var(--color-text-muted)] font-medium">Détails</th>
                  <th className="text-left px-4 py-3 text-[var(--color-text-muted)] font-medium">IP</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border-subtle)]">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-[var(--color-bg-elevated)] transition-colors">
                    <td className="px-4 py-3 text-[var(--color-text-secondary)] whitespace-nowrap">
                      {formatTimestamp(log.timestamp)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                          CATEGORY_COLORS[log.category] || 'bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]'
                        }`}
                      >
                        {log.category}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-[var(--color-text-primary)] font-mono text-xs">
                      {log.action}
                    </td>
                    <td className="px-4 py-3 text-[var(--color-text-secondary)]">
                      {log.username || '—'}
                    </td>
                    <td className="px-4 py-3 text-[var(--color-text-muted)] text-xs max-w-xs truncate">
                      {log.details ? JSON.stringify(log.details) : '—'}
                    </td>
                    <td className="px-4 py-3 text-[var(--color-text-muted)] font-mono text-xs">
                      {log.ip_address || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {totalPages > 1 && (
        <div className="flex justify-center items-center gap-2 mt-4">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setPage(page - 1)}
            className="btn btn-secondary text-sm disabled:opacity-50"
          >
            Précédent
          </button>
          <span className="text-sm text-[var(--color-text-muted)]">
            Page {page} / {totalPages}
          </span>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => setPage(page + 1)}
            className="btn btn-secondary text-sm disabled:opacity-50"
          >
            Suivant
          </button>
        </div>
      )}
    </div>
  );
}

function AppLogsTab() {
  const [data, setData] = useState<AppLogsResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchAppLogs(500);
      setData(result);
    } catch {
      // silently handled
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const getLineColor = (line: string): string => {
    if (line.includes('"ERROR"') || line.includes('"level": "ERROR"')) return 'text-red-400';
    if (line.includes('"WARNING"') || line.includes('"level": "WARNING"')) return 'text-yellow-400';
    if (line.includes('"DEBUG"') || line.includes('"level": "DEBUG"')) return 'text-[var(--color-text-muted)]';
    return 'text-[var(--color-text-secondary)]';
  };

  return (
    <div>
      <div className="card mb-4">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={load}
            className="btn btn-secondary flex items-center gap-1 text-sm"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Rafraîchir
          </button>
          {data && (
            <span className="text-sm text-[var(--color-text-muted)]">
              {data.total_lines} lignes au total — affichage des {data.lines.length} dernières
            </span>
          )}
        </div>
      </div>

      <div className="card overflow-hidden">
        {loading ? (
          <div className="p-6 text-center text-[var(--color-text-muted)]">Chargement…</div>
        ) : !data || data.lines.length === 0 ? (
          <div className="p-6 text-center text-[var(--color-text-muted)]">Aucun log disponible.</div>
        ) : (
          <pre className="p-4 text-xs leading-5 overflow-x-auto max-h-[600px] overflow-y-auto">
            {data.lines.map((line, i) => (
              <div key={i} className={getLineColor(line)}>
                {line}
              </div>
            ))}
          </pre>
        )}
      </div>
    </div>
  );
}

export default LogsPanel;
