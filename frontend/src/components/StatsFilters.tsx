import type { ProductItem } from './StatisticsPage';

interface StatsFiltersProps {
  supplierId: number | '';
  setSupplierId: (v: number | '') => void;
  brandId: number | '';
  setBrandId: (v: number | '') => void;
  productId: number | '';
  setProductId: (v: number | '') => void;
  startWeek: string;
  setStartWeek: (v: string) => void;
  endWeek: string;
  setEndWeek: (v: string) => void;
  suppliers: any[];
  brands: any[];
  filteredProducts: ProductItem[];
  graphVisible: Record<string, boolean>;
  toggleGraph: (key: string) => void;
  graphOptions: { key: string; label: string }[];
}

function StatsFilters({
  supplierId,
  setSupplierId,
  brandId,
  setBrandId,
  productId,
  setProductId,
  startWeek,
  setStartWeek,
  endWeek,
  setEndWeek,
  suppliers,
  brands,
  filteredProducts,
  graphVisible,
  toggleGraph,
  graphOptions,
}: StatsFiltersProps) {
  return (
    <div className="card mb-6 space-y-4">
      <div className="flex flex-wrap gap-4 items-end">
        <select
          value={supplierId}
          onChange={(e) => setSupplierId(e.target.value ? Number(e.target.value) : '')}
          className="bg-[var(--color-bg-input)] border border-[var(--color-border-strong)] rounded-md px-3 py-2 text-sm"
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
          className="bg-[var(--color-bg-input)] border border-[var(--color-border-strong)] rounded-md px-3 py-2 text-sm"
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
          className="bg-[var(--color-bg-input)] border border-[var(--color-border-strong)] rounded-md px-3 py-2 text-sm"
        />
        <input
          type="week"
          value={endWeek}
          onChange={(e) => setEndWeek(e.target.value)}
          className="bg-[var(--color-bg-input)] border border-[var(--color-border-strong)] rounded-md px-3 py-2 text-sm"
        />
        <select
          value={productId}
          onChange={(e) => setProductId(e.target.value ? Number(e.target.value) : '')}
          className="bg-[var(--color-bg-input)] border border-[var(--color-border-strong)] rounded-md px-3 py-2 text-sm"
        >
          <option value="">Choisir un produit</option>
          {filteredProducts.map((p) => (
            <option key={p.id} value={p.id}>
              {p.model}
            </option>
          ))}
        </select>
      </div>
      <div className="flex flex-wrap gap-4 pt-3 border-t border-[var(--color-border-subtle)]">
        {graphOptions.map((opt) => (
          <label key={opt.key} className="flex items-center space-x-1 text-sm">
            <input
              type="checkbox"
              checked={graphVisible[opt.key] ?? true}
              onChange={() => toggleGraph(opt.key)}
              className="accent-[#B8860B]"
            />
            <span>{opt.label}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

export default StatsFilters;
