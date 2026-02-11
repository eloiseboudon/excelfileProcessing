import { RefreshCw } from 'lucide-react';
import { useState } from 'react';
import SupplierApiSyncPanel from './SupplierApiSyncPanel';
import SupplierApiReports from './SupplierApiReports';

type ImportTab = 'sync' | 'report';

function DataImportPage() {
  const [activeTab, setActiveTab] = useState<ImportTab>('sync');

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold text-[var(--color-text-heading)] flex items-center gap-3">
          <RefreshCw className="w-8 h-8 text-[#B8860B]" />
          Synchronisation
        </h1>
        <p className="text-[var(--color-text-muted)] mt-1">
          Synchronisez les données fournisseurs et consultez les rapports.
        </p>
      </div>
      <div className="border-b border-[var(--color-border-subtle)]/60 mb-6">
        <nav className="flex gap-4" aria-label="Import navigation">
          <button
            type="button"
            onClick={() => setActiveTab('sync')}
            className={`px-2 pb-3 text-sm font-medium transition-colors border-b-2 ${
              activeTab === 'sync'
                ? 'border-[#B8860B] text-[var(--color-text-heading)]'
                : 'border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
            }`}
          >
            Synchronisation
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('report')}
            className={`px-2 pb-3 text-sm font-medium transition-colors border-b-2 ${
              activeTab === 'report'
                ? 'border-[#B8860B] text-[var(--color-text-heading)]'
                : 'border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
            }`}
          >
            Rapports
          </button>
        </nav>
      </div>
      {activeTab === 'sync' ? <SupplierApiSyncPanel /> : <SupplierApiReports />}
    </div>
  );
}

export default DataImportPage;
