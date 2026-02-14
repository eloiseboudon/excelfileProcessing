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
    expect(screen.getByText('Lancer le rapprochement')).toBeInTheDocument();
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
        screen.getByText('Aucun match en attente de validation.')
      ).toBeInTheDocument();
    });
  });

  it('renders the limit selector', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('Lancer le rapprochement')).toBeInTheDocument();
    });
    expect(screen.getByText('50 produits')).toBeInTheDocument();
    expect(screen.getByText('100 produits')).toBeInTheDocument();
    expect(screen.getByText('200 produits')).toBeInTheDocument();
    expect(screen.getByText('Tous')).toBeInTheDocument();
  });

  it('runs matching with default limit and shows report', async () => {
    mockRunMatching.mockResolvedValue({
      total_labels: 10,
      from_cache: 3,
      llm_calls: 1,
      auto_matched: 5,
      pending_review: 2,
      auto_created: 0,
      errors: 0,
      cost_estimate: 0.0012,
      duration_seconds: 3.5,
      remaining: 0,
    });

    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('Lancer le rapprochement')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Lancer le rapprochement'));

    await waitFor(() => {
      expect(mockRunMatching).toHaveBeenCalledWith(undefined, 50);
    });

    await waitFor(() => {
      expect(screen.getByText('5')).toBeInTheDocument();
      expect(screen.getByText('Matches auto')).toBeInTheDocument();
    });
  });

  it('shows remaining count after run with limit', async () => {
    mockRunMatching.mockResolvedValue({
      total_labels: 50,
      from_cache: 0,
      llm_calls: 2,
      auto_matched: 30,
      pending_review: 10,
      auto_created: 10,
      errors: 0,
      cost_estimate: 0.005,
      duration_seconds: 5.0,
      remaining: 150,
    });

    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('Lancer le rapprochement')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Lancer le rapprochement'));

    await waitFor(() => {
      expect(
        screen.getByText(/150 produits restants a traiter/)
      ).toBeInTheDocument();
    });
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
    expect(screen.getByText('Creer produit')).toBeInTheDocument();
    expect(screen.getByText('Ignorer')).toBeInTheDocument();
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

  it('rejects a match with product creation', async () => {
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
    mockRejectMatch.mockResolvedValue({ status: 'created' });

    renderPanel();

    await waitFor(() => {
      expect(screen.getByText('Creer produit')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Creer produit'));

    await waitFor(() => {
      expect(mockRejectMatch).toHaveBeenCalledWith(2, true);
    });
  });
});
