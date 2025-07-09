import React, { useState } from 'react';
import { Calculator, Palette } from 'lucide-react';
import { fetchProducts, refreshProduction } from './api';
import ProcessingPage from './components/ProcessingPage';
import FormattingPage from './components/FormattingPage';

function App() {
  const [currentPage, setCurrentPage] = useState<'processing' | 'formatting'>('processing');
  const [apiTestMessage, setApiTestMessage] = useState<string | null>(null);
  const [refreshMessage, setRefreshMessage] = useState<string | null>(null);

  const handleApiTest = async () => {
    setApiTestMessage(null);
    try {
      await fetchProducts();
      setApiTestMessage('Connexion réussie !');
    } catch {
      setApiTestMessage("Erreur lors de la connexion à l'API");
    }
  };

  const handleRefresh = async () => {
    setRefreshMessage(null);
    try {
      await refreshProduction();
      setRefreshMessage('Données de prod mises à jour');
    } catch {
      setRefreshMessage("Erreur lors du rafraîchissement des données de prod");
    }
  };

  return (
    <div className="min-h-screen bg-black text-white flex flex-col">
      {/* Navigation Header */}
      <div className="bg-black border-b border-[#B8860B]/20">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <div className="flex justify-center space-x-4">
            <button
              onClick={() => setCurrentPage('processing')}
              className={`flex items-center space-x-2 px-6 py-3 rounded-lg font-semibold transition-all duration-200 ${
                currentPage === 'processing'
                  ? 'bg-[#B8860B] text-black'
                  : 'bg-zinc-800 text-white hover:bg-zinc-700'
              }`}
            >
              <Calculator className="w-5 h-5" />
              <span>Étape 1 - Calculs et Traitement</span>
            </button>
            <button
              onClick={() => setCurrentPage('formatting')}
              className={`flex items-center space-x-2 px-6 py-3 rounded-lg font-semibold transition-all duration-200 ${
                currentPage === 'formatting'
                  ? 'bg-[#B8860B] text-black'
                  : 'bg-zinc-800 text-white hover:bg-zinc-700'
              }`}
            >
              <Palette className="w-5 h-5" />
              <span>Étape 2 - Mise en Forme</span>
            </button>
          </div>
        </div>
      </div>

      {/* Page Content */}
      {currentPage === 'processing' ? (
        <ProcessingPage onNext={() => setCurrentPage('formatting')} />
      ) : (
        <FormattingPage onBack={() => setCurrentPage('processing')} />
      )}
      <div className="text-center mt-12 mb-8">
        <button
          onClick={handleApiTest}
          className="px-4 py-2 bg-[#B8860B] text-black rounded-lg hover:bg-[#B8860B]/90 font-semibold"
        >
          Tester la connexion API
        </button>
        {apiTestMessage && (
          <p className="mt-2 text-sm text-zinc-400">{apiTestMessage}</p>
        )}
        <div className="mt-6">
          <button
            onClick={handleRefresh}
            className="px-4 py-2 bg-[#B8860B] text-black rounded-lg hover:bg-[#B8860B]/90 font-semibold"
          >
            Rafraîchir la prod
          </button>
          {refreshMessage && (
            <p className="mt-2 text-sm text-zinc-400">{refreshMessage}</p>
          )}
        </div>
      </div>
    </div>
  );
}
export default App;