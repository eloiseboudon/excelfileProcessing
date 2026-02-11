import { ChevronLeft, ChevronRight, Trash2 } from 'lucide-react';
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
  filteredCount: number;
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
  filteredCount,
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
      <span className="text-sm text-[var(--color-text-muted)]">
        {filteredCount} résultat{filteredCount === 1 ? '' : 's'}
      </span>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1">
          <span className="text-sm text-[var(--color-text-secondary)] mr-1">Lignes</span>
          <select
            id="refRowsPerPage"
            value={rowsPerPage}
            onChange={(e) => onRowsPerPageChange(Number(e.target.value))}
            className="bg-[var(--color-bg-surface)] text-[var(--color-text-primary)] border border-[var(--color-border-strong)] rounded px-2 py-1 text-sm"
          >
            <option value={10}>10</option>
            <option value={20}>20</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>
        <span className="text-sm text-[var(--color-text-secondary)]">
          {currentPage} / {totalPages}
        </span>
        <div className="flex items-center">
          <button
            onClick={() => onPageChange(Math.max(1, currentPage - 1))}
            disabled={currentPage === 1}
            className="btn btn-secondary p-1.5 disabled:opacity-30"
            aria-label="Page précédente"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage === totalPages}
            className="btn btn-secondary p-1.5 disabled:opacity-30"
            aria-label="Page suivante"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
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
            className="px-2 py-1 bg-[var(--color-bg-input)] text-[var(--color-text-primary)] rounded"
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
            className="px-2 py-1 bg-[var(--color-bg-input)] text-[var(--color-text-primary)] rounded"
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
            className="px-2 py-1 bg-[var(--color-bg-input)] text-[var(--color-text-primary)] rounded"
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
            className="px-2 py-1 bg-[var(--color-bg-input)] text-[var(--color-text-primary)] rounded"
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
            className="px-2 py-1 bg-[var(--color-bg-input)] text-[var(--color-text-primary)] rounded"
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
            className="px-2 py-1 bg-[var(--color-bg-input)] text-[var(--color-text-primary)] rounded"
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
            className="w-full px-2 py-1 bg-[var(--color-bg-input)] text-[var(--color-text-primary)] rounded"
          />
        );
      case 'description':
        return (
          <input
            value={row.description}
            onChange={(e) => onChange(row.id, 'description', e.target.value)}
            className="w-full px-2 py-1 bg-[var(--color-bg-input)] text-[var(--color-text-primary)] rounded"
          />
        );
      case 'ean':
        return (
          <input
            value={row.ean ?? ''}
            onChange={(e) => onChange(row.id, 'ean', e.target.value)}
            className="w-full px-2 py-1 bg-[var(--color-bg-input)] text-[var(--color-text-primary)] rounded"
          />
        );
      default:
        return String((row as any)[colKey] ?? '');
    }
  };

  return (
    <div className="card overflow-hidden">
      <div className="overflow-auto">
        <table className="min-w-full text-sm text-left border-0">
          <thead>
            <tr className="bg-[var(--color-bg-elevated)]">
              <th className="px-3 py-2 border-b border-[var(--color-border-default)] w-12" />
              {columns.map(
                (col) =>
                  visibleColumns.includes(col.key) && (
                    <th key={col.key} className="px-3 py-2 border-b border-[var(--color-border-default)]">
                      {col.label}
                    </th>
                  )
              )}
              <th className="px-3 py-2 border-b border-[var(--color-border-default)] w-20 text-center">
                Actions
              </th>
            </tr>
            <tr>
              <th className="px-3 py-1 border-b border-[var(--color-border-default)]" />
              {columns.map(
                (col) =>
                  visibleColumns.includes(col.key) && (
                    <th key={col.key} className="px-3 py-1 border-b border-[var(--color-border-default)]">
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
                          className="w-full px-2 py-1 bg-[var(--color-bg-surface)] text-[var(--color-text-primary)] border border-[var(--color-border-strong)] rounded"
                        />
                      )}
                    </th>
                  )
              )}
              <th className="px-3 py-1 border-b border-[var(--color-border-default)]" />
            </tr>
          </thead>
          <tbody>
            {paginatedData.map((row) => (
              <tr key={String(row.id)} className="odd:bg-[var(--color-bg-surface)] even:bg-[var(--color-bg-elevated)]">
                <td className="px-3 py-1 border-b border-[var(--color-border-default)]">
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
                      <td key={col.key} className="px-3 py-1 border-b border-[var(--color-border-default)]">
                        {renderCellContent(row, col.key)}
                      </td>
                    )
                )}
                <td className="px-3 py-1 border-b border-[var(--color-border-default)] text-center">
                  <button
                    onClick={() => onDelete(row.id)}
                    className="btn btn-secondary p-1.5 text-red-500"
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
      <div className="px-4 py-3 border-t border-[var(--color-border-subtle)]">
        {paginationControls}
      </div>
    </div>
  );
}

export default ProductReferenceTable;
