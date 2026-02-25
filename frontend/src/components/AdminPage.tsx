import { Settings } from 'lucide-react';
import { useState } from 'react';
import LogsPanel from './LogsPanel';
import NightlyPipelinePanel from './NightlyPipelinePanel';
import ReferenceAdmin from './ReferenceAdmin';
import SupplierApiAdmin from './SupplierApiAdmin';
import TranslationAdmin from './TranslationAdmin';
import UserAdmin from './UserAdmin';

type AdminTab = 'references' | 'translations' | 'apis' | 'users' | 'logs' | 'automation';

const TABS: { key: AdminTab; label: string }[] = [
  { key: 'references', label: 'Tables référence' },
  { key: 'translations', label: 'Cohérence des tables' },
  { key: 'apis', label: 'API fournisseurs' },
  { key: 'users', label: 'Utilisateurs' },
  { key: 'logs', label: 'Logs' },
  { key: 'automation', label: 'Automatisation' },
];

function AdminPage() {
  const [tab, setTab] = useState<AdminTab>('references');

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-semibold text-[var(--color-text-heading)] flex items-center gap-3">
          <Settings className="w-8 h-8 text-[#B8860B]" />
          Administration
        </h1>
        <p className="text-[var(--color-text-muted)] mt-1">
          Gérez les tables de référence, la cohérence des données, les API fournisseurs et les utilisateurs.
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
      {tab === 'references' && (
        <ReferenceAdmin isVisible onClose={() => setTab('references')} />
      )}
      {tab === 'translations' && (
        <TranslationAdmin isVisible onClose={() => setTab('translations')} />
      )}
      {tab === 'apis' && (
        <SupplierApiAdmin isVisible onClose={() => setTab('apis')} />
      )}
      {tab === 'users' && (
        <UserAdmin isVisible onClose={() => setTab('users')} />
      )}
      {tab === 'logs' && <LogsPanel />}
      {tab === 'automation' && <NightlyPipelinePanel />}
    </div>
  );
}

export default AdminPage;
