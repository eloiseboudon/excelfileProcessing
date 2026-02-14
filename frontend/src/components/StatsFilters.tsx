interface StatsFiltersProps {
  supplierId: number | '';
  setSupplierId: (v: number | '') => void;
  startWeek: string;
  setStartWeek: (v: string) => void;
  endWeek: string;
  setEndWeek: (v: string) => void;
  suppliers: { id: number; name: string }[];
}

function StatsFilters({
  supplierId,
  setSupplierId,
  startWeek,
  setStartWeek,
  endWeek,
  setEndWeek,
  suppliers,
}: StatsFiltersProps) {
  return (
    <div className="card mb-6">
      <div className="flex flex-wrap gap-4 items-end">
        <select
          value={supplierId}
          onChange={(e) => setSupplierId(e.target.value ? Number(e.target.value) : '')}
          className="bg-[var(--color-bg-input)] border border-[var(--color-border-strong)] rounded-md px-3 py-2 text-sm"
        >
          <option value="">Tous fournisseurs</option>
          {suppliers.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        <input
          type="week"
          value={startWeek}
          onChange={(e) => setStartWeek(e.target.value)}
          className="bg-[var(--color-bg-input)] border border-[var(--color-border-strong)] rounded-md px-3 py-2 text-sm"
        />
        <input
          type="week"
          value={endWeek}
          onChange={(e) => setEndWeek(e.target.value)}
          className="bg-[var(--color-bg-input)] border border-[var(--color-border-strong)] rounded-md px-3 py-2 text-sm"
        />
      </div>
    </div>
  );
}

export default StatsFilters;
