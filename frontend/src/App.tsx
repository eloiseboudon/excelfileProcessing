import { BarChart3, ChevronDown, GitMerge, LibraryBig, LogOut, RefreshCw, Search, Settings } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { logout as apiLogout, setAuthToken } from './api';
import AdminPage from './components/AdminPage';
import LoginPage from './components/LoginPage';
import MatchingPanel from './components/MatchingPanel';
import ProductsPage from './components/ProductsPage';
import SearchPage from './components/SearchPage';
import StatisticsPage from './components/StatisticsPage';
import SyncPage from './components/SyncPage';

function App() {
  const storedRole = localStorage.getItem('role');
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [role, setRole] = useState<string>(storedRole || '');
  const [showSettingsMenu, setShowSettingsMenu] = useState(false);
  const settingsMenuRef = useRef<HTMLDivElement | null>(null);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (token) {
      setAuthToken(token);
    }
  }, [token]);

  const handleLogin = (userRole: string, newToken: string) => {
    setRole(userRole);
    setToken(newToken);
    localStorage.setItem('role', userRole);
    setAuthToken(newToken);
    navigate('/products');
  };

  const handleLogout = () => {
    setRole('');
    setToken(null);
    setAuthToken(null);
    localStorage.removeItem('role');
    setShowSettingsMenu(false);
    apiLogout();
  };

  useEffect(() => {
    const onLogout = () => handleLogout();
    window.addEventListener('auth:logout', onLogout);
    return () => window.removeEventListener('auth:logout', onLogout);
  }, []);

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

  const isProductsActive = location.pathname === '/products';
  const isSettingsActive = location.pathname === '/admin' || location.pathname === '/sync';

  // Client : header simplifié
  if (role === 'client') {
    return (
      <div className="min-h-screen text-[var(--color-text-primary)] flex flex-col">
        <header className="sticky top-0 z-40 bg-[var(--color-bg-nav)] backdrop-blur-lg border-b border-[#B8860B]/15">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-14">
              <span className="text-lg font-bold tracking-tight text-[#B8860B] select-none">AJT Pro</span>
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-elevated)] transition-colors"
              >
                <LogOut className="w-4 h-4" />
                <span>Déconnexion</span>
              </button>
            </div>
          </div>
        </header>
        <main className="flex-1">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
            <ProductsPage role={role} />
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen text-[var(--color-text-primary)] flex flex-col">
      {/* Navigation Header */}
      <header className="sticky top-0 z-40 bg-[var(--color-bg-nav)] backdrop-blur-lg border-b border-[#B8860B]/15">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">

            {/* Logo + Nav links */}
            <div className="flex items-center gap-8">
              <span className="text-lg font-bold tracking-tight text-[#B8860B] select-none">AJT Pro</span>

              <nav className="hidden sm:flex items-center gap-1">
                <button
                  onClick={() => {
                    navigate('/products');
                    setShowSettingsMenu(false);
                  }}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    isProductsActive
                      ? 'bg-[#B8860B]/15 text-[#B8860B]'
                      : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-elevated)]'
                  }`}
                >
                  <LibraryBig className="w-4 h-4" />
                  <span>Produits</span>
                </button>

                <button
                  onClick={() => {
                    navigate('/search');
                    setShowSettingsMenu(false);
                  }}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    location.pathname === '/search'
                      ? 'bg-[#B8860B]/15 text-[#B8860B]'
                      : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-elevated)]'
                  }`}
                >
                  <Search className="w-4 h-4" />
                  <span>Recherche</span>
                </button>

                <button
                  onClick={() => {
                    navigate('/statistics');
                    setShowSettingsMenu(false);
                  }}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    location.pathname === '/statistics'
                      ? 'bg-[#B8860B]/15 text-[#B8860B]'
                      : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-elevated)]'
                  }`}
                >
                  <BarChart3 className="w-4 h-4" />
                  <span>Statistiques</span>
                </button>

                {role === 'admin' && (
                  <button
                    onClick={() => {
                      navigate('/matching');
                      setShowSettingsMenu(false);
                    }}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                      location.pathname === '/matching'
                        ? 'bg-[#B8860B]/15 text-[#B8860B]'
                        : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-elevated)]'
                    }`}
                  >
                    <GitMerge className="w-4 h-4" />
                    <span>Rapprochement</span>
                  </button>
                )}
              </nav>
            </div>

            {/* Right section */}
            <div className="flex items-center gap-2">
              {/* Mobile nav buttons */}
              <div className="flex sm:hidden items-center gap-1">
                <button
                  onClick={() => {
                    navigate('/products');
                    setShowSettingsMenu(false);
                  }}
                  className={`p-2 rounded-md transition-colors ${
                    isProductsActive ? 'text-[#B8860B] bg-[#B8860B]/15' : 'text-[var(--color-text-muted)]'
                  }`}
                  aria-label="Produits"
                >
                  <LibraryBig className="w-5 h-5" />
                </button>
                <button
                  onClick={() => {
                    navigate('/search');
                    setShowSettingsMenu(false);
                  }}
                  className={`p-2 rounded-md transition-colors ${
                    location.pathname === '/search' ? 'text-[#B8860B] bg-[#B8860B]/15' : 'text-[var(--color-text-muted)]'
                  }`}
                  aria-label="Recherche"
                >
                  <Search className="w-5 h-5" />
                </button>
                <button
                  onClick={() => {
                    navigate('/statistics');
                    setShowSettingsMenu(false);
                  }}
                  className={`p-2 rounded-md transition-colors ${
                    location.pathname === '/statistics' ? 'text-[#B8860B] bg-[#B8860B]/15' : 'text-[var(--color-text-muted)]'
                  }`}
                  aria-label="Statistiques"
                >
                  <BarChart3 className="w-5 h-5" />
                </button>
                {role === 'admin' && (
                  <button
                    onClick={() => {
                      navigate('/matching');
                      setShowSettingsMenu(false);
                    }}
                    className={`p-2 rounded-md transition-colors ${
                      location.pathname === '/matching' ? 'text-[#B8860B] bg-[#B8860B]/15' : 'text-[var(--color-text-muted)]'
                    }`}
                    aria-label="Rapprochement"
                  >
                    <GitMerge className="w-5 h-5" />
                  </button>
                )}
              </div>

              {/* Admin : dropdown Paramètres */}
              {role === 'admin' && (
                <div className="relative" ref={settingsMenuRef}>
                  <button
                    onClick={() => setShowSettingsMenu((prev) => !prev)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                      isSettingsActive
                        ? 'bg-[#B8860B]/15 text-[#B8860B]'
                        : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-elevated)]'
                    }`}
                  >
                    <Settings className="w-4 h-4" />
                    <span className="hidden sm:inline">Paramètres</span>
                    <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showSettingsMenu ? 'rotate-180' : ''}`} />
                  </button>
                  {showSettingsMenu && (
                    <div className="absolute right-0 mt-2 w-48 rounded-md border border-[var(--color-border-default)] bg-[var(--color-bg-surface)] shadow-xl z-50 py-1">
                      <button
                        onClick={() => {
                          navigate('/sync');
                          setShowSettingsMenu(false);
                        }}
                        className={`flex w-full items-center gap-2.5 px-4 py-2.5 text-left text-sm transition-colors hover:bg-[var(--color-bg-elevated)] ${
                          location.pathname === '/sync' ? 'text-[#B8860B]' : 'text-[var(--color-text-primary)]'
                        }`}
                      >
                        <RefreshCw className="w-4 h-4" />
                        <span>Synchronisation</span>
                      </button>
                      <button
                        onClick={() => {
                          navigate('/admin');
                          setShowSettingsMenu(false);
                        }}
                        className={`flex w-full items-center gap-2.5 px-4 py-2.5 text-left text-sm transition-colors hover:bg-[var(--color-bg-elevated)] ${
                          location.pathname === '/admin' ? 'text-[#B8860B]' : 'text-[var(--color-text-primary)]'
                        }`}
                      >
                        <Settings className="w-4 h-4" />
                        <span>Administration</span>
                      </button>
                      <div className="my-1 border-t border-[var(--color-border-subtle)]" />
                      <button
                        onClick={handleLogout}
                        className="flex w-full items-center gap-2.5 px-4 py-2.5 text-left text-sm text-red-400 transition-colors hover:bg-[var(--color-bg-elevated)]"
                      >
                        <LogOut className="w-4 h-4" />
                        <span>Déconnexion</span>
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* User : bouton logout icône uniquement */}
              {role === 'user' && (
                <button
                  onClick={handleLogout}
                  className="p-2 rounded-md text-[var(--color-text-muted)] hover:text-red-400 hover:bg-[var(--color-bg-elevated)] transition-colors"
                  aria-label="Déconnexion"
                  title="Déconnexion"
                >
                  <LogOut className="w-5 h-5" />
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Page Content */}
      <main className="flex-1">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
          <Routes>
            <Route path="/" element={<Navigate to="/products" replace />} />
            <Route path="/products" element={<ProductsPage role={role} />} />
            <Route path="/search"
              element={role !== 'client' ? <SearchPage /> : <Navigate to="/products" replace />} />
            <Route path="/statistics"
              element={role !== 'client' ? <StatisticsPage /> : <Navigate to="/products" replace />} />
            <Route path="/matching"
              element={role === 'admin' ? <MatchingPanel /> : <Navigate to="/products" replace />} />
            <Route path="/sync"
              element={role === 'admin' ? <SyncPage /> : <Navigate to="/products" replace />} />
            <Route path="/admin"
              element={role === 'admin' ? <AdminPage /> : <Navigate to="/products" replace />} />
            <Route path="*" element={<Navigate to="/products" replace />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
export default App;
