import MultiSelectFilter from './MultiSelectFilter';

interface ProductFiltersProps {
  columns: { key: string; label: string }[];
  baseColumns: { key: string; label: string }[];
  visibleColumns: string[];
  filters: Record<string, string | string[]>;
  setFilters: (filters: Record<string, string | string[]>) => void;
  brandOptions: string[];
  colorOptions: string[];
  memoryOptions: string[];
  typeOptions: string[];
  ramOptions: string[];
  normeOptions: string[];
  role?: string;
}

function ProductFilters({
  columns,
  baseColumns,
  visibleColumns,
  filters,
  setFilters,
  brandOptions,
  colorOptions,
  memoryOptions,
  typeOptions,
  ramOptions,
  normeOptions,
  role,
}: ProductFiltersProps) {
  return (
    <tr>
      {role !== 'client' && <th className="px-3 py-1 border-b border-zinc-700"></th>}
      {columns.map(
        (col) =>
          visibleColumns.includes(col.key) && (
            <th key={col.key} className="px-3 py-1 border-b border-zinc-700">
              {baseColumns.some((c) => c.key === col.key) ? (
                ['brand', 'memory', 'color', 'type', 'ram', 'norme'].includes(
                  col.key
                ) ? (
                  <MultiSelectFilter
                    options={
                      col.key === 'brand'
                        ? brandOptions
                        : col.key === 'memory'
                          ? memoryOptions
                          : col.key === 'color'
                            ? colorOptions
                            : col.key === 'type'
                              ? typeOptions
                              : col.key === 'ram'
                                ? ramOptions
                                : normeOptions
                    }
                    selected={(filters[col.key] as string[]) || []}
                    onChange={(selected) =>
                      setFilters({ ...filters, [col.key]: selected })
                    }
                  />
                ) : (
                  <input
                    type="text"
                    value={(filters[col.key] as string) || ''}
                    onChange={(e) =>
                      setFilters({ ...filters, [col.key]: e.target.value })
                    }
                    className="w-full px-2 py-1 bg-zinc-900 border border-zinc-600 rounded"
                  />
                )
              ) : null}
            </th>
          )
      )}
    </tr>
  );
}

export default ProductFilters;
