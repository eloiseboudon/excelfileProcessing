import { useEffect, useState } from 'react';
import {
  fetchProducts,
  fetchBrands,
  fetchColors,
  fetchMemoryOptions,
  fetchDeviceTypes,
  bulkUpdateProducts,
} from '../api';
import MultiSelectFilter from './MultiSelectFilter';

interface ProductItem {
  id: number;
  ean: string | null;
  model: string;
  description: string;
  brand_id: number | null;
  brand: string | null;
  memory_id: number | null;
  memory: string | null;
  color_id: number | null;
  color: string | null;
  type_id: number | null;
  type: string | null;
}

function ProductReference() {
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [edited, setEdited] = useState<Record<number, Partial<ProductItem>>>({});
  const [filters, setFilters] = useState<Record<string, string | string[]>>({});
  const [visibleColumns, setVisibleColumns] = useState<string[]>([]);
  const [showColumnMenu, setShowColumnMenu] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(20);
  const [brands, setBrands] = useState<any[]>([]);
  const [colors, setColors] = useState<any[]>([]);
  const [memories, setMemories] = useState<any[]>([]);
  const [types, setTypes] = useState<any[]>([]);
  const [brandOptions, setBrandOptions] = useState<string[]>([]);
  const [colorOptions, setColorOptions] = useState<string[]>([]);
  const [memoryOptions, setMemoryOptions] = useState<string[]>([]);
  const [typeOptions, setTypeOptions] = useState<string[]>([]);

  const columns: { key: string; label: string }[] = [
    { key: 'id', label: 'ID' },
    { key: 'model', label: 'Modèle' },
    { key: 'description', label: 'Description' },
    { key: 'brand', label: 'Marque' },
    { key: 'memory', label: 'Mémoire' },
    { key: 'color', label: 'Couleur' },
    { key: 'type', label: 'Type' },
    { key: 'ean', label: 'EAN' },
  ];

  useEffect(() => {
    fetchProducts()
      .then((res) => {
        setProducts(res as ProductItem[]);
        setVisibleColumns(columns.map((c) => c.key));
      })
      .catch(() => setProducts([]));

    Promise.all([
      fetchBrands(),
      fetchColors(),
      fetchMemoryOptions(),
      fetchDeviceTypes(),
    ])
      .then(([b, c, m, t]) => {
        setBrands(b as any[]);
        setColors(c as any[]);
        setMemories(m as any[]);
        setTypes(t as any[]);
        setBrandOptions((b as any[]).map((br) => br.brand));
        setColorOptions((c as any[]).map((co) => co.color));
        setMemoryOptions((m as any[]).map((me) => me.memory));
        setTypeOptions((t as any[]).map((ty) => ty.type));
      })
      .catch(() => {
        setBrands([]);
        setColors([]);
        setMemories([]);
        setTypes([]);
        setBrandOptions([]);
        setColorOptions([]);
        setMemoryOptions([]);
        setTypeOptions([]);
      });
  }, []);

  useEffect(() => {
    setCurrentPage(1);
  }, [filters, rowsPerPage]);

  const filteredData = products.filter((row) =>
    columns.every((col) => {
      const filterValue = filters[col.key];
      if (!filterValue || (Array.isArray(filterValue) && filterValue.length === 0))
        return true;
      const value = (row as any)[col.key];
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

  const handleChange = (
    id: number,
    field: keyof ProductItem,
    value: string | number | null
  ) => {
    setProducts((prev) =>
      prev.map((p) => (p.id === id ? { ...p, [field]: value } : p))
    );
    setEdited((prev) => ({
      ...prev,
      [id]: { ...(prev[id] || {}), [field]: value },
    }));
  };

  const saveAll = async () => {
    const payload = Object.entries(edited).map(([id, changes]) => ({
      id: Number(id),
      ...changes,
    }));
    if (!payload.length) return;
    try {
      await bulkUpdateProducts(payload);
      setEdited({});
      const res = await fetchProducts();
      setProducts(res as ProductItem[]);
    } catch {
      /* empty */
    }
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
    <div>
      <div className="flex justify-between mb-4">
        <div className="relative">
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
        <button
          onClick={saveAll}
          disabled={!Object.keys(edited).length}
          className="px-4 py-2 bg-green-600 text-white rounded disabled:opacity-50 hover:bg-green-700"
        >
          Enregistrer
        </button>
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
                        <MultiSelectFilter
                          options={
                            col.key === 'brand'
                              ? brandOptions
                              : col.key === 'memory'
                              ? memoryOptions
                              : col.key === 'color'
                              ? colorOptions
                              : typeOptions
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
                        {col.key === 'brand' ? (
                          <select
                            value={row.brand_id ?? ''}
                            onChange={(e) =>
                              handleChange(
                                row.id,
                                'brand_id',
                                e.target.value === '' ? null : Number(e.target.value)
                              )
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
                        ) : col.key === 'memory' ? (
                          <select
                            value={row.memory_id ?? ''}
                            onChange={(e) =>
                              handleChange(
                                row.id,
                                'memory_id',
                                e.target.value === '' ? null : Number(e.target.value)
                              )
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
                        ) : col.key === 'color' ? (
                          <select
                            value={row.color_id ?? ''}
                            onChange={(e) =>
                              handleChange(
                                row.id,
                                'color_id',
                                e.target.value === '' ? null : Number(e.target.value)
                              )
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
                        ) : col.key === 'type' ? (
                          <select
                            value={row.type_id ?? ''}
                            onChange={(e) =>
                              handleChange(
                                row.id,
                                'type_id',
                                e.target.value === '' ? null : Number(e.target.value)
                              )
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
                        ) : col.key === 'model' ? (
                          <input
                            value={row.model}
                            onChange={(e) => handleChange(row.id, 'model', e.target.value)}
                            className="w-full px-2 py-1 bg-zinc-700 rounded"
                          />
                        ) : col.key === 'description' ? (
                          <input
                            value={row.description}
                            onChange={(e) => handleChange(row.id, 'description', e.target.value)}
                            className="w-full px-2 py-1 bg-zinc-700 rounded"
                          />
                        ) : col.key === 'ean' ? (
                          <input
                            value={row.ean ?? ''}
                            onChange={(e) => handleChange(row.id, 'ean', e.target.value)}
                            className="w-full px-2 py-1 bg-zinc-700 rounded"
                          />
                        ) : (
                          String((row as any)[col.key] ?? '')
                        )}
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

