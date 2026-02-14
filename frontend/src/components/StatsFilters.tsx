interface StatsFiltersProps {
  supplierId: number | '';
  setSupplierId: (v: number | '') => void;
  productId: number | '';
  setProductId: (v: number | '') => void;
  startWeek: string;
  setStartWeek: (v: string) => void;
  endWeek: string;
  setEndWeek: (v: string) => void;
  suppliers: { id: number; name: string }[];
  products: { id: number; model: string }[];
}

function StatsFilters({
  supplierId,
  setSupplierId,
  productId,
  setProductId,
  startWeek,
  setStartWeek,
  endWeek,
  setEndWeek,
  suppliers,
  products,
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
        <select
          value={productId}
          onChange={(e) => setProductId(e.target.value ? Number(e.target.value) : '')}
          className="bg-[var(--color-bg-input)] border border-[var(--color-border-strong)] rounded-md px-3 py-2 text-sm"
        >
          <option value="">Tous produits</option>
          {products.map((p) => (
            <option key={p.id} value={p.id}>
              {p.model}
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
