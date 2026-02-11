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
    <div className="flex justify-between mb-4">
      <div className="flex space-x-2">
        <div className="relative">
          <button
            onClick={onToggleColumnMenu}
            className="px-4 py-2 bg-zinc-800 text-white rounded-lg hover:bg-zinc-700"
          >
            Colonnes
          </button>
          {showColumnMenu && (
            <div className="absolute z-10 mt-2 p-4 bg-zinc-900 border border-zinc-700 rounded shadow-xl grid grid-cols-2 gap-2">
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
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Ajouter
        </button>
      </div>
      <div className="flex space-x-2">
        {selectedCount > 0 && (
          <button
            onClick={onBulkDelete}
            disabled={isBulkDeleting}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Supprimer produit(s)
          </button>
        )}
        <button
          onClick={onSave}
          disabled={!hasEdits}
          className="px-4 py-2 bg-green-600 text-white rounded disabled:opacity-50 hover:bg-green-700"
        >
          Enregistrer
        </button>
      </div>
    </div>
  );
}

export default ProductReferenceForm;
