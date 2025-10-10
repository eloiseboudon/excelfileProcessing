import { RefreshCcw, Loader2, ShieldCheck, AlertCircle, Trash2 } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { fetchSupplierApiData, fetchSuppliers, SupplierApiRow, SupplierApiSyncResponse } from '../api';
import { useNotification } from './NotificationProvider';

interface Supplier {
  id: number;
  name: string;
}

interface ApiRowWithSupplier extends SupplierApiRow {
  supplier_id: number;
  supplier: string;
}

function mapResponseToRows(response: SupplierApiSyncResponse, fallbackName: string): ApiRowWithSupplier[] {
  return (response.rows || []).map((row) => ({
    supplier_id: response.supplier_id,
    supplier: response.supplier || fallbackName,
    description: row.description ?? '',
    quantity: row.quantity ?? 0,
    selling_price: row.selling_price ?? 0,
    ean: row.ean ?? null,
    part_number: row.part_number ?? null,
  }));
}

function SupplierApiSyncPanel() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loadingSupplier, setLoadingSupplier] = useState<number | null>(null);
  const [rows, setRows] = useState<ApiRowWithSupplier[]>([]);
  const [error, setError] = useState<string | null>(null);
  const notify = useNotification();

  useEffect(() => {
    fetchSuppliers()
      .then((data) => setSuppliers(Array.isArray(data) ? data : []))
      .catch(() => setSuppliers([]));
  }, []);

  const supplierMap = useMemo(() => {
    const entries = suppliers.map((s) => [s.id, s.name] as const);
    return Object.fromEntries(entries);
  }, [suppliers]);

  const handleFetch = async (supplierId: number) => {
    setLoadingSupplier(supplierId);
    setError(null);
    try {
      const response = await fetchSupplierApiData(supplierId);
      const fallbackName = supplierMap[supplierId] || response.supplier || 'Fournisseur';
      const mapped = mapResponseToRows(response, fallbackName);

      setRows((prev) => {
        const withoutSupplier = prev.filter((row) => row.supplier_id !== supplierId);
        return [...withoutSupplier, ...mapped];
      });

      notify(`Synchronisation réussie pour ${fallbackName}`, 'success');
    } catch (err) {
      const message = err instanceof Error ? err.message : "Impossible de contacter l'API fournisseur";
      setError(message);
      notify(message, 'error');
    } finally {
      setLoadingSupplier(null);
    }
  };

  const hasRows = rows.length > 0;

  return (
    <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="card">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
          <div>
            <h2 className="text-2xl font-semibold flex items-center gap-2">
              <ShieldCheck className="w-6 h-6 text-[#B8860B]" />
              Synchronisation des fournisseurs
            </h2>
            <p className="text-sm text-zinc-400 mt-1">
              Récupérez les prix et quantités en temps réel depuis les APIs fournisseurs pour alimenter la table temporaire.
            </p>
          </div>
          {hasRows && (
            <button
              onClick={() => setRows([])}
              className="btn btn-secondary flex items-center gap-2"
            >
              <Trash2 className="w-4 h-4" />
              Vider la table
            </button>
          )}
        </div>

        <div className="flex flex-wrap gap-3">
          {suppliers.map((supplier) => (
            <button
              key={supplier.id}
              onClick={() => handleFetch(supplier.id)}
              disabled={loadingSupplier === supplier.id}
              className={`btn px-4 py-2 flex items-center gap-2 ${loadingSupplier === supplier.id ? 'opacity-70 cursor-wait' : ''}`}
            >
              {loadingSupplier === supplier.id ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCcw className="w-4 h-4" />
              )}
              <span className="text-left">
                Lancer synchronisation donnée {supplier.name}
              </span>
            </button>
          ))}
        </div>

        {error && (
          <div className="mt-6 p-4 rounded-lg border border-red-500/30 bg-red-500/10 text-sm text-red-300 flex items-center gap-2">
            <AlertCircle className="w-5 h-5" />
            <span>{error}</span>
          </div>
        )}

        <div className="mt-8 overflow-x-auto">
          <table className="min-w-full text-left">
            <thead className="bg-black/30 border border-zinc-800/60">
              <tr>
                <th className="px-4 py-3 text-sm font-semibold text-zinc-300">Fournisseur</th>
                <th className="px-4 py-3 text-sm font-semibold text-zinc-300">Description</th>
                <th className="px-4 py-3 text-sm font-semibold text-zinc-300">EAN</th>
                <th className="px-4 py-3 text-sm font-semibold text-zinc-300">Part Number</th>
                <th className="px-4 py-3 text-sm font-semibold text-zinc-300 text-right">Quantité</th>
                <th className="px-4 py-3 text-sm font-semibold text-zinc-300 text-right">Prix</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60">
              {hasRows ? (
                rows.map((row, index) => (
                  <tr key={`${row.supplier_id}-${row.ean ?? row.part_number ?? index}`} className="hover:bg-white/5">
                    <td className="px-4 py-3 text-sm text-zinc-200 whitespace-nowrap">{row.supplier}</td>
                    <td className="px-4 py-3 text-sm text-zinc-300 max-w-xs">
                      <span className="line-clamp-2">{row.description || '—'}</span>
                    </td>
                    <td className="px-4 py-3 text-sm text-zinc-300 whitespace-nowrap">{row.ean || '—'}</td>
                    <td className="px-4 py-3 text-sm text-zinc-300 whitespace-nowrap">{row.part_number || '—'}</td>
                    <td className="px-4 py-3 text-sm text-zinc-100 text-right">{row.quantity ?? 0}</td>
                    <td className="px-4 py-3 text-sm text-zinc-100 text-right">{row.selling_price.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-sm text-zinc-400">
                    Aucune donnée temporaire. Lancez une synchronisation pour remplir la table.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

export default SupplierApiSyncPanel;
