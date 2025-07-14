import { ArrowLeft } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  fetchPriceStats,
  fetchSuppliers,
  fetchBrands,
  fetchProducts,
} from '../api';

interface PriceStat {
  supplier: string;
  product: string;
  brand: string;
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

function LineChart({ data }: { data: { label: string; value: number }[] }) {
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
      {/* grid */}
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
      {/* axes */}
      <line
        x1={padding}
        y1={height - padding}
        x2={width - padding}
        y2={height - padding}
        stroke="white"
      />
      <line
        x1={padding}
        y1={padding}
        x2={padding}
        y2={height - padding}
        stroke="white"
      />
      {/* labels */}
      {data.map((d, i) => (
        <text
          key={d.label}
          x={padding + i * stepX}
          y={height - padding + 15}
          fontSize="10"
          textAnchor="middle"
          fill="white"
        >
          {d.label}
        </text>
      ))}
      {/* Y-axis labels */}
      {Array.from({ length: ticks + 1 }).map((_, i) => (
        <text
          key={i}
          x={padding - 5}
          y={height - padding - i * stepY + 4}
          fontSize="10"
          textAnchor="end"
          fill="white"
        >
          {((maxVal / ticks) * i).toFixed(0)}
        </text>
      ))}
      {/* line */}
      <path d={path} fill="none" stroke="orange" strokeWidth="2" />
      {points.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={3} fill="orange" />
      ))}
    </svg>
  );
}

function StatisticsPage({ onBack }: StatisticsPageProps) {
  const [stats, setStats] = useState<PriceStat[]>([]);
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [brands, setBrands] = useState<any[]>([]);
  const [products, setProducts] = useState<ProductItem[]>([]);

  const [supplierId, setSupplierId] = useState<number | ''>('');
  const [brandId, setBrandId] = useState<number | ''>('');
  const [productId, setProductId] = useState<number | ''>('');

  useEffect(() => {
    fetchSuppliers().then((s) => setSuppliers(s as any[])).catch(() => setSuppliers([]));
    fetchBrands().then((b) => setBrands(b as any[])).catch(() => setBrands([]));
    fetchProducts().then((p) => setProducts(p as ProductItem[])).catch(() => setProducts([]));
  }, []);

  const loadStats = useCallback(() => {
    fetchPriceStats({
      supplierId: supplierId ? Number(supplierId) : undefined,
      brandId: brandId ? Number(brandId) : undefined,
      productId: productId ? Number(productId) : undefined,
    })
      .then((res) => setStats(res as PriceStat[]))
      .catch(() => setStats([]));
  }, [supplierId, brandId, productId]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  const filteredProducts = useMemo(
    () =>
      products.filter((p) =>
        brandId ? p.brand_id === Number(brandId) : true
      ),
    [products, brandId]
  );

  const chartData = stats
    .sort((a, b) => a.week.localeCompare(b.week))
    .map((f) => ({ label: f.week, value: f.avg_price }));

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
      <div className="flex flex-wrap gap-4 mb-6">
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
        <select
          value={productId}
          onChange={(e) => setProductId(e.target.value ? Number(e.target.value) : '')}
          className="bg-zinc-900 border border-zinc-600 rounded px-2 py-1"
        >
          <option value="">Tous produits</option>
          {filteredProducts.map((p) => (
            <option key={p.id} value={p.id}>
              {p.model}
            </option>
          ))}
        </select>
      </div>
      <div className="overflow-auto">
        <LineChart data={chartData} />
      </div>
    </div>
  );
}

export default StatisticsPage;
