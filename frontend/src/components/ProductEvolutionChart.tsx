import InfoButton from './InfoButton';
import type { Point } from './StatisticsPage';

interface ProductEvolutionChartProps {
  productSupplierSeries: { name: string; data: Point[] }[];
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
        className="w-full h-80 bg-[var(--color-bg-surface)] rounded"
      />
    );
  }

  const labels = Array.from(new Set(all.map((d) => d.label))).sort();
  const maxVal = Math.max(...all.map((d) => d.value)) * 1.1;
  const stepX = (width - padding * 2) / labels.length;
  const barWidth = (stepX - 10) / series.length;
  const colors = ['#B8860B', '#38bdf8', '#22c55e', '#e879f9', '#facc15', '#f43f5e'];

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

function ProductEvolutionChart({ productSupplierSeries }: ProductEvolutionChartProps) {
  return (
    <div>
      <h2 className="font-semibold mb-2 flex items-center">
        Prix moyen produit/fournisseur
        <InfoButton text="Compare les prix moyens par produit selon les fournisseurs." />
      </h2>
      <GroupedBarChart series={productSupplierSeries} />
      {productSupplierSeries.length === 0 && (
        <p className="text-center text-sm text-[var(--color-text-muted)] mt-2">Pas de données</p>
      )}
    </div>
  );
}

export default ProductEvolutionChart;
