import { RefreshCcw, Loader2, ShieldCheck, AlertCircle, Trash2 } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import {
  fetchSupplierApiData,
  fetchSuppliers,
  SupplierApiMappingSummary,
  SupplierApiRow,
  SupplierApiSyncResponse
} from '../api';
import { useNotification } from './NotificationProvider';

interface Supplier {
  id: number;
  name: string;
}

interface ApiRowWithSupplier extends SupplierApiRow {
  supplier_id: number;
  supplier: string;
}

function describeMapping(mapping: SupplierApiMappingSummary | null | undefined): string {
  if (!mapping) {
    return 'Non renseigné';
  }
  const count = mapping.field_count ?? 0;
  const plural = count > 1 ? 'champs' : 'champ';
  const status = mapping.is_active ? '' : ' (inactif)';
  return `v${mapping.version} • ${count} ${plural}${status}`;
}

function mapResponseToRows(response: SupplierApiSyncResponse, fallbackName: string): ApiRowWithSupplier[] {
  const rows = response.items ?? response.rows ?? [];
  return rows.map((row) => ({
    supplier_id: response.supplier_id,
    supplier: response.supplier || fallbackName,
    description: row.description ?? row.model ?? '',
    quantity: row.quantity ?? 0,
    selling_price: row.selling_price ?? 0,
    ean: row.ean ?? null,
    part_number: row.part_number ?? null,
    supplier_sku: row.supplier_sku ?? null,
  }));
}

function SupplierApiSyncPanel() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loadingSupplier, setLoadingSupplier] = useState<number | null>(null);
  const [rows, setRows] = useState<ApiRowWithSupplier[]>([]);
  const [mappingsBySupplier, setMappingsBySupplier] = useState<Record<number, SupplierApiMappingSummary | null>>({});
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

      setMappingsBySupplier((prev) => ({
        ...prev,
        [supplierId]: response.mapping ?? null,
      }));

      const count =
        response.temporary_import_count ??
        response.items?.length ??
        response.rows?.length ??
        mapped.length;
      const mappingInfo = describeMapping(response.mapping ?? null);
      notify(
        `Synchronisation réussie pour ${fallbackName} (${count} articles) • Mapping ${mappingInfo}`,
        'success'
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Impossible de contacter l'API fournisseur";
      setError(message);
      notify(message, 'error');
    } finally {
      setLoadingSupplier(null);
    }
  };

  const hasRows = rows.length > 0;
  const groupedRows = useMemo(() => {
    const map = new Map<
      number,
      { supplier: string; items: ApiRowWithSupplier[]; mapping: SupplierApiMappingSummary | null }
    >();

    rows.forEach((row) => {
      const existing = map.get(row.supplier_id);
      if (existing) {
        existing.items.push(row);
      } else {
        map.set(row.supplier_id, {
          supplier: row.supplier,
          items: [row],
          mapping: mappingsBySupplier[row.supplier_id] ?? null,
        });
      }
    });

    return Array.from(map.entries()).map(([supplierId, value]) => ({
      supplier_id: supplierId,
      supplier: value.supplier,
      items: value.items,
      mapping: value.mapping ?? mappingsBySupplier[supplierId] ?? null,
    }));
  }, [rows, mappingsBySupplier]);

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
              onClick={() => {
                setRows([]);
                setMappingsBySupplier({});
              }}
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
              className={`btn px-4 py-2 flex items-center gap-2 ${
                loadingSupplier === supplier.id ? 'opacity-70 cursor-wait' : ''
              }`}
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

        <div className="mt-8">
          {hasRows ? (
            <div className="space-y-6">
              {groupedRows.map(({ supplier_id, supplier, items, mapping }) => (
                <div
                  key={supplier_id}
                  className="border border-zinc-800/60 rounded-xl bg-black/30 divide-y divide-zinc-800/60"
                >
                  <div className="px-5 py-4 flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-sm text-zinc-400 uppercase tracking-wide">Fournisseur</p>
                      <h3 className="text-lg font-semibold text-zinc-100">{supplier}</h3>
                    </div>
                    <div className="text-sm text-zinc-400 text-right space-y-1">
                      <p>
                        {items.length} article{items.length > 1 ? 's' : ''}
                      </p>
                      <p>
                        Mapping :{' '}
                        <span className="font-medium text-zinc-200">
                          {describeMapping(mapping)}
                        </span>
                      </p>
                    </div>
                  </div>
                  <div className="p-5 space-y-4">
                    {items.map((row, index) => (
                      <div
                        key={`${
                          row.supplier_id
                        }-${row.ean ?? row.part_number ?? row.supplier_sku ?? index}`}
                        className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between bg-black/20 rounded-lg p-4"
                      >
                        <div className="space-y-1">
                          <p className="text-base font-medium text-zinc-100">
                            {row.description || '—'}
                          </p>
                          <div className="text-sm text-zinc-400 flex flex-wrap gap-3">
                            <span>EAN : {row.ean || '—'}</span>
                            <span>Part Number : {row.part_number || '—'}</span>
                            <span>SKU fournisseur : {row.supplier_sku || '—'}</span>
                          </div>
                        </div>
                        <div className="text-sm text-zinc-300 text-right space-y-1 min-w-[120px]">
                          <p className="text-lg font-semibold text-white">
                            {(row.selling_price ?? 0).toLocaleString('fr-FR', {
                              minimumFractionDigits: 2,
                              maximumFractionDigits: 2,
                            })}{' '}
                            €
                          </p>
                          <p>Quantité : {row.quantity ?? 0}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="px-4 py-6 text-center text-sm text-zinc-400 border border-dashed border-zinc-800/60 rounded-xl">
              Aucune donnée temporaire. Lancez une synchronisation pour remplir la table.
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

export default SupplierApiSyncPanel;
