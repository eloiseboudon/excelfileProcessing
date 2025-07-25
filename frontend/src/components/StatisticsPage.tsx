import { ArrowLeft } from 'lucide-react';
import InfoButton from './InfoButton';
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
  onBack: () => void;
}

interface ProductItem {
  id: number;
  model: string;
  brand_id: number | null;
}

interface Point {
  label: string;
  value: number;
}

const GRAPH_OPTIONS = [
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
        className="w-full h-80 bg-zinc-900 rounded"
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
      className="w-full h-80 bg-zinc-900 rounded"
      preserveAspectRatio="xMidYMid meet"
    >
      {Array.from({ length: ticks + 1 }).map((_, i) => (
        <line
          key={i}
          x1={padding}
          y1={height - padding - i * stepY}
          x2={width - padding}
          y2={height - padding - i * stepY}
          stroke="#333"
        />
      ))}
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="white" />
      <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="white" />
      {data.map((d, i) => (
        <text key={d.label} x={padding + i * stepX} y={height - padding + 15} fontSize="10" textAnchor="middle" fill="white">
          {d.label}
        </text>
      ))}
      {Array.from({ length: ticks + 1 }).map((_, i) => (
        <text key={i} x={padding - 5} y={height - padding - i * stepY + 4} fontSize="10" textAnchor="end" fill="white">
          {((maxVal / ticks) * i).toFixed(0)}
        </text>
      ))}
      <path d={path} fill="none" stroke="orange" strokeWidth="2" />
      {points.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={3} fill="orange" />
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
        className="w-full h-80 bg-zinc-900 rounded"
      />
    );
  }

  const maxVal = Math.max(...all.map((d) => d.value)) * 1.1;
  const labels = Array.from(new Set(all.map((d) => d.label))).sort();
  const stepX = (width - padding * 2) / Math.max(1, labels.length - 1);
  const ticks = 4;
  const stepY = (height - padding * 2) / ticks;
  const colors = ['#f97316', '#38bdf8', '#22c55e', '#e879f9', '#facc15', '#f43f5e'];

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
      className="w-full h-80 bg-zinc-900 rounded"
      preserveAspectRatio="xMidYMid meet"
    >
      {Array.from({ length: ticks + 1 }).map((_, i) => (
        <line key={i} x1={padding} y1={height - padding - i * stepY} x2={width - padding} y2={height - padding - i * stepY} stroke="#333" />
      ))}
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="white" />
      <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="white" />
      {labels.map((l, i) => (
        <text key={l} x={padding + i * stepX} y={height - padding + 15} fontSize="10" textAnchor="middle" fill="white">
          {l}
        </text>
      ))}
      {Array.from({ length: ticks + 1 }).map((_, i) => (
        <text key={i} x={padding - 5} y={height - padding - i * stepY + 4} fontSize="10" textAnchor="end" fill="white">
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
        className="w-full h-80 bg-zinc-900 rounded"
      />
    );
  }

  const maxVal = Math.max(...data.map((d) => d.value)) * 1.1;
  const stepX = (width - padding * 2) / data.length;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full h-80 bg-zinc-900 rounded"
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
              fill="#f97316"
            />
            <text
              x={x + stepX / 2}
              y={height - padding + 15}
              fontSize="10"
              textAnchor="middle"
              fill="white"
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
          fill="white"
        >
          {((maxVal / 4) * i).toFixed(0)}
        </text>
      ))}
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="white" />
      <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="white" />
    </svg>
  );
}

function GroupedBarChart({
  series,
}: {
  series: { name: string; data: Point[] }[];
}) {
  const width = 700;
  const height = 320;
  const padding = 40;

  const all = series.flatMap((s) => s.data);
  if (!all.length) {
    return (
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full h-80 bg-zinc-900 rounded"
      />
    );
  }

  const labels = Array.from(new Set(all.map((d) => d.label))).sort();
  const maxVal = Math.max(...all.map((d) => d.value)) * 1.1;
  const stepX = (width - padding * 2) / labels.length;
  const barWidth = (stepX - 10) / series.length;
  const colors = ['#f97316', '#38bdf8', '#22c55e', '#e879f9', '#facc15', '#f43f5e'];

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full h-80 bg-zinc-900 rounded"
      preserveAspectRatio="xMidYMid meet"
    >
      {labels.map((l, i) => (
        <text
          key={l}
          x={padding + i * stepX + stepX / 2}
          y={height - padding + 15}
          fontSize="10"
          textAnchor="middle"
          fill="white"
        >
          {l}
        </text>
      ))}
      {series.map((s, si) => (
        <g key={s.name}>
          {labels.map((l, li) => {
            const found = s.data.find((d) => d.label === l);
            if (!found) return null;
            const barH = (found.value / maxVal) * (height - padding * 2);
            const x = padding + li * stepX + 5 + si * barWidth;
            return (
              <rect
                key={l}
                x={x}
                y={height - padding - barH}
                width={barWidth - 2}
                height={barH}
                fill={colors[si % colors.length]}
              />
            );
          })}
        </g>
      ))}
      {Array.from({ length: 4 + 1 }).map((_, i) => (
        <text
          key={i}
          x={padding - 5}
          y={height - padding - ((height - padding * 2) / 4) * i + 4}
          fontSize="10"
          textAnchor="end"
          fill="white"
        >
          {((maxVal / 4) * i).toFixed(0)}
        </text>
      ))}
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="white" />
      <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="white" />
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
        className="w-full h-80 bg-zinc-900 rounded"
      />
    );
  }

  const maxVal = Math.max(...data.map((d) => d.max)) * 1.1;
  const stepX = (width - padding * 2) / Math.max(1, data.length - 1);

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full h-80 bg-zinc-900 rounded"
      preserveAspectRatio="xMidYMid meet"
    >
      {data.map((d, i) => {
        const x = padding + i * stepX;
        const yMin = height - padding - (d.min / maxVal) * (height - padding * 2);
        const yMax = height - padding - (d.max / maxVal) * (height - padding * 2);
        return (
          <g key={d.label}>
            <line x1={x} y1={yMin} x2={x} y2={yMax} stroke="#38bdf8" strokeWidth="4" />
            <text x={x} y={height - padding + 15} fontSize="10" textAnchor="middle" fill="white">
              {d.label}
            </text>
          </g>
        );
      })}
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="white" />
      <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="white" />
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
    <div className="max-w-7xl mx-auto px-1 sm:px-2 py-6 sm:py-8">
      <button
        onClick={onBack}
        className="flex items-center space-x-2 px-4 py-2 bg-zinc-800 text-white rounded-lg hover:bg-zinc-700 transition-colors mb-6"
      >
        <ArrowLeft className="w-5 h-5" />
        <span>Retour</span>
      </button>
      <h1 className="text-2xl font-bold text-center mb-4">Statistiques de prix</h1>
      <div className="flex flex-wrap gap-4 mb-6 items-end">
        <select
          value={supplierId}
          onChange={(e) => setSupplierId(e.target.value ? Number(e.target.value) : '')}
          className="bg-zinc-900 border border-zinc-600 rounded px-2 py-1"
        >
          <option value="">Tous fournisseurs</option>
          {suppliers.map((s: any) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        <select
          value={brandId}
          onChange={(e) => setBrandId(e.target.value ? Number(e.target.value) : '')}
          className="bg-zinc-900 border border-zinc-600 rounded px-2 py-1"
        >
          <option value="">Toutes marques</option>
          {brands.map((b: any) => (
            <option key={b.id} value={b.id}>
              {b.brand}
            </option>
          ))}
        </select>
        <input
          type="week"
          value={startWeek}
          onChange={(e) => setStartWeek(e.target.value)}
          className="bg-zinc-900 border border-zinc-600 rounded px-2 py-1"
        />
        <input
          type="week"
          value={endWeek}
          onChange={(e) => setEndWeek(e.target.value)}
          className="bg-zinc-900 border border-zinc-600 rounded px-2 py-1"
        />
        <select
          value={productId}
          onChange={(e) => setProductId(e.target.value ? Number(e.target.value) : '')}
          className="bg-zinc-900 border border-zinc-600 rounded px-2 py-1"
        >
          <option value="">Choisir un produit</option>
          {filteredProducts.map((p) => (
            <option key={p.id} value={p.id}>
              {p.model}
            </option>
          ))}
        </select>
      </div>
      <div className="flex flex-wrap gap-4 mb-6">
        {GRAPH_OPTIONS.map((opt) => (
          <label key={opt.key} className="flex items-center space-x-1 text-sm">
            <input
              type="checkbox"
              checked={graphVisible[opt.key] ?? true}
              onChange={() => toggleGraph(opt.key)}
              className="accent-orange-500"
            />
            <span>{opt.label}</span>
          </label>
        ))}
      </div>
      <div className="overflow-x-auto space-y-8">
        {graphVisible.global && (
        <div>
          <h2 className="font-semibold mb-2 flex items-center">Vue globale<InfoButton text="Prix moyen toutes marques et fournisseurs pour chaque semaine." /></h2>
          <LineChart data={globalData} />
          {globalData.length === 0 && (
            <p className="text-center text-sm text-zinc-400 mt-2">
              {brandId ? 'Pas de données pour cette marque' : 'Pas de données'}
            </p>
          )}
        </div>
        )}
        {graphVisible.brandSupplier && (
        <div>
          <h2 className="font-semibold mb-2 flex items-center">Prix moyen marque/fournisseur<InfoButton text="Compare les prix moyens par marque selon les fournisseurs." /></h2>
          <GroupedBarChart series={brandSupplierSeries} />
          {brandSupplierSeries.length === 0 && (
            <p className="text-center text-sm text-zinc-400 mt-2">Pas de données</p>
          )}
        </div>
        )}
        {graphVisible.productSupplier && (
        <div>
          <h2 className="font-semibold mb-2 flex items-center">Prix moyen produit/fournisseur<InfoButton text="Compare les prix moyens par produit selon les fournisseurs." /></h2>
          <GroupedBarChart series={productSupplierSeries} />
          {productSupplierSeries.length === 0 && (
            <p className="text-center text-sm text-zinc-400 mt-2">Pas de données</p>
          )}
        </div>
        )}
        {graphVisible.product && (
        <div>
          <h2 className="font-semibold mb-2 flex items-center">Évolution du produit<InfoButton text="Comparer l'évolution du prix du produit selon les fournisseurs." /></h2>
          <MultiLineChart series={productSeries} />
          {productId && productSeries.length === 0 && (
            <p className="text-center text-sm text-zinc-400 mt-2">
              Pas de données pour ce produit
            </p>
          )}
        </div>
        )}
        {graphVisible.relative && (
        <div>
          <h2 className="font-semibold mb-2 flex items-center">Évolution relative (%)<InfoButton text="Variation en pourcentage d'une semaine sur l'autre." /></h2>
          <LineChart data={relativeData} />
        </div>
        )}
        {graphVisible.distribution && (
        <div>
          <h2 className="font-semibold mb-2 flex items-center">Distribution des prix<InfoButton text="Répartition des prix moyens pour identifier les valeurs atypiques." /></h2>
          <BarChart data={distributionData} />
        </div>
        )}
        {graphVisible.stdev && (
        <div>
          <h2 className="font-semibold mb-2 flex items-center">Écart-type par fournisseur<InfoButton text="Mesure la dispersion des prix pour chaque fournisseur." /></h2>
          <BarChart data={stdevData} />
        </div>
        )}
        {graphVisible.range && (
        <div>
          <h2 className="font-semibold mb-2 flex items-center">Prix min/max par semaine<InfoButton text="Fourchette des prix observés chaque semaine." /></h2>
          <RangeChart data={rangeData} />
        </div>
        )}
        {graphVisible.index && (
        <div>
          <h2 className="font-semibold mb-2 flex items-center">Indice des prix (base 100)<InfoButton text="Indice basé sur la première semaine pour suivre l'évolution globale." /></h2>
          <LineChart data={priceIndexData} />
        </div>
        )}
        {graphVisible.correlation && (
        <div>
          <h2 className="font-semibold mb-2 flex items-center">Corrélation des prix<InfoButton text="Met en évidence les fournisseurs ayant des évolutions similaires." /></h2>
          <Heatmap labels={correlationMatrix.labels} matrix={correlationMatrix.matrix} />
        </div>
        )}
        {graphVisible.anomalies && (
        <div>
          <h2 className="font-semibold mb-2 flex items-center">Anomalies détectées<InfoButton text="Signale les variations supérieures à 20\u00a0% d'une semaine sur l'autre." /></h2>
          {anomalies.length ? (
            <table className="w-full text-sm text-center">
              <thead>
                <tr>
                  <th>Semaine</th>
                  <th>Variation %</th>
                </tr>
              </thead>
              <tbody>
                {anomalies.map((a) => (
                  <tr key={a.week} className="bg-zinc-800">
                    <td>{a.week}</td>
                    <td className="text-red-400">{a.change.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-center text-sm text-zinc-400">Aucune anomalie</p>
          )}
        </div>
        )}
      </div>
    </div>
  );
}

export default StatisticsPage;
