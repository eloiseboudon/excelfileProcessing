import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { NotificationProvider, useNotification } from '../NotificationProvider';

describe('NotificationProvider', () => {
  it('renders children', () => {
    render(
      <NotificationProvider>
        <div data-testid="child">Hello</div>
      </NotificationProvider>
    );
    expect(screen.getByTestId('child')).toBeInTheDocument();
  });

  it('throws when useNotification is used outside provider', () => {
    function BadComponent() {
      useNotification();
      return null;
    }

    // Suppress console.error for the expected error
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<BadComponent />)).toThrow(
      'useNotification must be used within NotificationProvider'
    );
    spy.mockRestore();
  });

  it('useNotification returns a function inside provider', () => {
    let notifyFn: ReturnType<typeof useNotification> | undefined;

    function TestConsumer() {
      notifyFn = useNotification();
      return <div>consumer</div>;
    }

    render(
      <NotificationProvider>
        <TestConsumer />
      </NotificationProvider>
    );

    expect(typeof notifyFn).toBe('function');
  });
});
