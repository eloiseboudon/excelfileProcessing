import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import LoginPage from '../LoginPage';
import { NotificationProvider } from '../NotificationProvider';

function renderLogin() {
  const onLogin = vi.fn();
  render(
    <NotificationProvider>
      <LoginPage onLogin={onLogin} />
    </NotificationProvider>
  );
  return { onLogin };
}

describe('LoginPage', () => {
  it('renders the login form', () => {
    renderLogin();
    expect(screen.getByText('Connexion')).toBeInTheDocument();
  });

  it('renders email input', () => {
    renderLogin();
    expect(screen.getByPlaceholderText('votre@email.com')).toBeInTheDocument();
  });

  it('renders password input', () => {
    renderLogin();
    expect(screen.getByPlaceholderText('Votre mot de passe')).toBeInTheDocument();
  });

  it('renders submit button', () => {
    renderLogin();
    expect(screen.getByRole('button', { name: 'Se connecter' })).toBeInTheDocument();
  });

  it('email input has type email', () => {
    renderLogin();
    const input = screen.getByPlaceholderText('votre@email.com');
    expect(input).toHaveAttribute('type', 'email');
  });

  it('password input has type password', () => {
    renderLogin();
    const input = screen.getByPlaceholderText('Votre mot de passe');
    expect(input).toHaveAttribute('type', 'password');
  });
});
