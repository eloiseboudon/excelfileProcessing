import { RefreshCw } from 'lucide-react';
import { useState } from 'react';
import MatchingPanel from './MatchingPanel';
import OdooSyncPanel from './OdooSyncPanel';
import SupplierApiSyncPanel from './SupplierApiSyncPanel';
import SupplierApiReports from './SupplierApiReports';

type ImportTab = 'sync' | 'report' | 'odoo' | 'matching';

function DataImportPage() {
  const [activeTab, setActiveTab] = useState<ImportTab>('odoo');

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-semibold text-[var(--color-text-heading)] flex items-center gap-3">
          <RefreshCw className="w-8 h-8 text-[#B8860B]" />
          Synchronisation
        </h1>
        <p className="text-[var(--color-text-muted)] mt-1">
          Synchronisez les données fournisseurs et consultez les rapports.
        </p>
      </div>
      <div className="border-b border-[var(--color-border-subtle)] mb-6">
        <nav className="flex gap-4" aria-label="Import navigation">
          {/* Onglets Synchronisation et Rapports masqués temporairement */}
          <button
            type="button"
            onClick={() => setActiveTab('odoo')}
            className={`px-2 pb-3 text-sm font-medium transition-colors border-b-2 ${
              activeTab === 'odoo'
                ? 'border-[#B8860B] text-[var(--color-text-heading)]'
                : 'border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
            }`}
          >
            Odoo
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('matching')}
            className={`px-2 pb-3 text-sm font-medium transition-colors border-b-2 ${
              activeTab === 'matching'
                ? 'border-[#B8860B] text-[var(--color-text-heading)]'
                : 'border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
            }`}
          >
            Rapprochement
          </button>
        </nav>
      </div>
      {activeTab === 'sync' && <SupplierApiSyncPanel />}
      {activeTab === 'report' && <SupplierApiReports />}
      {activeTab === 'odoo' && <OdooSyncPanel />}
      {activeTab === 'matching' && <MatchingPanel />}
    </div>
  );
}

export default DataImportPage;
