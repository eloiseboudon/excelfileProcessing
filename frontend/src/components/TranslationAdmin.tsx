import { useEffect, useState } from 'react';
import { ArrowLeft, Save, Trash2, Plus } from 'lucide-react';
import {
  fetchReferenceTable,
  updateReferenceItem,
  createReferenceItem,
  deleteReferenceItem,
  fetchColors
} from '../api';
import { useNotification } from './NotificationProvider';

interface TranslationAdminProps {
  onClose: () => void;
  isVisible: boolean;
}

const TABLES = [
  { key: 'color_translations', label: 'Cohérence des couleurs' },
];

function TranslationAdmin({ isVisible, onClose }: TranslationAdminProps) {
  const [table, setTable] = useState<string | null>(null);
  const [data, setData] = useState<Record<string, unknown>[]>([]);
  const [colors, setColors] = useState<Record<string, unknown>[]>([]);
  const notify = useNotification();

  useEffect(() => {
    if (isVisible && table) {
      load(table);
    }
  }, [isVisible, table]);

  const load = async (t: string) => {
    try {
      if (t === 'color_translations') {
        const [translations, cols] = await Promise.all([
          fetchReferenceTable(t),
          fetchColors(),
        ]);
        setColors(cols as Record<string, unknown>[]);
        const mapped = (translations as Record<string, unknown>[]).map((item) => {
          const c = (cols as Record<string, unknown>[]).find((cc) => cc.color === item.color_target);
          return { ...item, color_target_id: c ? c.id : '' };
        });
        setData(mapped);
      } else {
        const res = await fetchReferenceTable(t);
        setData(res as Record<string, unknown>[]);
      }
    } catch {
      setData([]);
    }
  };

  const handleChange = (id: number, field: string, value: string) => {
    setData((prev) =>
      prev.map((item) => {
        if (item.id !== id) return item;
        const updated = { ...item, [field]: value };
        if (table === 'color_translations' && field === 'color_target_id') {
          const col = colors.find((c) => String(c.id) === value);
          if (col) {
            updated.color_target = col.color;
          }
        }
        return updated;
      })
    );
  };

  const handleSave = async (id: number) => {
    const item = data.find((d) => d.id === id);
    if (!item) return;
    const payload: Record<string, unknown> = { ...item };
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
      notify(err instanceof Error ? err.message : 'Erreur de sauvegarde', 'error');
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
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Erreur de suppression', 'error');
    }
  };

  const handleAdd = () => {
    const fields =
      data.length > 0 ? Object.keys(data[0]).filter((k) => k !== 'id') : [];
    const newItem: Record<string, unknown> = { id: Date.now() * -1 };
    fields.forEach((f) => (newItem[f] = ''));
    if (table === 'color_translations') {
      newItem.color_target_id = colors[0]?.id ?? '';
      newItem.color_target = colors[0]?.color ?? '';
    }
    setData((prev) => [...prev, newItem]);
  };

  if (!isVisible) return null;

  const fields =
    data.length > 0 ? Object.keys(data[0]).filter((k) => k !== 'id') : [];
  const displayedFields =
    table === 'color_translations'
      ? fields.filter((f) => f !== 'color_target_id' && f !== 'color_target')
      : fields;

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
            <div className="divide-y divide-[var(--color-border-subtle)]">
              {data.map((item) => (
                <div key={item.id} className="flex items-center space-x-2 px-4 py-2">
                  <span className="w-10 text-[var(--color-text-muted)] text-sm">{item.id > 0 ? item.id : '-'}</span>
                  {displayedFields.map((f) => (
                    <input
                      key={f}
                      value={item[f] ?? ''}
                      placeholder={f}
                      onChange={(e) => handleChange(item.id, f, e.target.value)}
                      className="flex-1 px-2 py-1 bg-[var(--color-bg-input)] text-[var(--color-text-primary)] rounded placeholder:italic text-sm"
                    />
                  ))}
                  {table === 'color_translations' && (
                    <select
                      value={item.color_target_id ?? ''}
                      onChange={(e) => handleChange(item.id, 'color_target_id', e.target.value)}
                      className="flex-1 px-2 py-1 bg-[var(--color-bg-input)] text-[var(--color-text-primary)] rounded text-sm"
                    >
                      {colors.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.color}
                        </option>
                      ))}
                    </select>
                  )}
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

export default TranslationAdmin;
