import { ArrowLeft } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  fetchPriceStats,
  fetchSuppliers,
  fetchBrands,
  fetchProducts,
} from '../api';

interface PriceStat {
  supplier?: string;
  brand?: string;
  week: string;
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

function LineChart({ data }: { data: Point[] }) {
  const width = 700;
  const height = 320;
  const padding = 40;

  if (!data.length) {
    return <svg width={width} height={height} />;
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
    <svg width={width} height={height} className="bg-zinc-900 rounded">
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
    return <svg width={width} height={height} />;
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
    <svg width={width} height={height} className="bg-zinc-900 rounded">
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

function StatisticsPage({ onBack }: StatisticsPageProps) {
  const [globalStats, setGlobalStats] = useState<PriceStat[]>([]);
  const [productStats, setProductStats] = useState<PriceStat[]>([]);
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [brands, setBrands] = useState<any[]>([]);
  const [products, setProducts] = useState<ProductItem[]>([]);

  const [supplierId, setSupplierId] = useState<number | ''>('');
  const [brandId, setBrandId] = useState<number | ''>('');
  const [productId, setProductId] = useState<number | ''>('');
  const [startWeek, setStartWeek] = useState('');
  const [endWeek, setEndWeek] = useState('');

  useEffect(() => {
    fetchSuppliers().then((s) => setSuppliers(s as any[])).catch(() => setSuppliers([]));
    fetchBrands().then((b) => setBrands(b as any[])).catch(() => setBrands([]));
    fetchProducts().then((p) => setProducts(p as ProductItem[])).catch(() => setProducts([]));
  }, []);

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
      <div className="overflow-auto space-y-8">
        <div>
          <h2 className="font-semibold mb-2">Vue globale</h2>
          <LineChart data={globalData} />
        </div>
        <div>
          <h2 className="font-semibold mb-2">Évolution du produit</h2>
          <MultiLineChart series={productSeries} />
        </div>
      </div>
    </div>
  );
}

export default StatisticsPage;
