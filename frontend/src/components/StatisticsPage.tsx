import { ArrowLeft, BarChart3 } from 'lucide-react';
import InfoButton from './InfoButton';
import StatsFilters from './StatsFilters';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  fetchSuppliers,
  fetchProducts,
  fetchSupplierAvgPrice,
  fetchSupplierProductCount,
  fetchSupplierPriceDistribution,
  fetchSupplierPriceEvolution,
} from '../api';

export interface Point {
  label: string;
  value: number;
}

interface StatisticsPageProps {
  onBack?: () => void;
}

interface SupplierAvg {
  supplier: string;
  avg_price: number;
}

interface SupplierCount {
  supplier: string;
  count: number;
}

interface SupplierPrices {
  supplier: string;
  prices: number[];
}

interface SupplierEvolution {
  supplier: string;
  week: string;
  avg_price: number;
}

const COLORS = ['#B8860B', '#38bdf8', '#22c55e', '#e879f9', '#facc15', '#f43f5e'];

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
    return { name: s.name, color: COLORS[idx % COLORS.length], points: valid, path };
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

function GroupedBarChart({ series }: { series: { name: string; data: Point[] }[] }) {
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

  const labels = Array.from(new Set(all.map((d) => d.label))).sort();
  const maxVal = Math.max(...all.map((d) => d.value)) * 1.1;
  const stepX = (width - padding * 2) / labels.length;
  const barWidth = (stepX - 10) / series.length;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full h-80 bg-[var(--color-bg-surface)] rounded"
      preserveAspectRatio="xMidYMid meet"
    >
      {labels.map((l, i) => (
        <text
          key={l}
          x={padding + i * stepX + stepX / 2}
          y={height - padding + 15}
          fontSize="10"
          textAnchor="middle"
          fill="var(--color-chart-text)"
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
                fill={COLORS[si % COLORS.length]}
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

function Legend({ items }: { items: { name: string; color: string }[] }) {
  return (
    <div className="flex flex-wrap gap-4 mt-3">
      {items.map((item) => (
        <div key={item.name} className="flex items-center gap-1.5 text-sm text-[var(--color-text-muted)]">
          <span className="inline-block w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
          {item.name}
        </div>
      ))}
    </div>
  );
}

function StatisticsPage({ onBack }: StatisticsPageProps) {
  const [suppliers, setSuppliers] = useState<{ id: number; name: string }[]>([]);
  const [models, setModels] = useState<string[]>([]);
  const [avgPriceData, setAvgPriceData] = useState<SupplierAvg[]>([]);
  const [productCountData, setProductCountData] = useState<SupplierCount[]>([]);
  const [distributionData, setDistributionData] = useState<SupplierPrices[]>([]);
  const [evolutionData, setEvolutionData] = useState<SupplierEvolution[]>([]);
  const [productEvolutionData, setProductEvolutionData] = useState<SupplierEvolution[]>([]);

  const [supplierId, setSupplierId] = useState<number | ''>('');
  const [selectedModel, setSelectedModel] = useState('');
  const [startWeek, setStartWeek] = useState('');
  const [endWeek, setEndWeek] = useState('');

  useEffect(() => {
    fetchSuppliers()
      .then((s) => setSuppliers(s as { id: number; name: string }[]))
      .catch(() => setSuppliers([]));
    fetchProducts()
      .then((p: { id: number; model: string }[]) => {
        const unique = Array.from(new Set(p.map((x) => x.model).filter(Boolean))).sort();
        setModels(unique);
      })
      .catch(() => setModels([]));
    fetchSupplierAvgPrice()
      .then(setAvgPriceData)
      .catch(() => setAvgPriceData([]));
    fetchSupplierProductCount()
      .then(setProductCountData)
      .catch(() => setProductCountData([]));
    fetchSupplierPriceDistribution()
      .then(setDistributionData)
      .catch(() => setDistributionData([]));
  }, []);

  const toApiWeek = (val: string) => {
    if (!val) return undefined;
    const [year, week] = val.split('-W');
    return `S${week}-${year}`;
  };

  const loadEvolution = useCallback(() => {
    fetchSupplierPriceEvolution({
      supplierId: supplierId ? Number(supplierId) : undefined,
      startWeek: toApiWeek(startWeek),
      endWeek: toApiWeek(endWeek),
    })
      .then(setEvolutionData)
      .catch(() => setEvolutionData([]));
  }, [supplierId, startWeek, endWeek]);

  useEffect(() => {
    loadEvolution();
  }, [loadEvolution]);

  const loadProductEvolution = useCallback(() => {
    if (!selectedModel) {
      setProductEvolutionData([]);
      return;
    }
    fetchSupplierPriceEvolution({
      model: selectedModel,
      startWeek: toApiWeek(startWeek),
      endWeek: toApiWeek(endWeek),
    })
      .then(setProductEvolutionData)
      .catch(() => setProductEvolutionData([]));
  }, [selectedModel, startWeek, endWeek]);

  useEffect(() => {
    loadProductEvolution();
  }, [loadProductEvolution]);

  // ── Derived chart data ──────────────────────────────────────────

  const avgPriceChart = useMemo<Point[]>(
    () => avgPriceData.map((d) => ({ label: d.supplier, value: d.avg_price })),
    [avgPriceData],
  );

  const productCountChart = useMemo<Point[]>(
    () => productCountData.map((d) => ({ label: d.supplier, value: d.count })),
    [productCountData],
  );

  const evolutionSeries = useMemo(() => {
    const map: Record<string, Point[]> = {};
    evolutionData.forEach((d) => {
      if (!map[d.supplier]) map[d.supplier] = [];
      map[d.supplier].push({ label: d.week, value: d.avg_price });
    });
    return Object.entries(map).map(([name, data]) => ({
      name,
      data: data.sort((a, b) => a.label.localeCompare(b.label)),
    }));
  }, [evolutionData]);

  const distributionSeries = useMemo(() => {
    const bins = 10;
    const allPrices = distributionData.flatMap((d) => d.prices);
    if (!allPrices.length) return [];
    const min = Math.min(...allPrices);
    const max = Math.max(...allPrices);
    const step = (max - min) / bins || 1;
    const binLabels = Array.from({ length: bins }, (_, i) => {
      const start = min + i * step;
      const end = start + step;
      return `${start.toFixed(0)}-${end.toFixed(0)}`;
    });

    return distributionData.map((d) => {
      const counts = Array(bins).fill(0);
      d.prices.forEach((p) => {
        let idx = Math.floor((p - min) / step);
        if (idx >= bins) idx = bins - 1;
        counts[idx]++;
      });
      return {
        name: d.supplier,
        data: binLabels.map((label, i) => ({ label, value: counts[i] })),
      };
    });
  }, [distributionData]);

  const evolutionLegend = useMemo(
    () => evolutionSeries.map((s, i) => ({ name: s.name, color: COLORS[i % COLORS.length] })),
    [evolutionSeries],
  );

  const productEvolutionSeries = useMemo(() => {
    const map: Record<string, Point[]> = {};
    productEvolutionData.forEach((d) => {
      if (!map[d.supplier]) map[d.supplier] = [];
      map[d.supplier].push({ label: d.week, value: d.avg_price });
    });
    return Object.entries(map).map(([name, data]) => ({
      name,
      data: data.sort((a, b) => a.label.localeCompare(b.label)),
    }));
  }, [productEvolutionData]);

  const productEvolutionLegend = useMemo(
    () => productEvolutionSeries.map((s, i) => ({ name: s.name, color: COLORS[i % COLORS.length] })),
    [productEvolutionSeries],
  );

  const distributionLegend = useMemo(
    () => distributionSeries.map((s, i) => ({ name: s.name, color: COLORS[i % COLORS.length] })),
    [distributionSeries],
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold text-[var(--color-text-heading)] flex items-center gap-3">
            <BarChart3 className="w-8 h-8 text-[#B8860B]" />
            Statistiques fournisseurs
          </h1>
          <p className="text-[var(--color-text-muted)] mt-1">
            Analyse des prix et volumes du catalogue fournisseur
          </p>
        </div>
        {onBack && (
          <button onClick={onBack} className="btn btn-secondary">
            <ArrowLeft className="w-5 h-5" />
            <span>Retour</span>
          </button>
        )}
      </div>

      <StatsFilters
        supplierId={supplierId}
        setSupplierId={setSupplierId}
        startWeek={startWeek}
        setStartWeek={setStartWeek}
        endWeek={endWeek}
        setEndWeek={setEndWeek}
        suppliers={suppliers}
      />

      <div className="space-y-6">
        {/* Prix moyen par fournisseur */}
        <div className="card overflow-hidden">
          <h2 className="font-semibold mb-2 flex items-center">
            Prix moyen par fournisseur
            <InfoButton text="Prix de vente moyen de chaque fournisseur dans le catalogue actuel." />
          </h2>
          <BarChart data={avgPriceChart} />
          {avgPriceChart.length === 0 && (
            <p className="text-center text-sm text-[var(--color-text-muted)] mt-2">Pas de donnees</p>
          )}
        </div>

        {/* Evolution des prix par fournisseur */}
        <div className="card overflow-hidden">
          <h2 className="font-semibold mb-2 flex items-center">
            Evolution des prix par fournisseur
            <InfoButton text="Prix moyen par fournisseur par semaine (historique des calculs)." />
          </h2>
          <MultiLineChart series={evolutionSeries} />
          {evolutionSeries.length > 0 && <Legend items={evolutionLegend} />}
          {evolutionSeries.length === 0 && (
            <p className="text-center text-sm text-[var(--color-text-muted)] mt-2">Pas de donnees</p>
          )}
        </div>

        {/* Comparaison prix produit par fournisseur */}
        <div className="card overflow-hidden">
          <div className="flex flex-wrap items-center gap-4 mb-2">
            <h2 className="font-semibold flex items-center">
              Comparaison prix produit par fournisseur
              <InfoButton text="Prix moyen du produit selectionne compare entre fournisseurs au fil des semaines." />
            </h2>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="bg-[var(--color-bg-input)] border border-[var(--color-border-strong)] rounded-md px-3 py-2 text-sm"
            >
              <option value="">Selectionner un produit</option>
              {models.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
          {selectedModel ? (
            <>
              <MultiLineChart series={productEvolutionSeries} />
              {productEvolutionSeries.length > 0 && <Legend items={productEvolutionLegend} />}
              {productEvolutionSeries.length === 0 && (
                <p className="text-center text-sm text-[var(--color-text-muted)] mt-2">Pas de donnees pour ce produit</p>
              )}
            </>
          ) : (
            <p className="text-center text-sm text-[var(--color-text-muted)] py-8">Selectionnez un produit pour afficher la comparaison</p>
          )}
        </div>

        {/* Nombre de produits par fournisseur */}
        <div className="card overflow-hidden">
          <h2 className="font-semibold mb-2 flex items-center">
            Nombre de produits par fournisseur
            <InfoButton text="Nombre de references dans le catalogue de chaque fournisseur." />
          </h2>
          <BarChart data={productCountChart} />
          {productCountChart.length === 0 && (
            <p className="text-center text-sm text-[var(--color-text-muted)] mt-2">Pas de donnees</p>
          )}
        </div>

        {/* Repartition des prix */}
        <div className="card overflow-hidden">
          <h2 className="font-semibold mb-2 flex items-center">
            Repartition des prix
            <InfoButton text="Distribution des prix de vente par tranche, comparee entre fournisseurs." />
          </h2>
          <GroupedBarChart series={distributionSeries} />
          {distributionSeries.length > 0 && <Legend items={distributionLegend} />}
          {distributionSeries.length === 0 && (
            <p className="text-center text-sm text-[var(--color-text-muted)] mt-2">Pas de donnees</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default StatisticsPage;
