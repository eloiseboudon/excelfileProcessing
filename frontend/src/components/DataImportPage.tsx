import { useState } from 'react';
import FormattingPage from './FormattingPage';
import ProcessingPage from './ProcessingPage';
import SupplierApiSyncPanel from './SupplierApiSyncPanel';

type UpdateStep = 'processing' | 'formatting';

function DataImportPage() {
  const [updateStep, setUpdateStep] = useState<UpdateStep>('processing');
  // Temporary flag to hide the legacy "Calculs et traitements" workflow while preserving the code.
  const showUpdateWorkflow = false;

  return (
    <div className="flex-1 flex flex-col">
      <div className="flex-1 overflow-y-auto">
        <SupplierApiSyncPanel />
        {showUpdateWorkflow && (
          <div className="mt-6">
            {updateStep === 'processing' ? (
              <ProcessingPage onNext={() => setUpdateStep('formatting')} />
            ) : (
              <FormattingPage onBack={() => setUpdateStep('processing')} />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default DataImportPage;
