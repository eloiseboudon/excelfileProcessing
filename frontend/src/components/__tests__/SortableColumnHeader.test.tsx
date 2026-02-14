import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SortableColumnHeader from '../SortableColumnHeader';

describe('SortableColumnHeader', () => {
  it('renders label text', () => {
    render(
      <SortableColumnHeader
        label="Modèle"
        columnKey="model"
        currentSort={{ column: null, direction: null }}
        onSort={vi.fn()}
      />
    );
    expect(screen.getByText('Modèle')).toBeInTheDocument();
  });

  it('shows default ArrowUpDown icon when not sorted', () => {
    const { container } = render(
      <SortableColumnHeader
        label="Modèle"
        columnKey="model"
        currentSort={{ column: null, direction: null }}
        onSort={vi.fn()}
      />
    );
    // ArrowUpDown has a muted color
    const icon = container.querySelector('.text-\\[var\\(--color-text-muted\\)\\]');
    expect(icon).toBeInTheDocument();
  });

  it('shows ArrowUp icon with gold color when sorted asc', () => {
    const { container } = render(
      <SortableColumnHeader
        label="Modèle"
        columnKey="model"
        currentSort={{ column: 'model', direction: 'asc' }}
        onSort={vi.fn()}
      />
    );
    const icon = container.querySelector('.text-\\[\\#B8860B\\]');
    expect(icon).toBeInTheDocument();
  });

  it('shows ArrowDown icon with gold color when sorted desc', () => {
    const { container } = render(
      <SortableColumnHeader
        label="Modèle"
        columnKey="model"
        currentSort={{ column: 'model', direction: 'desc' }}
        onSort={vi.fn()}
      />
    );
    const icon = container.querySelector('.text-\\[\\#B8860B\\]');
    expect(icon).toBeInTheDocument();
  });

  it('shows default icon when another column is sorted', () => {
    const { container } = render(
      <SortableColumnHeader
        label="Modèle"
        columnKey="model"
        currentSort={{ column: 'brand', direction: 'asc' }}
        onSort={vi.fn()}
      />
    );
    const mutedIcon = container.querySelector('.text-\\[var\\(--color-text-muted\\)\\]');
    expect(mutedIcon).toBeInTheDocument();
  });

  it('calls onSort with column key when clicked', async () => {
    const onSort = vi.fn();
    const user = userEvent.setup();
    render(
      <SortableColumnHeader
        label="Modèle"
        columnKey="model"
        currentSort={{ column: null, direction: null }}
        onSort={onSort}
      />
    );
    await user.click(screen.getByRole('button'));
    expect(onSort).toHaveBeenCalledWith('model');
  });
});
