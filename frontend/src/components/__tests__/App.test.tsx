import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from '../../App';
import { NotificationProvider } from '../NotificationProvider';

// Mock heavy child components to keep tests fast and focused
vi.mock('../SearchPage', () => ({
  default: () => <div data-testid="search-page">Search</div>,
}));
vi.mock('../AdminPage', () => ({
  default: () => <div data-testid="admin-page">Admin</div>,
}));
vi.mock('../DataImportPage', () => ({
  default: () => <div data-testid="data-import-page">DataImport</div>,
}));
vi.mock('../ProductsPage', () => ({
  default: () => <div data-testid="products-page">Products</div>,
}));
vi.mock('../StatisticsPage', () => ({
  default: () => <div data-testid="statistics-page">Statistics</div>,
}));

function renderApp() {
  return render(
    <NotificationProvider>
      <App />
    </NotificationProvider>
  );
}

describe('App', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('shows login page when no token is stored', () => {
    renderApp();
    expect(screen.getByText('Connexion')).toBeInTheDocument();
  });

  it('shows navigation when token is present', () => {
    localStorage.setItem('token', 'fake-jwt-token');
    localStorage.setItem('role', 'admin');
    renderApp();
    expect(screen.getByText('Recherche')).toBeInTheDocument();
  });

  it('shows settings button when authenticated', () => {
    localStorage.setItem('token', 'fake-jwt-token');
    localStorage.setItem('role', 'admin');
    renderApp();
    expect(screen.getByText(/Paramètres/)).toBeInTheDocument();
  });

  it('shows Produits button for admin users', () => {
    localStorage.setItem('token', 'fake-jwt-token');
    localStorage.setItem('role', 'admin');
    renderApp();
    expect(screen.getByText('Produits')).toBeInTheDocument();
  });

  it('does not show Produits button for client users', () => {
    localStorage.setItem('token', 'fake-jwt-token');
    localStorage.setItem('role', 'client');
    renderApp();
    expect(screen.queryByText('Produits')).not.toBeInTheDocument();
  });
});
