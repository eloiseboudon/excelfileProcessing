import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MultiSelectFilter from '../MultiSelectFilter';

const defaultProps = {
  options: ['Apple', 'Samsung', 'Xiaomi'],
  selected: [] as string[],
  onChange: vi.fn(),
};

describe('MultiSelectFilter', () => {
  it('renders button with "Tous" when nothing selected', () => {
    render(<MultiSelectFilter {...defaultProps} />);
    expect(screen.getByText('Tous')).toBeInTheDocument();
  });

  it('renders selected values in button', () => {
    render(<MultiSelectFilter {...defaultProps} selected={['Apple', 'Samsung']} />);
    expect(screen.getByText('Apple, Samsung')).toBeInTheDocument();
  });

  it('shows search input when dropdown is open', async () => {
    const user = userEvent.setup();
    render(<MultiSelectFilter {...defaultProps} />);
    await user.click(screen.getByText('Tous'));
    expect(screen.getByPlaceholderText('Rechercher...')).toBeInTheDocument();
  });

  it('filters options by search query', async () => {
    const user = userEvent.setup();
    render(<MultiSelectFilter {...defaultProps} />);
    await user.click(screen.getByText('Tous'));
    await user.type(screen.getByPlaceholderText('Rechercher...'), 'sam');
    expect(screen.getByText('Samsung')).toBeInTheDocument();
    expect(screen.queryByText('Apple')).not.toBeInTheDocument();
    expect(screen.queryByText('Xiaomi')).not.toBeInTheDocument();
  });

  it('resets search query when dropdown closes', async () => {
    const user = userEvent.setup();
    render(<MultiSelectFilter {...defaultProps} />);
    await user.click(screen.getByText('Tous'));
    await user.type(screen.getByPlaceholderText('Rechercher...'), 'sam');
    expect(screen.queryByText('Apple')).not.toBeInTheDocument();
    // Close dropdown by clicking outside
    await user.click(document.body);
    // Reopen
    await user.click(screen.getByText('Tous'));
    expect(screen.getByText('Apple')).toBeInTheDocument();
    expect(screen.getByText('Samsung')).toBeInTheDocument();
    expect(screen.getByText('Xiaomi')).toBeInTheDocument();
  });

  it('calls onChange when checking an option', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<MultiSelectFilter {...defaultProps} onChange={onChange} />);
    await user.click(screen.getByText('Tous'));
    await user.click(screen.getByText('Apple'));
    expect(onChange).toHaveBeenCalledWith(['Apple']);
  });

  it('search is case-insensitive', async () => {
    const user = userEvent.setup();
    render(<MultiSelectFilter {...defaultProps} />);
    await user.click(screen.getByText('Tous'));
    await user.type(screen.getByPlaceholderText('Rechercher...'), 'APPLE');
    expect(screen.getByText('Apple')).toBeInTheDocument();
    expect(screen.queryByText('Samsung')).not.toBeInTheDocument();
  });
});
