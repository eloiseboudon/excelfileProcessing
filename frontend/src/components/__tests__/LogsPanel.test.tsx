import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import LogsPanel from '../LogsPanel';

vi.mock('../../api', () => ({
  fetchActivityLogs: vi.fn(),
  fetchAppLogs: vi.fn(),
}));

import { fetchActivityLogs, fetchAppLogs } from '../../api';

const mockFetchActivityLogs = fetchActivityLogs as ReturnType<typeof vi.fn>;
const mockFetchAppLogs = fetchAppLogs as ReturnType<typeof vi.fn>;

describe('LogsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchActivityLogs.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      per_page: 20,
    });
    mockFetchAppLogs.mockResolvedValue({
      lines: [],
      total_lines: 0,
    });
  });

  it('renders activity tab by default', async () => {
    render(<LogsPanel />);
    await waitFor(() => {
      expect(screen.getByText("Historique d'activité")).toBeInTheDocument();
    });
  });

  it('renders app logs tab', async () => {
    render(<LogsPanel />);
    await waitFor(() => {
      expect(screen.getByText('Logs application')).toBeInTheDocument();
    });
  });

  it('shows empty state for activity logs', async () => {
    render(<LogsPanel />);
    await waitFor(() => {
      expect(screen.getByText('Aucune activité enregistrée.')).toBeInTheDocument();
    });
  });

  it('displays activity log entries', async () => {
    mockFetchActivityLogs.mockResolvedValue({
      items: [
        {
          id: 1,
          timestamp: '2026-02-14T10:00:00',
          action: 'user.login',
          category: 'auth',
          user_id: 1,
          username: 'admin',
          details: { email: 'admin@test.com' },
          ip_address: '127.0.0.1',
        },
      ],
      total: 1,
      page: 1,
      per_page: 20,
    });

    render(<LogsPanel />);
    await waitFor(() => {
      expect(screen.getByText('user.login')).toBeInTheDocument();
      expect(screen.getByText('auth')).toBeInTheDocument();
      expect(screen.getByText('admin')).toBeInTheDocument();
      expect(screen.getByText('127.0.0.1')).toBeInTheDocument();
    });
  });

  it('switches to app logs tab', async () => {
    render(<LogsPanel />);
    fireEvent.click(screen.getByText('Logs application'));
    await waitFor(() => {
      expect(screen.getByText('Aucun log disponible.')).toBeInTheDocument();
    });
  });

  it('displays app log lines', async () => {
    mockFetchAppLogs.mockResolvedValue({
      lines: [
        '{"timestamp":"2026-02-14T10:00:00","level":"INFO","message":"Started"}',
        '{"timestamp":"2026-02-14T10:01:00","level":"ERROR","message":"Failed"}',
      ],
      total_lines: 2,
    });

    render(<LogsPanel />);
    fireEvent.click(screen.getByText('Logs application'));
    await waitFor(() => {
      expect(screen.getByText(/Started/)).toBeInTheDocument();
      expect(screen.getByText(/Failed/)).toBeInTheDocument();
    });
  });

  it('shows category filter', async () => {
    render(<LogsPanel />);
    await waitFor(() => {
      expect(screen.getByText('Catégorie :')).toBeInTheDocument();
    });
  });

  it('shows refresh button', async () => {
    render(<LogsPanel />);
    await waitFor(() => {
      expect(screen.getByText('Rafraîchir')).toBeInTheDocument();
    });
  });

  it('shows entry count', async () => {
    mockFetchActivityLogs.mockResolvedValue({
      items: [],
      total: 42,
      page: 1,
      per_page: 20,
    });

    render(<LogsPanel />);
    await waitFor(() => {
      expect(screen.getByText('42 entrées')).toBeInTheDocument();
    });
  });
});
