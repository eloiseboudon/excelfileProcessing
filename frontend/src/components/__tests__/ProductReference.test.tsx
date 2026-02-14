import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import ProductReference from '../ProductReference';
import { NotificationProvider } from '../NotificationProvider';

vi.mock('../../api', () => ({
  fetchProducts: vi.fn().mockResolvedValue([
    {
      id: 1,
      ean: '1234567890123',
      model: 'iPhone 15',
      description: 'Smartphone Apple',
      brand_id: 1,
      brand: 'Apple',
      memory_id: 1,
      memory: '128 Go',
      color_id: 1,
      color: 'Noir',
      type_id: 1,
      type: 'Smartphone',
      ram_id: null,
      ram: null,
      norme_id: null,
      norme: null,
    },
    {
      id: 2,
      ean: '9876543210987',
      model: 'Galaxy S24',
      description: 'Smartphone Samsung',
      brand_id: 2,
      brand: 'Samsung',
      memory_id: 2,
      memory: '256 Go',
      color_id: 2,
      color: 'Blanc',
      type_id: 1,
      type: 'Smartphone',
      ram_id: null,
      ram: null,
      norme_id: null,
      norme: null,
    },
  ]),
  fetchBrands: vi.fn().mockResolvedValue([
    { id: 1, brand: 'Apple' },
    { id: 2, brand: 'Samsung' },
  ]),
  fetchColors: vi.fn().mockResolvedValue([
    { id: 1, color: 'Noir' },
    { id: 2, color: 'Blanc' },
  ]),
  fetchMemoryOptions: vi.fn().mockResolvedValue([
    { id: 1, memory: '128 Go' },
    { id: 2, memory: '256 Go' },
  ]),
  fetchDeviceTypes: vi.fn().mockResolvedValue([{ id: 1, type: 'Smartphone' }]),
  fetchRAMOptions: vi.fn().mockResolvedValue([]),
  fetchNormeOptions: vi.fn().mockResolvedValue([]),
  bulkUpdateProducts: vi.fn().mockResolvedValue({}),
  createProduct: vi.fn().mockResolvedValue({}),
  deleteProduct: vi.fn().mockResolvedValue({}),
  bulkDeleteProducts: vi.fn().mockResolvedValue({ deleted: [] }),
  setAuthToken: vi.fn(),
  setRefreshToken: vi.fn(),
}));

function renderProductReference() {
  return render(
    <NotificationProvider>
      <ProductReference />
    </NotificationProvider>
  );
}

describe('ProductReference', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the toolbar buttons', () => {
    renderProductReference();
    expect(screen.getByText('Colonnes')).toBeInTheDocument();
    expect(screen.getByText('Enregistrer')).toBeInTheDocument();
  });

  it('renders the table after loading products', async () => {
    renderProductReference();
    await waitFor(() => {
      expect(screen.getByDisplayValue('iPhone 15')).toBeInTheDocument();
    });
    expect(screen.getByDisplayValue('Galaxy S24')).toBeInTheDocument();
  });

  it('renders column headers', async () => {
    renderProductReference();
    await waitFor(() => {
      expect(screen.getByText('Modèle')).toBeInTheDocument();
    });
    expect(screen.getByText('Description')).toBeInTheDocument();
    expect(screen.getByText('Marque')).toBeInTheDocument();
    expect(screen.getByText('EAN')).toBeInTheDocument();
  });

  it('renders pagination controls', async () => {
    renderProductReference();
    await waitFor(() => {
      expect(screen.getByLabelText('Page précédente')).toBeInTheDocument();
    });
    expect(screen.getByLabelText('Page suivante')).toBeInTheDocument();
  });

  it('disables save button when no edits exist', () => {
    renderProductReference();
    const saveButton = screen.getByText('Enregistrer');
    expect(saveButton).toBeDisabled();
  });
});
