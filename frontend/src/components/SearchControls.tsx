import React, { useState, useEffect, useRef } from 'react';
import { Search, TrendingUp, X } from 'lucide-react';

interface SearchControlsProps {
  searchTerm: string;
  onSearchChange: (term: string) => void;
  minPrice: number;
  maxPrice: number;
  onPriceRangeChange: (min: number, max: number) => void;
  allProducts: Array<{ name: string; price: number; brand: string }>;
  priceRange: { min: number; max: number };
  suppliers: string[];
  selectedSupplier: string;
  onSupplierChange: (supplier: string) => void;
  onlyInStock: boolean;
  onOnlyInStockChange: (value: boolean) => void;
  eanFilter: string;
  onEanFilterChange: (value: string) => void;
  sortOrder: 'asc' | 'desc';
  onSortOrderChange: (order: 'asc' | 'desc') => void;
  onResetFilters: () => void;
}

function SearchControls({
  searchTerm,
  onSearchChange,
  minPrice,
  maxPrice,
  onPriceRangeChange,
  allProducts,
  priceRange,
  suppliers,
  selectedSupplier,
  onSupplierChange,
  onlyInStock,
  onOnlyInStockChange,
  eanFilter,
  onEanFilterChange,
  sortOrder,
  onSortOrderChange,
  onResetFilters
}: SearchControlsProps) {
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [searchHistory, setSearchHistory] = useState<string[]>([]);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);

  // Charger l'historique depuis localStorage
  useEffect(() => {
    const savedHistory = localStorage.getItem('ajtpro_search_history');
    if (savedHistory) {
      setSearchHistory(JSON.parse(savedHistory));
    }
  }, []);

  // Fonction de recherche floue (distance de Levenshtein simplifiée)
  const fuzzyMatch = (term: string, target: string, threshold: number = 2): boolean => {
    if (!term || !target) return false;
    
    const termLower = term.toLowerCase();
    const targetLower = target.toLowerCase();
    
    // Correspondance exacte
    if (targetLower.includes(termLower)) return true;
    
    // Recherche floue simple
    if (Math.abs(termLower.length - targetLower.length) > threshold) return false;
    
    let distance = 0;
    const maxLen = Math.max(termLower.length, targetLower.length);
    
    for (let i = 0; i < maxLen; i++) {
      if (termLower[i] !== targetLower[i]) {
        distance++;
        if (distance > threshold) return false;
      }
    }
    
    return true;
  };

  // Générer des suggestions intelligentes
  const generateSuggestions = (term: string): string[] => {
    if (!term || term.length < 2) {
      // Afficher l'historique populaire si pas de terme
      return searchHistory.slice(0, 5);
    }

    const suggestions = new Set<string>();
    
    // Recherche dans les noms de produits
    allProducts.forEach(product => {
      const words = product.name.toLowerCase().split(' ');
      
      // Correspondance exacte
      if (product.name.toLowerCase().includes(term.toLowerCase())) {
        suggestions.add(product.name);
      }
      
      // Correspondance par mots
      words.forEach(word => {
        if (word.includes(term.toLowerCase()) && word.length > 2) {
          suggestions.add(product.name);
        }
      });
      
      // Recherche floue
      if (fuzzyMatch(term, product.name, 2)) {
        suggestions.add(product.name);
      }
    });

    // Ajouter des suggestions de marques
    const brands = ['Apple', 'Samsung', 'Xiaomi', 'Hotwav', 'JBL', 'Google', 'Honor', 'Nothing'];
    brands.forEach(brand => {
      if (fuzzyMatch(term, brand, 1)) {
        suggestions.add(brand);
      }
    });

    // Ajouter des suggestions de catégories
    const categories = ['iPhone', 'iPad', 'Galaxy', 'Note', 'Pro', 'Max', 'Mini', 'Watch', 'Buds'];
    categories.forEach(category => {
      if (fuzzyMatch(term, category, 1)) {
        suggestions.add(category);
      }
    });

    return Array.from(suggestions).slice(0, 8);
  };

  // Mettre à jour les suggestions quand le terme change
  useEffect(() => {
    const newSuggestions = generateSuggestions(searchTerm);
    setSuggestions(newSuggestions);
  }, [searchTerm, allProducts]);

  // Gérer la sélection d'une suggestion
  const handleSuggestionClick = (suggestion: string) => {
    onSearchChange(suggestion);
    setShowSuggestions(false);
    
    // Ajouter à l'historique
    const newHistory = [suggestion, ...searchHistory.filter(h => h !== suggestion)].slice(0, 10);
    setSearchHistory(newHistory);
    localStorage.setItem('ajtpro_search_history', JSON.stringify(newHistory));
  };

  // Gérer les clics en dehors pour fermer les suggestions
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(event.target as Node) &&
        searchInputRef.current &&
        !searchInputRef.current.contains(event.target as Node)
      ) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchTerm.trim()) {
      const newHistory = [searchTerm, ...searchHistory.filter(h => h !== searchTerm)].slice(0, 10);
      setSearchHistory(newHistory);
      localStorage.setItem('ajtpro_search_history', JSON.stringify(newHistory));
    }
    setShowSuggestions(false);
  };

  return (
    <div className="space-y-6">
      {/* Barre de recherche avec suggestions */}
      <div className="relative">
        <form onSubmit={handleSearchSubmit} className="relative">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-zinc-400 w-5 h-5" />
            <input
              ref={searchInputRef}
              type="text"
              value={searchTerm}
              onChange={(e) => onSearchChange(e.target.value)}
              onFocus={() => setShowSuggestions(true)}
              className="w-full pl-12 pr-12 py-4 text-lg bg-zinc-800 border-2 border-zinc-600 rounded-xl text-white placeholder-zinc-400 focus:border-[#B8860B] focus:outline-none transition-all duration-200"
              placeholder="🔍 Rechercher un produit... (ex: iPhone, Galaxy, Hotwav)"
            />
            {searchTerm && (
              <button
                type="button"
                onClick={() => {
                  onSearchChange('');
                  setShowSuggestions(false);
                }}
                className="absolute right-4 top-1/2 transform -translate-y-1/2 text-zinc-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>
        </form>

        {/* Suggestions */}
        {showSuggestions && suggestions.length > 0 && (
          <div
            ref={suggestionsRef}
            className="absolute top-full left-0 right-0 mt-2 bg-zinc-800 border border-zinc-600 rounded-xl shadow-2xl z-50 max-h-80 overflow-y-auto"
          >
            {!searchTerm && searchHistory.length > 0 && (
              <div className="p-3 border-b border-zinc-700">
                <div className="flex items-center space-x-2 text-sm text-zinc-400 mb-2">
                  <TrendingUp className="w-4 h-4" />
                  <span>Recherches récentes</span>
                </div>
              </div>
            )}
            
            {suggestions.map((suggestion, index) => (
              <button
                key={index}
                onClick={() => handleSuggestionClick(suggestion)}
                className="w-full text-left px-4 py-3 hover:bg-zinc-700 transition-colors border-b border-zinc-700 last:border-b-0"
              >
                <div className="flex items-center justify-between">
                  <span className="text-white">{suggestion}</span>
                  {searchHistory.includes(suggestion) && (
                    <TrendingUp className="w-4 h-4 text-[#B8860B]" />
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="bg-zinc-800 rounded-xl p-6 border border-zinc-600 space-y-6">
        <button
          type="button"
          onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
          className="flex items-center justify-between w-full text-left text-sm font-semibold text-zinc-300 uppercase tracking-wide"
        >
          <span>Filtres avancés</span>
          <svg
            className={`w-5 h-5 text-zinc-400 transform transition-transform ${showAdvancedFilters ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {showAdvancedFilters && (
          <div className="space-y-6">
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-zinc-400 mb-2">Gamme de prix</label>
            <div className="relative mb-4">
              {/* Curseur double pour la gamme de prix */}
              <div className="relative h-2 bg-zinc-600 rounded-full">
                <div
                  className="absolute h-2 bg-[#B8860B] rounded-full"
                  style={{
                    left: `${((minPrice - priceRange.min) / (priceRange.max - priceRange.min)) * 100}%`,
                    width: `${((maxPrice - minPrice) / (priceRange.max - priceRange.min)) * 100}%`
                  }}
                />
              </div>
              
              {/* Curseur minimum */}
              <input
                type="range"
                min={priceRange.min}
                max={priceRange.max}
                value={minPrice}
                onChange={(e) => {
                  const newMin = Math.min(Number(e.target.value), maxPrice - 1);
                  onPriceRangeChange(newMin, maxPrice);
                }}
                className="absolute top-0 w-full h-2 opacity-0 cursor-pointer"
              />
              
              {/* Curseur maximum */}
              <input
                type="range"
                min={priceRange.min}
                max={priceRange.max}
                value={maxPrice}
                onChange={(e) => {
                  const newMax = Math.max(Number(e.target.value), minPrice + 1);
                  onPriceRangeChange(minPrice, newMax);
                }}
                className="absolute top-0 w-full h-2 opacity-0 cursor-pointer"
              />
            </div>
            
            {/* Inputs numériques pour prix précis */}
            <div className="flex items-center space-x-3">
              <div className="flex-1">
                <input
                  type="number"
                  value={minPrice}
                  onChange={(e) => {
                    const newMin = Math.max(priceRange.min, Math.min(Number(e.target.value), maxPrice - 1));
                    onPriceRangeChange(newMin, maxPrice);
                  }}
                  className="w-full px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-lg text-white text-xs focus:border-[#B8860B] focus:outline-none"
                  min={priceRange.min}
                  max={maxPrice - 1}
                />
              </div>
              <span className="text-xs text-zinc-400">à</span>
              <div className="flex-1">
                <input
                  type="number"
                  value={maxPrice}
                  onChange={(e) => {
                    const newMax = Math.min(priceRange.max, Math.max(Number(e.target.value), minPrice + 1));
                    onPriceRangeChange(minPrice, newMax);
                  }}
                  className="w-full px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-lg text-white text-xs focus:border-[#B8860B] focus:outline-none"
                  min={minPrice + 1}
                  max={priceRange.max}
                />
              </div>
              <span className="text-xs text-zinc-400">€</span>
            </div>
          </div>
        </div>
        
        <div className="pt-4 border-t border-zinc-700">
          <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="block text-xs text-zinc-400 mb-1">Fournisseur</label>
            <select
              value={selectedSupplier}
              onChange={(event) => onSupplierChange(event.target.value)}
              className="w-full px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-lg text-white text-sm focus:border-[#B8860B] focus:outline-none"
            >
              <option value="all">Tous les fournisseurs</option>
              {suppliers.map((supplier) => (
                <option key={supplier} value={supplier}>
                  {supplier}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs text-zinc-400 mb-1">Disponibilité</label>
            <label className="flex items-center gap-2 px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-lg text-sm text-white">
              <input
                type="checkbox"
                checked={onlyInStock}
                onChange={(event) => onOnlyInStockChange(event.target.checked)}
                className="h-4 w-4 rounded border-zinc-500 text-[#B8860B] focus:ring-[#B8860B]"
              />
              Stock disponible uniquement
            </label>
          </div>

          <div>
            <label className="block text-xs text-zinc-400 mb-1">EAN</label>
            <input
              type="text"
              value={eanFilter}
              onChange={(event) => onEanFilterChange(event.target.value)}
              placeholder="Rechercher par EAN"
              className="w-full px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-lg text-white text-sm focus:border-[#B8860B] focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs text-zinc-400 mb-1">Tri par prix</label>
            <select
              value={sortOrder}
              onChange={(event) => onSortOrderChange(event.target.value as 'asc' | 'desc')}
              className="w-full px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-lg text-white text-sm focus:border-[#B8860B] focus:outline-none"
            >
              <option value="asc">Prix croissant</option>
              <option value="desc">Prix décroissant</option>
            </select>
          </div>
          </div>
            </div>
            
            <div className="pt-4 border-t border-zinc-700">
              <button
                onClick={onResetFilters}
                className="w-full py-2 bg-zinc-600 text-white rounded-lg hover:bg-zinc-500 transition-colors text-sm"
              >
                Réinitialiser les filtres
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default SearchControls;