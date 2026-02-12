import {
  CheckCircle,
  ChevronDown,
  ChevronRight,
  Clock,
  Database,
  Loader2,
  Play,
  Server,
  Settings,
  Wifi,
  XCircle,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import {
  fetchOdooConfig,
  fetchOdooSyncJob,
  fetchOdooSyncJobs,
  OdooConfigData,
  OdooSyncJobResponse,
  testOdooConnection,
  triggerOdooSync,
  updateOdooAutoSync,
  updateOdooConfig,
} from '../api';
import { useNotification } from './NotificationProvider';

const INTERVAL_OPTIONS = [
  { label: '15 min', value: 15 },
  { label: '1 heure', value: 60 },
  { label: '6 heures', value: 360 },
  { label: '12 heures', value: 720 },
  { label: '24 heures', value: 1440 },
];

function formatDuration(start: string | null, end: string | null): string {
  if (!start || !end) return '-';
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (ms < 1000) return `${ms}ms`;
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m}min ${rem}s`;
}

function formatDate(iso: string | null): string {
  if (!iso) return '-';
  return new Date(iso).toLocaleString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function OdooSyncPanel() {
  const notify = useNotification();

  // Config state
  const [config, setConfig] = useState<OdooConfigData | null>(null);
  const [form, setForm] = useState({ url: '', database: '', login: '', password: '' });
  const [saving, setSaving] = useState(false);

  // Test connection state
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ version: string; count: number } | null>(null);

  // Sync state
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<OdooSyncJobResponse | null>(null);

  // Auto-sync state
  const [autoEnabled, setAutoEnabled] = useState(false);
  const [autoInterval, setAutoInterval] = useState(1440);

  // Jobs history
  const [jobs, setJobs] = useState<OdooSyncJobResponse[]>([]);
  const [expandedJob, setExpandedJob] = useState<number | null>(null);
  const [jobDetail, setJobDetail] = useState<OdooSyncJobResponse | null>(null);

  // Load config on mount
  useEffect(() => {
    fetchOdooConfig()
      .then((data) => {
        setConfig(data);
        if (data.configured) {
          setForm({
            url: data.url || '',
            database: data.database || '',
            login: data.login || '',
            password: data.password || '',
          });
          setAutoEnabled(data.auto_sync_enabled || false);
          setAutoInterval(data.auto_sync_interval_minutes || 1440);
        }
      })
      .catch(() => setConfig({ configured: false }));
    loadJobs();
  }, []);

  const loadJobs = () => {
    fetchOdooSyncJobs(20)
      .then(setJobs)
      .catch(() => setJobs([]));
  };

  // Save config
  const handleSaveConfig = async () => {
    setSaving(true);
    try {
      await updateOdooConfig(form);
      notify('Configuration sauvegardée', 'success');
      setConfig({ ...config, configured: true, ...form });
      setTestResult(null);
    } catch (e: any) {
      notify(e.message || 'Erreur de sauvegarde', 'error');
    } finally {
      setSaving(false);
    }
  };

  // Test connection
  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await testOdooConnection();
      setTestResult({ version: result.server_version, count: result.product_count });
      notify('Connexion réussie', 'success');
    } catch (e: any) {
      notify(e.message || 'Échec de la connexion', 'error');
    } finally {
      setTesting(false);
    }
  };

  // Trigger sync
  const handleSync = async () => {
    setSyncing(true);
    setSyncResult(null);
    try {
      const { job_id } = await triggerOdooSync();
      notify('Synchronisation lancée', 'success');

      // Poll for completion
      const poll = async () => {
        try {
          const detail = await fetchOdooSyncJob(job_id);
          if (detail.status === 'running') {
            setTimeout(poll, 3000);
          } else {
            setSyncResult(detail);
            setSyncing(false);
            loadJobs();
            if (detail.status === 'success') {
              notify(
                `Synchronisation terminée : ${detail.created_count} créés, ${detail.updated_count} mis à jour`,
                'success'
              );
            } else {
              notify(detail.error_message || 'Synchronisation échouée', 'error');
            }
          }
        } catch {
          setSyncing(false);
        }
      };
      setTimeout(poll, 3000);
    } catch (e: any) {
      notify(e.message || 'Erreur de synchronisation', 'error');
      setSyncing(false);
    }
  };

  // Auto-sync toggle
  const handleAutoSyncToggle = async () => {
    const newEnabled = !autoEnabled;
    try {
      await updateOdooAutoSync({ enabled: newEnabled, interval_minutes: autoInterval });
      setAutoEnabled(newEnabled);
      notify(
        newEnabled ? 'Synchronisation automatique activée' : 'Synchronisation automatique désactivée',
        'success'
      );
    } catch (e: any) {
      notify(e.message || 'Erreur', 'error');
    }
  };

  const handleIntervalChange = async (minutes: number) => {
    setAutoInterval(minutes);
    if (autoEnabled) {
      try {
        await updateOdooAutoSync({ interval_minutes: minutes });
      } catch (e: any) {
        notify(e.message || 'Erreur', 'error');
      }
    }
  };

  // Expand job detail
  const handleToggleJob = async (jobId: number) => {
    if (expandedJob === jobId) {
      setExpandedJob(null);
      setJobDetail(null);
      return;
    }
    setExpandedJob(jobId);
    try {
      const detail = await fetchOdooSyncJob(jobId);
      setJobDetail(detail);
    } catch {
      setJobDetail(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Section 1: Configuration */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <Settings className="w-5 h-5 text-[#B8860B]" />
          <h2 className="text-lg font-semibold text-[var(--color-text-heading)]">
            Configuration Odoo
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1">
              URL Odoo
            </label>
            <input
              type="url"
              className="w-full px-3 py-2 rounded-md border border-[var(--color-border-default)] bg-[var(--color-bg-input)] text-[var(--color-text-primary)] text-sm"
              placeholder="https://odoo.monentreprise.fr"
              value={form.url}
              onChange={(e) => setForm({ ...form, url: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1">
              Base de données
            </label>
            <input
              type="text"
              className="w-full px-3 py-2 rounded-md border border-[var(--color-border-default)] bg-[var(--color-bg-input)] text-[var(--color-text-primary)] text-sm"
              placeholder="nom_base"
              value={form.database}
              onChange={(e) => setForm({ ...form, database: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1">
              Identifiant
            </label>
            <input
              type="text"
              className="w-full px-3 py-2 rounded-md border border-[var(--color-border-default)] bg-[var(--color-bg-input)] text-[var(--color-text-primary)] text-sm"
              placeholder="admin"
              value={form.login}
              onChange={(e) => setForm({ ...form, login: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1">
              Mot de passe
            </label>
            <input
              type="password"
              className="w-full px-3 py-2 rounded-md border border-[var(--color-border-default)] bg-[var(--color-bg-input)] text-[var(--color-text-primary)] text-sm"
              placeholder="••••••••"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 mt-4">
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleSaveConfig}
            disabled={saving || !form.url || !form.database || !form.login}
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
            Enregistrer
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleTest}
            disabled={testing || !config?.configured}
          >
            {testing ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Wifi className="w-4 h-4 mr-2" />}
            Tester la connexion
          </button>
        </div>

        {testResult && (
          <div className="mt-3 flex items-center gap-3 text-sm text-[var(--color-text-secondary)]">
            <CheckCircle className="w-4 h-4 text-green-500" />
            <span>
              Serveur Odoo <strong>{testResult.version}</strong> — {testResult.count} produits actifs
            </span>
          </div>
        )}

        {/* Auto-sync settings */}
        {config?.configured && (
          <div className="mt-5 pt-4 border-t border-[var(--color-border-subtle)]">
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoEnabled}
                  onChange={handleAutoSyncToggle}
                  className="w-4 h-4 rounded accent-[#B8860B]"
                />
                <span className="text-sm font-medium text-[var(--color-text-secondary)]">
                  Synchronisation automatique
                </span>
              </label>
              <select
                className="px-2 py-1 rounded-md border border-[var(--color-border-default)] bg-[var(--color-bg-input)] text-sm text-[var(--color-text-primary)]"
                value={autoInterval}
                onChange={(e) => handleIntervalChange(Number(e.target.value))}
                disabled={!autoEnabled}
              >
                {INTERVAL_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Section 2: Trigger Sync */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <Database className="w-5 h-5 text-[#B8860B]" />
          <h2 className="text-lg font-semibold text-[var(--color-text-heading)]">
            Synchronisation
          </h2>
        </div>

        <button
          type="button"
          className="btn btn-primary"
          onClick={handleSync}
          disabled={syncing || !config?.configured}
        >
          {syncing ? (
            <Loader2 className="w-4 h-4 animate-spin mr-2" />
          ) : (
            <Play className="w-4 h-4 mr-2" />
          )}
          {syncing ? 'Synchronisation en cours...' : 'Lancer la synchronisation Odoo'}
        </button>

        {syncResult && (
          <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="text-center p-3 rounded-lg bg-green-500/10">
              <div className="text-2xl font-bold text-green-500">{syncResult.created_count}</div>
              <div className="text-xs text-[var(--color-text-muted)]">Créés</div>
            </div>
            <div className="text-center p-3 rounded-lg bg-blue-500/10">
              <div className="text-2xl font-bold text-blue-400">{syncResult.updated_count}</div>
              <div className="text-xs text-[var(--color-text-muted)]">Mis à jour</div>
            </div>
            <div className="text-center p-3 rounded-lg bg-[var(--color-bg-elevated)]">
              <div className="text-2xl font-bold text-[var(--color-text-muted)]">{syncResult.unchanged_count}</div>
              <div className="text-xs text-[var(--color-text-muted)]">Inchangés</div>
            </div>
            <div className="text-center p-3 rounded-lg bg-red-500/10">
              <div className="text-2xl font-bold text-red-400">{syncResult.error_count}</div>
              <div className="text-xs text-[var(--color-text-muted)]">Erreurs</div>
            </div>
          </div>
        )}
      </div>

      {/* Section 3: Job History */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <Clock className="w-5 h-5 text-[#B8860B]" />
          <h2 className="text-lg font-semibold text-[var(--color-text-heading)]">
            Historique des synchronisations
          </h2>
        </div>

        {jobs.length === 0 ? (
          <p className="text-sm text-[var(--color-text-muted)]">
            Aucune synchronisation effectuée.
          </p>
        ) : (
          <div className="divide-y divide-[var(--color-border-subtle)]">
            {jobs.map((job) => (
              <div key={job.id}>
                <button
                  type="button"
                  className="w-full flex items-center justify-between py-3 text-left hover:bg-[var(--color-bg-elevated)] transition-colors px-2 rounded-md"
                  onClick={() => handleToggleJob(job.id)}
                >
                  <div className="flex items-center gap-3">
                    {job.status === 'success' ? (
                      <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0" />
                    ) : job.status === 'running' ? (
                      <Loader2 className="w-4 h-4 text-[#B8860B] animate-spin flex-shrink-0" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                    )}
                    <div>
                      <span className="text-sm text-[var(--color-text-primary)]">
                        {formatDate(job.started_at)}
                      </span>
                      <span className="text-xs text-[var(--color-text-muted)] ml-2">
                        ({job.trigger === 'auto' ? 'auto' : 'manuel'})
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 text-xs">
                      {job.status === 'success' && (
                        <>
                          <span className="text-green-500">{job.created_count} créés</span>
                          <span className="text-blue-400">{job.updated_count} MAJ</span>
                          <span className="text-[var(--color-text-muted)]">{job.unchanged_count} id.</span>
                          {job.error_count > 0 && (
                            <span className="text-red-400">{job.error_count} err.</span>
                          )}
                        </>
                      )}
                      {job.status === 'running' && (
                        <span className="text-[#B8860B]">En cours...</span>
                      )}
                      {job.status === 'failed' && (
                        <span className="text-red-400">Échec</span>
                      )}
                    </div>
                    <span className="text-xs text-[var(--color-text-muted)]">
                      {formatDuration(job.started_at, job.ended_at)}
                    </span>
                    {expandedJob === job.id ? (
                      <ChevronDown className="w-4 h-4 text-[var(--color-text-muted)]" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-[var(--color-text-muted)]" />
                    )}
                  </div>
                </button>

                {expandedJob === job.id && jobDetail && (
                  <div className="px-4 pb-4 space-y-3">
                    {jobDetail.error_message && (
                      <div className="p-2 rounded-md bg-[var(--color-bg-elevated)] border border-red-500/30 text-red-400 text-sm">
                        {jobDetail.error_message}
                      </div>
                    )}

                    <div className="text-xs text-[var(--color-text-muted)]">
                      Total produits Odoo : {jobDetail.total_odoo_products}
                    </div>

                    {jobDetail.report_created && jobDetail.report_created.length > 0 && (
                      <ReportSection
                        title="Produits créés"
                        items={jobDetail.report_created}
                        color="text-green-500"
                      />
                    )}
                    {jobDetail.report_updated && jobDetail.report_updated.length > 0 && (
                      <ReportSection
                        title="Produits mis à jour"
                        items={jobDetail.report_updated}
                        color="text-blue-400"
                      />
                    )}
                    {jobDetail.report_errors && jobDetail.report_errors.length > 0 && (
                      <ReportSection
                        title="Erreurs"
                        items={jobDetail.report_errors}
                        color="text-red-400"
                      />
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ReportSection({
  title,
  items,
  color,
}: {
  title: string;
  items: { odoo_id: string; name: string; ean?: string; error?: string }[];
  color: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button
        type="button"
        className={`text-xs font-medium ${color} flex items-center gap-1`}
        onClick={() => setOpen(!open)}
      >
        {open ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        {title} ({items.length})
      </button>
      {open && (
        <div className="mt-1 max-h-48 overflow-y-auto text-xs space-y-0.5">
          {items.map((item, i) => (
            <div key={i} className="flex gap-2 text-[var(--color-text-secondary)] py-0.5">
              <span className="text-[var(--color-text-muted)] w-12 flex-shrink-0">#{item.odoo_id}</span>
              <span className="truncate">{item.name}</span>
              {item.ean && <span className="text-[var(--color-text-muted)] flex-shrink-0">{item.ean}</span>}
              {item.error && <span className="text-red-400 flex-shrink-0">{item.error}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default OdooSyncPanel;
