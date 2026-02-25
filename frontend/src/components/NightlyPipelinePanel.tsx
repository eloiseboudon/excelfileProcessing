import { CheckCircle, Clock, Loader2, Mail, Play, RefreshCw, Trash2, XCircle } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import {
  NightlyConfig,
  NightlyJob,
  NightlyRecipient,
  addNightlyRecipient,
  deleteNightlyRecipient,
  fetchNightlyConfig,
  fetchNightlyJobs,
  fetchNightlyRecipients,
  triggerNightly,
  updateNightlyConfig,
} from '../api';

function formatDuration(job: NightlyJob): string {
  if (!job.started_at || !job.finished_at) return '—';
  const ms = new Date(job.finished_at).getTime() - new Date(job.started_at).getTime();
  const secs = Math.floor(ms / 1000);
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    completed: 'bg-green-500/15 text-green-400 border border-green-500/30',
    failed: 'bg-red-500/15 text-red-400 border border-red-500/30',
    running: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/30',
  };
  const labels: Record<string, string> = {
    completed: 'Succès',
    failed: 'Échec',
    running: 'En cours',
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${styles[status] ?? 'bg-zinc-500/15 text-zinc-400'}`}>
      {labels[status] ?? status}
    </span>
  );
}

export default function NightlyPipelinePanel() {
  const [config, setConfig] = useState<NightlyConfig | null>(null);
  const [jobs, setJobs] = useState<NightlyJob[]>([]);
  const [recipients, setRecipients] = useState<NightlyRecipient[]>([]);
  const [loadingConfig, setLoadingConfig] = useState(true);
  const [savingConfig, setSavingConfig] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [pipelineResult, setPipelineResult] = useState<'success' | 'error' | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [newEmail, setNewEmail] = useState('');
  const [newName, setNewName] = useState('');
  const [addingRecipient, setAddingRecipient] = useState(false);
  const [recipientError, setRecipientError] = useState<string | null>(null);

  async function load() {
    try {
      const [cfg, j, r] = await Promise.all([
        fetchNightlyConfig(),
        fetchNightlyJobs(),
        fetchNightlyRecipients(),
      ]);
      setConfig(cfg);
      setJobs(j);
      setRecipients(r);
    } catch (e: unknown) {
      setConfigError(e instanceof Error ? e.message : 'Erreur de chargement');
    } finally {
      setLoadingConfig(false);
    }
  }

  useEffect(() => {
    load();
    return () => stopPolling();
  }, []);

  async function handleSaveConfig() {
    if (!config) return;
    setSavingConfig(true);
    setConfigError(null);
    try {
      const updated = await updateNightlyConfig({
        enabled: config.enabled,
        run_hour: config.run_hour,
        run_minute: config.run_minute,
      });
      setConfig(updated);
    } catch (e: unknown) {
      setConfigError(e instanceof Error ? e.message : 'Erreur de sauvegarde');
    } finally {
      setSavingConfig(false);
    }
  }

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  async function handleTrigger() {
    setTriggering(true);
    setPipelineResult(null);
    try {
      await triggerNightly();
      setPipelineRunning(true);

      pollRef.current = setInterval(async () => {
        try {
          const j = await fetchNightlyJobs();
          setJobs(j);
          const latest = j[0];
          if (latest && latest.status !== 'running') {
            stopPolling();
            setPipelineRunning(false);
            setPipelineResult(latest.status === 'completed' ? 'success' : 'error');
          }
        } catch {
          // silently ignore poll errors
        }
      }, 5000);
    } catch (e: unknown) {
      setPipelineResult('error');
      setConfigError(e instanceof Error ? e.message : 'Erreur lors du déclenchement');
    } finally {
      setTriggering(false);
    }
  }

  async function handleAddRecipient() {
    if (!newEmail.trim()) return;
    setAddingRecipient(true);
    setRecipientError(null);
    try {
      const r = await addNightlyRecipient({ email: newEmail.trim(), name: newName.trim() || undefined });
      setRecipients((prev) => [...prev, r]);
      setNewEmail('');
      setNewName('');
    } catch (e: unknown) {
      setRecipientError(e instanceof Error ? e.message : 'Erreur lors de l\'ajout');
    } finally {
      setAddingRecipient(false);
    }
  }

  async function handleDeleteRecipient(id: number) {
    try {
      await deleteNightlyRecipient(id);
      setRecipients((prev) => prev.filter((r) => r.id !== id));
    } catch (e: unknown) {
      setRecipientError(e instanceof Error ? e.message : 'Erreur lors de la suppression');
    }
  }

  if (loadingConfig) {
    return (
      <div className="flex items-center justify-center py-12 text-[var(--color-text-muted)]">
        <RefreshCw className="w-5 h-5 animate-spin mr-2" />
        Chargement…
      </div>
    );
  }

  const hours = Array.from({ length: 24 }, (_, i) => i);

  return (
    <div className="space-y-6">
      {/* Configuration */}
      <div className="card">
        <h2 className="text-lg font-semibold text-[var(--color-text-heading)] flex items-center gap-2 mb-4">
          <Clock className="w-5 h-5 text-[#B8860B]" />
          Configuration du pipeline nightly
        </h2>

        {configError && (
          <div className="mb-4 p-3 rounded-md bg-[var(--color-bg-elevated)] border border-red-500/30 text-red-400 text-sm">
            {configError}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-6">
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <div
              role="switch"
              aria-checked={config?.enabled ?? false}
              onClick={() => config && setConfig({ ...config, enabled: !config.enabled })}
              className={`relative inline-flex h-6 w-11 rounded-full transition-colors ${
                config?.enabled ? 'bg-[#B8860B]' : 'bg-zinc-600'
              }`}
            >
              <span
                className={`inline-block h-5 w-5 rounded-full bg-white shadow transform transition-transform mt-0.5 ${
                  config?.enabled ? 'translate-x-5' : 'translate-x-0.5'
                }`}
              />
            </div>
            <span className="text-sm text-[var(--color-text-secondary)]">
              Activer le pipeline automatique
            </span>
          </label>

          <div className="flex items-center gap-2">
            <span className="text-sm text-[var(--color-text-muted)]">Heure (UTC) :</span>
            <select
              value={config?.run_hour ?? 2}
              onChange={(e) =>
                config && setConfig({ ...config, run_hour: parseInt(e.target.value, 10) })
              }
              className="rounded-md border border-[var(--color-border-default)] bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)] px-2 py-1 text-sm"
            >
              {hours.map((h) => (
                <option key={h} value={h}>
                  {String(h).padStart(2, '0')}:00
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-4">
          <button
            type="button"
            onClick={handleSaveConfig}
            disabled={savingConfig}
            className="btn btn-primary"
          >
            {savingConfig ? 'Sauvegarde…' : 'Enregistrer'}
          </button>
        </div>
      </div>

      {/* Lancement manuel */}
      <div className="card">
        <h2 className="text-lg font-semibold text-[var(--color-text-heading)] flex items-center gap-2 mb-4">
          <Play className="w-5 h-5 text-[#B8860B]" />
          Lancement manuel
        </h2>
        <div className="space-y-3">
          <button
            type="button"
            onClick={handleTrigger}
            disabled={triggering || pipelineRunning}
            className="btn btn-primary flex items-center gap-2"
          >
            {triggering ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            {triggering ? 'Lancement…' : 'Lancer maintenant'}
          </button>

          {pipelineRunning && (
            <div className="flex items-center gap-2 p-3 rounded-md bg-[var(--color-bg-elevated)] border border-[var(--color-border-subtle)]">
              <Loader2 className="w-4 h-4 animate-spin text-[#B8860B] shrink-0" />
              <p className="text-sm text-[var(--color-text-primary)]">
                Pipeline en cours — Odoo sync, fournisseurs, matching… Les résultats apparaîtront dans l'historique.
              </p>
            </div>
          )}

          {pipelineResult === 'success' && (
            <div className="flex items-center gap-2 p-3 rounded-md bg-[var(--color-bg-elevated)] border border-green-500/30">
              <CheckCircle className="w-4 h-4 text-green-400 shrink-0" />
              <p className="text-sm text-green-400">Pipeline terminé avec succès.</p>
            </div>
          )}

          {pipelineResult === 'error' && (
            <div className="flex items-center gap-2 p-3 rounded-md bg-[var(--color-bg-elevated)] border border-red-500/30">
              <XCircle className="w-4 h-4 text-red-400 shrink-0" />
              <p className="text-sm text-red-400">Le pipeline a échoué — vérifiez l'historique.</p>
            </div>
          )}
        </div>
      </div>

      {/* Historique */}
      <div className="card overflow-hidden">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-[var(--color-text-heading)]">
            Historique des executions
          </h2>
          <button
            type="button"
            onClick={() => fetchNightlyJobs().then(setJobs).catch(() => null)}
            className="btn btn-secondary flex items-center gap-1 text-xs"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Actualiser
          </button>
        </div>

        {jobs.length === 0 ? (
          <p className="text-sm text-[var(--color-text-muted)] py-4">Aucune exécution enregistrée.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border-subtle)]">
                  <th className="text-left py-2 px-3 text-[var(--color-text-muted)] font-medium">Date</th>
                  <th className="text-left py-2 px-3 text-[var(--color-text-muted)] font-medium">Statut</th>
                  <th className="text-right py-2 px-3 text-[var(--color-text-muted)] font-medium">Odoo</th>
                  <th className="text-right py-2 px-3 text-[var(--color-text-muted)] font-medium">Fournis.</th>
                  <th className="text-right py-2 px-3 text-[var(--color-text-muted)] font-medium">Matching</th>
                  <th className="text-center py-2 px-3 text-[var(--color-text-muted)] font-medium">Email</th>
                  <th className="text-right py-2 px-3 text-[var(--color-text-muted)] font-medium">Durée</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border-subtle)]">
                {jobs.map((job) => (
                  <tr key={job.id} className="hover:bg-[var(--color-bg-elevated)] transition-colors">
                    <td className="py-2 px-3 text-[var(--color-text-secondary)]">
                      {formatDate(job.started_at)}
                    </td>
                    <td className="py-2 px-3">
                      <StatusBadge status={job.status} />
                      {job.error_message && (
                        <span
                          className="ml-2 text-xs text-red-400"
                          title={job.error_message}
                        >
                          (voir erreur)
                        </span>
                      )}
                    </td>
                    <td className="py-2 px-3 text-right text-[var(--color-text-secondary)]">
                      {job.odoo_synced ?? '—'}
                    </td>
                    <td className="py-2 px-3 text-right text-[var(--color-text-secondary)]">
                      {job.suppliers_synced ?? '—'}
                    </td>
                    <td className="py-2 px-3 text-right text-[var(--color-text-secondary)]">
                      {job.matching_submitted ?? '—'}
                    </td>
                    <td className="py-2 px-3 text-center">
                      {job.email_sent ? (
                        <span className="text-green-400 text-xs">Oui</span>
                      ) : (
                        <span className="text-[var(--color-text-muted)] text-xs">Non</span>
                      )}
                    </td>
                    <td className="py-2 px-3 text-right text-[var(--color-text-muted)]">
                      {formatDuration(job)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Destinataires email */}
      <div className="card">
        <h2 className="text-lg font-semibold text-[var(--color-text-heading)] flex items-center gap-2 mb-4">
          <Mail className="w-5 h-5 text-[#B8860B]" />
          Destinataires du rapport email
        </h2>

        {recipientError && (
          <div className="mb-3 p-3 rounded-md bg-[var(--color-bg-elevated)] border border-red-500/30 text-red-400 text-sm">
            {recipientError}
          </div>
        )}

        {recipients.length > 0 && (
          <div className="mb-4 divide-y divide-[var(--color-border-subtle)]">
            {recipients.map((r) => (
              <div key={r.id} className="flex items-center justify-between py-2">
                <div>
                  <span className="text-sm text-[var(--color-text-primary)]">{r.email}</span>
                  {r.name && (
                    <span className="ml-2 text-xs text-[var(--color-text-muted)]">{r.name}</span>
                  )}
                  {!r.active && (
                    <span className="ml-2 text-xs text-[var(--color-text-muted)]">(inactif)</span>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => handleDeleteRecipient(r.id)}
                  className="p-1 text-[var(--color-text-muted)] hover:text-red-400 transition-colors"
                  title="Supprimer"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          <input
            type="email"
            placeholder="Email *"
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
            className="flex-1 min-w-48 rounded-md border border-[var(--color-border-default)] bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)] px-3 py-1.5 text-sm placeholder:text-[var(--color-text-muted)]"
          />
          <input
            type="text"
            placeholder="Nom (optionnel)"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            className="flex-1 min-w-36 rounded-md border border-[var(--color-border-default)] bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)] px-3 py-1.5 text-sm placeholder:text-[var(--color-text-muted)]"
          />
          <button
            type="button"
            onClick={handleAddRecipient}
            disabled={addingRecipient || !newEmail.trim()}
            className="btn btn-primary"
          >
            {addingRecipient ? 'Ajout…' : 'Ajouter'}
          </button>
        </div>
      </div>
    </div>
  );
}
