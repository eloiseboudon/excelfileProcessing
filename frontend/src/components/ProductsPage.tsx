import { ArrowLeft } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import * as XLSX from 'xlsx';
import { fetchProductPriceSummary, updateProduct } from '../api';
import { getCurrentTimestamp } from '../utils/date';
import MultiSelectFilter from './MultiSelectFilter';
import ProductReference from './ProductReference';
import SupplierPriceModal from './SupplierPriceModal';
import WeekToolbar from './WeekToolbar';

import {
  fetchBrands,
  fetchColors,
  fetchDeviceTypes,
  fetchMemoryOptions,
  fetchNormeOptions,
  fetchRAMOptions,
} from '../api';
import { useNotification } from './NotificationProvider';

interface AggregatedProduct {
  id: number;
  model: string | null;
  description: string | null;
  brand: string | null;
  memory: string | null;
  color: string | null;
  type: string | null;
  ram: string | null;
  norme: string | null;
  marge: number;
  averagePrice: number;
  buyPrices: Record<string, number | undefined>;
  salePrices: Record<string, number | undefined>;
  minBuyPrice: number;
  tcp: number;
}

interface ProductsPageProps {
  onBack: () => void;
  role?: string;
}

function ProductsPage({ onBack, role }: ProductsPageProps) {
  const [data, setData] = useState<AggregatedProduct[]>([]);
  const [suppliers, setSuppliers] = useState<string[]>([]);
  const [filters, setFilters] = useState<Record<string, string | string[]>>({});
  const [editedPrices, setEditedPrices] = useState<Record<number, number>>({});
  const [visibleColumns, setVisibleColumns] = useState<string[]>([]);
  const [showColumnMenu, setShowColumnMenu] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(20);
  const [brandOptions, setBrandOptions] = useState<string[]>([]);
  const [colorOptions, setColorOptions] = useState<string[]>([]);
  const [memoryOptions, setMemoryOptions] = useState<string[]>([]);
  const [typeOptions, setTypeOptions] = useState<string[]>([]);
  const [ramOptions, setRamOptions] = useState<string[]>([]);
  const [normeOptions, setNormeOptions] = useState<string[]>([]);
  const [tab, setTab] = useState<'calculations' | 'reference'>('calculations');
  const [selectedProduct, setSelectedProduct] = useState<AggregatedProduct | null>(null);
  const notify = useNotification();
  const hasEdits = Object.keys(editedPrices).length > 0;

  const baseColumns: { key: string; label: string }[] = [
    { key: 'id', label: 'ID' },
    { key: 'model', label: 'Modèle' },
    { key: 'description', label: 'Description' },
    { key: 'brand', label: 'Marque' },
    { key: 'memory', label: 'Mémoire' },
    { key: 'color', label: 'Couleur' },
    { key: 'type', label: 'Type' },
    { key: 'ram', label: 'RAM' },
    { key: 'norme', label: 'Norme' },
    { key: 'averagePrice', label: 'Prix de vente' },
    { key: 'marge', label: 'Marge' },
  ];

  const columns = useMemo(
    () =>
      [
        ...baseColumns,
        ...(role !== 'client'
          ? suppliers.map((s) => ({ key: `pa_${s}`, label: `PA ${s}` }))
          : []),
      ].filter((c) => !c.label.includes('%')),
    [suppliers, role]
  );

  useEffect(() => {
    setVisibleColumns(columns.map((c) => c.key));
  }, [columns]);


  useEffect(() => {
    fetchProductPriceSummary()
      .then((res) => {
        const items = res as any[];
        const suppliersSet = new Set<string>();
        const aggregated: AggregatedProduct[] = items.map((it) => {
          Object.keys(it.buy_price || {}).forEach((s) => suppliersSet.add(s));
          return {
            id: it.id,
            model: it.model,
            description: it.description,
            brand: it.brand,
            memory: it.memory,
            color: it.color,
            type: it.type,
            ram: it.ram,
            norme: it.norme,
            marge: it.marge ?? 0,
            averagePrice:
              it.recommended_price ?? it.average_price ?? 0,
            buyPrices: it.buy_price || {},
            salePrices: it.supplier_prices || {},
            minBuyPrice:
              typeof it.min_buy_price === 'number' ? it.min_buy_price : 0,
            tcp: typeof it.tcp === 'number' ? it.tcp : 0,
          } as AggregatedProduct;
        });
        setSuppliers(Array.from(suppliersSet).sort());
        setData(aggregated);
      })
      .catch(() => {
        setData([]);
        setSuppliers([]);
      });

    Promise.all([
      fetchBrands(),
      fetchColors(),
      fetchMemoryOptions(),
      fetchDeviceTypes(),
      fetchRAMOptions(),
      fetchNormeOptions(),
    ])
      .then(([brands, colors, memories, types, rams, normes]) => {
        setBrandOptions(brands.map((b: any) => b.brand));
        setColorOptions(colors.map((c: any) => c.color));
        setMemoryOptions(memories.map((m: any) => m.memory));
        setTypeOptions(types.map((t: any) => t.type));
        setRamOptions(rams.map((r: any) => r.ram));
        setNormeOptions(normes.map((n: any) => n.norme));
      })
      .catch(() => {
        setBrandOptions([]);
        setColorOptions([]);
        setMemoryOptions([]);
        setTypeOptions([]);
        setRamOptions([]);
        setNormeOptions([]);
      });
  }, []);

  useEffect(() => {
    const usedBrands = Array.from(
      new Set(data.map((d) => d.brand).filter((brand): brand is string => typeof brand === 'string'))
    );
    if (usedBrands.length) {
      setBrandOptions((prev) => Array.from(new Set([...prev, ...usedBrands])));
    }

    const usedColors = Array.from(
      new Set(data.map((d) => d.color).filter((color): color is string => typeof color === 'string'))
    );
    if (usedColors.length) {
      setColorOptions((prev) => Array.from(new Set([...prev, ...usedColors])));
    }

    const usedMemories = Array.from(
      new Set(data.map((d) => d.memory).filter((memory): memory is string => typeof memory === 'string'))
    );
    if (usedMemories.length) {
      setMemoryOptions((prev) => Array.from(new Set([...prev, ...usedMemories])));
    }

    const usedTypes = Array.from(
      new Set(data.map((d) => d.type).filter((type): type is string => typeof type === 'string'))
    );
    if (usedTypes.length) {
      setTypeOptions((prev) => Array.from(new Set([...prev, ...usedTypes])));
    }

    const usedRams = Array.from(
      new Set(data.map((d) => d.ram).filter((ram): ram is string => typeof ram === 'string'))
    );
    if (usedRams.length) {
      setRamOptions((prev) => Array.from(new Set([...prev, ...usedRams])));
    }

    const usedNormes = Array.from(
      new Set(data.map((d) => d.norme).filter((n): n is string => typeof n === 'string'))
    );
    if (usedNormes.length) {
      setNormeOptions((prev) => Array.from(new Set([...prev, ...usedNormes])));
    }
  }, [data]);

  useEffect(() => {
    setCurrentPage(1);
  }, [filters, rowsPerPage]);

  const filteredData = data.filter((row) =>
    baseColumns.every((col) => {
      const filterVal = filters[col.key];
      if (!filterVal || (Array.isArray(filterVal) && filterVal.length === 0)) {
        return true;
      }
      const value = (row as any)[col.key];
      if (['brand', 'memory', 'color', 'type', 'ram', 'norme'].includes(col.key)) {
        return (filterVal as string[]).includes(String(value ?? ''));
      }
      return String(value ?? '')
        .toLowerCase()
        .includes((filterVal as string).toLowerCase());
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

  const buildExportRows = () =>
    filteredData.map((row) => {
      const obj: Record<string, any> = {};
      columns.forEach((c) => {
        if (!visibleColumns.includes(c.key)) return;
        let val: any = (row as any)[c.key];
        if (c.key.startsWith('pa_')) {
          const sup = c.key.slice(3);
          val = row.buyPrices[sup];
        }
        if (c.key === 'averagePrice' && editedPrices[row.id] !== undefined) {
          val = editedPrices[row.id];
        }
        obj[c.label] = val;
      });
      return obj;
    });

  const handleExportExcel = () => {
    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(buildExportRows());
    XLSX.utils.book_append_sheet(wb, ws, 'Data');
    XLSX.writeFile(wb, `tcp_marge_${getCurrentTimestamp()}.xlsx`);
  };

  const handleSavePrices = async () => {
    const entries = Object.entries(editedPrices);
    if (!entries.length) return;
    try {
      await Promise.all(
        entries.map(([id, price]) => {
          const prod = data.find((p) => p.id === Number(id));
          return updateProduct(Number(id), {
            recommended_price: price,
            marge: prod?.marge,
          });
        })
      );
      notify(`${entries.length} prix mis à jour`, 'success');
      setEditedPrices({});
    } catch {
      notify("Erreur lors de l'enregistrement", 'error');
    }
  };

  const handleExportJSON = () => {
    const dataStr = JSON.stringify(buildExportRows(), null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `tcp_marge_${getCurrentTimestamp()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleExportHtml = () => {
    const rows = buildExportRows();
    if (!rows.length) return;
    const headers = Object.keys(rows[0]);

    const tableHead = headers.map((h) => `<th>${h}</th>`).join('');
    const tableRows = rows
      .map(
        (r) =>
          `<tr>${headers
            .map((h) => `<td>${r[h] ?? ''}</td>`)
            .join('')}</tr>`
      )
      .join('');

    const style = `
      body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background: linear-gradient(135deg, #000000 0%, #1a1a1a 100%);
        color: white;
        padding: 20px;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
      }
      th, td {
        border: 1px solid #3f3f46;
        padding: 8px;
      }
      th { background: #27272a; }
      tr:nth-child(odd) { background: #18181b; }
      tr:nth-child(even) { background: #27272a; }
    `;

    const html = `<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><title>Export TCP/Marge</title><style>${style}</style></head><body><table><thead><tr>${tableHead}</tr></thead><tbody>${tableRows}</tbody></table></body></html>`;

    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const filename = `ajt_product_${getCurrentTimestamp()}.html`;

    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    window.open(url, '_blank');

    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const paginationControls = (
    <div className="flex items-center justify-between">
      <div className="flex items-center space-x-2">
        <button
          onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
          disabled={currentPage === 1}
          className="btn btn-secondary px-3 py-1 disabled:opacity-50"
        >
          Précédent
        </button>
        <span>
          Page {currentPage} / {totalPages}
        </span>
        <button
          onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
          disabled={currentPage === totalPages}
          className="btn btn-secondary px-3 py-1 disabled:opacity-50"
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
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
      <WeekToolbar />
      <button
        onClick={onBack}
        className="btn btn-secondary mb-6"
      >
        <ArrowLeft className="w-5 h-5" />
        <span>Retour</span>
      </button>
      <h1 className="text-2xl font-bold text-center mb-4">Produits</h1>
      <div className="flex justify-center space-x-4 mb-6">
        <button
          onClick={() => setTab('calculations')}
          className={`btn ${tab === 'calculations' ? 'btn-primary' : 'btn-secondary'}`}
        >
          TCP/Marges
        </button>
        {role !== 'client' && (
          <button
            onClick={() => setTab('reference')}
            className={`btn ${tab === 'reference' ? 'btn-primary' : 'btn-secondary'}`}
          >
            Référentiel
          </button>
        )}
      </div>
      {tab === 'calculations' && (
        <>
          {role !== 'client' && (
            <div className="relative mb-4">
              <button
                onClick={() => setShowColumnMenu((s) => !s)}
                className="btn btn-secondary"
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
          )}
          {paginationControls}
          <div className="flex space-x-2 my-4">
            {role !== 'client' && (
              <button
                onClick={handleSavePrices}
                className="btn btn-primary"
                disabled={!hasEdits}
              >
                Enregistrer
              </button>
            )}
            <button onClick={handleExportExcel} className="btn btn-secondary">
              Export Excel
            </button>
            <button onClick={handleExportJSON} className="btn btn-secondary">
              Export JSON
            </button>
            <button onClick={handleExportHtml} className="btn btn-secondary">
              Génère HTML
            </button>
          </div>
          <div className="overflow-auto mt-4">
            <table className="table">
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
              </thead>
              <tbody>
                {paginatedData.map((row) => {
                  const prices = suppliers.map((s) => row.buyPrices[s]);
                  const validPrices = prices.filter((p) => typeof p === 'number') as number[];
                  const minPrice = validPrices.length ? Math.min(...validPrices) : undefined;
                  const baseBuyPrice =
                    typeof row.minBuyPrice === 'number' && !Number.isNaN(row.minBuyPrice)
                      ? row.minBuyPrice
                      : minPrice ?? 0;
                  return (
                    <tr
                      key={String(row.id)}
                      className={`odd:bg-zinc-900 even:bg-zinc-800 ${role !== 'client' ? 'cursor-pointer' : ''}`}
                      onClick={() => role !== 'client' && setSelectedProduct(row)}
                    >
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
                            className={`px-3 py-1 border-b border-zinc-700 ${isMin ? 'text-green-400' : ''}`}
                          >
                            {col.key === 'averagePrice' && role !== 'client' ? (
                              <input
                                type="number"
                                step="0.01"
                                value={editedPrices[row.id] ?? row.averagePrice}
                                onClick={(e) => e.stopPropagation()}
                                onChange={(e) => {
                                  const v = Number(e.target.value);
                                  setEditedPrices({ ...editedPrices, [row.id]: v });
                                  setData((prev) =>
                                    prev.map((p) =>
                                      p.id === row.id ? { ...p, averagePrice: v } : p
                                    )
                                  );
                                }}
                                className="w-20 px-1 bg-zinc-700 rounded"
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
                                  setEditedPrices({ ...editedPrices, [row.id]: newPrice });
                                  setData((prev) =>
                                    prev.map((p) =>
                                      p.id === row.id
                                        ? { ...p, marge: v, averagePrice: newPrice }
                                        : p
                                    )
                                  );
                                }}
                                className="w-20 px-1 bg-zinc-700 rounded"
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
          </div>
          <div className="mt-4">{paginationControls}</div>
        </>
      )}
      {tab === 'reference' && <ProductReference />}
      {role !== 'client' && selectedProduct && (
        <SupplierPriceModal
          prices={selectedProduct.salePrices}
          onClose={() => setSelectedProduct(null)}
        />
      )}
    </div>
  );
}

export default ProductsPage;
