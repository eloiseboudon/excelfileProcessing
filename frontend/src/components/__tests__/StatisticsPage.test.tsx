import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import StatisticsPage from '../StatisticsPage';

vi.mock('../../api', () => ({
  fetchSuppliers: vi.fn(),
  fetchSupplierAvgPrice: vi.fn(),
  fetchSupplierProductCount: vi.fn(),
  fetchSupplierPriceDistribution: vi.fn(),
  fetchSupplierPriceEvolution: vi.fn(),
}));

import {
  fetchSuppliers,
  fetchSupplierAvgPrice,
  fetchSupplierProductCount,
  fetchSupplierPriceDistribution,
  fetchSupplierPriceEvolution,
} from '../../api';

const mockFetchSuppliers = fetchSuppliers as ReturnType<typeof vi.fn>;
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
});
