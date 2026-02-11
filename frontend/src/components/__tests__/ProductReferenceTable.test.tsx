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
  referenceData: {
    brands: [
      { id: 1, brand: 'Apple' },
      { id: 2, brand: 'Samsung' },
    ],
    colors: [
      { id: 1, color: 'Noir' },
      { id: 2, color: 'Blanc' },
    ],
    memories: [
      { id: 1, memory: '128 Go' },
      { id: 2, memory: '256 Go' },
    ],
    types: [{ id: 1, type: 'Smartphone' }],
    rams: [],
    normes: [],
  },
  selectedProducts: [] as number[],
  onToggleSelectProduct: vi.fn(),
  onChange: vi.fn(),
  onDelete: vi.fn(),
  currentPage: 1,
  totalPages: 1,
  rowsPerPage: 20,
  onPageChange: vi.fn(),
  onRowsPerPageChange: vi.fn(),
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
    expect(screen.getByText('Actions')).toBeInTheDocument();
  });

  it('renders product data in rows', () => {
    render(<ProductReferenceTable {...defaultProps} />);
    expect(screen.getByDisplayValue('iPhone 15')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Galaxy S24')).toBeInTheDocument();
    expect(screen.getByDisplayValue('1234567890123')).toBeInTheDocument();
  });

  it('renders pagination info', () => {
    render(<ProductReferenceTable {...defaultProps} />);
    expect(screen.getAllByText('Page 1 / 1').length).toBeGreaterThan(0);
  });

  it('disables previous button on first page', () => {
    render(<ProductReferenceTable {...defaultProps} />);
    const prevButtons = screen.getAllByText('Précédent');
    prevButtons.forEach((btn) => {
      expect(btn).toBeDisabled();
    });
  });

  it('disables next button on last page', () => {
    render(<ProductReferenceTable {...defaultProps} />);
    const nextButtons = screen.getAllByText('Suivant');
    nextButtons.forEach((btn) => {
      expect(btn).toBeDisabled();
    });
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
    const nextButtons = screen.getAllByText('Suivant');
    await user.click(nextButtons[0]);
    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it('renders checkboxes for product selection', () => {
    render(<ProductReferenceTable {...defaultProps} />);
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes.length).toBeGreaterThanOrEqual(2);
  });

  it('renders delete buttons for each row', () => {
    render(<ProductReferenceTable {...defaultProps} />);
    const deleteButtons = screen.getAllByTitle('Supprimer');
    expect(deleteButtons).toHaveLength(2);
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
    // text filter inputs + editable cell inputs
    expect(textInputs.length).toBeGreaterThanOrEqual(4);
  });
});
