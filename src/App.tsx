import React, { useState, useMemo } from 'react';
import { Calculator, Palette } from 'lucide-react';
import { fetchProducts, refreshProduction, refreshProductionByWeek } from './api';
import ProcessingPage from './components/ProcessingPage';
import FormattingPage from './components/FormattingPage';

function App() {
  const [currentPage, setCurrentPage] = useState<'processing' | 'formatting'>('processing');
  const [apiTestMessage, setApiTestMessage] = useState<string | null>(null);
  const [refreshMessage, setRefreshMessage] = useState<string | null>(null);
  const [selectedWeekStart, setSelectedWeekStart] = useState<Date | null>(null);

   const getStartOfWeek = (date: Date) => {
    const d = new Date(date);
    const day = (d.getDay() + 6) % 7; // Monday=0
    d.setDate(d.getDate() - day);
    d.setHours(0, 0, 0, 0);
    return d;
  };

  const getISOWeek = (date: Date) => {
    const tmp = new Date(date);
    tmp.setDate(tmp.getDate() + 4 - (tmp.getDay() || 7));
    const yearStart = new Date(Date.UTC(tmp.getFullYear(), 0, 1));
    const weekNo = Math.ceil(((tmp.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
    return weekNo;
  };

  const weekOptions = useMemo(() => {
    const today = new Date();
    const start = getStartOfWeek(today);
    return Array.from({ length: 4 }, (_, i) => {
      const d = new Date(start);
      d.setDate(start.getDate() - i * 7);
      return {
        label: `Semaine ${getISOWeek(d)}`,
        value: d.toISOString(),
      };
    });
  }, []);

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

  const handleRefreshWeek = async () => {
    setRefreshMessage(null);
    if (!selectedWeekStart) return;
    try {
      await refreshProductionByWeek([selectedWeekStart]);
      setRefreshMessage('Semaine mise à jour');
    } catch {
      setRefreshMessage("Erreur lors du rafraîchissement des données de la semaine");
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
        <div className="mt-6 space-y-4">
          <button
            onClick={handleRefresh}
            className="px-4 py-2 bg-[#B8860B] text-black rounded-lg hover:bg-[#B8860B]/90 font-semibold"
          >
            Rafraîchir la prod
          </button>
            <div className="flex items-center justify-center space-x-2">
            <select
              value={selectedWeekStart ? selectedWeekStart.toISOString() : ''}
              onChange={(e) => setSelectedWeekStart(e.target.value ? new Date(e.target.value) : null)}
              className="bg-zinc-800 border border-zinc-700 rounded-lg px-2 py-1 text-white"
            >
              <option value="">Choisir la semaine</option>
              {weekOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <button
              onClick={handleRefreshWeek}
              className="px-4 py-2 bg-[#B8860B] text-black rounded-lg hover:bg-[#B8860B]/90 font-semibold"
            >
              Rafraîchir la semaine sélectionnée
            </button>
          </div>
          {refreshMessage && (
            <p className="mt-2 text-sm text-zinc-400">{refreshMessage}</p>
          )}
        </div>
      </div>
    </div>
  );
}
export default App;
