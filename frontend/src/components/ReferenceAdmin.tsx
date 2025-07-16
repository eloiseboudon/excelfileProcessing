import { ArrowLeft, Plus, Save, Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import {
  createReferenceItem,
  deleteReferenceItem,
  fetchReferenceTable,
  fetchSuppliers,
  updateReferenceItem
} from '../api';
import { useNotification } from './NotificationProvider';

interface ReferenceAdminProps {
  onClose: () => void;
  isVisible: boolean;
}

const TABLES = [
  { key: 'brands', label: 'Marques' },
  { key: 'colors', label: 'Couleurs' },
  { key: 'memory_options', label: 'Options mémoire' },
  { key: 'device_types', label: "Types d'appareil" },
  { key: 'exclusions', label: 'Exclusions' },
  { key: 'suppliers', label: 'Fournisseurs' },
  { key: 'format_imports', label: 'Format import' },
];

function ReferenceAdmin({ isVisible, onClose }: ReferenceAdminProps) {
  const [table, setTable] = useState<string | null>(null);
  const [data, setData] = useState<any[]>([]);
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const notify = useNotification();

  useEffect(() => {
    if (isVisible && table) {
      load(table);
    }
  }, [isVisible, table]);

  useEffect(() => {
    if (table === 'format_imports') {
      fetchSuppliers()
        .then((s) => setSuppliers(s as any[]))
        .catch(() => setSuppliers([]));
    }
  }, [table]);

  const load = async (t: string) => {
    try {
      const res = await fetchReferenceTable(t);
      setData(res as any[]);
    } catch {
      setData([]);
    }
  };

  const handleChange = (id: number, field: string, value: string) => {
    setData((prev) =>
      prev.map((item) => (item.id === id ? { ...item, [field]: value } : item))
    );
  };

  const handleSave = async (id: number) => {
    const item = data.find((d) => d.id === id);
    if (!item) return;
    const payload: Record<string, any> = { ...item };
    delete payload.id;
    try {
      if (id < 0) {
        await createReferenceItem(table!, payload);
        notify('Entrée créée', 'success');
      } else {
        await updateReferenceItem(table!, id, payload);
        notify('Entrée mise à jour', 'success');
      }
      await load(table!);
    } catch {
      /* empty */
    }
  };

  const handleDelete = async (id: number) => {
    try {
      if (id < 0) {
        setData((prev) => prev.filter((i) => i.id !== id));
      } else {
        await deleteReferenceItem(table!, id);
        notify('Entrée supprimée', 'success');
        await load(table!);
      }
    } catch {
      /* empty */
    }
  };

  const handleAdd = () => {
    const fields = data.length > 0 ? Object.keys(data[0]).filter((k) => k !== 'id') : [];
    const newItem: any = { id: Date.now() * -1 };
    fields.forEach((f) => (newItem[f] = ''));
    setData((prev) => [...prev, newItem]);
  };

  if (!isVisible) return null;

  const fields = data.length > 0 ? Object.keys(data[0]).filter((k) => k !== 'id') : [];

  return (
    <div className="mt-8">
      <div className="flex justify-end mb-4">
        <button
          onClick={() => {
            setTable(null);
            onClose();
          }}
          className="px-3 py-1 bg-zinc-800 rounded hover:bg-zinc-700"
        >
          Fermer
        </button>
      </div>
      {!table && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {TABLES.map((t) => (
            <button
              key={t.key}
              onClick={() => setTable(t.key)}
              className="p-6 rounded-xl bg-zinc-800 border border-zinc-700 hover:bg-zinc-700 flex items-center justify-center font-semibold"
            >
              {t.label}
            </button>
          ))}
        </div>
      )}
      {table && (
        <div>
          <div className="flex items-center mb-4 space-x-4">
            <button onClick={() => setTable(null)} className="flex items-center space-x-2 px-3 py-2 bg-zinc-800 rounded hover:bg-zinc-700">
              <ArrowLeft className="w-4 h-4" />
              <span>Retour</span>
            </button>
            <h3 className="text-xl font-semibold">
              {TABLES.find((t) => t.key === table)?.label}
            </h3>
            <button onClick={handleAdd} className="ml-auto flex items-center space-x-2 px-3 py-2 bg-green-600 text-white rounded hover:bg-green-700">
              <Plus className="w-4 h-4" />
              <span>Ajouter</span>
            </button>
          </div>
          <div className="space-y-2">
            {fields.length > 0 && (
              <div className="flex items-center space-x-2 font-semibold px-2">
                <span className="w-10 text-zinc-400">ID</span>
                {fields.map((f) => (
                  <span key={f} className="flex-1 capitalize">
                    {f}
                  </span>
                ))}
                <span className="w-8" />
                <span className="w-8" />
              </div>
            )}
            {data.map((item) => (
              <div key={item.id} className="flex items-center space-x-2 bg-zinc-800 p-2 rounded">
                <span className="w-10 text-zinc-400">{item.id > 0 ? item.id : '-'}</span>
                {fields.map((f) => (
                  table === 'format_imports' && f === 'supplier_id' ? (
                    <select
                      key={f}
                      value={item[f] ?? ''}
                      onChange={(e) => handleChange(item.id, f, e.target.value)}
                      className="flex-1 px-2 py-1 bg-zinc-700 text-white rounded"
                    >
                      <option value="">--</option>
                      {suppliers.map((s) => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      key={f}
                      value={item[f] ?? ''}
                      placeholder={f}
                      onChange={(e) => handleChange(item.id, f, e.target.value)}
                      className="flex-1 px-2 py-1 bg-zinc-700 text-white rounded placeholder:italic"
                    />
                  )
                ))}
                <button onClick={() => handleSave(item.id)} className="p-2 bg-green-600 text-white rounded hover:bg-green-700">
                  <Save className="w-4 h-4" />
                </button>
                <button onClick={() => handleDelete(item.id)} className="p-2 bg-red-600 text-white rounded hover:bg-red-700">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default ReferenceAdmin;

