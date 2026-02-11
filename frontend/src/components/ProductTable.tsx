import type { AggregatedProduct } from './ProductsPage';
import ProductFilters from './ProductFilters';

interface ProductTableProps {
  columns: { key: string; label: string }[];
  baseColumns: { key: string; label: string }[];
  visibleColumns: string[];
  paginatedData: AggregatedProduct[];
  suppliers: string[];
  role?: string;
  editedPrices: Record<number, number>;
  setEditedPrices: React.Dispatch<React.SetStateAction<Record<number, number>>>;
  setData: React.Dispatch<React.SetStateAction<AggregatedProduct[]>>;
  selectedSet: Set<number>;
  toggleProductSelection: (productId: number) => void;
  toggleSelectAllCurrentPage: () => void;
  setSelectedProduct: (product: AggregatedProduct | null) => void;
  getBaseBuyPrice: (product: AggregatedProduct) => number;
  filters: Record<string, string | string[]>;
  setFilters: (filters: Record<string, string | string[]>) => void;
  brandOptions: string[];
  colorOptions: string[];
  memoryOptions: string[];
  typeOptions: string[];
  ramOptions: string[];
  normeOptions: string[];
}

function ProductTable({
  columns,
  baseColumns,
  visibleColumns,
  paginatedData,
  suppliers,
  role,
  editedPrices,
  setEditedPrices,
  setData,
  selectedSet,
  toggleProductSelection,
  toggleSelectAllCurrentPage,
  setSelectedProduct,
  getBaseBuyPrice,
  filters,
  setFilters,
  brandOptions,
  colorOptions,
  memoryOptions,
  typeOptions,
  ramOptions,
  normeOptions,
}: ProductTableProps) {
  return (
    <table className="table border-0">
      <thead>
        <tr className="bg-[var(--color-bg-elevated)]">
          {role !== 'client' && (
            <th className="px-3 py-2 border-b border-[var(--color-border-default)] w-12">
              <input
                type="checkbox"
                onChange={toggleSelectAllCurrentPage}
                checked={
                  paginatedData.length > 0 &&
                  paginatedData.every((row) => selectedSet.has(row.id))
                }
                aria-checked={
                  paginatedData.some((row) => selectedSet.has(row.id)) &&
                    !paginatedData.every((row) => selectedSet.has(row.id))
                    ? 'mixed'
                    : undefined
                }
                className="rounded"
              />
            </th>
          )}
          {columns.map(
            (col) =>
              visibleColumns.includes(col.key) && (
                <th key={col.key} className="px-3 py-2 border-b border-[var(--color-border-default)]">
                  {col.label}
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
          const baseBuyPrice = getBaseBuyPrice(row);
          const isSelected = selectedSet.has(row.id);
          return (
            <tr
              key={String(row.id)}
              className={`odd:bg-[var(--color-bg-surface)] even:bg-[var(--color-bg-elevated)] ${role !== 'client' ? 'cursor-pointer' : ''
                } ${isSelected ? 'bg-indigo-900/40 ring-1 ring-indigo-500' : ''}`}
              onClick={() => role !== 'client' && setSelectedProduct(row)}
            >
              {role !== 'client' && (
                <td className="px-3 py-1 border-b border-[var(--color-border-default)]">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onClick={(e) => e.stopPropagation()}
                    onChange={() => toggleProductSelection(row.id)}
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
                    {col.key === 'averagePrice' && role !== 'client' ? (
                      <input
                        type="number"
                        step="0.01"
                        value={editedPrices[row.id] ?? row.averagePrice}
                        onClick={(e) => e.stopPropagation()}
                        onChange={(e) => {
                          const v = Number(e.target.value);
                          setEditedPrices((prev) => ({ ...prev, [row.id]: v }));
                          setData((prev) =>
                            prev.map((p) =>
                              p.id === row.id ? { ...p, averagePrice: v } : p
                            )
                          );
                        }}
                        className="w-20 px-1 bg-[var(--color-bg-input)] rounded"
                      />
                    ) : col.key === 'averagePrice' ? (
                      row.averagePrice
                    ) : col.key === 'marge' && role !== 'client' ? (
                      <input
                        type="number"
                        step="0.01"
                        value={row.marge}
                        onClick={(e) => e.stopPropagation()}
                        onChange={(e) => {
                          const v = Number(e.target.value);
                          if (Number.isNaN(v)) {
                            return;
                          }
                          const tcpValue = Number.isFinite(row.tcp)
                            ? row.tcp
                            : row.averagePrice - row.marge - baseBuyPrice;
                          const newPrice = Number(
                            (tcpValue + baseBuyPrice + v).toFixed(2)
                          );
                          const baseCost = baseBuyPrice + tcpValue;
                          const newPercent = baseCost
                            ? Number(((v / baseCost) * 100).toFixed(4))
                            : null;
                          setEditedPrices((prev) => ({
                            ...prev,
                            [row.id]: newPrice,
                          }));
                          setData((prev) =>
                            prev.map((p) =>
                              p.id === row.id
                                ? {
                                  ...p,
                                  marge: v,
                                  margePercent: newPercent,
                                  averagePrice: newPrice,
                                }
                                : p
                            )
                          );
                        }}
                        className="w-20 px-1 bg-[var(--color-bg-input)] rounded"
                      />
                    ) : col.key === 'marge' ? (
                      row.marge
                    ) : value !== undefined ? (
                      String(value)
                    ) : (
                      ''
                    )}
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
