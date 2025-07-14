import { ArrowLeft } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { fetchPriceStats } from '../api';

interface PriceStat {
  supplier: string;
  brand: string;
  week: string;
  avg_price: number;
}

interface StatisticsPageProps {
  onBack: () => void;
}

function LineChart({ data }: { data: { label: string; value: number }[] }) {
  const width = 600;
  const height = 300;
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

  return (
    <svg width={width} height={height} className="bg-zinc-900 rounded">
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
      {/* line */}
      <path d={path} fill="none" stroke="#B8860B" strokeWidth="2" />
      {points.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={3} fill="#B8860B" />
      ))}
    </svg>
  );
}

function StatisticsPage({ onBack }: StatisticsPageProps) {
  const [stats, setStats] = useState<PriceStat[]>([]);
  const [supplier, setSupplier] = useState('');
  const [brand, setBrand] = useState('');

  useEffect(() => {
    fetchPriceStats()
      .then((res) => {
        setStats(res as PriceStat[]);
      })
      .catch(() => setStats([]));
  }, []);

  const suppliers = useMemo(
    () => Array.from(new Set(stats.map((s) => s.supplier))).sort(),
    [stats]
  );
  const brands = useMemo(
    () => Array.from(new Set(stats.map((s) => s.brand))).sort(),
    [stats]
  );

  useEffect(() => {
    if (!supplier && suppliers.length) {
      setSupplier(suppliers[0]);
    }
  }, [supplier, suppliers]);

  useEffect(() => {
    if (!brand && brands.length) {
      setBrand(brands[0]);
    }
  }, [brand, brands]);

  const filtered = stats
    .filter((s) => (supplier ? s.supplier === supplier : true))
    .filter((s) => (brand ? s.brand === brand : true))
    .sort((a, b) => a.week.localeCompare(b.week));

  const chartData = filtered.map((f) => ({ label: f.week, value: f.avg_price }));

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
          value={supplier}
          onChange={(e) => setSupplier(e.target.value)}
          className="bg-zinc-900 border border-zinc-600 rounded px-2 py-1"
        >
          {suppliers.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <select
          value={brand}
          onChange={(e) => setBrand(e.target.value)}
          className="bg-zinc-900 border border-zinc-600 rounded px-2 py-1"
        >
          {brands.map((b) => (
            <option key={b} value={b}>
              {b}
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
