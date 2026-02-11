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
    <>
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
        {graphOptions.map((opt) => (
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
    </>
  );
}

export default StatsFilters;
