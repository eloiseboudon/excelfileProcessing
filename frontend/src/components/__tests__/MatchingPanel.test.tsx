import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import MatchingPanel from '../MatchingPanel';
import { NotificationProvider } from '../NotificationProvider';

vi.mock('../../api', () => ({
  fetchSuppliers: vi.fn(),
  fetchPendingMatches: vi.fn(),
  fetchMatchingStats: vi.fn(),
  runMatching: vi.fn(),
  validateMatch: vi.fn(),
  rejectMatch: vi.fn(),
}));

import {
  fetchSuppliers,
  fetchPendingMatches,
  fetchMatchingStats,
  runMatching,
  validateMatch,
  rejectMatch,
} from '../../api';

const mockFetchSuppliers = fetchSuppliers as ReturnType<typeof vi.fn>;
const mockFetchPending = fetchPendingMatches as ReturnType<typeof vi.fn>;
const mockFetchStats = fetchMatchingStats as ReturnType<typeof vi.fn>;
const mockRunMatching = runMatching as ReturnType<typeof vi.fn>;
const mockValidateMatch = validateMatch as ReturnType<typeof vi.fn>;
const mockRejectMatch = rejectMatch as ReturnType<typeof vi.fn>;

function renderPanel() {
  return render(
    <NotificationProvider>
      <MatchingPanel />
    </NotificationProvider>
  );
}

describe('MatchingPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchSuppliers.mockResolvedValue([
      { id: 1, name: 'Yukatel' },
      { id: 2, name: 'PlusPos' },
    ]);
    mockFetchPending.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      per_page: 10,
    });
    mockFetchStats.mockResolvedValue({
      total_cached: 0,
      total_pending: 0,
      total_auto_matched: 0,
      total_manual: 0,
      cache_hit_rate: 0,
      by_supplier: [],
    });
  });

  it('renders the heading and run button', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('Rapprochement LLM')).toBeInTheDocument();
    });
    expect(screen.getByText('Lancer maintenant')).toBeInTheDocument();
  });

  it('loads suppliers on mount', async () => {
    renderPanel();
    await waitFor(() => {
      expect(mockFetchSuppliers).toHaveBeenCalledTimes(1);
    });
  });

  it('loads pending matches and stats on mount', async () => {
    renderPanel();
    await waitFor(() => {
      expect(mockFetchPending).toHaveBeenCalled();
      expect(mockFetchStats).toHaveBeenCalled();
    });
  });

  it('shows empty state when no pending matches', async () => {
    renderPanel();
    await waitFor(() => {
      expect(
        screen.getByText('Aucun match a afficher.')
      ).toBeInTheDocument();
    });
  });

  it('run button is enabled and shows correct label before launch', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('Lancer maintenant')).toBeInTheDocument();
    });
    const btn = screen.getByRole('button', { name: /Lancer maintenant/ });
    expect(btn).not.toBeDisabled();
  });

  it('runs matching and shows in-progress banner', async () => {
    mockRunMatching.mockResolvedValue(undefined);

    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('Lancer maintenant')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Lancer maintenant'));

    await waitFor(() => {
      expect(mockRunMatching).toHaveBeenCalledWith(undefined, undefined);
    });

    await waitFor(() => {
      expect(screen.getByText(/Rapprochement en cours/)).toBeInTheDocument();
    });
  });

  it('run button becomes disabled during matching', async () => {
    mockRunMatching.mockResolvedValue(undefined);

    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('Lancer maintenant')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Lancer maintenant'));

    await waitFor(() => {
      expect(screen.getByText('En cours…')).toBeInTheDocument();
    });
    const btn = screen.getByRole('button', { name: /En cours/ });
    expect(btn).toBeDisabled();
  });

  it('renders pending matches with candidates', async () => {
    mockFetchPending.mockResolvedValue({
      items: [
        {
          id: 1,
          supplier_id: 1,
          supplier_name: 'Yukatel',
          source_label: 'SM-S938B 256 BLK',
          extracted_attributes: {
            brand: 'Samsung',
            model_family: 'Galaxy S25 Ultra',
            storage: '256 Go',
            color: 'Noir',
          },
          candidates: [
            {
              product_id: 42,
              score: 85,
              product_name: 'Galaxy S25 Ultra',
              details: {},
            },
          ],
          status: 'pending',
          created_at: '2026-02-14T10:00:00',
        },
      ],
      total: 1,
      page: 1,
      per_page: 10,
    });

    renderPanel();

    await waitFor(() => {
      expect(screen.getByText('SM-S938B 256 BLK')).toBeInTheDocument();
    });

    expect(screen.getByText('Samsung')).toBeInTheDocument();
    expect(screen.getAllByText('Galaxy S25 Ultra').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('256 Go')).toBeInTheDocument();
    expect(screen.getByText('85%')).toBeInTheDocument();
    expect(screen.getByText('Valider')).toBeInTheDocument();
    expect(screen.getByText('Ignorer')).toBeInTheDocument();
    expect(screen.queryByText('Creer produit')).not.toBeInTheDocument();
  });

  it('validates a match', async () => {
    mockFetchPending.mockResolvedValue({
      items: [
        {
          id: 1,
          supplier_id: 1,
          supplier_name: 'Yukatel',
          source_label: 'Test Label',
          extracted_attributes: { brand: 'Samsung' },
          candidates: [
            { product_id: 42, score: 85, product_name: 'Product 42', details: {} },
          ],
          status: 'pending',
          created_at: null,
        },
      ],
      total: 1,
      page: 1,
      per_page: 10,
    });
    mockValidateMatch.mockResolvedValue({ status: 'validated' });

    renderPanel();

    await waitFor(() => {
      expect(screen.getByText('Valider')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Valider'));

    await waitFor(() => {
      expect(mockValidateMatch).toHaveBeenCalledWith(1, 42);
    });
  });

  it('ignores a match', async () => {
    mockFetchPending.mockResolvedValue({
      items: [
        {
          id: 2,
          supplier_id: 1,
          supplier_name: 'Yukatel',
          source_label: 'Unknown Product',
          extracted_attributes: { brand: 'Unknown' },
          candidates: [],
          status: 'pending',
          created_at: null,
        },
      ],
      total: 1,
      page: 1,
      per_page: 10,
    });
    mockRejectMatch.mockResolvedValue({ status: 'rejected' });

    renderPanel();

    await waitFor(() => {
      expect(screen.getByText('Ignorer')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Ignorer'));

    await waitFor(() => {
      expect(mockRejectMatch).toHaveBeenCalledWith(2, false);
    });
  });

  // --- New tests for filters, pagination, and scroll ---

  it('renders the status filter dropdown', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByTestId('status-filter')).toBeInTheDocument();
    });
    const select = screen.getByTestId('status-filter') as HTMLSelectElement;
    expect(select.value).toBe('pending');
    const options = Array.from(select.options).map((o) => o.text);
    expect(options).toContain('En attente');
    expect(options).toContain('Valides');
    expect(options).toContain('Rejetes');
    expect(options).toContain('Crees');
  });

  it('changes title based on status filter', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('Matchs en attente (0)')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId('status-filter'), {
      target: { value: 'validated' },
    });

    await waitFor(() => {
      expect(screen.getByText('Matchs valides (0)')).toBeInTheDocument();
    });
  });

  it('passes status filter to API call', async () => {
    renderPanel();
    await waitFor(() => {
      expect(mockFetchPending).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'pending' })
      );
    });

    fireEvent.change(screen.getByTestId('status-filter'), {
      target: { value: 'rejected' },
    });

    await waitFor(() => {
      expect(mockFetchPending).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'rejected' })
      );
    });
  });

  it('renders the model filter input', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByTestId('model-filter')).toBeInTheDocument();
    });
    expect(screen.getByPlaceholderText('Filtrer par modele...')).toBeInTheDocument();
  });

  it('shows bottom pagination when multiple pages', async () => {
    mockFetchPending.mockResolvedValue({
      items: Array.from({ length: 10 }, (_, i) => ({
        id: i + 1,
        supplier_id: 1,
        supplier_name: 'Yukatel',
        source_label: `Product ${i + 1}`,
        extracted_attributes: { brand: 'Samsung' },
        candidates: [],
        status: 'pending',
        created_at: null,
      })),
      total: 25,
      page: 1,
      per_page: 10,
    });

    renderPanel();

    await waitFor(() => {
      expect(screen.getAllByText('1 / 3').length).toBe(2);
    });
  });

  it('hides action buttons when viewing non-pending status', async () => {
    mockFetchPending.mockResolvedValue({
      items: [
        {
          id: 1,
          supplier_id: 1,
          supplier_name: 'Yukatel',
          source_label: 'Validated Product',
          extracted_attributes: { brand: 'Samsung' },
          candidates: [
            { product_id: 42, score: 85, product_name: 'Galaxy S25', details: {} },
          ],
          status: 'validated',
          created_at: null,
        },
      ],
      total: 1,
      page: 1,
      per_page: 10,
    });

    renderPanel();

    await waitFor(() => {
      expect(screen.getByTestId('status-filter')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId('status-filter'), {
      target: { value: 'validated' },
    });

    await waitFor(() => {
      expect(screen.getByText('Validated Product')).toBeInTheDocument();
    });

    expect(screen.queryByText('Valider')).not.toBeInTheDocument();
    expect(screen.queryByText('Ignorer')).not.toBeInTheDocument();
  });

  it('preserves scroll position after validation', async () => {
    const scrollToSpy = vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
    Object.defineProperty(window, 'scrollY', { value: 500, writable: true });

    mockFetchPending.mockResolvedValue({
      items: [
        {
          id: 1,
          supplier_id: 1,
          supplier_name: 'Yukatel',
          source_label: 'Scroll Test',
          extracted_attributes: { brand: 'Samsung' },
          candidates: [
            { product_id: 42, score: 85, product_name: 'Product 42', details: {} },
          ],
          status: 'pending',
          created_at: null,
        },
      ],
      total: 1,
      page: 1,
      per_page: 10,
    });
    mockValidateMatch.mockResolvedValue({ status: 'validated' });

    renderPanel();

    await waitFor(() => {
      expect(screen.getByText('Valider')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Valider'));

    await waitFor(() => {
      expect(mockValidateMatch).toHaveBeenCalled();
    });

    // Allow requestAnimationFrame to fire
    await new Promise((resolve) => setTimeout(resolve, 50));

    expect(scrollToSpy).toHaveBeenCalledWith(0, 500);
    scrollToSpy.mockRestore();
  });
});
