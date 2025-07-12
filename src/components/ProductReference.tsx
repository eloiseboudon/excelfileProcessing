import { useEffect, useState } from 'react';
import {
  fetchProducts,
  fetchBrands,
  fetchColors,
  fetchMemoryOptions,
  fetchDeviceTypes,
} from '../api';

interface ProductItem {
  [key: string]: string | number | null;
}

function ProductReference() {
  const [data, setData] = useState<ProductItem[]>([]);
  const [filters, setFilters] = useState<Record<string, string | string[]>>({});
  const [visibleColumns, setVisibleColumns] = useState<string[]>([]);
  const [showColumnMenu, setShowColumnMenu] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(20);
  const [brandOptions, setBrandOptions] = useState<string[]>([]);
  const [colorOptions, setColorOptions] = useState<string[]>([]);
  const [memoryOptions, setMemoryOptions] = useState<string[]>([]);
  const [typeOptions, setTypeOptions] = useState<string[]>([]);

  const columns: { key: string; label: string }[] = [
    { key: 'id', label: 'ID' },
    { key: 'model', label: 'Mod\u00e8le' },
    { key: 'description', label: 'Description' },
    { key: 'brand', label: 'Marque' },
    { key: 'memory', label: 'M\u00e9moire' },
    { key: 'color', label: 'Couleur' },
    { key: 'type', label: 'Type' },
    { key: 'ean', label: 'EAN' },
  ];

  useEffect(() => {
    fetchProducts()
      .then((res) => {
        setData(res as ProductItem[]);
        setVisibleColumns(columns.map((c) => c.key));
      })
      .catch(() => setData([]));

    Promise.all([
      fetchBrands(),
      fetchColors(),
      fetchMemoryOptions(),
      fetchDeviceTypes(),
    ])
      .then(([brands, colors, memories, types]) => {
        setBrandOptions((brands as any[]).map((b) => b.brand));
        setColorOptions((colors as any[]).map((c) => c.color));
        setMemoryOptions((memories as any[]).map((m) => m.memory));
        setTypeOptions((types as any[]).map((t) => t.type));
      })
      .catch(() => {
        setBrandOptions([]);
        setColorOptions([]);
        setMemoryOptions([]);
        setTypeOptions([]);
      });
  }, []);

  useEffect(() => {
    setCurrentPage(1);
  }, [filters, rowsPerPage]);

  const filteredData = data.filter((row) =>
    columns.every((col) => {
      const filterValue = filters[col.key];
      if (
        !filterValue ||
        (Array.isArray(filterValue) && filterValue.length === 0)
      )
        return true;
      const value = row[col.key];
      if (['brand', 'memory', 'color', 'type'].includes(col.key)) {
        return (filterValue as string[]).includes(String(value ?? ''));
      }
      return String(value ?? '')
        .toLowerCase()
        .includes((filterValue as string).toLowerCase());
    })
  );

  const totalPages = Math.max(1, Math.ceil(filteredData.length / rowsPerPage));
  const paginatedData = filteredData.slice(
    (currentPage - 1) * rowsPerPage,
    currentPage * rowsPerPage
  );

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [totalPages, currentPage]);

  const toggleColumn = (key: string) => {
    setVisibleColumns((prev) =>
      prev.includes(key) ? prev.filter((c) => c !== key) : [...prev, key]
    );
  };

  const paginationControls = (
    <div className="flex items-center justify-between">
      <div className="flex items-center space-x-2">
        <button
          onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
          disabled={currentPage === 1}
          className="px-3 py-1 bg-zinc-800 rounded disabled:opacity-50"
        >
          Pr\u00e9c\u00e9dent
        </button>
        <span>
          Page {currentPage} / {totalPages}
        </span>
        <button
          onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
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
          onChange={(e) => setRowsPerPage(Number(e.target.value))}
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

  return (
    <div>
      <div className="relative mb-4">
        <button
          onClick={() => setShowColumnMenu((s) => !s)}
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
                  onChange={() => toggleColumn(col.key)}
                  className="rounded"
                />
                <span>{col.label}</span>
              </label>
            ))}
          </div>
        )}
      </div>
      {paginationControls}
      <div className="overflow-auto mt-4">
        <table className="min-w-full text-sm text-left border border-zinc-700">
          <thead>
            <tr className="bg-zinc-800">
              {columns.map(
                (col) =>
                  visibleColumns.includes(col.key) && (
                    <th key={col.key} className="px-3 py-2 border-b border-zinc-700">
                      {col.label}
                    </th>
                  )
              )}
            </tr>
            <tr>
              {columns.map(
                (col) =>
                  visibleColumns.includes(col.key) && (
                    <th key={col.key} className="px-3 py-1 border-b border-zinc-700">
                      {['brand', 'memory', 'color', 'type'].includes(col.key) ? (
                        <select
                          multiple
                          size={3}
                          value={(filters[col.key] as string[]) || []}
                          onChange={(e) => {
                            const selected = Array.from(e.target.selectedOptions).map(
                              (o) => o.value
                            );
                            setFilters({ ...filters, [col.key]: selected });
                          }}
                          className="w-full px-2 py-1 bg-zinc-900 border border-zinc-600 rounded"
                        >
                          {(col.key === 'brand'
                            ? brandOptions
                            : col.key === 'memory'
                            ? memoryOptions
                            : col.key === 'color'
                            ? colorOptions
                            : typeOptions
                          ).map((opt) => (
                            <option key={opt} value={opt}>
                              {opt}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type="text"
                          value={(filters[col.key] as string) || ''}
                          onChange={(e) =>
                            setFilters({ ...filters, [col.key]: e.target.value })
                          }
                          className="w-full px-2 py-1 bg-zinc-900 border border-zinc-600 rounded"
                        />
                      )}
                    </th>
                  )
              )}
            </tr>
          </thead>
          <tbody>
            {paginatedData.map((row) => (
              <tr key={String(row.id)} className="odd:bg-zinc-900 even:bg-zinc-800">
                {columns.map(
                  (col) =>
                    visibleColumns.includes(col.key) && (
                      <td key={col.key} className="px-3 py-1 border-b border-zinc-700">
                        {String(row[col.key] ?? '')}
                      </td>
                    )
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-4">{paginationControls}</div>
    </div>
  );
}

export default ProductReference;
