import { ArrowLeft, BarChart3 } from 'lucide-react';
import InfoButton from './InfoButton';
import StatsFilters from './StatsFilters';
import PriceChart from './PriceChart';
import BrandSupplierChart from './BrandSupplierChart';
import ProductEvolutionChart from './ProductEvolutionChart';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  fetchPriceStats,
  fetchSuppliers,
  fetchBrands,
  fetchProducts,
  fetchBrandSupplierAverage,
  fetchProductSupplierAverage,
  fetchGraphSettings,
  updateGraphSetting,
} from '../api';

interface PriceStat {
  supplier?: string;
  brand?: string;
  week: string;
  avg_price: number;
}

interface BrandSupplierAvg {
  supplier: string;
  brand: string;
  avg_price: number;
}

interface ProductSupplierAvg {
  supplier: string;
  product: string;
  avg_price: number;
}

interface StatisticsPageProps {
  onBack?: () => void;
}

export interface ProductItem {
  id: number;
  model: string;
  brand_id: number | null;
}

export interface Point {
  label: string;
  value: number;
}

export const GRAPH_OPTIONS = [
  { key: 'global', label: 'Vue globale' },
  { key: 'brandSupplier', label: 'Prix moyen marque/fournisseur' },
  { key: 'productSupplier', label: 'Prix moyen produit/fournisseur' },
  { key: 'product', label: 'Évolution du produit' },
  { key: 'relative', label: 'Évolution relative (%)' },
  { key: 'distribution', label: 'Distribution des prix' },
  { key: 'stdev', label: 'Écart-type par fournisseur' },
  { key: 'range', label: 'Prix min/max par semaine' },
  { key: 'index', label: 'Indice des prix' },
  { key: 'correlation', label: 'Corrélation des prix' },
  { key: 'anomalies', label: 'Anomalies détectées' },
];

function LineChart({ data }: { data: Point[] }) {
  const width = 700;
  const height = 320;
  const padding = 40;

  if (!data.length) {
    return (
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full h-80 bg-[var(--color-bg-surface)] rounded"
      />
    );
  }

  const maxVal = Math.max(...data.map((d) => d.value)) * 1.1;
  const stepX = (width - padding * 2) / Math.max(1, data.length - 1);

  const points = data.map((d, i) => {
    const x = padding + i * stepX;
    const y = height - padding - (d.value / maxVal) * (height - padding * 2);
    return { x, y };
  });

  const path = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`)
    .join(' ');

  const ticks = 4;
  const stepY = (height - padding * 2) / ticks;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full h-80 bg-[var(--color-bg-surface)] rounded"
      preserveAspectRatio="xMidYMid meet"
    >
      {Array.from({ length: ticks + 1 }).map((_, i) => (
        <line
          key={i}
          x1={padding}
          y1={height - padding - i * stepY}
          x2={width - padding}
          y2={height - padding - i * stepY}
          stroke="var(--color-chart-grid)"
        />
      ))}
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="var(--color-chart-axis)" />
      <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="var(--color-chart-axis)" />
      {data.map((d, i) => (
        <text key={d.label} x={padding + i * stepX} y={height - padding + 15} fontSize="10" textAnchor="middle" fill="var(--color-chart-text)">
          {d.label}
        </text>
      ))}
      {Array.from({ length: ticks + 1 }).map((_, i) => (
        <text key={i} x={padding - 5} y={height - padding - i * stepY + 4} fontSize="10" textAnchor="end" fill="var(--color-chart-text)">
          {((maxVal / ticks) * i).toFixed(0)}
        </text>
      ))}
      <path d={path} fill="none" stroke="#B8860B" strokeWidth="2" />
      {points.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={3} fill="#B8860B" />
      ))}
    </svg>
  );
}

function MultiLineChart({ series }: { series: { name: string; data: Point[] }[] }) {
  const width = 700;
  const height = 320;
  const padding = 40;
  const all = series.flatMap((s) => s.data);

  if (!all.length) {
    return (
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full h-80 bg-[var(--color-bg-surface)] rounded"
      />
    );
  }

  const maxVal = Math.max(...all.map((d) => d.value)) * 1.1;
  const labels = Array.from(new Set(all.map((d) => d.label))).sort();
  const stepX = (width - padding * 2) / Math.max(1, labels.length - 1);
  const ticks = 4;
  const stepY = (height - padding * 2) / ticks;
  const colors = ['#B8860B', '#38bdf8', '#22c55e', '#e879f9', '#facc15', '#f43f5e'];

  const seriesPaths = series.map((s, idx) => {
    const pts = labels.map((l) => {
      const found = s.data.find((d) => d.label === l);
      return {
        x: padding + labels.indexOf(l) * stepX,
        y: found ? height - padding - (found.value / maxVal) * (height - padding * 2) : null,
      };
    });
    const valid = pts.filter((p) => p.y !== null) as { x: number; y: number }[];
    const path = valid.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ');
    return { name: s.name, color: colors[idx % colors.length], points: valid, path };
  });

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full h-80 bg-[var(--color-bg-surface)] rounded"
      preserveAspectRatio="xMidYMid meet"
    >
      {Array.from({ length: ticks + 1 }).map((_, i) => (
        <line key={i} x1={padding} y1={height - padding - i * stepY} x2={width - padding} y2={height - padding - i * stepY} stroke="var(--color-chart-grid)" />
      ))}
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="var(--color-chart-axis)" />
      <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="var(--color-chart-axis)" />
      {labels.map((l, i) => (
        <text key={l} x={padding + i * stepX} y={height - padding + 15} fontSize="10" textAnchor="middle" fill="var(--color-chart-text)">
          {l}
        </text>
      ))}
      {Array.from({ length: ticks + 1 }).map((_, i) => (
        <text key={i} x={padding - 5} y={height - padding - i * stepY + 4} fontSize="10" textAnchor="end" fill="var(--color-chart-text)">
          {((maxVal / ticks) * i).toFixed(0)}
        </text>
      ))}
      {seriesPaths.map((s) => (
        <g key={s.name}>
          <path d={s.path} fill="none" stroke={s.color} strokeWidth="2" />
          {s.points.map((p, i) => (
            <circle key={i} cx={p.x} cy={p.y} r={3} fill={s.color} />
          ))}
        </g>
      ))}
    </svg>
  );
}

function BarChart({ data }: { data: Point[] }) {
  const width = 700;
  const height = 320;
  const padding = 40;

  if (!data.length) {
    return (
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full h-80 bg-[var(--color-bg-surface)] rounded"
      />
    );
  }

  const maxVal = Math.max(...data.map((d) => d.value)) * 1.1;
  const stepX = (width - padding * 2) / data.length;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full h-80 bg-[var(--color-bg-surface)] rounded"
      preserveAspectRatio="xMidYMid meet"
    >
      {data.map((d, i) => {
        const x = padding + i * stepX;
        const barH = (d.value / maxVal) * (height - padding * 2);
        return (
          <g key={d.label}>
            <rect
              x={x + 5}
              y={height - padding - barH}
              width={stepX - 10}
              height={barH}
              fill="#B8860B"
            />
            <text
              x={x + stepX / 2}
              y={height - padding + 15}
              fontSize="10"
              textAnchor="middle"
              fill="var(--color-chart-text)"
            >
              {d.label}
            </text>
          </g>
        );
      })}
      {Array.from({ length: 4 + 1 }).map((_, i) => (
        <text
          key={i}
          x={padding - 5}
          y={height - padding - ((height - padding * 2) / 4) * i + 4}
          fontSize="10"
          textAnchor="end"
          fill="var(--color-chart-text)"
        >
          {((maxVal / 4) * i).toFixed(0)}
        </text>
      ))}
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="var(--color-chart-axis)" />
      <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="var(--color-chart-axis)" />
    </svg>
  );
}

function RangeChart({ data }: { data: { label: string; min: number; max: number }[] }) {
  const width = 700;
  const height = 320;
  const padding = 40;

  if (!data.length) {
    return (
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full h-80 bg-[var(--color-bg-surface)] rounded"
      />
    );
  }

  const maxVal = Math.max(...data.map((d) => d.max)) * 1.1;
  const stepX = (width - padding * 2) / Math.max(1, data.length - 1);

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full h-80 bg-[var(--color-bg-surface)] rounded"
      preserveAspectRatio="xMidYMid meet"
    >
      {data.map((d, i) => {
        const x = padding + i * stepX;
        const yMin = height - padding - (d.min / maxVal) * (height - padding * 2);
        const yMax = height - padding - (d.max / maxVal) * (height - padding * 2);
        return (
          <g key={d.label}>
            <line x1={x} y1={yMin} x2={x} y2={yMax} stroke="#B8860B" strokeWidth="4" />
            <text x={x} y={height - padding + 15} fontSize="10" textAnchor="middle" fill="var(--color-chart-text)">
              {d.label}
            </text>
          </g>
        );
      })}
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="var(--color-chart-axis)" />
      <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="var(--color-chart-axis)" />
    </svg>
  );
}

function Heatmap({ labels, matrix }: { labels: string[]; matrix: number[][] }) {
  if (!labels.length) {
    return <div className="h-40" />;
  }

  const color = (v: number) => {
    const t = Math.max(-1, Math.min(1, v));
    const r = Math.round(255 * (t < 0 ? 1 : 1 - t));
    const g = Math.round(255 * (t > 0 ? 1 : 1 + t));
    return `rgb(${r},${g},150)`;
  };

  return (
    <table className="border-collapse">
      <thead>
        <tr>
          <th className="w-20" />
          {labels.map((l) => (
            <th key={l} className="text-xs px-2">
              {l}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {labels.map((row, i) => (
          <tr key={row}>
            <th className="text-xs pr-2 text-right">{row}</th>
            {labels.map((col, j) => (
              <td key={col} style={{ backgroundColor: color(matrix[i][j]) }} className="w-10 h-6 text-center text-xs">
                {matrix[i][j].toFixed(2)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function StatisticsPage({ onBack }: StatisticsPageProps) {
  const [globalStats, setGlobalStats] = useState<PriceStat[]>([]);
  const [productStats, setProductStats] = useState<PriceStat[]>([]);
  const [brandSupplierStats, setBrandSupplierStats] = useState<BrandSupplierAvg[]>([]);
  const [productSupplierStats, setProductSupplierStats] = useState<ProductSupplierAvg[]>([]);
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [brands, setBrands] = useState<any[]>([]);
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [graphVisible, setGraphVisible] = useState<Record<string, boolean>>({});

  const [supplierId, setSupplierId] = useState<number | ''>('');
  const [brandId, setBrandId] = useState<number | ''>('');
  const [productId, setProductId] = useState<number | ''>('');
  const [startWeek, setStartWeek] = useState('');
  const [endWeek, setEndWeek] = useState('');

  useEffect(() => {
    fetchSuppliers().then((s) => setSuppliers(s as any[])).catch(() => setSuppliers([]));
    fetchBrands().then((b) => setBrands(b as any[])).catch(() => setBrands([]));
    fetchProducts().then((p) => setProducts(p as ProductItem[])).catch(() => setProducts([]));
    fetchGraphSettings()
      .then((gs) => {
        const vis: Record<string, boolean> = {};
        (gs as any[]).forEach((g) => {
          vis[g.name] = g.visible;
        });
        GRAPH_OPTIONS.forEach((o) => {
          if (!(o.key in vis)) vis[o.key] = true;
        });
        setGraphVisible(vis);
      })
      .catch(() => {
        const vis: Record<string, boolean> = {};
        GRAPH_OPTIONS.forEach((o) => (vis[o.key] = true));
        setGraphVisible(vis);
      });
  }, []);

  const toggleGraph = (key: string) => {
    setGraphVisible((prev) => {
      const newVal = !prev[key];
      const next = { ...prev, [key]: newVal };
      updateGraphSetting(key, newVal).catch(() => undefined);
      return next;
    });
  };

  const toApiWeek = (val: string) => {
    if (!val) return undefined;
    const [year, week] = val.split('-W');
    return `S${week}-${year}`;
  };

  const loadGlobal = useCallback(() => {
    fetchPriceStats({
      supplierId: supplierId ? Number(supplierId) : undefined,
      brandId: brandId ? Number(brandId) : undefined,
      startWeek: toApiWeek(startWeek),
      endWeek: toApiWeek(endWeek),
    })
      .then((res) => setGlobalStats(res as PriceStat[]))
      .catch(() => setGlobalStats([]));
  }, [supplierId, brandId, startWeek, endWeek]);

  const loadBrandSupplier = useCallback(() => {
    fetchBrandSupplierAverage({
      supplierId: supplierId ? Number(supplierId) : undefined,
      brandId: brandId ? Number(brandId) : undefined,
      startWeek: toApiWeek(startWeek),
      endWeek: toApiWeek(endWeek),
    })
      .then((res) => setBrandSupplierStats(res as BrandSupplierAvg[]))
      .catch(() => setBrandSupplierStats([]));
  }, [supplierId, brandId, startWeek, endWeek]);

  const loadProductSupplier = useCallback(() => {
    fetchProductSupplierAverage({
      supplierId: supplierId ? Number(supplierId) : undefined,
      brandId: brandId ? Number(brandId) : undefined,
      productId: productId ? Number(productId) : undefined,
      startWeek: toApiWeek(startWeek),
      endWeek: toApiWeek(endWeek),
    })
      .then((res) => setProductSupplierStats(res as ProductSupplierAvg[]))
      .catch(() => setProductSupplierStats([]));
  }, [supplierId, brandId, productId, startWeek, endWeek]);

  const loadProduct = useCallback(() => {
    if (!productId) {
      setProductStats([]);
      return;
    }
    fetchPriceStats({
      productId: Number(productId),
      startWeek: toApiWeek(startWeek),
      endWeek: toApiWeek(endWeek),
    })
      .then((res) => setProductStats(res as PriceStat[]))
      .catch(() => setProductStats([]));
  }, [productId, startWeek, endWeek]);

  useEffect(() => {
    loadGlobal();
  }, [loadGlobal]);

  useEffect(() => {
    loadProduct();
  }, [loadProduct]);

  useEffect(() => {
    loadBrandSupplier();
  }, [loadBrandSupplier]);

  useEffect(() => {
    loadProductSupplier();
  }, [loadProductSupplier]);

  const filteredProducts = useMemo(
    () => products.filter((p) => (brandId ? p.brand_id === Number(brandId) : true)),
    [products, brandId]
  );

  const globalData = useMemo(() => {
    const map: Record<string, { sum: number; count: number }> = {};
    globalStats.forEach((s) => {
      if (!map[s.week]) {
        map[s.week] = { sum: s.avg_price, count: 1 };
      } else {
        map[s.week].sum += s.avg_price;
        map[s.week].count += 1;
      }
    });
    return Object.entries(map)
      .map(([week, { sum, count }]) => ({ label: week, value: sum / count }))
      .sort((a, b) => a.label.localeCompare(b.label));
  }, [globalStats]);

  const productSeries = useMemo(() => {
    const map: Record<string, Point[]> = {};
    productStats.forEach((s) => {
      if (!s.supplier) return;
      if (!map[s.supplier]) map[s.supplier] = [];
      map[s.supplier].push({ label: s.week, value: s.avg_price });
    });
    return Object.entries(map).map(([name, data]) => ({
      name,
      data: data.sort((a, b) => a.label.localeCompare(b.label)),
    }));
  }, [productStats]);

  const relativeData = useMemo(() => {
    const sorted = globalData.slice().sort((a, b) => a.label.localeCompare(b.label));
    return sorted.map((cur, i) => {
      if (i === 0) return { label: cur.label, value: 0 };
      const prev = sorted[i - 1].value;
      const pct = prev ? ((cur.value - prev) / prev) * 100 : 0;
      return { label: cur.label, value: pct };
    });
  }, [globalData]);

  const distributionData = useMemo(() => {
    if (!globalStats.length) return [] as Point[];
    const values = globalStats.map((s) => s.avg_price);
    const bins = 10;
    const min = Math.min(...values);
    const max = Math.max(...values);
    const step = (max - min) / bins || 1;
    const result: Point[] = [];
    for (let i = 0; i < bins; i++) {
      const start = min + i * step;
      const end = start + step;
      const count = values.filter((v) => v >= start && v < end).length;
      result.push({ label: `${(start).toFixed(0)}-${(end).toFixed(0)}`, value: count });
    }
    return result;
  }, [globalStats]);

  const stdevData = useMemo(() => {
    const map: Record<string, number[]> = {};
    productStats.forEach((s) => {
      if (!s.supplier) return;
      if (!map[s.supplier]) map[s.supplier] = [];
      map[s.supplier].push(s.avg_price);
    });
    const calc = (arr: number[]) => {
      const mean = arr.reduce((a, b) => a + b, 0) / arr.length;
      const variance = arr.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / arr.length;
      return Math.sqrt(variance);
    };
    return Object.entries(map).map(([name, arr]) => ({ label: name, value: calc(arr) }));
  }, [productStats]);

  const rangeData = useMemo(() => {
    const map: Record<string, { min: number; max: number }> = {};
    productStats.forEach((s) => {
      if (!map[s.week]) map[s.week] = { min: s.avg_price, max: s.avg_price };
      else {
        map[s.week].min = Math.min(map[s.week].min, s.avg_price);
        map[s.week].max = Math.max(map[s.week].max, s.avg_price);
      }
    });
    return Object.entries(map)
      .map(([week, { min, max }]) => ({ label: week, min, max }))
      .sort((a, b) => a.label.localeCompare(b.label));
  }, [productStats]);

  const priceIndexData = useMemo(() => {
    if (!globalData.length) return [] as Point[];
    const base = globalData[0].value || 1;
    return globalData.map((d) => ({ label: d.label, value: (d.value / base) * 100 }));
  }, [globalData]);

  const correlationMatrix = useMemo(() => {
    const suppliersNames = Array.from(new Set(productStats.map((p) => p.supplier).filter(Boolean))) as string[];
    const weeks = Array.from(new Set(productStats.map((p) => p.week))).sort();
    const bySupplier: Record<string, (number | null)[]> = {};
    suppliersNames.forEach((s) => {
      bySupplier[s] = weeks.map((w) => {
        const rec = productStats.find((p) => p.supplier === s && p.week === w);
        return rec ? rec.avg_price : null;
      });
    });
    const corr = (a: (number | null)[], b: (number | null)[]) => {
      const pairs = a.map((v, i) => [v, b[i]] as [number | null, number | null]).filter((p) => p[0] !== null && p[1] !== null) as [number, number][];
      const n = pairs.length;
      if (n < 2) return 0;
      const mean1 = pairs.reduce((s, [x]) => s + x, 0) / n;
      const mean2 = pairs.reduce((s, [, y]) => s + y, 0) / n;
      const num = pairs.reduce((s, [x, y]) => s + (x - mean1) * (y - mean2), 0);
      const den1 = Math.sqrt(pairs.reduce((s, [x]) => s + Math.pow(x - mean1, 2), 0));
      const den2 = Math.sqrt(pairs.reduce((s, [, y]) => s + Math.pow(y - mean2, 2), 0));
      const den = den1 * den2;
      return den ? num / den : 0;
    };
    const matrix = suppliersNames.map((s1) => suppliersNames.map((s2) => corr(bySupplier[s1], bySupplier[s2])));
    return { labels: suppliersNames, matrix };
  }, [productStats]);

  const brandSupplierSeries = useMemo(() => {
    const map: Record<string, Point[]> = {};
    brandSupplierStats.forEach((s) => {
      if (!map[s.supplier]) map[s.supplier] = [];
      map[s.supplier].push({ label: s.brand, value: s.avg_price });
    });
    return Object.entries(map).map(([name, data]) => ({
      name,
      data: data.sort((a, b) => a.label.localeCompare(b.label)),
    }));
  }, [brandSupplierStats]);

  const productSupplierSeries = useMemo(() => {
    const map: Record<string, Point[]> = {};
    productSupplierStats.forEach((s) => {
      if (!map[s.supplier]) map[s.supplier] = [];
      map[s.supplier].push({ label: s.product, value: s.avg_price });
    });
    return Object.entries(map).map(([name, data]) => ({
      name,
      data: data.sort((a, b) => a.label.localeCompare(b.label)),
    }));
  }, [productSupplierStats]);

  const anomalies = useMemo(() => {
    const sorted = globalData.slice().sort((a, b) => a.label.localeCompare(b.label));
    const arr: { week: string; change: number }[] = [];
    for (let i = 1; i < sorted.length; i++) {
      const prev = sorted[i - 1].value;
      const curr = sorted[i].value;
      if (prev && Math.abs((curr - prev) / prev) >= 0.2) {
        arr.push({ week: sorted[i].label, change: ((curr - prev) / prev) * 100 });
      }
    }
    return arr;
  }, [globalData]);

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold text-[var(--color-text-heading)] flex items-center gap-3">
            <BarChart3 className="w-8 h-8 text-[#B8860B]" />
            Statistiques de prix
          </h1>
          <p className="text-[var(--color-text-muted)] mt-1">
            Analyse graphique des prix, marges et tendances fournisseurs
          </p>
        </div>
        {onBack && (
          <button
            onClick={onBack}
            className="btn btn-secondary"
          >
            <ArrowLeft className="w-5 h-5" />
            <span>Retour</span>
          </button>
        )}
      </div>
      <StatsFilters
        supplierId={supplierId}
        setSupplierId={setSupplierId}
        brandId={brandId}
        setBrandId={setBrandId}
        productId={productId}
        setProductId={setProductId}
        startWeek={startWeek}
        setStartWeek={setStartWeek}
        endWeek={endWeek}
        setEndWeek={setEndWeek}
        suppliers={suppliers}
        brands={brands}
        filteredProducts={filteredProducts}
        graphVisible={graphVisible}
        toggleGraph={toggleGraph}
        graphOptions={GRAPH_OPTIONS}
      />
      <div className="space-y-6">
        {graphVisible.global && (
          <div className="card overflow-hidden">
            <PriceChart globalData={globalData} brandId={brandId} />
          </div>
        )}
        {graphVisible.brandSupplier && (
          <div className="card overflow-hidden">
            <BrandSupplierChart brandSupplierSeries={brandSupplierSeries} />
          </div>
        )}
        {graphVisible.productSupplier && (
          <div className="card overflow-hidden">
            <ProductEvolutionChart productSupplierSeries={productSupplierSeries} />
          </div>
        )}
        {graphVisible.product && (
        <div className="card overflow-hidden">
          <h2 className="font-semibold mb-2 flex items-center">Évolution du produit<InfoButton text="Comparer l'évolution du prix du produit selon les fournisseurs." /></h2>
          <MultiLineChart series={productSeries} />
          {productId && productSeries.length === 0 && (
            <p className="text-center text-sm text-[var(--color-text-muted)] mt-2">
              Pas de données pour ce produit
            </p>
          )}
        </div>
        )}
        {graphVisible.relative && (
        <div className="card overflow-hidden">
          <h2 className="font-semibold mb-2 flex items-center">Évolution relative (%)<InfoButton text="Variation en pourcentage d'une semaine sur l'autre." /></h2>
          <LineChart data={relativeData} />
        </div>
        )}
        {graphVisible.distribution && (
        <div className="card overflow-hidden">
          <h2 className="font-semibold mb-2 flex items-center">Distribution des prix<InfoButton text="Répartition des prix moyens pour identifier les valeurs atypiques." /></h2>
          <BarChart data={distributionData} />
        </div>
        )}
        {graphVisible.stdev && (
        <div className="card overflow-hidden">
          <h2 className="font-semibold mb-2 flex items-center">Écart-type par fournisseur<InfoButton text="Mesure la dispersion des prix pour chaque fournisseur." /></h2>
          <BarChart data={stdevData} />
        </div>
        )}
        {graphVisible.range && (
        <div className="card overflow-hidden">
          <h2 className="font-semibold mb-2 flex items-center">Prix min/max par semaine<InfoButton text="Fourchette des prix observés chaque semaine." /></h2>
          <RangeChart data={rangeData} />
        </div>
        )}
        {graphVisible.index && (
        <div className="card overflow-hidden">
          <h2 className="font-semibold mb-2 flex items-center">Indice des prix (base 100)<InfoButton text="Indice basé sur la première semaine pour suivre l'évolution globale." /></h2>
          <LineChart data={priceIndexData} />
        </div>
        )}
        {graphVisible.correlation && (
        <div className="card overflow-hidden">
          <h2 className="font-semibold mb-2 flex items-center">Corrélation des prix<InfoButton text="Met en évidence les fournisseurs ayant des évolutions similaires." /></h2>
          <Heatmap labels={correlationMatrix.labels} matrix={correlationMatrix.matrix} />
        </div>
        )}
        {graphVisible.anomalies && (
        <div className="card overflow-hidden">
          <h2 className="font-semibold mb-2 flex items-center">Anomalies détectées<InfoButton text="Signale les variations supérieures à 20\u00a0% d'une semaine sur l'autre." /></h2>
          {anomalies.length ? (
            <table className="table border-0">
              <thead>
                <tr>
                  <th>Semaine</th>
                  <th>Variation %</th>
                </tr>
              </thead>
              <tbody>
                {anomalies.map((a) => (
                  <tr key={a.week}>
                    <td>{a.week}</td>
                    <td className="text-red-400">{a.change.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-center text-sm text-[var(--color-text-muted)]">Aucune anomalie</p>
          )}
        </div>
        )}
      </div>
    </div>
  );
}

export default StatisticsPage;
