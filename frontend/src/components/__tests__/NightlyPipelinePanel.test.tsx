import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import NightlyPipelinePanel from '../NightlyPipelinePanel';

vi.mock('../../api', () => ({
  fetchNightlyConfig: vi.fn(),
  updateNightlyConfig: vi.fn(),
  triggerNightly: vi.fn(),
  fetchNightlyJobs: vi.fn(),
  fetchNightlyRecipients: vi.fn(),
  addNightlyRecipient: vi.fn(),
  deleteNightlyRecipient: vi.fn(),
}));

import {
  fetchNightlyConfig,
  updateNightlyConfig,
  triggerNightly,
  fetchNightlyJobs,
  fetchNightlyRecipients,
  addNightlyRecipient,
  deleteNightlyRecipient,
} from '../../api';

const mockFetchConfig = fetchNightlyConfig as ReturnType<typeof vi.fn>;
const mockUpdateConfig = updateNightlyConfig as ReturnType<typeof vi.fn>;
const mockTrigger = triggerNightly as ReturnType<typeof vi.fn>;
const mockFetchJobs = fetchNightlyJobs as ReturnType<typeof vi.fn>;
const mockFetchRecipients = fetchNightlyRecipients as ReturnType<typeof vi.fn>;
const mockAddRecipient = addNightlyRecipient as ReturnType<typeof vi.fn>;
const mockDeleteRecipient = deleteNightlyRecipient as ReturnType<typeof vi.fn>;

const defaultConfig = {
  id: 1,
  enabled: false,
  run_hour: 2,
  run_minute: 0,
  updated_at: null,
};

function renderPanel() {
  return render(<NightlyPipelinePanel />);
}

describe('NightlyPipelinePanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchConfig.mockResolvedValue(defaultConfig);
    mockFetchJobs.mockResolvedValue([]);
    mockFetchRecipients.mockResolvedValue([]);
  });

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  it('renders configuration section', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('Configuration du pipeline nightly')).toBeInTheDocument();
    });
  });

  it('renders manual trigger button', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('Lancer maintenant')).toBeInTheDocument();
    });
  });

  it('renders history section', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('Historique des executions')).toBeInTheDocument();
    });
  });

  it('renders recipients section', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('Destinataires du rapport email')).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // Toggle enabled
  // ---------------------------------------------------------------------------

  it('shows enabled=false initially', async () => {
    renderPanel();
    await waitFor(() => {
      const toggle = screen.getByRole('switch');
      expect(toggle).toHaveAttribute('aria-checked', 'false');
    });
  });

  it('toggles enabled state on click', async () => {
    renderPanel();
    await waitFor(() => screen.getByRole('switch'));

    fireEvent.click(screen.getByRole('switch'));
    const toggle = screen.getByRole('switch');
    expect(toggle).toHaveAttribute('aria-checked', 'true');
  });

  // ---------------------------------------------------------------------------
  // Save config
  // ---------------------------------------------------------------------------

  it('calls updateNightlyConfig on save', async () => {
    mockUpdateConfig.mockResolvedValue({ ...defaultConfig, run_hour: 4 });
    renderPanel();
    await waitFor(() => screen.getByText('Enregistrer'));

    fireEvent.click(screen.getByText('Enregistrer'));
    await waitFor(() => {
      expect(mockUpdateConfig).toHaveBeenCalledOnce();
    });
  });

  // ---------------------------------------------------------------------------
  // Trigger
  // ---------------------------------------------------------------------------

  it('calls triggerNightly on trigger button click', async () => {
    mockTrigger.mockResolvedValue({ status: 'triggered' });
    renderPanel();
    await waitFor(() => screen.getByText('Lancer maintenant'));

    fireEvent.click(screen.getByText('Lancer maintenant'));
    await waitFor(() => {
      expect(mockTrigger).toHaveBeenCalledOnce();
    });
  });

  it('shows in-progress banner after trigger', async () => {
    mockTrigger.mockResolvedValue({ status: 'triggered' });
    renderPanel();
    await waitFor(() => screen.getByText('Lancer maintenant'));

    fireEvent.click(screen.getByText('Lancer maintenant'));
    await waitFor(() => {
      expect(screen.getByText(/Pipeline en cours/)).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // Jobs
  // ---------------------------------------------------------------------------

  it('shows message when no jobs', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('Aucune exécution enregistrée.')).toBeInTheDocument();
    });
  });

  it('renders job rows', async () => {
    mockFetchJobs.mockResolvedValue([
      {
        id: 1,
        started_at: '2026-02-24T02:00:00Z',
        finished_at: '2026-02-24T02:05:00Z',
        status: 'completed',
        odoo_synced: 20,
        suppliers_synced: 2,
        matching_submitted: 15,
        email_sent: true,
        error_message: null,
      },
    ]);
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('Succès')).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // Recipients
  // ---------------------------------------------------------------------------

  it('renders existing recipients', async () => {
    mockFetchRecipients.mockResolvedValue([
      { id: 1, email: 'alice@example.com', name: 'Alice', active: true },
    ]);
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('alice@example.com')).toBeInTheDocument();
    });
  });

  it('adds a recipient', async () => {
    mockAddRecipient.mockResolvedValue({
      id: 2,
      email: 'bob@example.com',
      name: null,
      active: true,
    });
    renderPanel();
    await waitFor(() => screen.getByPlaceholderText('Email *'));

    fireEvent.change(screen.getByPlaceholderText('Email *'), {
      target: { value: 'bob@example.com' },
    });
    fireEvent.click(screen.getByText('Ajouter'));

    await waitFor(() => {
      expect(mockAddRecipient).toHaveBeenCalledWith({
        email: 'bob@example.com',
        name: undefined,
      });
      expect(screen.getByText('bob@example.com')).toBeInTheDocument();
    });
  });

  it('deletes a recipient', async () => {
    mockFetchRecipients.mockResolvedValue([
      { id: 1, email: 'charlie@example.com', name: null, active: true },
    ]);
    mockDeleteRecipient.mockResolvedValue(undefined);

    renderPanel();
    await waitFor(() => screen.getByText('charlie@example.com'));

    fireEvent.click(screen.getByTitle('Supprimer'));
    await waitFor(() => {
      expect(mockDeleteRecipient).toHaveBeenCalledWith(1);
      expect(screen.queryByText('charlie@example.com')).not.toBeInTheDocument();
    });
  });
});
