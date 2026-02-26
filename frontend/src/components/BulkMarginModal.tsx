import { useState } from 'react';
import { X } from 'lucide-react';

interface BulkMarginModalProps {
  count: number;
  onConfirm: (margin: number) => void;
  onClose: () => void;
}

function BulkMarginModal({ count, onConfirm, onClose }: BulkMarginModalProps) {
  const [marginInput, setMarginInput] = useState('');

  const parsedMargin = parseFloat(marginInput.replace(',', '.'));
  const isValid = !isNaN(parsedMargin) && parsedMargin >= 0;

  const handleSubmit = () => {
    if (!isValid) return;
    onConfirm(parsedMargin);
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
        <div className="mb-5">
          <label className="block text-sm text-[var(--color-text-muted)] mb-1">
            Nouvelle marge (€)
          </label>
          <input
            type="number"
            min="0"
            step="0.01"
            value={marginInput}
            onChange={(e) => setMarginInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
            placeholder="Ex : 15"
            className="w-full px-3 py-2 bg-[var(--color-bg-surface)] border border-[var(--color-border-strong)] rounded-md text-sm"
            autoFocus
          />
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
