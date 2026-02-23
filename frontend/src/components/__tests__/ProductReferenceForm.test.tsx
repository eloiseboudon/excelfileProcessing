import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ProductReferenceForm from '../ProductReferenceForm';
import type { Column } from '../ProductReference';

const columns: Column[] = [
  { key: 'id', label: 'ID' },
  { key: 'model', label: 'Modèle' },
  { key: 'description', label: 'Description' },
  { key: 'brand', label: 'Marque' },
  { key: 'ean', label: 'EAN' },
];

const defaultProps = {
  columns,
  visibleColumns: columns.map((c) => c.key),
  showColumnMenu: false,
  onToggleColumnMenu: vi.fn(),
  onToggleColumn: vi.fn(),
};

describe('ProductReferenceForm', () => {
  it('renders Colonnes button', () => {
    render(<ProductReferenceForm {...defaultProps} />);
    expect(screen.getByText('Colonnes')).toBeInTheDocument();
  });

  it('does not show column menu when showColumnMenu is false', () => {
    render(<ProductReferenceForm {...defaultProps} showColumnMenu={false} />);
    expect(screen.queryByText('ID')).not.toBeInTheDocument();
  });

  it('shows column menu with checkboxes when showColumnMenu is true', () => {
    render(<ProductReferenceForm {...defaultProps} showColumnMenu={true} />);
    expect(screen.getByText('ID')).toBeInTheDocument();
    expect(screen.getByText('Modèle')).toBeInTheDocument();
    expect(screen.getByText('Marque')).toBeInTheDocument();
  });

  it('calls onToggleColumnMenu when clicking Colonnes', async () => {
    const user = userEvent.setup();
    const onToggleColumnMenu = vi.fn();
    render(
      <ProductReferenceForm {...defaultProps} onToggleColumnMenu={onToggleColumnMenu} />
    );
    await user.click(screen.getByText('Colonnes'));
    expect(onToggleColumnMenu).toHaveBeenCalledOnce();
  });
});
