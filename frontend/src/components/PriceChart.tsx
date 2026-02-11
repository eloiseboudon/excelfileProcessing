import InfoButton from './InfoButton';
import type { Point } from './StatisticsPage';

interface PriceChartProps {
  globalData: Point[];
  brandId: number | '';
}

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

function PriceChart({ globalData, brandId }: PriceChartProps) {
  return (
    <div>
      <h2 className="font-semibold mb-2 flex items-center">
        Vue globale
        <InfoButton text="Prix moyen toutes marques et fournisseurs pour chaque semaine." />
      </h2>
      <LineChart data={globalData} />
      {globalData.length === 0 && (
        <p className="text-center text-sm text-zinc-400 mt-2">
          {brandId ? 'Pas de données pour cette marque' : 'Pas de données'}
        </p>
      )}
    </div>
  );
}

export default PriceChart;
