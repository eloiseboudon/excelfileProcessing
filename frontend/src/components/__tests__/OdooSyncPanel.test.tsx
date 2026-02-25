import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import OdooSyncPanel from '../OdooSyncPanel';
import { NotificationProvider } from '../NotificationProvider';

// Mock API functions
vi.mock('../../api', () => ({
  fetchOdooConfig: vi.fn(),
  updateOdooConfig: vi.fn(),
  testOdooConnection: vi.fn(),
  triggerOdooSync: vi.fn(),
  fetchOdooSyncJobs: vi.fn(),
  fetchOdooSyncJob: vi.fn(),
  updateOdooAutoSync: vi.fn(),
}));

import {
  fetchOdooConfig,
  updateOdooConfig,
  testOdooConnection,
  triggerOdooSync,
  fetchOdooSyncJobs,
  fetchOdooSyncJob,
  updateOdooAutoSync,
} from '../../api';

const mockFetchConfig = fetchOdooConfig as ReturnType<typeof vi.fn>;
const mockUpdateConfig = updateOdooConfig as ReturnType<typeof vi.fn>;
const mockTestConnection = testOdooConnection as ReturnType<typeof vi.fn>;
const mockTriggerSync = triggerOdooSync as ReturnType<typeof vi.fn>;
const mockFetchJobs = fetchOdooSyncJobs as ReturnType<typeof vi.fn>;

function renderPanel() {
  return render(
    <NotificationProvider>
      <OdooSyncPanel />
    </NotificationProvider>
  );
}

describe('OdooSyncPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchConfig.mockResolvedValue({ configured: false });
    mockFetchJobs.mockResolvedValue([]);
  });

  it('renders configuration section', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('Configuration Odoo')).toBeInTheDocument();
    });
  });

  it('renders synchronization section', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('Synchronisation', { selector: 'h2' })).toBeInTheDocument();
    });
  });

  it('renders history section', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('Historique des synchronisations')).toBeInTheDocument();
    });
  });

  it('shows empty state when not configured', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('Aucune synchronisation effectuée.')).toBeInTheDocument();
    });
  });

  it('renders URL input', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByPlaceholderText('https://odoo.monentreprise.fr')).toBeInTheDocument();
    });
  });

  it('renders database input', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByPlaceholderText('nom_base')).toBeInTheDocument();
    });
  });

  it('renders login input', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByPlaceholderText('admin')).toBeInTheDocument();
    });
  });

  it('populates form when config exists', async () => {
    mockFetchConfig.mockResolvedValue({
      configured: true,
      url: 'https://odoo.test.com',
      database: 'mydb',
      login: 'user',
      password: '__UNCHANGED__',
      auto_sync_enabled: false,
      auto_sync_interval_minutes: 1440,
    });
    renderPanel();
    await waitFor(() => {
      const urlInput = screen.getByPlaceholderText('https://odoo.monentreprise.fr') as HTMLInputElement;
      expect(urlInput.value).toBe('https://odoo.test.com');
    });
  });

  it('shows sync button', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('Lancer la synchronisation Odoo')).toBeInTheDocument();
    });
  });

  it('shows test connection button', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('Tester la connexion')).toBeInTheDocument();
    });
  });

  it('shows jobs when they exist', async () => {
    mockFetchJobs.mockResolvedValue([
      {
        id: 1,
        started_at: '2026-02-12T10:00:00',
        ended_at: '2026-02-12T10:01:00',
        status: 'success',
        trigger: 'manual',
        created_count: 5,
        updated_count: 3,
        unchanged_count: 10,
        error_count: 0,
        total_odoo_products: 18,
      },
    ]);
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('5 créés')).toBeInTheDocument();
      expect(screen.getByText('3 MAJ')).toBeInTheDocument();
    });
  });
});
