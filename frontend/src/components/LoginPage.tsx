import { Lock, Mail } from 'lucide-react';
import { useState } from 'react';
import { login } from '../api';
import { useNotification } from './NotificationProvider';

interface Props {
  onLogin: (role: string, token: string, refresh: string) => void;
}

export default function LoginPage({ onLogin }: Props) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const notify = useNotification();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await login(email, password);
      onLogin(data.role, data.token, data.refresh_token);
    } catch (err: any) {
      notify(err.message || 'Erreur de connexion', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg-surface)] text-[var(--color-text-primary)] px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <span className="text-3xl font-bold tracking-tight text-[#B8860B]">AJT Pro</span>
          <p className="text-sm text-[var(--color-text-muted)] mt-2">Connectez-vous pour accéder à votre espace</p>
        </div>

        <form onSubmit={handleSubmit} className="card space-y-5">
          <h2 className="text-lg font-semibold text-[var(--color-text-heading)] text-center">Connexion</h2>

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1.5">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-text-muted)]" />
                <input
                  type="email"
                  placeholder="votre@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full pl-10 pr-3 py-2.5 bg-[var(--color-bg-input)] border border-[var(--color-border-strong)] rounded-md text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:border-[#B8860B] focus:outline-none transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1.5">Mot de passe</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-text-muted)]" />
                <input
                  type="password"
                  placeholder="Votre mot de passe"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full pl-10 pr-3 py-2.5 bg-[var(--color-bg-input)] border border-[var(--color-border-strong)] rounded-md text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:border-[#B8860B] focus:outline-none transition-colors"
                />
              </div>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary w-full text-sm"
          >
            {loading ? 'Connexion...' : 'Se connecter'}
          </button>
        </form>
      </div>
    </div>
  );
}
