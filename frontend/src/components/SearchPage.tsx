import { Barcode, Boxes, Loader2, PackageSearch, RefreshCw } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { fetchSearchCatalog, refreshAllSupplierCatalogs } from '../api';
import { normalizeText } from '../utils/text';
import SearchControls from './SearchControls';

interface SearchProduct {
  id: string;
  name: string;
  description: string | null;
  brand: string | null;
  price: number;
  hasPrice: boolean;
  supplier: string | null;
  quantity: number | null;
  ean: string | null;
  partNumber: string | null;
  colorSynonyms: string[];
  searchIndex: string;
}


const SUPPLIER_BADGE_STYLES = [
  'bg-emerald-500/15 text-emerald-700 dark:text-emerald-200 ring-emerald-500/40',
  'bg-sky-500/15 text-sky-700 dark:text-sky-200 ring-sky-500/40',
  'bg-violet-500/15 text-violet-700 dark:text-violet-200 ring-violet-500/40',
  'bg-rose-500/15 text-rose-700 dark:text-rose-200 ring-rose-500/40',
  'bg-amber-500/15 text-amber-700 dark:text-amber-200 ring-amber-500/40',
  'bg-lime-500/15 text-lime-700 dark:text-lime-200 ring-lime-500/40',
  'bg-cyan-500/15 text-cyan-700 dark:text-cyan-200 ring-cyan-500/40',
  'bg-fuchsia-500/15 text-fuchsia-700 dark:text-fuchsia-200 ring-fuchsia-500/40',
];

function hashSupplierName(value: string): number {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) % 2 ** 32;
  }
  return Math.abs(hash);
}

function buildSearchIndex(...values: Array<string | null | undefined | string[]>): string {
  const parts: string[] = [];
  values.forEach((value) => {
    if (!value) {
      return;
    }
    if (Array.isArray(value)) {
      value.forEach((part) => {
        if (typeof part === 'string' && part.trim().length > 0) {
          parts.push(part);
        }
      });
      return;
    }
    if (typeof value === 'string' && value.trim().length > 0) {
      parts.push(value);
    }
  });

  const normalized = normalizeText(parts.join(' '));
  return normalized.replace(/[^a-z0-9]+/g, ' ').trim();
}

function getSupplierBadgeClass(name: string | null): string {
  if (!name) {
    return 'bg-[var(--color-bg-input)]/40 text-[var(--color-text-secondary)] ring-zinc-500/20';
  }

  const paletteIndex = hashSupplierName(name) % SUPPLIER_BADGE_STYLES.length;
  return SUPPLIER_BADGE_STYLES[paletteIndex];
}

function normalisePrice(value: unknown): number {
  if (typeof value === 'number' && !Number.isNaN(value)) {
    return Math.round(value * 100) / 100;
  }
  return 0;
}

function SearchPage() {
  const [products, setProducts] = useState<SearchProduct[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [minPrice, setMinPrice] = useState(0);
  const [maxPrice, setMaxPrice] = useState(0);
  const [priceRange, setPriceRange] = useState({ min: 0, max: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSupplier, setSelectedSupplier] = useState('all');
  const [onlyInStock, setOnlyInStock] = useState(false);
  const [eanFilter, setEanFilter] = useState('');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [refreshing, setRefreshing] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const loadCatalog = useCallback(() => {
    setLoading(true);
    fetchSearchCatalog()
      .then((res) => {
        const items = (res as any[]).map((item, index) => {
          const rawPrice = item.price ?? item.selling_price ?? null;
          const hasPrice = typeof rawPrice === 'number' && !Number.isNaN(rawPrice);
          const price = normalisePrice(hasPrice ? rawPrice : 0);
          const name = item.name ?? item.model ?? item.description ?? `Produit ${index + 1}`;
          const colorSynonyms = Array.isArray(item.color_synonyms)
            ? (item.color_synonyms as unknown[])
                .filter((entry): entry is string => typeof entry === 'string')
                .map((entry) => entry.trim())
                .filter((entry) => entry.length > 0)
            : [];
          const searchIndex = buildSearchIndex(
            name,
            item.description ?? null,
            item.brand ?? null,
            item.supplier ?? null,
            colorSynonyms,
            item.ean ?? null,
            item.part_number ?? null,
          );
          return {
            id: String(item.id ?? name ?? index),
            name,
            description: item.description ?? null,
            brand: item.brand ?? null,
            price,
            hasPrice,
            supplier: item.supplier ?? null,
            quantity: typeof item.quantity === 'number' && !Number.isNaN(item.quantity) ? item.quantity : null,
            ean: typeof item.ean === 'string' && item.ean.trim().length > 0 ? item.ean.trim() : null,
            partNumber:
              typeof item.part_number === 'string' && item.part_number.trim().length > 0
                ? item.part_number.trim()
                : null,
            colorSynonyms,
            searchIndex,
          } as SearchProduct;
        });

        const validPrices = items
          .map((product) => product.price)
          .filter((value) => typeof value === 'number' && !Number.isNaN(value));

        let min = validPrices.length ? Math.floor(Math.min(...validPrices)) : 0;
        let max = validPrices.length ? Math.ceil(Math.max(...validPrices)) : 0;

        if (min === max) {
          max = min + 1;
        }

        setPriceRange({ min, max });
        setMinPrice(min);
        setMaxPrice(max);
        setProducts(items);
        setError(null);
      })
      .catch((err) => {
        console.error('Unable to fetch supplier catalog', err);
        setProducts([]);
        setPriceRange({ min: 0, max: 1 });
        setMinPrice(0);
        setMaxPrice(1);
        const message =
          err instanceof Error && err.message
            ? err.message
            : "Impossible de récupérer les produits. Veuillez réessayer.";
        setError(message);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadCatalog();
  }, [loadCatalog]);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 4000);
    return () => clearTimeout(timer);
  }, [toast]);

  const handleRefreshCatalog = async () => {
    setRefreshing(true);
    try {
      const result = await refreshAllSupplierCatalogs();
      setToast({
        message: `Catalogues rafraîchis : ${result.total_items} articles en ${result.duration_seconds}s`,
        type: 'success',
      });
      loadCatalog();
    } catch (err) {
      const message =
        err instanceof Error && err.message
          ? err.message
          : 'Erreur lors du rafraîchissement des catalogues';
      setToast({ message, type: 'error' });
    } finally {
      setRefreshing(false);
    }
  };

  const supplierOptions = useMemo(() => {
    const uniqueSuppliers = new Set<string>();
    products.forEach((product) => {
      if (product.supplier) {
        uniqueSuppliers.add(product.supplier);
      }
    });
    return Array.from(uniqueSuppliers).sort((a, b) => a.localeCompare(b));
  }, [products]);

  const displayedProducts = useMemo(() => {
    const normalizedTerm = normalizeText(searchTerm.trim());
    const termTokens = normalizedTerm
      .split(/[^a-z0-9]+/)
      .map((token) => token.trim())
      .filter((token) => token.length > 0);
    const normalizedEanFilter = eanFilter.trim().toLowerCase();

    return products
      .filter((product) => {
        const matchesTerm =
          termTokens.length === 0 || termTokens.every((token) => product.searchIndex.includes(token));
        const matchesPrice = product.price >= minPrice && product.price <= maxPrice;
        const matchesSupplier = selectedSupplier === 'all' || product.supplier === selectedSupplier;
        const matchesStock =
          !onlyInStock || (typeof product.quantity === 'number' && !Number.isNaN(product.quantity) && product.quantity > 0);
        const matchesEan =
          normalizedEanFilter.length === 0 ||
          (typeof product.ean === 'string' && product.ean.toLowerCase().includes(normalizedEanFilter));
        return matchesTerm && matchesPrice && matchesSupplier && matchesStock && matchesEan;
      })
      .sort((a, b) => (sortOrder === 'asc' ? a.price - b.price : b.price - a.price));
  }, [products, searchTerm, minPrice, maxPrice, selectedSupplier, onlyInStock, eanFilter, sortOrder]);

  const handlePriceRangeChange = (min: number, max: number) => {
    setMinPrice(Math.max(priceRange.min, Math.min(min, max - 1)));
    setMaxPrice(Math.min(priceRange.max, Math.max(max, min + 1)));
  };

  const handleResetFilters = () => {
    setSearchTerm('');
    setMinPrice(priceRange.min);
    setMaxPrice(priceRange.max);
    setSelectedSupplier('all');
    setOnlyInStock(false);
    setEanFilter('');
    setSortOrder('asc');
  };

  return (
    <div>
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 rounded-md px-4 py-3 text-sm font-medium shadow-lg transition-opacity ${
            toast.type === 'success'
              ? 'bg-emerald-500/15 text-emerald-200 border border-emerald-500/30'
              : 'bg-[var(--color-bg-elevated)] border border-red-500/30 text-red-400'
          }`}
        >
          {toast.message}
        </div>
      )}

      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-[var(--color-text-heading)] flex items-center gap-3">
            <PackageSearch className="w-8 h-8 text-[#B8860B]" />
            Moteur de recherche produits
          </h1>
          <p className="text-[var(--color-text-muted)] mt-1">
            Explorez le catalogue, affinez vos recherches par prix ou mots-clés et accédez rapidement aux produits pertinents.
          </p>
        </div>
        <button
          type="button"
          className="btn btn-secondary flex items-center gap-2 mt-1"
          onClick={handleRefreshCatalog}
          disabled={refreshing}
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          {refreshing ? 'Rafraîchissement...' : 'Rafraîchir les catalogues'}
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-[var(--color-text-muted)]">
          <Loader2 className="w-6 h-6 animate-spin mr-3" />
          Chargement des produits...
        </div>
      ) : error ? (
        <div className="rounded-md border border-red-500/40 bg-red-500/10 px-6 py-4 text-red-200">
          {error}
        </div>
      ) : (
        <>
          <div className="card mb-6 overflow-visible relative z-20">
            <SearchControls
              searchTerm={searchTerm}
              onSearchChange={setSearchTerm}
              minPrice={minPrice}
              maxPrice={maxPrice}
              onPriceRangeChange={handlePriceRangeChange}
              allProducts={products.map((product) => ({
                name: product.name,
                price: product.price,
                brand: product.brand ?? 'Inconnu',
              }))}
              priceRange={priceRange}
              suppliers={supplierOptions}
              selectedSupplier={selectedSupplier}
              onSupplierChange={setSelectedSupplier}
              onlyInStock={onlyInStock}
              onOnlyInStockChange={setOnlyInStock}
              eanFilter={eanFilter}
              onEanFilterChange={setEanFilter}
              sortOrder={sortOrder}
              onSortOrderChange={setSortOrder}
              onResetFilters={handleResetFilters}
            />
          </div>

          <div className="card overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border-subtle)]">
              <h2 className="text-sm font-semibold text-[var(--color-text-heading)]">Résultats ({displayedProducts.length})</h2>
              <span className="text-xs text-[var(--color-text-muted)]">
                Gamme : {minPrice}€ – {maxPrice}€
              </span>
            </div>

            {displayedProducts.length === 0 ? (
              <div className="px-6 py-12 text-center text-[var(--color-text-muted)]">
                Aucun produit ne correspond à votre recherche pour le moment.
              </div>
            ) : (
              <div className="divide-y divide-[var(--color-border-subtle)]">
                {displayedProducts.map((product) => (
                  <div
                    key={product.id}
                    className="px-4 py-4 hover:bg-[var(--color-bg-elevated)]/50 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-6">
                      <div className="flex-1 min-w-0">
                        <h3 className="text-base font-semibold text-[var(--color-text-primary)]">{product.name}</h3>
                        {product.brand && (
                          <p className="mt-0.5 text-sm uppercase tracking-wide text-[#B8860B]">{product.brand}</p>
                        )}
                        {product.description && (
                          <p className="mt-1.5 text-sm text-[var(--color-text-muted)] line-clamp-2">{product.description}</p>
                        )}
                        <div className="mt-2 flex items-center gap-4 text-xs text-[var(--color-text-muted)]">
                          <span className="flex items-center gap-1.5">
                            <Boxes className="h-3.5 w-3.5" />
                            Stock: {typeof product.quantity === 'number' ? product.quantity : 'N/C'}
                          </span>
                          <span className="flex items-center gap-1.5">
                            <Barcode className="h-3.5 w-3.5" />
                            EAN: {product.ean ?? 'N/C'}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 flex-shrink-0">
                        <span
                          className={`inline-flex items-center rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-wide ring-1 ring-inset ${getSupplierBadgeClass(
                            product.supplier
                          )}`}
                        >
                          {product.supplier ?? 'Fournisseur inconnu'}
                        </span>
                        <div className="rounded-md bg-[#B8860B]/10 px-4 py-2 text-[#B8860B] font-semibold whitespace-nowrap">
                          {product.hasPrice ? `${product.price.toFixed(2)}€` : 'Prix N/C'}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default SearchPage;
