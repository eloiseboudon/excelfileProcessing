import { ArrowLeft, ChevronLeft, ChevronRight, Package, RefreshCw } from 'lucide-react';
import { useEffect, useMemo, useState, useCallback } from 'react';
import * as XLSX from 'xlsx';
import { calculateProducts, fetchProductPriceSummary, updateProduct } from '../api';
import { getCurrentTimestamp, getCurrentWeekYear } from '../utils/date';
import ProductReference from './ProductReference';
import SupplierPriceModal from './SupplierPriceModal';
import ProductTable from './ProductTable';
import type { SortConfig } from './SortableColumnHeader';

import { useProductAttributeOptions } from '../hooks/useProductAttributeOptions';
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
  const [visibleColumns, setVisibleColumns] = useState<string[]>([]);
  const [showColumnMenu, setShowColumnMenu] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(20);
  const {
    brandNames: brandOptions,
    colorNames: colorOptions,
    memoryNames: memoryOptions,
    typeNames: typeOptions,
    ramNames: ramOptions,
    normeNames: normeOptions,
  } = useProductAttributeOptions();
  const [tab, setTab] = useState<'calculations' | 'reference'>('calculations');
  const [recalculating, setRecalculating] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<AggregatedProduct | null>(null);
  const notify = useNotification();

  const getBaseBuyPrice = useCallback((product: AggregatedProduct) => {
    if (typeof product.minBuyPrice === 'number' && !Number.isNaN(product.minBuyPrice)) {
      return product.minBuyPrice;
    }
    const buyValues = Object.values(product.buyPrices || {}).filter(
      (v): v is number => typeof v === 'number' && !Number.isNaN(v)
    );
    return buyValues.length ? Math.min(...buyValues) : 0;
  }, []);

  const handleProductMarginUpdate = useCallback(async (
    productId: number,
    margin: number,
    marginPercent: number | null
  ) => {
    const product = data.find((p) => p.id === productId);
    if (!product) return;
    const baseBuyPrice = getBaseBuyPrice(product);
    const tcpValue = Number.isFinite(product.tcp) ? product.tcp : 0;
    const normalizedMargin = Number(margin.toFixed(2));
    const baseCost = baseBuyPrice + tcpValue;
    const derivedPercent = baseCost
      ? Number(((normalizedMargin / baseCost) * 100).toFixed(4))
      : marginPercent !== null ? Number(marginPercent.toFixed(4)) : null;
    const recommendedPrice = Number((baseCost + normalizedMargin).toFixed(2));
    try {
      await updateProduct(productId, {
        marge: normalizedMargin,
        marge_percent: derivedPercent ?? undefined,
        recommended_price: recommendedPrice,
      });
    } catch {
      notify('Erreur lors de la mise à jour de la marge', 'error');
      throw new Error('update failed');
    }
    setData((prev) =>
      prev.map((item) =>
        item.id === productId
          ? { ...item, marge: normalizedMargin, margePercent: derivedPercent, averagePrice: recommendedPrice }
          : item
      )
    );
    setSelectedProduct((prev) =>
      prev && prev.id === productId
        ? { ...prev, marge: normalizedMargin, margePercent: derivedPercent, averagePrice: recommendedPrice }
        : prev
    );
  }, [data, getBaseBuyPrice, notify]);

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
    refreshData();
  }, []);

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

  const [sortConfig, setSortConfig] = useState<SortConfig>({ column: null, direction: null });

  const handleSort = useCallback((column: string) => {
    setSortConfig((prev) => {
      if (prev.column !== column) return { column, direction: 'asc' };
      if (prev.direction === 'asc') return { column, direction: 'desc' };
      return { column: null, direction: null };
    });
  }, []);

  const sortedData = useMemo(() => {
    if (!sortConfig.column || !sortConfig.direction) return filteredData;
    return [...filteredData].sort((a, b) => {
      let aVal: any = (a as any)[sortConfig.column!];
      let bVal: any = (b as any)[sortConfig.column!];
      if (sortConfig.column!.startsWith('pa_')) {
        aVal = a.buyPrices[sortConfig.column!.slice(3)];
        bVal = b.buyPrices[sortConfig.column!.slice(3)];
      }
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      if (typeof aVal === 'number' && typeof bVal === 'number')
        return sortConfig.direction === 'asc' ? aVal - bVal : bVal - aVal;
      return sortConfig.direction === 'asc'
        ? String(aVal).localeCompare(String(bVal), 'fr')
        : String(bVal).localeCompare(String(aVal), 'fr');
    });
  }, [filteredData, sortConfig]);

  const totalPages = Math.max(1, Math.ceil(sortedData.length / rowsPerPage));
  const paginatedData = sortedData.slice(
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
        obj[c.label] = val;
      });
      return obj;
    });

  const handleExportExcel = async () => {
    if (!filteredData.length) return;

    const ExcelJS = (await import('exceljs')).default;
    const wb = new ExcelJS.Workbook();
    const ws = wb.addWorksheet('Tarif AJT PRO');

    ws.columns = [{ width: 70 }, { width: 12 }];

    // ISO week number
    const now = new Date();
    const wd = new Date(now);
    wd.setHours(0, 0, 0, 0);
    wd.setDate(wd.getDate() + 3 - (wd.getDay() + 6) % 7);
    const w1 = new Date(wd.getFullYear(), 0, 4);
    const week = 1 + Math.round(((wd.getTime() - w1.getTime()) / 86400000 - 3 + (w1.getDay() + 6) % 7) / 7);

    // Monday and Friday of current week
    const monday = new Date(now);
    monday.setDate(now.getDate() - (now.getDay() + 6) % 7);
    const friday = new Date(monday);
    friday.setDate(monday.getDate() + 4);
    const fmt = (d: Date) => d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit' });

    const addMergedRow = (text: string, fontSize = 12, bold = true, color?: string) => {
      const row = ws.addRow([text, null]);
      ws.mergeCells(row.number, 1, row.number, 2);
      row.getCell(1).alignment = { horizontal: 'center', vertical: 'middle' };
      row.getCell(1).font = { bold, size: fontSize, color: color ? { argb: color } : undefined };
      return row;
    };

    // Header section matching the Excel template
    addMergedRow('TARIF AJT PRO', 12, true);
    addMergedRow(`Semaine n\u00b0${week}`, 12, true);
    addMergedRow(`Du ${fmt(monday)} au ${fmt(friday)}`, 12, true);
    ws.addRow([]);
    addMergedRow('T\u00e9l\u00a0: 05 54 55 56 57 / +33 757 02 45 21 - contact@ajtpro.com', 12, true);
    ws.addRow([]);
    ws.addRow([]);
    ws.addRow([]);
    addMergedRow('AJTPro votre partenaire Pro Actif\u00a0!', 12, true);
    ws.addRow([]);
    ws.addRow([]);

    // Column headers
    const hdrRow = ws.addRow(['Nom produit', 'Prix']);
    hdrRow.getCell(1).font = { bold: true, size: 12 };
    hdrRow.getCell(1).alignment = { horizontal: 'center' };
    hdrRow.getCell(2).font = { bold: true, size: 12 };
    hdrRow.getCell(2).alignment = { horizontal: 'center' };

    // Group by brand
    const brandMap = new Map<string, AggregatedProduct[]>();
    filteredData.forEach((p) => {
      const brand = (p.brand || 'Autres').trim().toUpperCase();
      if (!brandMap.has(brand)) brandMap.set(brand, []);
      brandMap.get(brand)!.push(p);
    });
    const sortedBrands = [...brandMap.keys()].sort();
    let total = 0;

    sortedBrands.forEach((brand) => {
      const products = brandMap.get(brand)!;

      // Brand header — gold background
      const brandRow = ws.addRow([brand, null]);
      ws.mergeCells(brandRow.number, 1, brandRow.number, 2);
      brandRow.getCell(1).font = { bold: true, size: 12 };
      brandRow.getCell(1).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFFFC000' } };
      brandRow.getCell(1).alignment = { horizontal: 'center' };

      // Group by type within brand
      const typeMap = new Map<string, AggregatedProduct[]>();
      products.forEach((p) => {
        const t = (p.type || '').trim();
        if (!typeMap.has(t)) typeMap.set(t, []);
        typeMap.get(t)!.push(p);
      });
      const multiType = typeMap.size > 1;

      typeMap.forEach((list, type) => {
        if (multiType && type) {
          // Type sub-header — red background, white text
          const typeRow = ws.addRow([type, null]);
          ws.mergeCells(typeRow.number, 1, typeRow.number, 2);
          typeRow.getCell(1).font = { bold: true, size: 12, color: { argb: 'FFFFFFFF' } };
          typeRow.getCell(1).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFC00000' } };
        }

        list.sort((a, b) => (a.description || '').localeCompare(b.description || '', 'fr'));
        list.forEach((p) => {
          const name = p.description || [p.brand, p.model, p.memory, p.color].filter(Boolean).join(' ');
          const price = p.averagePrice > 0 ? p.averagePrice : null;
          const prow = ws.addRow([name, price]);
          prow.getCell(1).font = { bold: true, size: 12 };
          prow.getCell(2).font = { bold: true, size: 12 };
          if (price !== null) prow.getCell(2).numFmt = '#,##0.00';
          total++;
        });
      });
    });

    // Footer
    const footerRow = ws.addRow([
      `Tarif HT TCP incluse / hors DEEE de 2,56\u00a0\u20ac HT par pi\u00e8ce / FRA`,
    ]);
    footerRow.getCell(1).font = { italic: true, size: 11 };

    const buffer = await wb.xlsx.writeBuffer();
    const blob = new Blob([buffer], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `ajt_tarif_s${week}_${getCurrentTimestamp()}.xlsx`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  };

  const refreshData = () => {
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
  };

  const handleRecalculate = async () => {
    setRecalculating(true);
    try {
      const result = await calculateProducts();
      notify(`Recalcul terminé (${result.created} enregistrements)`, 'success');
      refreshData();
    } catch {
      notify('Erreur lors du recalcul', 'error');
    } finally {
      setRecalculating(false);
    }
  };

  const handleExportExcelClient = async () => {
    if (!filteredData.length) return;
    const XLSX_lib = await import('xlsx');
    const rows = filteredData.map((p) => ({
      'Prix de vente': p.averagePrice > 0 ? p.averagePrice : '',
      'Modèle': p.model ?? '',
      'Description': p.description ?? '',
    }));
    const ws = XLSX_lib.utils.json_to_sheet(rows);
    const wb = XLSX_lib.utils.book_new();
    XLSX_lib.utils.book_append_sheet(wb, ws, 'Tarif');
    XLSX_lib.writeFile(wb, `ajt_tarif_${getCurrentTimestamp()}.xlsx`);
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
    const now = new Date().toLocaleString('fr-FR');

    // Detect numeric columns (>50% of values are numbers)
    const numericCols = new Set<string>();
    headers.forEach((h) => {
      const vals = rows.map((r) => r[h]).filter((v) => v !== null && v !== undefined && v !== '');
      if (!vals.length) return;
      if (vals.filter((v) => typeof v === 'number').length / vals.length > 0.5) numericCols.add(h);
    });

    const isMarginCol = (h: string) => h.toLowerCase().includes('marge');

    const fmtCell = (v: any, h: string): string => {
      if (v === null || v === undefined) return '';
      if (typeof v === 'number') {
        if (h.includes('%')) return v.toFixed(1) + '\u202f%';
        if (numericCols.has(h)) return v.toFixed(2);
      }
      return String(v);
    };

    const thHtml = headers
      .map((h, i) => `<th onclick="srt(${i})">${h}<span id="ic${i}"></span></th>`)
      .join('');

    const tbodyHtml = rows
      .map((r) => {
        const cells = headers.map((h) => {
          const v = r[h];
          const raw = typeof v === 'number' ? v : (v ?? '');
          const disp = fmtCell(v, h);
          const isMargin = isMarginCol(h) && typeof v === 'number';
          const cls = isMargin ? (v < 0 ? ' class="neg"' : v > 0 ? ' class="pos"' : '') : '';
          return `<td data-raw="${raw}"${cls}>${disp}</td>`;
        }).join('');
        return `<tr>${cells}</tr>`;
      })
      .join('\n');

    const html = `<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Export TCP / Marges \u2014 AJT Pro</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#0a0a0a;color:#e4e4e7;min-height:100vh}
header{background:#18181b;border-bottom:1px solid #3f3f46;padding:14px 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:20}
.logo{display:flex;align-items:center;gap:8px}
.dot{width:9px;height:9px;border-radius:50%;background:#B8860B;box-shadow:0 0 8px #B8860B88}
.brand{font-size:15px;font-weight:700;color:#B8860B;letter-spacing:.4px}
.sep{color:#3f3f46;margin:0 6px}
.subtitle{font-size:13px;color:#a1a1aa}
.meta{font-size:11px;color:#52525b}
.toolbar{background:#111113;border-bottom:1px solid #27272a;padding:9px 24px;display:flex;align-items:center;gap:10px;position:sticky;top:49px;z-index:19}
.sw{position:relative;flex:1;max-width:340px}
.si{position:absolute;left:9px;top:50%;transform:translateY(-50%);color:#52525b;font-size:13px;pointer-events:none}
input[type=search]{width:100%;background:#1c1c1e;border:1px solid #3f3f46;border-radius:6px;color:#e4e4e7;padding:6px 10px 6px 30px;font-size:13px;outline:none;transition:border-color .15s}
input[type=search]:focus{border-color:#B8860B}
input[type=search]::placeholder{color:#52525b}
.counter{font-size:12px;color:#71717a;margin-left:auto;white-space:nowrap}
.counter b{color:#B8860B}
.wrap{overflow-x:auto;padding:16px 24px 40px}
table{width:100%;border-collapse:collapse;font-size:13px}
thead th{background:#111113;color:#a1a1aa;font-weight:600;text-align:left;padding:9px 12px;white-space:nowrap;border-bottom:2px solid #B8860B;cursor:pointer;user-select:none}
thead th:hover{color:#e4e4e7;background:#1a1a1e}
thead th span{display:inline-block;margin-left:4px;color:#B8860B;font-size:10px;width:10px}
tbody tr{border-bottom:1px solid #1f1f23}
tbody tr:hover{background:rgba(184,134,11,.07)}
tbody td{padding:7px 12px;white-space:nowrap;color:#d4d4d8}
td.pos{color:#4ade80;font-weight:500}
td.neg{color:#f87171;font-weight:500}
.empty{text-align:center;padding:60px 24px;color:#52525b;font-size:14px;display:none}
</style>
</head>
<body>
<header>
  <div class="logo">
    <div class="dot"></div>
    <span class="brand">AJT Pro</span>
    <span class="sep">|</span>
    <span class="subtitle">Export TCP / Marges</span>
  </div>
  <span class="meta">Export\u00e9 le ${now}&nbsp;&nbsp;\u00b7&nbsp;&nbsp;${rows.length} produits</span>
</header>
<div class="toolbar">
  <div class="sw">
    <span class="si">&#128269;</span>
    <input type="search" id="q" placeholder="Rechercher\u2026" oninput="flt()" autocomplete="off">
  </div>
  <div class="counter"><b id="cnt">${rows.length}</b>&thinsp;/&thinsp;${rows.length} r\u00e9sultats</div>
</div>
<div class="wrap">
  <table id="tbl">
    <thead><tr>${thHtml}</tr></thead>
    <tbody id="tb">${tbodyHtml}</tbody>
  </table>
  <div class="empty" id="empty">Aucun r\u00e9sultat pour cette recherche.</div>
</div>
<script>
(function(){
  var sc=-1,sd=1;
  var ar=Array.from(document.querySelectorAll('#tb tr'));
  function gv(row,col){
    var td=row.cells[col];
    if(!td)return'';
    var r=td.getAttribute('data-raw');
    if(r!==null&&r!==''&&!isNaN(Number(r)))return Number(r);
    return td.textContent.trim().toLowerCase();
  }
  window.srt=function(col){
    if(sc===col){sd*=-1;}else{sc=col;sd=1;}
    document.querySelectorAll('thead th span').forEach(function(s){s.textContent='';});
    document.querySelector('#ic'+col).textContent=sd===1?' \u25b2':' \u25bc';
    var tb=document.getElementById('tb');
    ar.sort(function(a,b){
      var av=gv(a,col),bv=gv(b,col);
      if(typeof av==='number'&&typeof bv==='number')return(av-bv)*sd;
      return String(av).localeCompare(String(bv),'fr')*sd;
    });
    ar.forEach(function(r){tb.appendChild(r);});
  };
  window.flt=function(){
    var q=document.getElementById('q').value.trim().toLowerCase();
    var n=0;
    ar.forEach(function(row){
      var txt=Array.from(row.cells).map(function(td){return td.textContent;}).join(' ').toLowerCase();
      var show=!q||txt.includes(q);
      row.style.display=show?'':'none';
      if(show)n++;
    });
    document.getElementById('cnt').textContent=n;
    document.getElementById('empty').style.display=n===0?'':'none';
    document.getElementById('tbl').style.display=n===0?'none':'';
  };
})();
</script>
</body>
</html>`;

    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const filename = `ajt_tcp_${getCurrentTimestamp()}.html`;

    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    window.open(url, '_blank');
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  };

  const paginationControls = (
    <div className="flex items-center justify-between">
      <span className="text-sm text-[var(--color-text-muted)]">
        {filteredData.length} résultat{filteredData.length === 1 ? '' : 's'}
      </span>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1">
          <span className="text-sm text-[var(--color-text-secondary)] mr-1">Lignes</span>
          <select
            id="rowsPerPage"
            value={rowsPerPage}
            onChange={(e) => setRowsPerPage(Number(e.target.value))}
            className="bg-[var(--color-bg-surface)] border border-[var(--color-border-strong)] rounded px-2 py-1 text-sm"
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
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="btn btn-secondary p-1.5 disabled:opacity-30"
            aria-label="Page précédente"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
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
    <div>
      {onBack && (
        <button
          onClick={onBack}
          className="btn btn-secondary mb-6"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>Retour</span>
        </button>
      )}
      <div className="mb-8">
        <h1 className="text-3xl font-semibold text-[var(--color-text-heading)] flex items-center gap-3">
          <Package className="w-8 h-8 text-[#B8860B]" />
          Produits
        </h1>
        <p className="text-[var(--color-text-muted)] mt-1">
          Gérez les prix, marges et le référentiel produits. Semaine en cours : {getCurrentWeekYear()}
        </p>
      </div>
      {role !== 'client' && (
        <div className="border-b border-[var(--color-border-subtle)] mb-6">
          <nav className="flex gap-4">
            <button
              type="button"
              onClick={() => setTab('calculations')}
              className={`px-2 pb-3 text-sm font-medium transition-colors border-b-2 ${
                tab === 'calculations'
                  ? 'border-[#B8860B] text-[var(--color-text-heading)]'
                  : 'border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
              }`}
            >
              TCP/Marges
            </button>
            <button
              type="button"
              onClick={() => setTab('reference')}
              className={`px-2 pb-3 text-sm font-medium transition-colors border-b-2 ${
                tab === 'reference'
                  ? 'border-[#B8860B] text-[var(--color-text-heading)]'
                  : 'border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
              }`}
            >
              Référentiel
            </button>
          </nav>
        </div>
      )}
      {role === 'client' && (
        <>
          <div className="card p-4 mb-6">
            <div className="flex items-center gap-2">
              <button onClick={handleExportExcelClient} className="btn btn-secondary text-sm">
                Export XLSX
              </button>
            </div>
          </div>
          <div className="card overflow-hidden">
            <div className="overflow-auto">
              <ProductTable
                columns={columns}
                baseColumns={baseColumns}
                visibleColumns={visibleColumns}
                paginatedData={paginatedData}
                suppliers={suppliers}
                role={role}
                filters={filters}
                setFilters={setFilters}
                brandOptions={brandOptions}
                colorOptions={colorOptions}
                memoryOptions={memoryOptions}
                typeOptions={typeOptions}
                ramOptions={ramOptions}
                normeOptions={normeOptions}
                sortConfig={sortConfig}
                onSort={handleSort}
              />
            </div>
            <div className="px-4 py-3 border-t border-[var(--color-border-subtle)]">
              {paginationControls}
            </div>
          </div>
        </>
      )}
      {role !== 'client' && tab === 'calculations' && (
        <>
          <div className="card p-4 mb-6 overflow-visible relative z-20">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div className="flex flex-wrap items-center gap-2">
                <div className="relative">
                  <button
                    onClick={() => setShowColumnMenu((s) => !s)}
                    className="btn btn-secondary text-sm"
                  >
                    Colonnes
                  </button>
                  {showColumnMenu && (
                    <div className="absolute z-50 mt-2 p-4 min-w-[10rem] bg-[var(--color-bg-input)] text-[var(--color-text-primary)] border border-[var(--color-border-strong)] rounded-md shadow-2xl flex flex-col gap-2">
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
                <div className="w-px h-6 bg-[var(--color-border-subtle)]" />
                <button
                  onClick={handleRecalculate}
                  disabled={recalculating}
                  className="btn btn-primary text-sm"
                >
                  <RefreshCw className={`w-4 h-4 ${recalculating ? 'animate-spin' : ''}`} />
                  {recalculating ? 'Recalcul...' : 'Recalculer'}
                </button>
                <div className="w-px h-6 bg-[var(--color-border-subtle)]" />
                <button onClick={handleExportExcel} className="btn btn-secondary text-sm">
                  Export Excel
                </button>
                <button onClick={handleExportJSON} className="btn btn-secondary text-sm">
                  Export JSON
                </button>
                <button onClick={handleExportHtml} className="btn btn-secondary text-sm">
                  Génère HTML
                </button>
              </div>
            </div>
          </div>
          <div className="card overflow-hidden">
            <div className="overflow-auto">
              <ProductTable
                columns={columns}
                baseColumns={baseColumns}
                visibleColumns={visibleColumns}
                paginatedData={paginatedData}
                suppliers={suppliers}
                role={role}
                filters={filters}
                setFilters={setFilters}
                brandOptions={brandOptions}
                colorOptions={colorOptions}
                memoryOptions={memoryOptions}
                typeOptions={typeOptions}
                ramOptions={ramOptions}
                normeOptions={normeOptions}
                sortConfig={sortConfig}
                onSort={handleSort}
                onRowClick={role !== 'client' ? setSelectedProduct : undefined}
              />
            </div>
            <div className="px-4 py-3 border-t border-[var(--color-border-subtle)]">
              {paginationControls}
            </div>
          </div>
        </>
      )}
      {role !== 'client' && tab === 'reference' && <ProductReference />}
      {role !== 'client' && selectedProduct && (
        <SupplierPriceModal
          prices={selectedProduct.salePrices}
          stocks={selectedProduct.stockLevels}
          calculations={selectedProduct.latestCalculations}
          currentMargin={selectedProduct.marge}
          currentMarginPercent={selectedProduct.margePercent}
          baseCost={getBaseBuyPrice(selectedProduct) + (Number.isFinite(selectedProduct.tcp) ? selectedProduct.tcp : 0)}
          recommendedPrice={selectedProduct.averagePrice}
          onUpdateMargin={(margin, percent) => handleProductMarginUpdate(selectedProduct.id, margin, percent)}
          onClose={() => setSelectedProduct(null)}
        />
      )}
    </div>
  );
}

export default ProductsPage;
