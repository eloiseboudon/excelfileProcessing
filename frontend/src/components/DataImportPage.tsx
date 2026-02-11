import { useState } from 'react';
import SupplierApiSyncPanel from './SupplierApiSyncPanel';
import SupplierApiReports from './SupplierApiReports';

type ImportTab = 'sync' | 'report';

function DataImportPage() {
  const [activeTab, setActiveTab] = useState<ImportTab>('sync');

  return (
    <div className="flex-1 flex flex-col">
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-6">
          <div className="border-b border-zinc-800/60">
            <nav className="flex gap-4" aria-label="Import navigation">
              <button
                type="button"
                onClick={() => setActiveTab('sync')}
                className={`px-2 pb-3 text-sm font-medium transition-colors border-b-2 ${
                  activeTab === 'sync'
                    ? 'border-[#B8860B] text-zinc-100'
                    : 'border-transparent text-zinc-400 hover:text-zinc-200'
                }`}
              >
                Synchronisation
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('report')}
                className={`px-2 pb-3 text-sm font-medium transition-colors border-b-2 ${
                  activeTab === 'report'
                    ? 'border-[#B8860B] text-zinc-100'
                    : 'border-transparent text-zinc-400 hover:text-zinc-200'
                }`}
              >
                Rapports
              </button>
            </nav>
          </div>
        </div>
        {activeTab === 'sync' ? <SupplierApiSyncPanel /> : <SupplierApiReports />}
      </div>
    </div>
  );
}

export default DataImportPage;
