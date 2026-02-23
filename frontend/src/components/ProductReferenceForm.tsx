import type { Column } from './ProductReference';

interface ProductReferenceFormProps {
  columns: Column[];
  visibleColumns: string[];
  showColumnMenu: boolean;
  onToggleColumnMenu: () => void;
  onToggleColumn: (key: string) => void;
}

function ProductReferenceForm({
  columns,
  visibleColumns,
  showColumnMenu,
  onToggleColumnMenu,
  onToggleColumn,
}: ProductReferenceFormProps) {
  return (
    <div className="card p-4 mb-6 overflow-visible relative z-20">
      <div className="relative inline-block">
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
    </div>
  );
}

export default ProductReferenceForm;
