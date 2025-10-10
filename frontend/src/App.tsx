import { BarChart3, LibraryBig, Settings, Upload } from 'lucide-react';
import { useState, useEffect } from 'react';
import { fetchApitest, setAuthToken, setRefreshToken } from './api';
import AdminPage from './components/AdminPage';
import DataImportPage from './components/DataImportPage';
import LoginPage from './components/LoginPage';
import ProductsPage from './components/ProductsPage';
import StatisticsPage from './components/StatisticsPage';

function App() {
  const storedRole = localStorage.getItem('role');
  const [currentPage, setCurrentPage] = useState<'products' | 'dataImport' | 'statistics' | 'admin'>('products');
  const [apiTestMessage, setApiTestMessage] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [role, setRole] = useState<string>(storedRole || '');

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
    setCurrentPage('products');
  };

  const handleLogout = () => {
    setRole('');
    setToken(null);
    setAuthToken(null);
    setRefreshToken(null);
    localStorage.removeItem('role');
    setCurrentPage('products');
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
                  onClick={() => setCurrentPage('dataImport')}
                  className={`btn px-6 py-3 ${currentPage === 'dataImport' ? 'btn-primary' : 'btn-secondary'}`}
                >
                  <Upload className="w-5 h-5" />
                  <span>Import de données</span>
                </button>
                <button
                  onClick={() => setCurrentPage('statistics')}
                  className={`btn px-6 py-3 ${currentPage === 'statistics' ? 'btn-primary' : 'btn-secondary'}`}
                >
                  <BarChart3 className="w-5 h-5" />
                  <span>Statistiques</span>
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
      {role !== 'client' && currentPage === 'dataImport' && <DataImportPage />}
      {role !== 'client' && currentPage === 'statistics' && <StatisticsPage />}
      {role !== 'client' && currentPage === 'admin' && (
        <AdminPage onBack={() => setCurrentPage('dataImport')} />
      )}
      {currentPage === 'products' && <ProductsPage role={role} />}
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
