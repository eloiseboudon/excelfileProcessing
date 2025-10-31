import { Barcode, Boxes, Loader2, PackageSearch } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { fetchSearchCatalog } from '../api';
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
  'bg-emerald-500/15 text-emerald-200 ring-emerald-500/40',
  'bg-sky-500/15 text-sky-200 ring-sky-500/40',
  'bg-violet-500/15 text-violet-200 ring-violet-500/40',
  'bg-rose-500/15 text-rose-200 ring-rose-500/40',
  'bg-amber-500/15 text-amber-200 ring-amber-500/40',
  'bg-lime-500/15 text-lime-200 ring-lime-500/40',
  'bg-cyan-500/15 text-cyan-200 ring-cyan-500/40',
  'bg-fuchsia-500/15 text-fuchsia-200 ring-fuchsia-500/40',
];

function hashSupplierName(value: string): number {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) % 2 ** 32;
  }
  return Math.abs(hash);
}

function normalizeText(value: string): string {
  return value
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase();
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
    return 'bg-zinc-700/40 text-zinc-300 ring-zinc-500/20';
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

  useEffect(() => {
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

  const displayedProducts = useMemo(() => {
    const normalizedTerm = normalizeText(searchTerm.trim());
    const termTokens = normalizedTerm
      .split(/[^a-z0-9]+/)
      .map((token) => token.trim())
      .filter((token) => token.length > 0);

    return products
      .filter((product) => {
        const matchesTerm =
          termTokens.length === 0 || termTokens.every((token) => product.searchIndex.includes(token));
        const matchesPrice = product.price >= minPrice && product.price <= maxPrice;
        return matchesTerm && matchesPrice;
      })
      .sort((a, b) => a.price - b.price);
  }, [products, searchTerm, minPrice, maxPrice]);

  const handlePriceRangeChange = (min: number, max: number) => {
    setMinPrice(Math.max(priceRange.min, Math.min(min, max - 1)));
    setMaxPrice(Math.min(priceRange.max, Math.max(max, min + 1)));
  };

  return (
    <div className="max-w-7xl mx-auto w-full flex-1 px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold text-white mb-2 flex items-center gap-3">
          <PackageSearch className="w-8 h-8 text-[#B8860B]" />
          Moteur de recherche produits
        </h1>
        <p className="text-zinc-400 max-w-2xl">
          Explorez l&apos;ensemble du catalogue, affinez vos recherches par prix ou mots-clés et accédez rapidement aux produits pertinents.
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-zinc-400">
          <Loader2 className="w-6 h-6 animate-spin mr-3" />
          Chargement des produits...
        </div>
      ) : error ? (
        <div className="rounded-xl border border-red-500/40 bg-red-500/10 px-6 py-4 text-red-200">
          {error}
        </div>
      ) : (
        <>
          <div className="card p-6 mb-10">
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
            />
          </div>

          <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-white">Résultats ({displayedProducts.length})</h2>
            <span className="text-sm text-zinc-400">
              Gamme sélectionnée : {minPrice}€ - {maxPrice}€
            </span>
          </div>

          {displayedProducts.length === 0 ? (
            <div className="rounded-xl border border-zinc-700 bg-zinc-900/60 px-6 py-12 text-center text-zinc-400">
              Aucun produit ne correspond à votre recherche pour le moment.
            </div>
          ) : (
            <div className="space-y-3">
              {displayedProducts.map((product) => (
                <div
                  key={product.id}
                  className="w-full rounded-xl border border-zinc-700/60 bg-zinc-900/60 p-5"
                >
                  <div className="flex items-start justify-between gap-6">
                    <div className="flex-1 min-w-0">
                      <h3 className="text-lg font-semibold text-white">{product.name}</h3>
                      {product.brand && (
                        <p className="mt-1 text-sm uppercase tracking-wide text-[#B8860B]">{product.brand}</p>
                      )}
                      {product.description && (
                        <p className="mt-2 text-sm text-zinc-400 line-clamp-2">{product.description}</p>
                      )}
                      <div className="mt-3 flex items-center gap-4 text-xs text-zinc-400">
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
                    <div className="flex items-center gap-4 flex-shrink-0">
                      <span
                        className={`inline-flex items-center rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-wide ring-1 ring-inset ${getSupplierBadgeClass(
                          product.supplier
                        )}`}
                      >
                        {product.supplier ?? 'Fournisseur inconnu'}
                      </span>
                      <div className="rounded-lg bg-[#B8860B]/10 px-4 py-2 text-[#B8860B] font-semibold whitespace-nowrap">
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
