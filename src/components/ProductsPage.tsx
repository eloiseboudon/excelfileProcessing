import React, { useEffect, useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import {
  fetchProductCalculations,
  fetchBrands,
  fetchColors,
  fetchMemoryOptions,
  fetchDeviceTypes,
} from '../api';

interface ProductCalculation {
  [key: string]: string | number | null;
}

interface ProductsPageProps {
  onBack: () => void;
}

function ProductsPage({ onBack }: ProductsPageProps) {
  const [data, setData] = useState<ProductCalculation[]>([]);
  const [filters, setFilters] = useState<Record<string, string>>({});
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
    { key: 'name', label: 'Nom' },
    { key: 'description', label: 'Description' },
    { key: 'brand', label: 'Marque' },
    { key: 'price', label: 'Prix' },
    { key: 'memory', label: 'Mémoire' },
    { key: 'color', label: 'Couleur' },
    { key: 'type', label: 'Type' },
    { key: 'tcp', label: 'TCP' },
    { key: 'marge4_5', label: 'Marge 4.5' },
    { key: 'prixht_tcp_marge4_5', label: 'PrixHT TCP Marge4.5' },
    { key: 'prixht_marge4_5', label: 'PrixHT Marge4.5' },
    { key: 'prixht_max', label: 'PrixHT Max' },
    { key: 'date', label: 'Date' },
    { key: 'week', label: 'Semaine' }
  ];

  useEffect(() => {
    fetchProductCalculations()
      .then((res) => {
        setData(res as ProductCalculation[]);
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
        setBrandOptions(brands.map((b: any) => b.brand));
        setColorOptions(colors.map((c: any) => c.color));
        setMemoryOptions(memories.map((m: any) => m.memory));
        setTypeOptions(types.map((t: any) => t.type));
      })
      .catch(() => {
        setBrandOptions([]);
        setColorOptions([]);
        setMemoryOptions([]);
        setTypeOptions([]);
      });
  }, []);

  useEffect(() => {
    const usedBrands = Array.from(
      new Set(data.map((d) => d.brand).filter(Boolean))
    );
    if (usedBrands.length) {
      setBrandOptions((prev) => Array.from(new Set([...prev, ...usedBrands])));
    }

    const usedColors = Array.from(
      new Set(data.map((d) => d.color).filter(Boolean))
    );
    if (usedColors.length) {
      setColorOptions((prev) => Array.from(new Set([...prev, ...usedColors])));
    }

    const usedMemories = Array.from(
      new Set(data.map((d) => d.memory).filter(Boolean))
    );
    if (usedMemories.length) {
      setMemoryOptions((prev) => Array.from(new Set([...prev, ...usedMemories])));
    }

    const usedTypes = Array.from(
      new Set(data.map((d) => d.type).filter(Boolean))
    );
    if (usedTypes.length) {
      setTypeOptions((prev) => Array.from(new Set([...prev, ...usedTypes])));
    }
  }, [data]);

  useEffect(() => {
    setCurrentPage(1);
  }, [filters, rowsPerPage]);

  const filteredData = data.filter((row) =>
    columns.every((col) => {
      if (!filters[col.key]) return true;
      const value = row[col.key];
      if (['brand', 'memory', 'color', 'type'].includes(col.key)) {
        return (
          String(value ?? '').toLowerCase() ===
          filters[col.key].toLowerCase()
        );
      }
      return String(value ?? '')
        .toLowerCase()
        .includes(filters[col.key].toLowerCase());
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
          Précédent
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
    <div className="max-w-6xl mx-auto px-2 sm:px-4 py-6 sm:py-8">
      <button
        onClick={onBack}
        className="flex items-center space-x-2 px-4 py-2 bg-zinc-800 text-white rounded-lg hover:bg-zinc-700 transition-colors mb-6"
      >
        <ArrowLeft className="w-5 h-5" />
        <span>Retour</span>
      </button>
      <h1 className="text-2xl font-bold text-center mb-4">
        Calculs TCP et Marges par produits
      </h1>
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
                          value={filters[col.key] || ''}
                          onChange={(e) =>
                            setFilters({ ...filters, [col.key]: e.target.value })
                          }
                          className="w-full px-2 py-1 bg-zinc-900 border border-zinc-600 rounded"
                        >
                          <option value="">Tous</option>
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
                          value={filters[col.key] || ''}
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

export default ProductsPage;
