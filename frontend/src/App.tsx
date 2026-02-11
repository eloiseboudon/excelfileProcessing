import { ChevronDown, LibraryBig, LogOut, RefreshCw, Search, Settings } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { fetchApitest, setAuthToken, setRefreshToken } from './api';
import AdminPage from './components/AdminPage';
import DataImportPage from './components/DataImportPage';
import LoginPage from './components/LoginPage';
import ProductsPage from './components/ProductsPage';
import SearchPage from './components/SearchPage';
import StatisticsPage from './components/StatisticsPage';

function App() {
  const storedRole = localStorage.getItem('role');
  const [currentPage, setCurrentPage] = useState<'search' | 'products' | 'dataImport' | 'statistics' | 'admin' | 'sync'>('search');
  const [apiTestMessage, setApiTestMessage] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [role, setRole] = useState<string>(storedRole || '');
  const [showSettingsMenu, setShowSettingsMenu] = useState(false);
  const settingsMenuRef = useRef<HTMLDivElement | null>(null);

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
    setCurrentPage('search');
  };

  const handleLogout = () => {
    setRole('');
    setToken(null);
    setAuthToken(null);
    setRefreshToken(null);
    localStorage.removeItem('role');
    setCurrentPage('search');
    setShowSettingsMenu(false);
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

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        settingsMenuRef.current &&
        !settingsMenuRef.current.contains(event.target as Node)
      ) {
        setShowSettingsMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);


  if (!token) {
    return <LoginPage onLogin={handleLogin} />;
  }

  const isProductsActive = currentPage === 'products';
  const isSettingsActive = currentPage === 'admin' || currentPage === 'sync';

  return (
    <div className="min-h-screen text-[var(--color-text-primary)] flex flex-col">
      {/* Navigation Header */}
      <div className="bg-[var(--color-bg-nav)] backdrop-blur border-b border-[#B8860B]/20">
        <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-2">

            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => {
                  setCurrentPage('search');
                  setShowSettingsMenu(false);
                }}
                className={`btn px-6 py-3 ${currentPage === 'search' ? 'btn-primary' : 'btn-secondary'}`}
              >
                <Search className="w-5 h-5" />
                <span>Moteur de recherche</span>
              </button>

              {role !== 'client' && (
                <div className="relative">
                  <button
                    onClick={() => {
                      setCurrentPage('products');
                      setShowSettingsMenu(false);
                    }}
                    className={`btn px-6 py-3 ${isProductsActive ? 'btn-primary' : 'btn-secondary'}`}
                  >
                    <LibraryBig className="w-5 h-5" />
                    <span>Produits</span>
                  </button>
                </div>
              )}
            </div>

            <div className="relative" ref={settingsMenuRef}>
              <button
                onClick={() => {
                  setShowSettingsMenu((prev) => !prev);
                }}
                className={`btn px-6 py-3 ${isSettingsActive ? 'btn-primary' : 'btn-secondary'}`}
              >
                <Settings className="w-5 h-5" />
                <span>Paramètres</span>
                <ChevronDown className="w-4 h-4 ml-2" />
              </button>
              {showSettingsMenu && (
                <div className="absolute right-0 mt-2 w-48 rounded-md border border-[var(--color-border-default)] bg-[var(--color-bg-surface)] shadow-xl">
                  {role !== 'client' && (
                    <>
                      <button
                        onClick={() => {
                          setCurrentPage('admin');
                          setShowSettingsMenu(false);
                        }}
                        className={`flex w-full items-center gap-2 px-4 py-3 text-left hover:bg-[var(--color-bg-elevated)] ${currentPage === 'admin' ? 'text-[#B8860B]' : 'text-[var(--color-text-primary)]'
                          }`}
                      >
                        <Settings className="w-4 h-4" />
                        <span>Admin</span>
                      </button>
                      <button
                        onClick={() => {
                          setCurrentPage('sync');
                          setShowSettingsMenu(false);
                        }}
                        className={`flex w-full items-center gap-2 px-4 py-3 text-left hover:bg-[var(--color-bg-elevated)] ${currentPage === 'sync' ? 'text-[#B8860B]' : 'text-[var(--color-text-primary)]'
                          }`}
                      >
                        <RefreshCw className="w-4 h-4" />
                        <span>Synchro</span>
                      </button>
                    </>
                  )}
                  <button
                    onClick={handleLogout}
                    className="flex w-full items-center gap-2 px-4 py-3 text-left text-[var(--color-text-primary)] hover:bg-[var(--color-bg-elevated)]"
                  >
                    <LogOut className="w-4 h-4" />
                    <span>Déconnexion</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Page Content */}
      {currentPage === 'search' && <SearchPage />}
      {role !== 'client' && currentPage === 'dataImport' && <DataImportPage />}
      {role !== 'client' && currentPage === 'statistics' && <StatisticsPage />}
      {role !== 'client' && currentPage === 'admin' && <AdminPage />}
      {role !== 'client' && currentPage === 'sync' && <DataImportPage />}
      {role !== 'client' && currentPage === 'products' && <ProductsPage role={role} />}
      {currentPage !== 'admin' && currentPage !== 'sync' && (
        <div className="text-center mt-8 mb-6">
          <button
            onClick={handleApiTest}
            className="btn btn-primary"
          >
            Tester la connexion API
          </button>
          {apiTestMessage && (
            <p className="mt-2 text-sm text-[var(--color-text-muted)]">{apiTestMessage}</p>
          )}
        </div>
      )}
    </div>
  );
}
export default App;
