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
  onSave: vi.fn(),
  onBulkDelete: vi.fn(),
  selectedCount: 0,
  isBulkDeleting: false,
  hasEdits: false,
};

describe('ProductReferenceForm', () => {
  it('renders Colonnes button', () => {
    render(<ProductReferenceForm {...defaultProps} />);
    expect(screen.getByText('Colonnes')).toBeInTheDocument();
  });

  it('renders Enregistrer button', () => {
    render(<ProductReferenceForm {...defaultProps} />);
    expect(screen.getByText('Enregistrer')).toBeInTheDocument();
  });

  it('disables Enregistrer button when no edits', () => {
    render(<ProductReferenceForm {...defaultProps} />);
    expect(screen.getByText('Enregistrer')).toBeDisabled();
  });

  it('enables Enregistrer button when hasEdits is true', () => {
    render(<ProductReferenceForm {...defaultProps} hasEdits={true} />);
    expect(screen.getByText('Enregistrer')).not.toBeDisabled();
  });

  it('does not show bulk delete button when no selection', () => {
    render(<ProductReferenceForm {...defaultProps} />);
    expect(screen.queryByText('Supprimer produit(s)')).not.toBeInTheDocument();
  });

  it('shows bulk delete button when products are selected', () => {
    render(<ProductReferenceForm {...defaultProps} selectedCount={3} />);
    expect(screen.getByText('Supprimer produit(s)')).toBeInTheDocument();
  });

  it('disables bulk delete button when isBulkDeleting', () => {
    render(
      <ProductReferenceForm {...defaultProps} selectedCount={2} isBulkDeleting={true} />
    );
    expect(screen.getByText('Supprimer produit(s)')).toBeDisabled();
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

  it('calls onSave when clicking Enregistrer', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<ProductReferenceForm {...defaultProps} hasEdits={true} onSave={onSave} />);
    await user.click(screen.getByText('Enregistrer'));
    expect(onSave).toHaveBeenCalledOnce();
  });
});
