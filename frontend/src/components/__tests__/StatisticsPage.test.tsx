import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import StatisticsPage from '../StatisticsPage';

vi.mock('../../api', () => ({
  fetchSuppliers: vi.fn(),
  fetchProducts: vi.fn(),
  fetchSupplierAvgPrice: vi.fn(),
  fetchSupplierProductCount: vi.fn(),
  fetchSupplierPriceDistribution: vi.fn(),
  fetchSupplierPriceEvolution: vi.fn(),
}));

import {
  fetchSuppliers,
  fetchProducts,
  fetchSupplierAvgPrice,
  fetchSupplierProductCount,
  fetchSupplierPriceDistribution,
  fetchSupplierPriceEvolution,
} from '../../api';

const mockFetchSuppliers = fetchSuppliers as ReturnType<typeof vi.fn>;
const mockFetchProducts = fetchProducts as ReturnType<typeof vi.fn>;
const mockAvgPrice = fetchSupplierAvgPrice as ReturnType<typeof vi.fn>;
const mockProductCount = fetchSupplierProductCount as ReturnType<typeof vi.fn>;
const mockDistribution = fetchSupplierPriceDistribution as ReturnType<typeof vi.fn>;
const mockEvolution = fetchSupplierPriceEvolution as ReturnType<typeof vi.fn>;

function renderPage(props = {}) {
  return render(<StatisticsPage {...props} />);
}

describe('StatisticsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchSuppliers.mockResolvedValue([]);
    mockFetchProducts.mockResolvedValue([]);
    mockAvgPrice.mockResolvedValue([]);
    mockProductCount.mockResolvedValue([]);
    mockDistribution.mockResolvedValue([]);
    mockEvolution.mockResolvedValue([]);
  });

  it('renders the page title', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Statistiques fournisseurs')).toBeDefined();
    });
  });

  it('renders all 4 chart titles', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Prix moyen par fournisseur')).toBeDefined();
      expect(screen.getByText('Evolution des prix par fournisseur')).toBeDefined();
      expect(screen.getByText('Nombre de produits par fournisseur')).toBeDefined();
      expect(screen.getByText('Repartition des prix')).toBeDefined();
    });
  });

  it('calls onBack when button is clicked', async () => {
    const onBack = vi.fn();
    renderPage({ onBack });
    await waitFor(() => {
      expect(screen.getByText('Retour')).toBeDefined();
    });
    screen.getByText('Retour').click();
    expect(onBack).toHaveBeenCalledOnce();
  });

  it('shows placeholder then chart when a model is selected', async () => {
    mockFetchProducts.mockResolvedValue([
      { id: 1, model: 'iPhone 15' },
      { id: 2, model: 'Galaxy S24' },
      { id: 3, model: 'iPhone 15' },
    ]);
    mockEvolution.mockResolvedValue([
      { supplier: 'SupA', week: 'S01-2025', avg_price: 100 },
      { supplier: 'SupB', week: 'S01-2025', avg_price: 110 },
    ]);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Comparaison prix produit par fournisseur')).toBeDefined();
      expect(screen.getByText('Selectionnez un produit pour afficher la comparaison')).toBeDefined();
    });

    const productSelect = screen.getByDisplayValue('Selectionner un produit');
    const options = productSelect.querySelectorAll('option');
    expect(options.length).toBe(3);

    fireEvent.change(productSelect, { target: { value: 'iPhone 15' } });

    await waitFor(() => {
      expect(screen.queryByText('Selectionnez un produit pour afficher la comparaison')).toBeNull();
    });
  });
});
