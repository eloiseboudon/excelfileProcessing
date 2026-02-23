import { ChevronLeft, ChevronRight } from 'lucide-react';
import MultiSelectFilter from './MultiSelectFilter';
import type { ProductItem, Column } from './ProductReference';
import SortableColumnHeader from './SortableColumnHeader';
import type { SortConfig } from './SortableColumnHeader';

interface FilterOptions {
  brandOptions: string[];
  colorOptions: string[];
  memoryOptions: string[];
  typeOptions: string[];
  ramOptions: string[];
  normeOptions: string[];
}

interface ProductReferenceTableProps {
  columns: Column[];
  visibleColumns: string[];
  paginatedData: ProductItem[];
  filters: Record<string, string | string[]>;
  onFilterChange: (filters: Record<string, string | string[]>) => void;
  filterOptions: FilterOptions;
  filteredCount: number;
  currentPage: number;
  totalPages: number;
  rowsPerPage: number;
  onPageChange: (page: number) => void;
  onRowsPerPageChange: (rowsPerPage: number) => void;
  sortConfig: SortConfig;
  onSort: (column: string) => void;
}

function ProductReferenceTable({
  columns,
  visibleColumns,
  paginatedData,
  filters,
  onFilterChange,
  filterOptions,
  filteredCount,
  currentPage,
  totalPages,
  rowsPerPage,
  onPageChange,
  onRowsPerPageChange,
  sortConfig,
  onSort,
}: ProductReferenceTableProps) {
  const { brandOptions, colorOptions, memoryOptions, typeOptions, ramOptions, normeOptions } =
    filterOptions;

  const getFilterOptions = (key: string): string[] => {
    switch (key) {
      case 'brand': return brandOptions;
      case 'memory': return memoryOptions;
      case 'color': return colorOptions;
      case 'type': return typeOptions;
      case 'ram': return ramOptions;
      case 'norme': return normeOptions;
      default: return [];
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

  return (
    <div className="card overflow-hidden">
      <div className="overflow-auto">
        <table className="min-w-full text-sm text-left border-0">
          <thead>
            <tr className="bg-[var(--color-bg-elevated)]">
              {columns.map(
                (col) =>
                  visibleColumns.includes(col.key) && (
                    <th key={col.key} className="px-3 py-2 border-b border-[var(--color-border-default)]">
                      <SortableColumnHeader
                        label={col.label}
                        columnKey={col.key}
                        currentSort={sortConfig}
                        onSort={onSort}
                      />
                    </th>
                  )
              )}
            </tr>
            <tr>
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
            </tr>
          </thead>
          <tbody>
            {paginatedData.map((row) => (
              <tr key={String(row.id)} className="odd:bg-[var(--color-bg-surface)] even:bg-[var(--color-bg-elevated)] hover:bg-[var(--color-bg-elevated)]/80">
                {columns.map(
                  (col) =>
                    visibleColumns.includes(col.key) && (
                      <td key={col.key} className="px-3 py-1 border-b border-[var(--color-border-default)]">
                        {String((row as any)[col.key] ?? '')}
                      </td>
                    )
                )}
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
