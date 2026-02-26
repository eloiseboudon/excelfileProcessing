import { CheckCircle, ChevronDown, ChevronRight, Clock, Loader2, Mail, Play, RefreshCw, Trash2, XCircle } from 'lucide-react';
import { Fragment, useEffect, useRef, useState } from 'react';
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
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${styles[status] ?? 'bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]'}`}>
      {labels[status] ?? status}
    </span>
  );
}

/** Convert a UTC hour (0-23) to Europe/Paris local hour. */
function utcToParisHour(utcHour: number): number {
  const d = new Date();
  d.setUTCHours(utcHour, 0, 0, 0);
  const parts = new Intl.DateTimeFormat('fr-FR', {
    hour: 'numeric',
    hour12: false,
    timeZone: 'Europe/Paris',
  }).formatToParts(d);
  const hourPart = parts.find((p) => p.type === 'hour');
  return hourPart ? parseInt(hourPart.value, 10) : utcHour;
}

/** Convert a Europe/Paris local hour (0-23) to UTC hour. */
function parisHourToUtc(parisHour: number): number {
  const today = new Date();
  const formatter = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Europe/Paris',
    timeZoneName: 'shortOffset',
  });
  const parts = formatter.formatToParts(today);
  const tzPart = parts.find((p) => p.type === 'timeZoneName');
  const offsetMatch = tzPart?.value.match(/GMT([+-]\d+)/);
  const offsetHours = offsetMatch ? parseInt(offsetMatch[1], 10) : 0;
  return (parisHour - offsetHours + 24) % 24;
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
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
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
            <span className="text-sm text-[var(--color-text-muted)]">Heure (Paris) :</span>
            <select
              value={utcToParisHour(config?.run_hour ?? 2)}
              onChange={(e) =>
                config && setConfig({ ...config, run_hour: parisHourToUtc(parseInt(e.target.value, 10)) })
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
                {jobs.map((job) => {
                  const isSelected = selectedJobId === job.id;
                  const md = job.matching_detail;
                  return (
                    <Fragment key={job.id}>
                      <tr
                        className="hover:bg-[var(--color-bg-elevated)] transition-colors cursor-pointer"
                        onClick={() => setSelectedJobId(isSelected ? null : job.id)}
                      >
                        <td className="py-2 px-3 text-[var(--color-text-secondary)] flex items-center gap-1.5">
                          {isSelected ? (
                            <ChevronDown className="w-3.5 h-3.5 text-[#B8860B] shrink-0" />
                          ) : (
                            <ChevronRight className="w-3.5 h-3.5 text-[var(--color-text-muted)] shrink-0" />
                          )}
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
                      {isSelected && (
                        <tr>
                          <td colSpan={7} className="p-0">
                            <div className="bg-[var(--color-bg-elevated)] border-l-2 border-[#B8860B] px-5 py-4 space-y-4">
                              {/* Résumé pipeline */}
                              <div>
                                <h4 className="text-sm font-semibold text-[var(--color-text-heading)] mb-2">
                                  Résumé pipeline
                                </h4>
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                                  <div>
                                    <span className="text-[var(--color-text-muted)]">Produits Odoo sync.</span>
                                    <p className="text-[var(--color-text-primary)] font-medium">{job.odoo_synced ?? '—'}</p>
                                  </div>
                                  <div>
                                    <span className="text-[var(--color-text-muted)]">Fournisseurs traités</span>
                                    <p className="text-[var(--color-text-primary)] font-medium">{job.suppliers_synced ?? '—'}</p>
                                  </div>
                                  <div>
                                    <span className="text-[var(--color-text-muted)]">Labels soumis</span>
                                    <p className="text-[var(--color-text-primary)] font-medium">{job.matching_submitted ?? '—'}</p>
                                  </div>
                                  <div>
                                    <span className="text-[var(--color-text-muted)]">Durée totale</span>
                                    <p className="text-[var(--color-text-primary)] font-medium">{formatDuration(job)}</p>
                                  </div>
                                </div>
                                {job.error_message && (
                                  <div className="mt-3 p-2 rounded-md bg-[var(--color-bg-surface)] border border-red-500/30 text-red-400 text-xs">
                                    {job.error_message}
                                  </div>
                                )}
                              </div>

                              {/* Détail matching LLM */}
                              {md && (
                                <div>
                                  <h4 className="text-sm font-semibold text-[var(--color-text-heading)] mb-2">
                                    Détail matching LLM
                                  </h4>
                                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                                    <div>
                                      <span className="text-[var(--color-text-muted)]">Produits traités</span>
                                      <p className="text-[var(--color-text-primary)] font-medium">{md.total_products ?? '—'}</p>
                                    </div>
                                    <div>
                                      <span className="text-[var(--color-text-muted)]">Depuis le cache</span>
                                      <p className="text-[var(--color-text-primary)] font-medium">{md.from_cache ?? '—'}</p>
                                    </div>
                                    <div>
                                      <span className="text-[var(--color-text-muted)]">Appels LLM</span>
                                      <p className="text-[var(--color-text-primary)] font-medium">{md.llm_calls ?? '—'}</p>
                                    </div>
                                    <div>
                                      <span className="text-[var(--color-text-muted)]">Auto-matchés</span>
                                      <p className="text-green-400 font-medium">{md.auto_matched ?? '—'}</p>
                                    </div>
                                    <div>
                                      <span className="text-[var(--color-text-muted)]">À valider</span>
                                      <p className="text-yellow-400 font-medium">{md.pending_review ?? '—'}</p>
                                    </div>
                                    <div>
                                      <span className="text-[var(--color-text-muted)]">Rejetés auto</span>
                                      <p className="text-red-400 font-medium">{md.auto_rejected ?? '—'}</p>
                                    </div>
                                    <div>
                                      <span className="text-[var(--color-text-muted)]">Non trouvés</span>
                                      <p className="text-[var(--color-text-muted)] font-medium">{md.not_found ?? '—'}</p>
                                    </div>
                                    <div>
                                      <span className="text-[var(--color-text-muted)]">Erreurs</span>
                                      <p className={`font-medium ${md.errors ? 'text-red-400' : 'text-[var(--color-text-primary)]'}`}>{md.errors ?? '0'}</p>
                                    </div>
                                    <div>
                                      <span className="text-[var(--color-text-muted)]">Coût estimé</span>
                                      <p className="text-[var(--color-text-primary)] font-medium">
                                        {md.cost_estimate != null ? `$${md.cost_estimate.toFixed(4)}` : '—'}
                                      </p>
                                    </div>
                                    <div>
                                      <span className="text-[var(--color-text-muted)]">Durée matching</span>
                                      <p className="text-[var(--color-text-primary)] font-medium">
                                        {md.duration_seconds != null
                                          ? md.duration_seconds >= 60
                                            ? `${Math.floor(md.duration_seconds / 60)}m ${Math.floor(md.duration_seconds % 60)}s`
                                            : `${Math.floor(md.duration_seconds)}s`
                                          : '—'}
                                      </p>
                                    </div>
                                  </div>
                                </div>
                              )}

                              {!md && (
                                <p className="text-xs text-[var(--color-text-muted)] italic">
                                  Aucun détail de matching disponible pour cette exécution.
                                </p>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
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
