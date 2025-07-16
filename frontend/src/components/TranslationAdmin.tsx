import React, { useEffect, useState } from 'react';
import { Save, Trash2, Plus, ArrowLeft } from 'lucide-react';
import {
  fetchReferenceTable,
  updateReferenceItem,
  createReferenceItem,
  deleteReferenceItem,
  fetchColors
} from '../api';

interface TranslationAdminProps {
  onClose: () => void;
  isVisible: boolean;
}

const TABLES = [
  { key: 'color_translations', label: 'Cohérence des couleurs' },
];

function TranslationAdmin({ isVisible, onClose }: TranslationAdminProps) {
  const [table, setTable] = useState<string | null>(null);
  const [data, setData] = useState<any[]>([]);
  const [colors, setColors] = useState<any[]>([]);

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
        setColors(cols as any[]);
        const mapped = (translations as any[]).map((item) => {
          const c = (cols as any[]).find((cc) => cc.color === item.color_target);
          return { ...item, color_target_id: c ? c.id : '' };
        });
        setData(mapped);
      } else {
        const res = await fetchReferenceTable(t);
        setData(res as any[]);
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
    const payload: Record<string, any> = { ...item };
    delete payload.id;
    try {
      if (id < 0) {
        await createReferenceItem(table!, payload);
      } else {
        await updateReferenceItem(table!, id, payload);
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
        await load(table!);
      }
    } catch {
      /* empty */
    }
  };

  const handleAdd = () => {
    const fields =
      data.length > 0 ? Object.keys(data[0]).filter((k) => k !== 'id') : [];
    const newItem: any = { id: Date.now() * -1 };
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
            {data.map((item) => (
              <div key={item.id} className="flex items-center space-x-2 bg-zinc-800 p-2 rounded">
                <span className="w-10 text-zinc-400">{item.id > 0 ? item.id : '-'}</span>
                {displayedFields.map((f) => (
                  <input
                    key={f}
                    value={item[f] ?? ''}
                    placeholder={f}
                    onChange={(e) => handleChange(item.id, f, e.target.value)}
                    className="flex-1 px-2 py-1 bg-zinc-700 text-white rounded placeholder:italic"
                  />
                ))}
                {table === 'color_translations' && (
                  <select
                    value={item.color_target_id ?? ''}
                    onChange={(e) => handleChange(item.id, 'color_target_id', e.target.value)}
                    className="flex-1 px-2 py-1 bg-zinc-700 text-white rounded"
                  >
                    {colors.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.color}
                      </option>
                    ))}
                  </select>
                )}
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

export default TranslationAdmin;

