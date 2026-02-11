import { Trash2 } from 'lucide-react';
import MultiSelectFilter from './MultiSelectFilter';
import type { ProductItem, Column } from './ProductReference';

interface FilterOptions {
  brandOptions: string[];
  colorOptions: string[];
  memoryOptions: string[];
  typeOptions: string[];
  ramOptions: string[];
  normeOptions: string[];
}

interface ReferenceData {
  brands: any[];
  colors: any[];
  memories: any[];
  types: any[];
  rams: any[];
  normes: any[];
}

interface ProductReferenceTableProps {
  columns: Column[];
  visibleColumns: string[];
  paginatedData: ProductItem[];
  filters: Record<string, string | string[]>;
  onFilterChange: (filters: Record<string, string | string[]>) => void;
  filterOptions: FilterOptions;
  referenceData: ReferenceData;
  selectedProducts: number[];
  onToggleSelectProduct: (id: number) => void;
  onChange: (id: number, field: keyof ProductItem, value: string | number | null) => void;
  onDelete: (id: number) => void;
  currentPage: number;
  totalPages: number;
  rowsPerPage: number;
  onPageChange: (page: number) => void;
  onRowsPerPageChange: (rowsPerPage: number) => void;
}

function ProductReferenceTable({
  columns,
  visibleColumns,
  paginatedData,
  filters,
  onFilterChange,
  filterOptions,
  referenceData,
  selectedProducts,
  onToggleSelectProduct,
  onChange,
  onDelete,
  currentPage,
  totalPages,
  rowsPerPage,
  onPageChange,
  onRowsPerPageChange,
}: ProductReferenceTableProps) {
  const { brandOptions, colorOptions, memoryOptions, typeOptions, ramOptions, normeOptions } =
    filterOptions;
  const { brands, colors, memories, types, rams, normes } = referenceData;

  const getFilterOptions = (key: string): string[] => {
    switch (key) {
      case 'brand':
        return brandOptions;
      case 'memory':
        return memoryOptions;
      case 'color':
        return colorOptions;
      case 'type':
        return typeOptions;
      case 'ram':
        return ramOptions;
      case 'norme':
        return normeOptions;
      default:
        return [];
    }
  };

  const paginationControls = (
    <div className="flex items-center justify-between">
      <div className="flex items-center space-x-2">
        <button
          onClick={() => onPageChange(Math.max(1, currentPage - 1))}
          disabled={currentPage === 1}
          className="px-3 py-1 bg-zinc-800 rounded disabled:opacity-50"
        >
          Précédent
        </button>
        <span>
          Page {currentPage} / {totalPages}
        </span>
        <button
          onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
          disabled={currentPage === totalPages}
          className="px-3 py-1 bg-zinc-800 rounded disabled:opacity-50"
        >
          Suivant
        </button>
      </div>
      <div className="flex items-center space-x-2">
        <label htmlFor="rowsPerPage" className="text-sm">
          Lignes par page:
        </label>
        <select
          id="rowsPerPage"
          value={rowsPerPage}
          onChange={(e) => onRowsPerPageChange(Number(e.target.value))}
          className="bg-zinc-900 border border-zinc-600 rounded px-2 py-1"
        >
          <option value={10}>10</option>
          <option value={20}>20</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
        </select>
      </div>
    </div>
  );

  const renderCellContent = (row: ProductItem, colKey: string) => {
    switch (colKey) {
      case 'brand':
        return (
          <select
            value={row.brand_id ?? ''}
            onChange={(e) =>
              onChange(row.id, 'brand_id', e.target.value === '' ? null : Number(e.target.value))
            }
            className="px-2 py-1 bg-zinc-700 rounded"
          >
            <option value="">null</option>
            {brands.map((b) => (
              <option key={b.id} value={b.id}>
                {b.brand}
              </option>
            ))}
          </select>
        );
      case 'memory':
        return (
          <select
            value={row.memory_id ?? ''}
            onChange={(e) =>
              onChange(row.id, 'memory_id', e.target.value === '' ? null : Number(e.target.value))
            }
            className="px-2 py-1 bg-zinc-700 rounded"
          >
            <option value="">null</option>
            {memories.map((m) => (
              <option key={m.id} value={m.id}>
                {m.memory}
              </option>
            ))}
          </select>
        );
      case 'color':
        return (
          <select
            value={row.color_id ?? ''}
            onChange={(e) =>
              onChange(row.id, 'color_id', e.target.value === '' ? null : Number(e.target.value))
            }
            className="px-2 py-1 bg-zinc-700 rounded"
          >
            <option value="">null</option>
            {colors.map((c) => (
              <option key={c.id} value={c.id}>
                {c.color}
              </option>
            ))}
          </select>
        );
      case 'type':
        return (
          <select
            value={row.type_id ?? ''}
            onChange={(e) =>
              onChange(row.id, 'type_id', e.target.value === '' ? null : Number(e.target.value))
            }
            className="px-2 py-1 bg-zinc-700 rounded"
          >
            <option value="">null</option>
            {types.map((t) => (
              <option key={t.id} value={t.id}>
                {t.type}
              </option>
            ))}
          </select>
        );
      case 'ram':
        return (
          <select
            value={row.ram_id ?? ''}
            onChange={(e) =>
              onChange(row.id, 'ram_id', e.target.value === '' ? null : Number(e.target.value))
            }
            className="px-2 py-1 bg-zinc-700 rounded"
          >
            <option value="">null</option>
            {rams.map((r) => (
              <option key={r.id} value={r.id}>
                {r.ram}
              </option>
            ))}
          </select>
        );
      case 'norme':
        return (
          <select
            value={row.norme_id ?? ''}
            onChange={(e) =>
              onChange(row.id, 'norme_id', e.target.value === '' ? null : Number(e.target.value))
            }
            className="px-2 py-1 bg-zinc-700 rounded"
          >
            <option value="">null</option>
            {normes.map((n) => (
              <option key={n.id} value={n.id}>
                {n.norme}
              </option>
            ))}
          </select>
        );
      case 'model':
        return (
          <input
            value={row.model}
            onChange={(e) => onChange(row.id, 'model', e.target.value)}
            className="w-full px-2 py-1 bg-zinc-700 rounded"
          />
        );
      case 'description':
        return (
          <input
            value={row.description}
            onChange={(e) => onChange(row.id, 'description', e.target.value)}
            className="w-full px-2 py-1 bg-zinc-700 rounded"
          />
        );
      case 'ean':
        return (
          <input
            value={row.ean ?? ''}
            onChange={(e) => onChange(row.id, 'ean', e.target.value)}
            className="w-full px-2 py-1 bg-zinc-700 rounded"
          />
        );
      default:
        return String((row as any)[colKey] ?? '');
    }
  };

  return (
    <>
      {paginationControls}
      <div className="overflow-auto mt-4">
        <table className="min-w-full text-sm text-left border border-zinc-700">
          <thead>
            <tr className="bg-zinc-800">
              <th className="px-3 py-2 border-b border-zinc-700 w-12" />
              {columns.map(
                (col) =>
                  visibleColumns.includes(col.key) && (
                    <th key={col.key} className="px-3 py-2 border-b border-zinc-700">
                      {col.label}
                    </th>
                  )
              )}
              <th className="px-3 py-2 border-b border-zinc-700 w-20 text-center">
                Actions
              </th>
            </tr>
            <tr>
              <th className="px-3 py-1 border-b border-zinc-700" />
              {columns.map(
                (col) =>
                  visibleColumns.includes(col.key) && (
                    <th key={col.key} className="px-3 py-1 border-b border-zinc-700">
                      {['brand', 'memory', 'color', 'type', 'ram', 'norme'].includes(col.key) ? (
                        <MultiSelectFilter
                          options={getFilterOptions(col.key)}
                          selected={(filters[col.key] as string[]) || []}
                          onChange={(selected) =>
                            onFilterChange({ ...filters, [col.key]: selected })
                          }
                        />
                      ) : (
                        <input
                          type="text"
                          value={(filters[col.key] as string) || ''}
                          onChange={(e) =>
                            onFilterChange({ ...filters, [col.key]: e.target.value })
                          }
                          className="w-full px-2 py-1 bg-zinc-900 border border-zinc-600 rounded"
                        />
                      )}
                    </th>
                  )
              )}
              <th className="px-3 py-1 border-b border-zinc-700" />
            </tr>
          </thead>
          <tbody>
            {paginatedData.map((row) => (
              <tr key={String(row.id)} className="odd:bg-zinc-900 even:bg-zinc-800">
                <td className="px-3 py-1 border-b border-zinc-700">
                  <input
                    type="checkbox"
                    checked={selectedProducts.includes(row.id)}
                    onChange={() => onToggleSelectProduct(row.id)}
                    className="rounded"
                  />
                </td>
                {columns.map(
                  (col) =>
                    visibleColumns.includes(col.key) && (
                      <td key={col.key} className="px-3 py-1 border-b border-zinc-700">
                        {renderCellContent(row, col.key)}
                      </td>
                    )
                )}
                <td className="px-3 py-1 border-b border-zinc-700 text-center">
                  <button
                    onClick={() => onDelete(row.id)}
                    className="inline-flex items-center justify-center w-8 h-8 rounded bg-red-600 text-white hover:bg-red-700"
                    title="Supprimer"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-4">{paginationControls}</div>
    </>
  );
}

export default ProductReferenceTable;
