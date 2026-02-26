import { useCallback, useState } from 'react';
import { ArrowLeft, Save, Trash2, Plus } from 'lucide-react';
import {
  fetchReferenceTable,
  createReferenceItem,
  deleteReferenceItem,
  updateReferenceItem,
  fetchColors
} from '../api';
import { useAdminCrud } from '../hooks/useAdminCrud';

interface TranslationAdminProps {
  onClose: () => void;
  isVisible: boolean;
}

const TABLES = [
  { key: 'color_translations', label: 'Cohérence des couleurs' },
];

function TranslationAdmin({ isVisible }: TranslationAdminProps) {
  const [table, setTable] = useState<string | null>(null);
  const [colors, setColors] = useState<Record<string, unknown>[]>([]);

  const fetchFn = useCallback(async (): Promise<Record<string, unknown>[]> => {
    if (!table) return [];
    if (table === 'color_translations') {
      const [translations, cols] = await Promise.all([
        fetchReferenceTable(table),
        fetchColors(),
      ]);
      setColors(cols as Record<string, unknown>[]);
      return (translations as Record<string, unknown>[]).map((item) => {
        const c = (cols as Record<string, unknown>[]).find((cc) => cc.color === item.color_target);
        return { ...item, color_target_id: c ? c.id : '' };
      });
    }
    return fetchReferenceTable(table).then((r) => r as Record<string, unknown>[]);
  }, [table]);

  const onFieldChange = useCallback(
    (item: Record<string, unknown>, field: string, value: string) => {
      if (table === 'color_translations' && field === 'color_target_id') {
        const col = colors.find((c) => String(c.id) === value);
        if (col) return { ...item, color_target: col.color };
      }
      return item;
    },
    [table, colors]
  );

  const { data, handleChange, handleSave, handleDelete, handleAdd } = useAdminCrud({
    fetchFn,
    createFn: (payload) => createReferenceItem(table!, payload),
    updateFn: (id, payload) => updateReferenceItem(table!, id, payload),
    deleteFn: (id) => deleteReferenceItem(table!, id),
    onFieldChange,
    enabled: isVisible && !!table,
  });

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
                  <span className="w-10 text-[var(--color-text-muted)] text-sm">{(item.id as number) > 0 ? item.id as number : '-'}</span>
                  {displayedFields.map((f) => (
                    <input
                      key={f}
                      value={item[f] as string ?? ''}
                      placeholder={f}
                      onChange={(e) => handleChange(item.id as number, f, e.target.value)}
                      className="flex-1 px-2 py-1 bg-[var(--color-bg-input)] text-[var(--color-text-primary)] rounded placeholder:italic text-sm"
                    />
                  ))}
                  {table === 'color_translations' && (
                    <select
                      value={item.color_target_id as string ?? ''}
                      onChange={(e) => handleChange(item.id as number, 'color_target_id', e.target.value)}
                      className="flex-1 px-2 py-1 bg-[var(--color-bg-input)] text-[var(--color-text-primary)] rounded text-sm"
                    >
                      {colors.map((c) => (
                        <option key={c.id as number} value={c.id as number}>
                          {c.color as string}
                        </option>
                      ))}
                    </select>
                  )}
                  <div className="flex items-center gap-1">
                    <button onClick={() => handleSave(item.id as number)} className="btn btn-primary p-1.5">
                      <Save className="w-4 h-4" />
                    </button>
                    <button onClick={() => handleDelete(item.id as number)} className="btn btn-secondary p-1.5 text-red-500">
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
