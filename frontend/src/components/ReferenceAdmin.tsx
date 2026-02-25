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
  { key: 'ram_options', label: 'Options RAM' },
  { key: 'norme_options', label: 'Normes' },
  { key: 'exclusions', label: 'Exclusions' },
  { key: 'suppliers', label: 'Fournisseurs' },
  { key: 'format_imports', label: 'Format import' },
];

const FIELD_LABELS: Record<string, string> = {
  name: 'Nom',
  model: 'Modèle',
  memory: 'Mémoire',
  tcp_value: 'Valeur TCP',
  supplier_id: 'Fournisseur',
  keyword: 'Mot-clé',
  pattern: 'Motif',
};

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
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erreur';
      notify(message, 'error');
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
    <div>
      {!table && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {TABLES.map((t) => (
            <button
              key={t.key}
              onClick={() => setTable(t.key)}
              className="card p-6 hover:bg-[var(--color-bg-elevated)] flex items-center justify-center font-semibold transition-colors"
            >
              {t.label}
            </button>
          ))}
        </div>
      )}
      {table && (
        <div>
          <div className="card p-4 mb-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-3">
              <button onClick={() => setTable(null)} className="btn btn-secondary text-sm">
                <ArrowLeft className="w-4 h-4" />
                <span>Retour</span>
              </button>
              <h3 className="text-xl font-semibold">
                {TABLES.find((t) => t.key === table)?.label}
              </h3>
            </div>
            <button onClick={handleAdd} className="btn btn-primary text-sm">
              <Plus className="w-4 h-4" />
              <span>Ajouter</span>
            </button>
          </div>
          <div className="card overflow-hidden">
            {fields.length > 0 && (
              <div className="flex items-center space-x-2 font-semibold px-4 py-3 border-b border-[var(--color-border-subtle)]">
                <span className="w-10 text-[var(--color-text-muted)]">ID</span>
                {fields.map((f) => (
                  <span key={f} className="flex-1 text-sm">
                    {FIELD_LABELS[f] ?? f}
                  </span>
                ))}
                <span className="w-20" />
              </div>
            )}
            <div className="divide-y divide-[var(--color-border-subtle)]">
              {data.map((item) => (
                <div key={item.id} className="flex items-center space-x-2 px-4 py-2">
                  <span className="w-10 text-[var(--color-text-muted)] text-sm">{item.id > 0 ? item.id : '-'}</span>
                  {fields.map((f) => (
                    table === 'format_imports' && f === 'supplier_id' ? (
                      <select
                        key={f}
                        value={item[f] ?? ''}
                        onChange={(e) => handleChange(item.id, f, e.target.value)}
                        className="flex-1 px-2 py-1 bg-[var(--color-bg-input)] text-[var(--color-text-primary)] rounded text-sm"
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
                        className="flex-1 px-2 py-1 bg-[var(--color-bg-input)] text-[var(--color-text-primary)] rounded placeholder:italic text-sm"
                      />
                    )
                  ))}
                  <div className="flex items-center gap-1">
                    <button onClick={() => handleSave(item.id)} className="btn btn-primary p-1.5">
                      <Save className="w-4 h-4" />
                    </button>
                    <button onClick={() => handleDelete(item.id)} className="btn btn-secondary p-1.5 text-red-500">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ReferenceAdmin;
