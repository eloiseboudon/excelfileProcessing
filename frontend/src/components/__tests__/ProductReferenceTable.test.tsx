import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ProductReferenceTable from '../ProductReferenceTable';
import type { ProductItem, Column } from '../ProductReference';

const columns: Column[] = [
  { key: 'id', label: 'ID' },
  { key: 'model', label: 'Modèle' },
  { key: 'description', label: 'Description' },
  { key: 'brand', label: 'Marque' },
  { key: 'memory', label: 'Mémoire' },
  { key: 'color', label: 'Couleur' },
  { key: 'type', label: 'Type' },
  { key: 'ram', label: 'RAM' },
  { key: 'norme', label: 'Norme' },
  { key: 'ean', label: 'EAN' },
];

const visibleColumns = columns.map((c) => c.key);

const mockProducts: ProductItem[] = [
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
];

const defaultProps = {
  columns,
  visibleColumns,
  paginatedData: mockProducts,
  filters: {} as Record<string, string | string[]>,
  onFilterChange: vi.fn(),
  filterOptions: {
    brandOptions: ['Apple', 'Samsung'],
    colorOptions: ['Noir', 'Blanc'],
    memoryOptions: ['128 Go', '256 Go'],
    typeOptions: ['Smartphone'],
    ramOptions: [],
    normeOptions: [],
  },
  filteredCount: 2,
  currentPage: 1,
  totalPages: 1,
  rowsPerPage: 20,
  onPageChange: vi.fn(),
  onRowsPerPageChange: vi.fn(),
  sortConfig: { column: null, direction: null } as { column: string | null; direction: 'asc' | 'desc' | null },
  onSort: vi.fn(),
};

describe('ProductReferenceTable', () => {
  it('renders column headers', () => {
    render(<ProductReferenceTable {...defaultProps} />);
    expect(screen.getByText('Modèle')).toBeInTheDocument();
    expect(screen.getByText('Description')).toBeInTheDocument();
    expect(screen.getByText('Marque')).toBeInTheDocument();
    expect(screen.getByText('Mémoire')).toBeInTheDocument();
    expect(screen.getByText('Couleur')).toBeInTheDocument();
    expect(screen.getByText('EAN')).toBeInTheDocument();
  });

  it('renders product data in rows as read-only text', () => {
    render(<ProductReferenceTable {...defaultProps} />);
    expect(screen.getByText('iPhone 15')).toBeInTheDocument();
    expect(screen.getByText('Galaxy S24')).toBeInTheDocument();
    expect(screen.getByText('1234567890123')).toBeInTheDocument();
  });

  it('renders pagination info', () => {
    render(<ProductReferenceTable {...defaultProps} />);
    expect(screen.getByText('1 / 1')).toBeInTheDocument();
  });

  it('disables previous button on first page', () => {
    render(<ProductReferenceTable {...defaultProps} />);
    expect(screen.getByLabelText('Page précédente')).toBeDisabled();
  });

  it('disables next button on last page', () => {
    render(<ProductReferenceTable {...defaultProps} />);
    expect(screen.getByLabelText('Page suivante')).toBeDisabled();
  });

  it('calls onPageChange when clicking next', async () => {
    const user = userEvent.setup();
    const onPageChange = vi.fn();
    render(
      <ProductReferenceTable
        {...defaultProps}
        currentPage={1}
        totalPages={3}
        onPageChange={onPageChange}
      />
    );
    await user.click(screen.getByLabelText('Page suivante'));
    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it('renders multi-select filters for reference columns', () => {
    render(<ProductReferenceTable {...defaultProps} />);
    const tousButtons = screen.getAllByText('Tous');
    // brand, memory, color, type, ram, norme = 6 multi-select filters
    expect(tousButtons.length).toBe(6);
  });

  it('renders text input filters for text columns', () => {
    render(<ProductReferenceTable {...defaultProps} />);
    // id, model, description, ean = 4 text filters
    const textInputs = screen.getAllByRole('textbox');
    expect(textInputs.length).toBeGreaterThanOrEqual(4);
  });
});
