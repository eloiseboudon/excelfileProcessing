import React, { useEffect, useState } from 'react';
import { X, Save } from 'lucide-react';
import { fetchReferenceTable, updateReferenceItem } from '../api';

interface ReferenceAdminProps {
  isVisible: boolean;
  onClose: () => void;
}

const TABLES = [
  { key: 'brands', label: 'Marques' },
  { key: 'colors', label: 'Couleurs' },
  { key: 'memory_options', label: 'Options mémoire' },
  { key: 'device_types', label: "Types d'appareil" },
  { key: 'exclusions', label: 'Exclusions' },
  { key: 'suppliers', label: 'Fournisseurs' },
];

function ReferenceAdmin({ isVisible, onClose }: ReferenceAdminProps) {
  const [table, setTable] = useState<string>('brands');
  const [data, setData] = useState<any[]>([]);

  useEffect(() => {
    if (isVisible) {
      load(table);
    }
  }, [isVisible, table]);

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
      await updateReferenceItem(table, id, payload);
    } catch {
      /* empty */
    }
  };

  if (!isVisible) return null;

  const fields = data.length > 0 ? Object.keys(data[0]).filter((k) => k !== 'id') : [];

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-zinc-900 rounded-2xl border border-[#B8860B]/30 max-w-3xl w-full max-h-[90vh] overflow-hidden">
        <div className="bg-[#B8860B] p-6 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-black">Tables de référence</h2>
          <button onClick={onClose} className="p-2 hover:bg-black/10 rounded-lg">
            <X className="w-6 h-6 text-black" />
          </button>
        </div>
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)] space-y-4">
          <select
            value={table}
            onChange={(e) => setTable(e.target.value)}
            className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white mb-4"
          >
            {TABLES.map((t) => (
              <option key={t.key} value={t.key}>
                {t.label}
              </option>
            ))}
          </select>
          {data.map((item) => (
            <div key={item.id} className="flex items-center space-x-2 bg-zinc-800 p-2 rounded">
              <span className="w-10 text-zinc-400">{item.id}</span>
              {fields.map((f) => (
                <input
                  key={f}
                  value={item[f] ?? ''}
                  onChange={(e) => handleChange(item.id, f, e.target.value)}
                  className="flex-1 px-2 py-1 bg-zinc-700 text-white rounded"
                />
              ))}
              <button
                onClick={() => handleSave(item.id)}
                className="p-2 bg-green-600 text-white rounded hover:bg-green-700"
              >
                <Save className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default ReferenceAdmin;

