import { BarChart2, Calculator, LibraryBig, Settings } from 'lucide-react';
import { useState, useEffect } from 'react';
import { fetchApitest, setAuthToken, setRefreshToken } from './api';
import AdminPage from './components/AdminPage';
import FormattingPage from './components/FormattingPage';
import ProcessingPage from './components/ProcessingPage';
import ProductsPage from './components/ProductsPage';
import StatisticsPage from './components/StatisticsPage';
import LoginPage from './components/LoginPage';

function App() {
  const [currentPage, setCurrentPage] = useState<'processing' | 'formatting' | 'admin' | 'products' | 'stats'>('processing');
  const [apiTestMessage, setApiTestMessage] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [role, setRole] = useState<string>(localStorage.getItem('role') || '');

  useEffect(() => {
    if (token) {
      setAuthToken(token);
    }
  }, [token]);

  const handleLogin = (userRole: string, newToken: string, newRefresh: string) => {
    setRole(userRole);
    setToken(newToken);
    localStorage.setItem('role', userRole);
    setAuthToken(newToken);
    setRefreshToken(newRefresh);
  };

  const handleLogout = () => {
    setRole('');
    setToken(null);
    setAuthToken(null);
    setRefreshToken(null);
    localStorage.removeItem('role');
  };

  useEffect(() => {
    const onLogout = () => handleLogout();
    window.addEventListener('auth:logout', onLogout);
    return () => window.removeEventListener('auth:logout', onLogout);
  }, []);

  const handleApiTest = async () => {
    setApiTestMessage(null);
    try {
      await fetchApitest();
      setApiTestMessage('Connexion réussie !');
    } catch {
      setApiTestMessage("Impossible de se connecter à l'API. Vérifiez la configuration du serveur.");
    }
  };


  if (!token) {
    return <LoginPage onLogin={handleLogin} />;
  }

  return (
    <div className="min-h-screen text-white flex flex-col">
      {/* Navigation Header */}
      <div className="bg-black/50 backdrop-blur border-b border-[#B8860B]/20">
        <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-2">

            {role !== 'client' && (
              <button
                onClick={() => setCurrentPage('processing')}
                className={`btn px-6 py-3 ${currentPage === 'processing' ? 'btn-primary' : 'btn-secondary'}`}
              >
                <Calculator className="w-5 h-5" />
                <span>Calculs et Traitement</span>
              </button>
            )}
            <button
              onClick={() => setCurrentPage('products')}
              className={`btn px-6 py-3 ${currentPage === 'products' ? 'btn-primary' : 'btn-secondary'}`}
            >
              <LibraryBig className="w-5 h-5" />
              <span>Produits</span>
            </button>
            {role !== 'client' && (
              <>
                <button
                  onClick={() => setCurrentPage('stats')}
                  className={`flex items-center space-x-2 px-6 py-3 rounded-lg font-semibold transition-all duration-200
                ${currentPage === 'stats'
                  ? 'bg-[#B8860B] text-black'
                  : 'bg-zinc-800 text-white hover:bg-zinc-700'
                }`}
                >
                  <BarChart2 className="w-5 h-5" />
                  <span>Stats</span>
                </button>
                <button
                  onClick={() => setCurrentPage('admin')}
                  className={`btn px-6 py-3 ${currentPage === 'admin' ? 'btn-primary' : 'btn-secondary'}`}
                >
                  <Settings className="w-5 h-5" />
                  <span>Admin</span>
                </button>
              </>
            )}
            <button onClick={handleLogout} className="btn btn-secondary">Déconnexion</button>
          </div>
        </div>
      </div>

      {/* Page Content */}
      {role !== 'client' && currentPage === 'processing' && (
        <ProcessingPage onNext={() => setCurrentPage('formatting')} />
      )}
      {role !== 'client' && currentPage === 'formatting' && (
        <FormattingPage onBack={() => setCurrentPage('processing')} />
      )}
      {role !== 'client' && currentPage === 'admin' && (
        <AdminPage onBack={() => setCurrentPage('processing')} />
      )}
      {currentPage === 'products' && (
        <ProductsPage onBack={() => setCurrentPage('processing')} role={role} />
      )}
      {role !== 'client' && currentPage === 'stats' && (
        <StatisticsPage onBack={() => setCurrentPage('processing')} />
      )}
      {currentPage !== 'admin' && (
        <div className="text-center mt-8 mb-6">
          <button
            onClick={handleApiTest}
            className="btn btn-primary"
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
