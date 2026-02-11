import { ArrowLeft } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import * as XLSX from 'xlsx';
import { fetchProductPriceSummary, updateProduct } from '../api';
import { getCurrentTimestamp } from '../utils/date';
import ProductEditModal from './ProductEditModal';
import ProductReference from './ProductReference';
import ProductTable from './ProductTable';
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

export interface AggregatedProduct {
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
  margePercent: number | null;
  averagePrice: number;
  buyPrices: Record<string, number | undefined>;
  salePrices: Record<string, number | undefined>;
  stockLevels: Record<string, number | undefined>;
  latestCalculations: Record<
    string,
    {
      price?: number;
      tcp?: number;
      marge45?: number;
      marge?: number;
      margePercent?: number | null;
      prixhtTcpMarge45?: number;
      prixhtMarge45?: number;
      prixhtMax?: number;
      stock?: number;
      updatedAt?: string | null;
    }
  >;
  minBuyPrice: number;
  tcp: number;
}

interface ProductsPageProps {
  onBack?: () => void;
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
  const [selectedProducts, setSelectedProducts] = useState<number[]>([]);
  const [showBulkMarginModal, setShowBulkMarginModal] = useState(false);
  const [bulkMarginValue, setBulkMarginValue] = useState('');
  const notify = useNotification();
  const modifiedCount = Object.keys(editedPrices).length;
  const hasEdits = modifiedCount > 0;
  const selectedCount = selectedProducts.length;
  const selectedSet = useMemo(() => new Set(selectedProducts), [selectedProducts]);

  const getBaseBuyPrice = (product: AggregatedProduct) => {
    const buyValues = Object.values(product.buyPrices || {}).filter(
      (value): value is number => typeof value === 'number' && !Number.isNaN(value)
    );
    if (typeof product.minBuyPrice === 'number' && !Number.isNaN(product.minBuyPrice)) {
      return product.minBuyPrice;
    }
    if (buyValues.length) {
      return Math.min(...buyValues);
    }
    return 0;
  };

  const baseColumns: { key: string; label: string }[] = useMemo(() => {
    if (role === 'client') {
      return [
        { key: 'averagePrice', label: 'Prix de vente' },
        { key: 'model', label: 'Modèle' },
        { key: 'description', label: 'Description' },
      ];
    }
    return [
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
  }, [role]);

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
          const latest: AggregatedProduct['latestCalculations'] = {};
          Object.entries(it.latest_calculations || {}).forEach(([supplier, detail]) => {
            latest[supplier] = {
              price: detail?.price ?? undefined,
              tcp: detail?.tcp ?? undefined,
              marge45: detail?.marge4_5 ?? undefined,
              marge: detail?.marge ?? undefined,
              margePercent: detail?.marge_percent ?? null,
              prixhtTcpMarge45: detail?.prixht_tcp_marge4_5 ?? undefined,
              prixhtMarge45: detail?.prixht_marge4_5 ?? undefined,
              prixhtMax: detail?.prixht_max ?? undefined,
              stock: detail?.stock ?? undefined,
              updatedAt: detail?.date ?? null,
            };
          });
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
            margePercent:
              typeof it.marge_percent === 'number' ? it.marge_percent : null,
            averagePrice:
              it.recommended_price ?? it.average_price ?? 0,
            buyPrices: it.buy_price || {},
            salePrices: it.supplier_prices || {},
            stockLevels: it.stock_levels || {},
            latestCalculations: latest,
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
    const existingIds = new Set(data.map((item) => item.id));
    setSelectedProducts((prev) => {
      const filtered = prev.filter((id) => existingIds.has(id));
      return filtered.length === prev.length ? prev : filtered;
    });
  }, [data]);

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

  const toggleProductSelection = (productId: number) => {
    setSelectedProducts((prev) => {
      const updated = new Set(prev);
      if (updated.has(productId)) {
        updated.delete(productId);
      } else {
        updated.add(productId);
      }
      return Array.from(updated);
    });
  };

  const toggleSelectAllCurrentPage = () => {
    const pageIds = paginatedData.map((row) => row.id);
    const allSelected = pageIds.every((id) => selectedSet.has(id));
    setSelectedProducts((prev) => {
      const updated = new Set(prev);
      if (allSelected) {
        pageIds.forEach((id) => updated.delete(id));
      } else {
        pageIds.forEach((id) => updated.add(id));
      }
      return Array.from(updated);
    });
  };

  const openBulkMarginModal = () => {
    setBulkMarginValue('');
    setShowBulkMarginModal(true);
  };

  const closeBulkMarginModal = () => {
    setShowBulkMarginModal(false);
    setBulkMarginValue('');
  };

  const applyBulkMargin = () => {
    const trimmed = bulkMarginValue.trim();
    if (!trimmed) {
      notify('Veuillez indiquer une marge', 'error');
      return;
    }
    const normalized = trimmed.replace(/,/g, '.');
    const parsed = Number(normalized);
    if (Number.isNaN(parsed)) {
      notify('Marge invalide', 'error');
      return;
    }
    const normalizedMargin = Number(parsed.toFixed(2));
    if (!selectedProducts.length) {
      closeBulkMarginModal();
      return;
    }

    const selectedIds = new Set(selectedProducts);
    const updatedPrices: Record<number, number> = {};
    setData((prev) =>
      prev.map((product) => {
        if (!selectedIds.has(product.id)) {
          return product;
        }
        const tcpValue = Number.isFinite(product.tcp) ? product.tcp : 0;
        const baseBuyPrice = getBaseBuyPrice(product);
        const newPrice = Number((tcpValue + baseBuyPrice + normalizedMargin).toFixed(2));
        const baseCost = baseBuyPrice + tcpValue;
        const newPercent = baseCost
          ? Number(((normalizedMargin / baseCost) * 100).toFixed(4))
          : null;
        updatedPrices[product.id] = newPrice;
        return {
          ...product,
          marge: normalizedMargin,
          margePercent: newPercent,
          averagePrice: newPrice,
        };
      })
    );
    setEditedPrices((prev) => ({ ...prev, ...updatedPrices }));
    notify(
      `${selectedIds.size} produit${selectedIds.size === 1 ? '' : 's'} mis à jour (en attente d'enregistrement)`,
      'success'
    );
    closeBulkMarginModal();
  };

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
            marge_percent: prod?.margePercent ?? undefined,
          });
        })
      );
      notify(`${entries.length} prix mis à jour`, 'success');
      setEditedPrices({});
    } catch {
      notify("Erreur lors de l'enregistrement", 'error');
    }
  };

  const handleProductMarginUpdate = async (
    productId: number,
    margin: number,
    marginPercent: number | null
  ) => {
    const product = data.find((p) => p.id === productId);
    if (!product) {
      return;
    }

    const baseBuyPrice = getBaseBuyPrice(product);
    const tcpValue = Number.isFinite(product.tcp) ? product.tcp : 0;
    const normalizedMargin = Number(margin.toFixed(2));
    const baseCost = baseBuyPrice + tcpValue;
    const derivedPercent = baseCost
      ? Number(((normalizedMargin / baseCost) * 100).toFixed(4))
      : marginPercent !== null
        ? Number(marginPercent.toFixed(4))
        : null;
    const recommendedPrice = Number((baseCost + normalizedMargin).toFixed(2));

    try {
      await updateProduct(productId, {
        marge: normalizedMargin,
        marge_percent: derivedPercent ?? undefined,
        recommended_price: recommendedPrice,
      });
    } catch (err) {
      notify('Erreur lors de la mise à jour de la marge', 'error');
      throw err;
    }

    const refreshProduct = (item: AggregatedProduct): AggregatedProduct => {
      const updatedLatest: AggregatedProduct['latestCalculations'] = {};
      Object.entries(item.latestCalculations || {}).forEach(([supplier, detail]) => {
        const detailData = detail ?? {};
        const buyPrice = detailData.price ?? item.buyPrices[supplier] ?? 0;
        const tcp = detailData.tcp ?? item.tcp ?? 0;
        const calcBaseCost = buyPrice + tcp;
        const supplierPercent = calcBaseCost
          ? Number(((normalizedMargin / calcBaseCost) * 100).toFixed(4))
          : derivedPercent;
        const newMax = Number((tcp + buyPrice + normalizedMargin).toFixed(2));
        updatedLatest[supplier] = {
          ...detailData,
          marge: normalizedMargin,
          margePercent: supplierPercent,
          prixhtMax: newMax,
        };
      });

      const updatedSalePrices = { ...item.salePrices };
      Object.entries(updatedLatest).forEach(([supplier, detail]) => {
        if (detail?.prixhtMax !== undefined) {
          updatedSalePrices[supplier] = detail.prixhtMax;
        }
      });

      return {
        ...item,
        marge: normalizedMargin,
        margePercent: derivedPercent,
        averagePrice: recommendedPrice,
        salePrices: updatedSalePrices,
        latestCalculations: updatedLatest,
      };
    };

    setData((prev) => prev.map((item) => (item.id === productId ? refreshProduct(item) : item)));
    setSelectedProduct((prev) =>
      prev && prev.id === productId ? refreshProduct(prev) : prev
    );
    setEditedPrices((prev) => {
      const next = { ...prev };
      delete next[productId];
      return next;
    });
    notify('Marge mise à jour', 'success');
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
          className="bg-[var(--color-bg-surface)] border border-[var(--color-border-strong)] rounded px-2 py-1"
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
      {onBack && (
        <button
          onClick={onBack}
          className="btn btn-secondary mb-6"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>Retour</span>
        </button>
      )}
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
                <div className="absolute z-50 mt-2 p-4 min-w-[10rem] bg-[var(--color-bg-input)] text-[var(--color-text-primary)] border border-[var(--color-border-strong)] rounded-lg shadow-2xl flex flex-col gap-2">
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
          <div className="flex flex-col gap-4 my-4 md:flex-row md:items-center md:justify-between">
            <div className="flex flex-wrap gap-2">
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
            {role !== 'client' && (
              <div className="flex flex-col items-end gap-2 md:items-center md:flex-row md:gap-4">
                {selectedCount > 0 && (
                  <button
                    onClick={openBulkMarginModal}
                    className="btn btn-secondary"
                  >
                    Mise à jour marge ({selectedCount})
                  </button>
                )}
                <div className="flex items-center gap-3">
                  <span className="text-sm text-[var(--color-text-secondary)]">
                    {modifiedCount} produit{modifiedCount === 1 ? '' : 's'} modifié{modifiedCount === 1 ? '' : 's'}
                  </span>
                  <button
                    onClick={handleSavePrices}
                    className="btn btn-primary"
                    disabled={!hasEdits}
                  >
                    Enregistrer ({modifiedCount})
                  </button>
                </div>
              </div>
            )}
          </div>
          <div className="overflow-auto mt-4">
            <ProductTable
              columns={columns}
              baseColumns={baseColumns}
              visibleColumns={visibleColumns}
              paginatedData={paginatedData}
              suppliers={suppliers}
              role={role}
              editedPrices={editedPrices}
              setEditedPrices={setEditedPrices}
              setData={setData}
              selectedSet={selectedSet}
              toggleProductSelection={toggleProductSelection}
              toggleSelectAllCurrentPage={toggleSelectAllCurrentPage}
              setSelectedProduct={setSelectedProduct}
              getBaseBuyPrice={getBaseBuyPrice}
              filters={filters}
              setFilters={setFilters}
              brandOptions={brandOptions}
              colorOptions={colorOptions}
              memoryOptions={memoryOptions}
              typeOptions={typeOptions}
              ramOptions={ramOptions}
              normeOptions={normeOptions}
            />
          </div>
          <div className="mt-4">{paginationControls}</div>
        </>
      )}
      {tab === 'reference' && <ProductReference />}
      {role !== 'client' && selectedProduct && (
        <SupplierPriceModal
          prices={selectedProduct.salePrices}
          stocks={selectedProduct.stockLevels}
          calculations={selectedProduct.latestCalculations}
          currentMargin={selectedProduct.marge}
          currentMarginPercent={selectedProduct.margePercent}
          baseCost={
            getBaseBuyPrice(selectedProduct) +
            (Number.isFinite(selectedProduct.tcp) ? selectedProduct.tcp : 0)
          }
          recommendedPrice={selectedProduct.averagePrice}
          onUpdateMargin={(margin, percent) =>
            handleProductMarginUpdate(selectedProduct.id, margin, percent)
          }
          onClose={() => setSelectedProduct(null)}
        />
      )}
      {showBulkMarginModal && (
        <ProductEditModal
          selectedCount={selectedCount}
          bulkMarginValue={bulkMarginValue}
          setBulkMarginValue={setBulkMarginValue}
          closeBulkMarginModal={closeBulkMarginModal}
          applyBulkMargin={applyBulkMargin}
        />
      )}
    </div>
  );
}

export default ProductsPage;
