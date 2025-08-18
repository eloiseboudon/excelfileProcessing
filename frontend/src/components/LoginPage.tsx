import { useState } from 'react';
import { login } from '../api';
import { useNotification } from './NotificationProvider';

interface Props {
  onLogin: (role: string, token: string, refresh: string) => void;
}

export default function LoginPage({ onLogin }: Props) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const notify = useNotification();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const data = await login(email, password);
      onLogin(data.role, data.token, data.refresh_token);
    } catch (err: any) {
      notify(err.message || 'Erreur de connexion', 'error');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-900 text-white">
      <form onSubmit={handleSubmit} className="bg-zinc-800 p-6 rounded space-y-4 w-80">
        <h1 className="text-xl font-bold text-center">Connexion</h1>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full px-3 py-2 bg-zinc-700 rounded"
        />
        <input
          type="password"
          placeholder="Mot de passe"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full px-3 py-2 bg-zinc-700 rounded"
        />
        <button type="submit" className="btn btn-primary w-full">
          Se connecter
        </button>
      </form>
    </div>
  );
}
