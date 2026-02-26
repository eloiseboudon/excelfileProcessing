import type { AggregatedProduct } from './ProductsPage';
import ProductFilters from './ProductFilters';
import SortableColumnHeader from './SortableColumnHeader';
import type { SortConfig } from './SortableColumnHeader';

interface ProductTableProps {
  columns: { key: string; label: string }[];
  baseColumns: { key: string; label: string }[];
  visibleColumns: string[];
  paginatedData: AggregatedProduct[];
  suppliers: string[];
  role?: string;
  filters: Record<string, string | string[]>;
  setFilters: (filters: Record<string, string | string[]>) => void;
  onRowClick?: (product: AggregatedProduct) => void;
  brandOptions: string[];
  colorOptions: string[];
  memoryOptions: string[];
  typeOptions: string[];
  ramOptions: string[];
  normeOptions: string[];
  sortConfig: SortConfig;
  onSort: (column: string) => void;
  selectedProductIds?: Set<number>;
  onToggleSelection?: (id: number) => void;
  onToggleSelectAll?: () => void;
}

function ProductTable({
  columns,
  baseColumns,
  visibleColumns,
  paginatedData,
  suppliers,
  role,
  filters,
  setFilters,
  brandOptions,
  colorOptions,
  memoryOptions,
  typeOptions,
  ramOptions,
  normeOptions,
  sortConfig,
  onSort,
  onRowClick,
  selectedProductIds,
  onToggleSelection,
  onToggleSelectAll,
}: ProductTableProps) {
  return (
    <table className="table border-0">
      <thead>
        <tr className="bg-[var(--color-bg-elevated)]">
          {role !== 'client' && (
            <th className="px-3 py-2 border-b border-[var(--color-border-default)] w-10">
              <input
                type="checkbox"
                checked={paginatedData.length > 0 && paginatedData.every((p) => selectedProductIds?.has(p.id))}
                onChange={onToggleSelectAll}
                className="rounded"
              />
            </th>
          )}
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
        <ProductFilters
          columns={columns}
          baseColumns={baseColumns}
          visibleColumns={visibleColumns}
          filters={filters}
          setFilters={setFilters}
          brandOptions={brandOptions}
          colorOptions={colorOptions}
          memoryOptions={memoryOptions}
          typeOptions={typeOptions}
          ramOptions={ramOptions}
          normeOptions={normeOptions}
          role={role}
        />
      </thead>
      <tbody>
        {paginatedData.map((row) => {
          const prices = suppliers.map((s) => row.buyPrices[s]);
          const validPrices = prices.filter((p) => typeof p === 'number') as number[];
          const minPrice = validPrices.length ? Math.min(...validPrices) : undefined;
          return (
            <tr
              key={String(row.id)}
              className={`odd:bg-[var(--color-bg-surface)] even:bg-[var(--color-bg-elevated)] hover:bg-[var(--color-bg-elevated)]/80 ${onRowClick ? 'cursor-pointer' : ''}`}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
            >
              {role !== 'client' && (
                <td
                  className="px-3 py-1 border-b border-[var(--color-border-default)]"
                  onClick={(e) => e.stopPropagation()}
                >
                  <input
                    type="checkbox"
                    checked={selectedProductIds?.has(row.id) ?? false}
                    onChange={() => onToggleSelection?.(row.id)}
                    className="rounded"
                  />
                </td>
              )}
              {columns.map((col) => {
                if (!visibleColumns.includes(col.key)) return null;
                let value: any = (row as any)[col.key];
                if (col.key.startsWith('pa_')) {
                  const supplierName = col.key.slice(3);
                  value = row.buyPrices[supplierName];
                }
                const isMin =
                  col.key.startsWith('pa_') &&
                  typeof value === 'number' &&
                  value === minPrice;
                return (
                  <td
                    key={col.key}
                    className={`px-3 py-1 border-b border-[var(--color-border-default)] ${isMin ? 'text-green-400' : ''}`}
                  >
                    {value !== undefined ? String(value) : ''}
                  </td>
                );
              })}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export default ProductTable;
