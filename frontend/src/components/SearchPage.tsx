import { Loader2, PackageSearch } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { fetchProductPriceSummary } from '../api';
import SearchControls from './SearchControls';

interface SearchProduct {
  id: string;
  name: string;
  description: string | null;
  brand: string | null;
  price: number;
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
    fetchProductPriceSummary()
      .then((res) => {
        const items = (res as any[]).map((item, index) => {
          const price = normalisePrice(item.recommended_price ?? item.average_price ?? item.marge ?? 0);
          const name = item.model ?? item.description ?? 'Produit';
          return {
            id: String(item.id ?? name ?? index),
            name,
            description: item.description ?? null,
            brand: item.brand ?? null,
            price,
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
        console.error('Unable to fetch product summary', err);
        setProducts([]);
        setPriceRange({ min: 0, max: 1 });
        setMinPrice(0);
        setMaxPrice(1);
        setError("Impossible de récupérer les produits. Veuillez réessayer.");
      })
      .finally(() => setLoading(false));
  }, []);

  const displayedProducts = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();

    return products
      .filter((product) => {
        const matchesTerm =
          term.length === 0 ||
          [product.name, product.description, product.brand]
            .filter((value): value is string => typeof value === 'string')
            .some((value) => value.toLowerCase().includes(term));
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
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {displayedProducts.map((product) => (
                <div
                  key={product.id}
                  className="rounded-xl border border-zinc-700/60 bg-zinc-900/60 p-5 transition-colors hover:border-[#B8860B]/60"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h3 className="text-lg font-semibold text-white line-clamp-2">{product.name}</h3>
                      {product.brand && (
                        <p className="mt-1 text-sm uppercase tracking-wide text-[#B8860B]">{product.brand}</p>
                      )}
                    </div>
                    <div className="rounded-lg bg-[#B8860B]/10 px-3 py-2 text-[#B8860B] font-semibold">
                      {product.price.toFixed(2)}€
                    </div>
                  </div>
                  {product.description && (
                    <p className="mt-4 text-sm text-zinc-400 line-clamp-3">{product.description}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default SearchPage;
