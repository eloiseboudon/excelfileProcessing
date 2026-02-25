import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from '../../App';
import { NotificationProvider } from '../NotificationProvider';

vi.mock('../SearchPage', () => ({
  default: () => <div data-testid="search-page">SearchPage</div>,
}));
vi.mock('../AdminPage', () => ({
  default: () => <div data-testid="admin-page">AdminPage</div>,
}));
vi.mock('../ProductsPage', () => ({
  default: () => <div data-testid="products-page">ProductsPage</div>,
}));
vi.mock('../StatisticsPage', () => ({
  default: () => <div data-testid="statistics-page">StatisticsPage</div>,
}));
vi.mock('../MatchingPanel', () => ({
  default: () => <div data-testid="matching-panel">MatchingPanel</div>,
}));
vi.mock('../SyncPage', () => ({
  default: () => <div data-testid="sync-page">SyncPage</div>,
}));

function renderApp(initialRoute = '/products', role = '', token = '') {
  if (token) {
    localStorage.setItem('token', token);
    localStorage.setItem('role', role);
  }
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <NotificationProvider>
        <App />
      </NotificationProvider>
    </MemoryRouter>
  );
}

describe('App — authentication', () => {
  beforeEach(() => localStorage.clear());

  it('shows login page when no token is stored', () => {
    renderApp('/products');
    expect(screen.getByText('Connexion')).toBeInTheDocument();
  });

  it('renders main nav when token is present', () => {
    renderApp('/products', 'admin', 'fake-jwt');
    expect(screen.getByText('Produits')).toBeInTheDocument();
  });
});

describe('App — admin role', () => {
  beforeEach(() => localStorage.clear());

  it('shows full navigation (Produits, Recherche, Statistiques, Rapprochement)', () => {
    renderApp('/products', 'admin', 'fake-jwt');
    expect(screen.getAllByText('Produits').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Recherche').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Statistiques').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Rapprochement').length).toBeGreaterThan(0);
  });

  it('shows Paramètres dropdown button', () => {
    renderApp('/products', 'admin', 'fake-jwt');
    expect(screen.getByText('Paramètres')).toBeInTheDocument();
  });

  it('renders ProductsPage on /products', () => {
    renderApp('/products', 'admin', 'fake-jwt');
    expect(screen.getByTestId('products-page')).toBeInTheDocument();
  });

  it('renders SearchPage on /search', () => {
    renderApp('/search', 'admin', 'fake-jwt');
    expect(screen.getByTestId('search-page')).toBeInTheDocument();
  });

  it('renders StatisticsPage on /statistics', () => {
    renderApp('/statistics', 'admin', 'fake-jwt');
    expect(screen.getByTestId('statistics-page')).toBeInTheDocument();
  });

  it('renders MatchingPanel on /matching', () => {
    renderApp('/matching', 'admin', 'fake-jwt');
    expect(screen.getByTestId('matching-panel')).toBeInTheDocument();
  });

  it('renders SyncPage on /sync', () => {
    renderApp('/sync', 'admin', 'fake-jwt');
    expect(screen.getByTestId('sync-page')).toBeInTheDocument();
  });

  it('renders AdminPage on /admin', () => {
    renderApp('/admin', 'admin', 'fake-jwt');
    expect(screen.getByTestId('admin-page')).toBeInTheDocument();
  });

  it('redirects unknown routes to /products', () => {
    renderApp('/unknown-route', 'admin', 'fake-jwt');
    expect(screen.getByTestId('products-page')).toBeInTheDocument();
  });

  it('redirects / to /products', () => {
    renderApp('/', 'admin', 'fake-jwt');
    expect(screen.getByTestId('products-page')).toBeInTheDocument();
  });
});

describe('App — user role', () => {
  beforeEach(() => localStorage.clear());

  it('shows Produits, Recherche, Statistiques in nav', () => {
    renderApp('/products', 'user', 'fake-jwt');
    expect(screen.getAllByText('Produits').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Recherche').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Statistiques').length).toBeGreaterThan(0);
  });

  it('does not show Rapprochement nav item', () => {
    renderApp('/products', 'user', 'fake-jwt');
    expect(screen.queryByText('Rapprochement')).not.toBeInTheDocument();
  });

  it('does not show Paramètres dropdown', () => {
    renderApp('/products', 'user', 'fake-jwt');
    expect(screen.queryByText('Paramètres')).not.toBeInTheDocument();
  });

  it('renders ProductsPage on /products', () => {
    renderApp('/products', 'user', 'fake-jwt');
    expect(screen.getByTestId('products-page')).toBeInTheDocument();
  });

  it('renders SearchPage on /search', () => {
    renderApp('/search', 'user', 'fake-jwt');
    expect(screen.getByTestId('search-page')).toBeInTheDocument();
  });

  it('renders StatisticsPage on /statistics', () => {
    renderApp('/statistics', 'user', 'fake-jwt');
    expect(screen.getByTestId('statistics-page')).toBeInTheDocument();
  });

  it('redirects /matching to /products', () => {
    renderApp('/matching', 'user', 'fake-jwt');
    expect(screen.getByTestId('products-page')).toBeInTheDocument();
    expect(screen.queryByTestId('matching-panel')).not.toBeInTheDocument();
  });

  it('redirects /sync to /products', () => {
    renderApp('/sync', 'user', 'fake-jwt');
    expect(screen.getByTestId('products-page')).toBeInTheDocument();
    expect(screen.queryByTestId('sync-page')).not.toBeInTheDocument();
  });

  it('redirects /admin to /products', () => {
    renderApp('/admin', 'user', 'fake-jwt');
    expect(screen.getByTestId('products-page')).toBeInTheDocument();
    expect(screen.queryByTestId('admin-page')).not.toBeInTheDocument();
  });
});

describe('App — client role', () => {
  beforeEach(() => localStorage.clear());

  it('shows simplified header without navigation links', () => {
    renderApp('/products', 'client', 'fake-jwt');
    expect(screen.queryByText('Recherche')).not.toBeInTheDocument();
    expect(screen.queryByText('Statistiques')).not.toBeInTheDocument();
    expect(screen.queryByText('Rapprochement')).not.toBeInTheDocument();
    expect(screen.queryByText('Paramètres')).not.toBeInTheDocument();
  });

  it('shows Déconnexion button in header', () => {
    renderApp('/products', 'client', 'fake-jwt');
    expect(screen.getByText('Déconnexion')).toBeInTheDocument();
  });

  it('shows AJT Pro brand in header', () => {
    renderApp('/products', 'client', 'fake-jwt');
    expect(screen.getByText('AJT Pro')).toBeInTheDocument();
  });

  it('renders ProductsPage directly', () => {
    renderApp('/products', 'client', 'fake-jwt');
    expect(screen.getByTestId('products-page')).toBeInTheDocument();
  });
});
