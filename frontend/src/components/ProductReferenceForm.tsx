import type { Column } from './ProductReference';

interface ProductReferenceFormProps {
  columns: Column[];
  visibleColumns: string[];
  showColumnMenu: boolean;
  onToggleColumnMenu: () => void;
  onToggleColumn: (key: string) => void;
  onAdd: () => void;
  onSave: () => void;
  onBulkDelete: () => void;
  selectedCount: number;
  isBulkDeleting: boolean;
  hasEdits: boolean;
}

function ProductReferenceForm({
  columns,
  visibleColumns,
  showColumnMenu,
  onToggleColumnMenu,
  onToggleColumn,
  onAdd,
  onSave,
  onBulkDelete,
  selectedCount,
  isBulkDeleting,
  hasEdits,
}: ProductReferenceFormProps) {
  return (
    <div className="card p-4 mb-6 overflow-visible relative z-20">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <button
              onClick={onToggleColumnMenu}
              className="btn btn-secondary text-sm"
            >
              Colonnes
            </button>
            {showColumnMenu && (
              <div className="absolute z-50 mt-2 p-4 min-w-[10rem] bg-[var(--color-bg-input)] text-[var(--color-text-primary)] border border-[var(--color-border-strong)] rounded-md shadow-2xl flex flex-col gap-2">
                {columns.map((col) => (
                  <label key={col.key} className="flex items-center space-x-2 text-sm">
                    <input
                      type="checkbox"
                      checked={visibleColumns.includes(col.key)}
                      onChange={() => onToggleColumn(col.key)}
                      className="rounded"
                    />
                    <span>{col.label}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
          <button
            onClick={onAdd}
            className="btn btn-primary text-sm"
          >
            Ajouter
          </button>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {selectedCount > 0 && (
            <button
              onClick={onBulkDelete}
              disabled={isBulkDeleting}
              className="btn btn-secondary text-sm text-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Supprimer produit(s)
            </button>
          )}
          <button
            onClick={onSave}
            disabled={!hasEdits}
            className="btn btn-primary text-sm"
          >
            Enregistrer
          </button>
        </div>
      </div>
    </div>
  );
}

export default ProductReferenceForm;
