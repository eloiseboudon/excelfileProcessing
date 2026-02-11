interface ProductEditModalProps {
  selectedCount: number;
  bulkMarginValue: string;
  setBulkMarginValue: (value: string) => void;
  closeBulkMarginModal: () => void;
  applyBulkMargin: () => void;
}

function ProductEditModal({
  selectedCount,
  bulkMarginValue,
  setBulkMarginValue,
  closeBulkMarginModal,
  applyBulkMargin,
}: ProductEditModalProps) {
  return (
    <div className="fixed inset-0 z-20 flex items-center justify-center bg-[var(--color-bg-overlay)] px-4">
      <div className="w-full max-w-sm rounded-lg border border-[var(--color-border-default)] bg-[var(--color-bg-surface)] p-6 shadow-xl">
        <h2 className="text-lg font-semibold mb-2">Mise à jour de la marge</h2>
        <p className="text-sm text-[var(--color-text-secondary)] mb-4">
          Appliquer une marge unique à {selectedCount}{' '}
          produit{selectedCount === 1 ? '' : 's'} sélectionné{selectedCount === 1 ? '' : 's'}.
        </p>
        <label htmlFor="bulkMarginInput" className="block text-sm mb-2">
          Nouvelle marge
        </label>
        <input
          id="bulkMarginInput"
          type="number"
          step="0.01"
          value={bulkMarginValue}
          onChange={(e) => setBulkMarginValue(e.target.value)}
          className="w-full rounded border border-[var(--color-border-strong)] bg-[var(--color-bg-elevated)] px-3 py-2"
          autoFocus
        />
        <div className="mt-6 flex justify-end gap-2">
          <button className="btn btn-secondary" onClick={closeBulkMarginModal}>
            Annuler
          </button>
          <button className="btn btn-primary" onClick={applyBulkMargin}>
            Appliquer
          </button>
        </div>
      </div>
    </div>
  );
}

export default ProductEditModal;
