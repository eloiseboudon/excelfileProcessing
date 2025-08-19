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
    <div className="mt-8">
      <div className="flex justify-end mb-4">
        <button
          onClick={onClose}
          className="px-3 py-1 bg-zinc-800 rounded hover:bg-zinc-700"
        >
          Fermer
        </button>
      </div>
      <div className="space-y-2">
        <div className="flex items-center space-x-2 font-semibold px-2">
          <span className="w-10 text-zinc-400">ID</span>
          <span className="flex-1">Username</span>
          <span className="flex-1">Nom</span>
          <span className="flex-1">Prénom</span>
          <span className="flex-1">Email</span>
          <span className="w-40">Rôle</span>
          <span className="w-16" />
        </div>
        {users.map(u => (
          <div key={u.id} className="flex items-center space-x-2 bg-zinc-800 p-2 rounded">
            <span className="w-10 text-zinc-400">{u.id > 0 ? u.id : '-'}</span>
            <input
              value={u.username}
              onChange={e => handleChange(u.id, 'username', e.target.value)}
              placeholder="username"
              className="flex-1 px-2 py-1 bg-zinc-700 text-white rounded"
            />

            <input
              value={u.last_name}
              onChange={e => handleChange(u.id, 'last_name', e.target.value)}
              placeholder="nom"
              className="flex-1 px-2 py-1 bg-zinc-700 text-white rounded"
            /> <input
              value={u.first_name}
              onChange={e => handleChange(u.id, 'first_name', e.target.value)}
              placeholder="prénom"
              className="flex-1 px-2 py-1 bg-zinc-700 text-white rounded"
            />
            <input
              value={u.email}
              onChange={e => handleChange(u.id, 'email', e.target.value)}
              placeholder="email"
              className="flex-1 px-2 py-1 bg-zinc-700 text-white rounded"
            />
            <select
              value={u.role}
              onChange={e => handleChange(u.id, 'role', e.target.value)}
              className="w-40 px-2 py-1 bg-zinc-700 text-white rounded"
            >
              <option value="client">client</option>
              <option value="admin">admin</option>
            </select>
            <button
              onClick={() => handleSave(u.id)}
              className="p-2 bg-green-600 text-white rounded hover:bg-green-700"
            >
              <Save className="w-4 h-4" />
            </button>
            <button
              onClick={() => handleDelete(u.id)}
              className="p-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              <Trash className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>
      <div className="flex justify-end mt-4">
        <button
          onClick={handleAdd}
          className="flex items-center space-x-2 px-3 py-2 bg-green-600 text-white rounded hover:bg-green-700"
        >
          <Plus className="w-4 h-4" />
          <span>Ajouter</span>
        </button>
      </div>
    </div>
  );
}

export default UserAdmin;
