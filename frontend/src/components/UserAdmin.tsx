import { Plus, Save, Trash } from 'lucide-react';
import { useEffect, useState } from 'react';
import { createUser, deleteUser, fetchUsers, updateUser } from '../api';
import { useNotification } from './NotificationProvider';

interface UserItem {
  id: number;
  username: string;
  role: string;
  first_name: string;
  last_name: string;
  email: string;
}

interface UserAdminProps {
  isVisible: boolean;
  onClose: () => void;
}

function UserAdmin({ isVisible, onClose }: UserAdminProps) {
  const [users, setUsers] = useState<UserItem[]>([]);
  const notify = useNotification();

  useEffect(() => {
    if (isVisible) {
      load();
    }
  }, [isVisible]);

  const load = async () => {
    try {
      const res = await fetchUsers();
      setUsers(res as any[]);
    } catch {
      setUsers([]);
    }
  };

  const handleChange = (id: number, field: keyof UserItem, value: string) => {
    setUsers(prev => prev.map(u => (u.id === id ? { ...u, [field]: value } : u)));
  };

  const handleSave = async (id: number) => {
    const item = users.find(u => u.id === id);
    if (!item) return;
    try {
      if (id < 0) {
        await createUser({ username: item.username, role: item.role, first_name: item.first_name, last_name: item.last_name, email: item.email });
        notify('Utilisateur créé', 'success');
      } else {
        await updateUser(id, { username: item.username, role: item.role, first_name: item.first_name, last_name: item.last_name, email: item.email });
        notify('Utilisateur mis à jour', 'success');
      }
      await load();
    } catch {
      /* empty */
    }
  };

  const handleDelete = async (id: number) => {
    if (id < 0) {
      setUsers(prev => prev.filter(u => u.id !== id));
      return;
    }
    if (!window.confirm('Supprimer cet utilisateur ?')) return;
    try {
      await deleteUser(id);
      notify('Utilisateur supprimé', 'success');
      await load();
    } catch {
      /* empty */
    }
  };

  const handleAdd = () => {
    setUsers(prev => [
      ...prev,
      { id: Date.now() * -1, username: '', role: 'client', first_name: '', last_name: '', email: '' }
    ]);
  };

  if (!isVisible) return null;

  return (
    <div>
      <div className="card p-4 mb-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <h3 className="text-xl font-semibold">Gestion des utilisateurs</h3>
        <button
          onClick={handleAdd}
          className="btn btn-primary text-sm"
        >
          <Plus className="w-4 h-4" />
          <span>Ajouter</span>
        </button>
      </div>
      <div className="card overflow-hidden">
        <div className="hidden md:flex items-center space-x-2 font-semibold px-4 py-3 border-b border-[var(--color-border-subtle)]">
          <span className="w-10 text-[var(--color-text-muted)] text-sm">ID</span>
          <span className="flex-1 text-sm">Username</span>
          <span className="flex-1 text-sm">Nom</span>
          <span className="flex-1 text-sm">Prénom</span>
          <span className="flex-1 text-sm">Email</span>
          <span className="w-40 text-sm">Rôle</span>
          <span className="w-20" />
        </div>
        <div className="divide-y divide-[var(--color-border-subtle)]">
          {users.map(u => (
            <div key={u.id} className="flex items-center space-x-2 px-4 py-2">
              <span className="w-10 text-[var(--color-text-muted)] text-sm">{u.id > 0 ? u.id : '-'}</span>
              <input
                value={u.username}
                onChange={e => handleChange(u.id, 'username', e.target.value)}
                placeholder="username"
                className="flex-1 px-2 py-1 bg-[var(--color-bg-input)] text-[var(--color-text-primary)] rounded text-sm"
              />
              <input
                value={u.last_name}
                onChange={e => handleChange(u.id, 'last_name', e.target.value)}
                placeholder="nom"
                className="flex-1 px-2 py-1 bg-[var(--color-bg-input)] text-[var(--color-text-primary)] rounded text-sm"
              />
              <input
                value={u.first_name}
                onChange={e => handleChange(u.id, 'first_name', e.target.value)}
                placeholder="prénom"
                className="flex-1 px-2 py-1 bg-[var(--color-bg-input)] text-[var(--color-text-primary)] rounded text-sm"
              />
              <input
                value={u.email}
                onChange={e => handleChange(u.id, 'email', e.target.value)}
                placeholder="email"
                className="flex-1 px-2 py-1 bg-[var(--color-bg-input)] text-[var(--color-text-primary)] rounded text-sm"
              />
              <select
                value={u.role}
                onChange={e => handleChange(u.id, 'role', e.target.value)}
                className="w-40 px-2 py-1 bg-[var(--color-bg-input)] text-[var(--color-text-primary)] rounded text-sm"
              >
                <option value="client">client</option>
                <option value="admin">admin</option>
              </select>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => handleSave(u.id)}
                  className="btn btn-primary p-1.5"
                >
                  <Save className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleDelete(u.id)}
                  className="btn btn-secondary p-1.5 text-red-500"
                >
                  <Trash className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default UserAdmin;
