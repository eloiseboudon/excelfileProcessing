import React, { useState, useMemo } from 'react';
import { Calculator, Palette, Settings,LibraryBig } from 'lucide-react';
import { fetchProducts, refreshProduction, refreshProductionByWeek } from './api';
import ProcessingPage from './components/ProcessingPage';
import FormattingPage from './components/FormattingPage';
import AdminPage from './components/AdminPage';

function App() {
  const [currentPage, setCurrentPage] = useState<'processing' | 'formatting' | 'admin' | 'products'>('processing');
  const [apiTestMessage, setApiTestMessage] = useState<string | null>(null);

  const handleApiTest = async () => {
    setApiTestMessage(null);
    try {
      await fetchProducts();
      setApiTestMessage('Connexion réussie !');
    } catch {
      setApiTestMessage("Erreur lors de la connexion à l'API");
    }
  };


  return (
    <div className="min-h-screen bg-black text-white flex flex-col">
      {/* Navigation Header */}
      <div className="bg-black border-b border-[#B8860B]/20">
        <div className="max-w-7xl mx-auto py-4 px-2 sm:px-4 lg:px-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap justify-center gap-2 sm:gap-4">
              <button
                onClick={() => setCurrentPage('processing')}
                className={`flex items-center space-x-2 px-6 py-3 rounded-lg font-semibold transition-all duration-200
                  ${currentPage === 'processing'
                    ? 'bg-[#B8860B] text-black'
                    : 'bg-zinc-800 text-white hover:bg-zinc-700'
                  }`}
              >
                <Calculator className="w-5 h-5" />
                <span>Étape 1 - Calculs et Traitement</span>
              </button>
              <button
                onClick={() => setCurrentPage('formatting')}
                className={`flex items-center space-x-2 px-6 py-3 rounded-lg font-semibold transition-all duration-200
                  ${currentPage === 'formatting'
                    ? 'bg-[#B8860B] text-black'
                    : 'bg-zinc-800 text-white hover:bg-zinc-700'
                  }`}
              >
                <Palette className="w-5 h-5" />
                <span>Étape 2 - Mise en Forme</span>
              </button>
            </div>
            <button
              onClick={() => setCurrentPage('products')}
              className="flex items-center space-x-2 px-4 py-2 rounded-lg font-semibold bg-zinc-800 text-white hover:bg-zinc-700 transition-all"
            >
              <LibraryBig className="w-5 h-5" />
              <span>Products</span>
            </button>
            <button
              onClick={() => setCurrentPage('admin')}
              className={`flex items-center space-x-2 px-6 py-3 rounded-lg font-semibold transition-all duration-200
                  ${currentPage === 'admin'
                    ? 'bg-[#B8860B] text-black'
                    : 'bg-zinc-800 text-white hover:bg-zinc-700'
                  }`}
              >
              <Settings className="w-5 h-5" />
              <span>Admin</span>
            </button>
          </div>
        </div>
      </div>

      {/* Page Content */}
      {currentPage === 'processing' && (
        <ProcessingPage onNext={() => setCurrentPage('formatting')} />
      )}
      {currentPage === 'formatting' && (
        <FormattingPage onBack={() => setCurrentPage('processing')} />
      )}
      {currentPage === 'admin' && (
        <AdminPage onBack={() => setCurrentPage('processing')} />
      )}
      {currentPage !== 'admin' && (
        <div className="text-center mt-8 mb-6">
          <button
            onClick={handleApiTest}
            className="px-4 py-2 bg-[#B8860B] text-black rounded-lg hover:bg-[#B8860B]/90 font-semibold"
          >
            Tester la connexion API
          </button>
          {apiTestMessage && (
            <p className="mt-2 text-sm text-zinc-400">{apiTestMessage}</p>
          )}
        </div>
      )}
    </div>
  );
}
export default App;
