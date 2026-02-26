import { useState } from 'react';
import { X } from 'lucide-react';

export type MarginUnit = '€' | '%';

interface BulkMarginModalProps {
  count: number;
  onConfirm: (value: number, unit: MarginUnit) => void;
  onClose: () => void;
}

function BulkMarginModal({ count, onConfirm, onClose }: BulkMarginModalProps) {
  const [marginInput, setMarginInput] = useState('');
  const [unit, setUnit] = useState<MarginUnit>('€');

  const parsedValue = parseFloat(marginInput.replace(',', '.'));
  const isValid = !isNaN(parsedValue) && parsedValue >= 0;

  const handleSubmit = () => {
    if (!isValid) return;
    onConfirm(parsedValue, unit);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="card w-full max-w-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-[var(--color-text-heading)]">
            Maj des marges — {count} produit{count > 1 ? 's' : ''}
          </h2>
          <button
            onClick={onClose}
            className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="mb-4">
          <span className="block text-sm text-[var(--color-text-muted)] mb-2">Unité</span>
          <div className="flex rounded-md overflow-hidden border border-[var(--color-border-strong)] w-fit">
            {(['€', '%'] as MarginUnit[]).map((u) => (
              <button
                key={u}
                type="button"
                onClick={() => setUnit(u)}
                className={`px-4 py-1.5 text-sm font-medium transition-colors ${
                  unit === u
                    ? 'bg-[#B8860B] text-white'
                    : 'bg-[var(--color-bg-surface)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'
                }`}
              >
                {u}
              </button>
            ))}
          </div>
        </div>

        <div className="mb-5">
          <label className="block text-sm text-[var(--color-text-muted)] mb-1">
            Nouvelle marge ({unit})
          </label>
          <div className="relative">
            <input
              type="number"
              min="0"
              step="0.01"
              value={marginInput}
              onChange={(e) => setMarginInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
              placeholder={unit === '%' ? 'Ex : 15' : 'Ex : 20'}
              className="w-full px-3 py-2 pr-8 bg-[var(--color-bg-surface)] border border-[var(--color-border-strong)] rounded-md text-sm"
              autoFocus
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-[var(--color-text-muted)] pointer-events-none">
              {unit}
            </span>
          </div>
        </div>

        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="btn btn-secondary text-sm">
            Annuler
          </button>
          <button
            onClick={handleSubmit}
            disabled={!isValid}
            className="btn btn-primary text-sm"
          >
            OK
          </button>
        </div>
      </div>
    </div>
  );
}

export default BulkMarginModal;
