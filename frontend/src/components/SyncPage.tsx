import { RefreshCw } from 'lucide-react';
import { useState } from 'react';
import NightlyPipelinePanel from './NightlyPipelinePanel';
import OdooSyncPanel from './OdooSyncPanel';

type SyncTab = 'odoo' | 'pipeline';

const TABS: { key: SyncTab; label: string }[] = [
  { key: 'odoo', label: 'Odoo' },
  { key: 'pipeline', label: 'Pipeline nightly' },
];

function SyncPage() {
  const [tab, setTab] = useState<SyncTab>('odoo');

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-semibold text-[var(--color-text-heading)] flex items-center gap-3">
          <RefreshCw className="w-8 h-8 text-[#B8860B]" />
          Synchronisation
        </h1>
        <p className="text-[var(--color-text-muted)] mt-1">
          Synchronisez les données Odoo et configurez le pipeline automatique.
        </p>
      </div>
      <div className="border-b border-[var(--color-border-subtle)] mb-6">
        <nav className="flex gap-4">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key)}
              className={`px-2 pb-3 text-sm font-medium transition-colors border-b-2 ${
                tab === t.key
                  ? 'border-[#B8860B] text-[var(--color-text-heading)]'
                  : 'border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>
      {tab === 'odoo' && <OdooSyncPanel />}
      {tab === 'pipeline' && <NightlyPipelinePanel />}
    </div>
  );
}

export default SyncPage;
