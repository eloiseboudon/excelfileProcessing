import { Plus, Save, Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import {
  createProduct,
  deleteProduct,
  fetchBrands,
  fetchColors,
  fetchDeviceTypes,
  fetchMemoryOptions,
  fetchProducts,
  updateProduct
} from '../api';
import { useNotification } from './NotificationProvider';

interface ProductItem {
  id: number;
  ean: string | null;
  model: string;
  description: string;
  brand_id: number | null;
  memory_id: number | null;
  color_id: number | null;
  type_id: number | null;
}

function ProductAdmin() {
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [brands, setBrands] = useState<any[]>([]);
  const [colors, setColors] = useState<any[]>([]);
  const [memories, setMemories] = useState<any[]>([]);
  const [types, setTypes] = useState<any[]>([]);
  const notify = useNotification();

  useEffect(() => {
    load();
    Promise.all([
      fetchBrands(),
      fetchColors(),
      fetchMemoryOptions(),
      fetchDeviceTypes(),
    ])
      .then(([b, c, m, t]) => {
        setBrands(b as any[]);
        setColors(c as any[]);
        setMemories(m as any[]);
        setTypes(t as any[]);
      })
      .catch(() => {
        setBrands([]);
        setColors([]);
        setMemories([]);
        setTypes([]);
      });
  }, []);

  const load = async () => {
    try {
      const res = await fetchProducts();
      setProducts(
        (res as any[]).map((p) => ({
          id: p.id,
          ean: p.ean ?? '',
          model: p.model ?? '',
          description: p.description ?? '',
          brand_id: p.brand_id ?? null,
          memory_id: p.memory_id ?? null,
          color_id: p.color_id ?? null,
          type_id: p.type_id ?? null,
        }))
      );
    } catch {
      setProducts([]);
    }
  };

  const handleChange = (
    id: number,
    field: keyof ProductItem,
    value: string | number | null
  ) => {
    setProducts((prev) =>
      prev.map((p) => (p.id === id ? { ...p, [field]: value } : p))
    );
  };

  const handleSave = async (id: number) => {
    const item = products.find((p) => p.id === id);
    if (!item) return;
    const payload = {
      ean: item.ean,
      model: item.model,
      description: item.description,
      brand_id: item.brand_id,
      memory_id: item.memory_id,
      color_id: item.color_id,
      type_id: item.type_id,
    };
    try {
      if (id < 0) {
        await createProduct(payload);
        notify('Produit créé', 'success');
      } else {
        await updateProduct(id, payload);
        notify('Produit mis à jour', 'success');
      }
      await load();
    } catch {
      /* empty */
    }
  };

  const handleDelete = async (id: number) => {
    try {
      if (id < 0) {
        setProducts((prev) => prev.filter((p) => p.id !== id));
      } else {
        await deleteProduct(id);
        notify('Produit supprimé', 'success');
        await load();
      }
    } catch {
      /* empty */
    }
  };

  const handleAdd = () => {
    setProducts((prev) => [
      ...prev,
      {
        id: Date.now() * -1,
        ean: '',
        model: '',
        description: '',
        brand_id: null,
        memory_id: null,
        color_id: null,
        type_id: null,
      },
    ]);
  };

  return (
    <div className="mt-4 space-y-2">
      <div className="flex justify-end mb-4">
        <button
          onClick={handleAdd}
          className="flex items-center space-x-2 px-3 py-2 bg-green-600 text-white rounded hover:bg-green-700"
        >
          <Plus className="w-4 h-4" />
          <span>Ajouter</span>
        </button>
      </div>
      <div className="space-y-2">
        {products.map((p) => (
          <div key={p.id} className="flex items-center space-x-2 bg-zinc-800 p-2 rounded">
            {/* <span className="w-10 text-zinc-400">{p.id > 0 ? p.id : '-'}</span> */}
            {/* <input
              value={p.ean ?? ''}
              onChange={(e) => handleChange(p.id, 'ean', e.target.value)}
              placeholder="ean"
              className="w-24 px-2 py-1 bg-zinc-700 rounded"
            /> */}

            <select
              value={p.brand_id ?? ''}
              onChange={(e) =>
                handleChange(
                  p.id,
                  'brand_id',
                  e.target.value === '' ? null : Number(e.target.value)
                )
              }

              className="px-2 py-1 bg-zinc-700 rounded"
            >
              <option value="">null</option>
              {brands.map((b) => (
                <option key={b.id} value={b.id}>{b.brand}</option>
              ))}
            </select>
            <input
              value={p.model}
              onChange={(e) => handleChange(p.id, 'model', e.target.value)}
              placeholder="model"
              className="flex-1 px-2 py-1 bg-zinc-700 rounded"
            />
            <input
              value={p.description}
              onChange={(e) => handleChange(p.id, 'description', e.target.value)}
              placeholder="description"
              className="flex-1 px-2 py-1 bg-zinc-700 rounded"
            />

            <select
              value={p.memory_id ?? ''}
              onChange={(e) =>
                handleChange(
                  p.id,
                  'memory_id',
                  e.target.value === '' ? null : Number(e.target.value)
                )
              }

              className="px-2 py-1 bg-zinc-700 rounded"
            >
              <option value="">null</option>
              {memories.map((m) => (
                <option key={m.id} value={m.id}>{m.memory}</option>
              ))}
            </select>
            <select
              value={p.color_id ?? ''}
              onChange={(e) =>
                handleChange(
                  p.id,
                  'color_id',
                  e.target.value === '' ? null : Number(e.target.value)
                )
              }

              className="px-2 py-1 bg-zinc-700 rounded"
            >
              <option value="">null</option>
              {colors.map((c) => (
                <option key={c.id} value={c.id}>{c.color}</option>
              ))}
            </select>
            <select
              value={p.type_id ?? ''}
              onChange={(e) =>
                handleChange(
                  p.id,
                  'type_id',
                  e.target.value === '' ? null : Number(e.target.value)
                )
              }

              className="px-2 py-1 bg-zinc-700 rounded"
            >
              <option value="">null</option>
              {types.map((t) => (
                <option key={t.id} value={t.id}>{t.type}</option>
              ))}
            </select>
            <button onClick={() => handleSave(p.id)} className="p-2 bg-green-600 text-white rounded hover:bg-green-700">
              <Save className="w-4 h-4" />
            </button>
            <button onClick={() => handleDelete(p.id)} className="p-2 bg-red-600 text-white rounded hover:bg-red-700">
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ProductAdmin;
