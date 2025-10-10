import { useState } from 'react';
import FormattingPage from './FormattingPage';
import ProcessingPage from './ProcessingPage';
import StatisticsPage from './StatisticsPage';

type DataImportSection = 'update' | 'reports';
type UpdateStep = 'processing' | 'formatting';

function DataImportPage() {
  const [activeSection, setActiveSection] = useState<DataImportSection>('update');
  const [updateStep, setUpdateStep] = useState<UpdateStep>('processing');

  return (
    <div className="flex-1 flex flex-col">
      <div className="bg-black/40 border-b border-[#B8860B]/10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => setActiveSection('update')}
              className={`btn px-5 py-2 ${activeSection === 'update' ? 'btn-primary' : 'btn-secondary'}`}
            >
              Mise à jour des données
            </button>
            <button
              onClick={() => setActiveSection('reports')}
              className={`btn px-5 py-2 ${activeSection === 'reports' ? 'btn-primary' : 'btn-secondary'}`}
            >
              Rapports
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1">
        {activeSection === 'update' ? (
          updateStep === 'processing' ? (
            <ProcessingPage onNext={() => setUpdateStep('formatting')} />
          ) : (
            <FormattingPage onBack={() => setUpdateStep('processing')} />
          )
        ) : (
          <StatisticsPage />
        )}
      </div>
    </div>
  );
}

export default DataImportPage;
