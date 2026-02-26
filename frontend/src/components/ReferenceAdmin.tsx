import { ArrowLeft, Plus, Save, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import {
  createReferenceItem,
  deleteReferenceItem,
  fetchReferenceTable,
  fetchSuppliers,
  updateReferenceItem
} from '../api';
import { useAdminCrud } from '../hooks/useAdminCrud';

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

function ReferenceAdmin({ isVisible }: ReferenceAdminProps) {
  const [table, setTable] = useState<string | null>(null);
  const [suppliers, setSuppliers] = useState<Record<string, unknown>[]>([]);

  const fetchFn = useCallback(
    () =>
      table
        ? fetchReferenceTable(table).then((r) => r as Record<string, unknown>[])
        : Promise.resolve([]),
    [table]
  );

  const { data, handleChange, handleSave, handleDelete, handleAdd } = useAdminCrud({
    fetchFn,
    createFn: (payload) => createReferenceItem(table!, payload),
    updateFn: (id, payload) => updateReferenceItem(table!, id, payload),
    deleteFn: (id) => deleteReferenceItem(table!, id),
    enabled: isVisible && !!table,
  });

  useEffect(() => {
    if (table === 'format_imports') {
      fetchSuppliers()
        .then((s) => setSuppliers(s as Record<string, unknown>[]))
        .catch(() => setSuppliers([]));
    }
  }, [table]);

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
                        onChange={(e) => handleChange(item.id as number, f, e.target.value)}
                        className="flex-1 px-2 py-1 bg-[var(--color-bg-input)] text-[var(--color-text-primary)] rounded text-sm"
                      >
                        <option value="">--</option>
                        {suppliers.map((s) => (
                          <option key={s.id as number} value={s.id as number}>{s.name as string}</option>
                        ))}
                      </select>
                    ) : (
                      <input
                        key={f}
                        value={item[f] as string ?? ''}
                        placeholder={f}
                        onChange={(e) => handleChange(item.id as number, f, e.target.value)}
                        className="flex-1 px-2 py-1 bg-[var(--color-bg-input)] text-[var(--color-text-primary)] rounded placeholder:italic text-sm"
                      />
                    )
                  ))}
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

export default ReferenceAdmin;
