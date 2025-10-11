import { AlertCircle, ArrowLeft, Link2, Server } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import {
  fetchSupplierApiConfigs,
  SupplierApiConfigApi,
  SupplierApiConfigField,
  SupplierApiConfigSupplier,
} from '../api';

interface SupplierApiAdminProps {
  isVisible: boolean;
  onClose: () => void;
}

const PRICE_FIELDS = new Set(['price', 'selling_price', 'purchase_price', 'recommended_price']);
const QUANTITY_FIELDS = new Set(['quantity', 'stock']);

type FieldCategory = 'price' | 'quantity' | 'other';

function getFieldCategory(field: SupplierApiConfigField): FieldCategory {
  const key = (field.target_field || '').toLowerCase();
  if (PRICE_FIELDS.has(key)) return 'price';
  if (QUANTITY_FIELDS.has(key)) return 'quantity';
  return 'other';
}

function useCategorisedFields(fields: SupplierApiConfigField[] | undefined) {
  return useMemo(() => {
    if (!fields) return [] as Array<SupplierApiConfigField & { category: FieldCategory }>;
    return fields
      .map((field) => ({ ...field, category: getFieldCategory(field) }))
      .sort((a, b) => (a.target_field || '').localeCompare(b.target_field || ''));
  }, [fields]);
}

function FieldCategoryBadge({ category }: { category: FieldCategory }) {
  const config = {
    price: {
      label: 'Prix',
      className: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/40',
    },
    quantity: {
      label: 'Quantité',
      className: 'bg-sky-500/10 text-sky-300 border-sky-500/40',
    },
    other: {
      label: 'Autre',
      className: 'bg-zinc-700/40 text-zinc-200 border-zinc-500/40',
    },
  } satisfies Record<FieldCategory, { label: string; className: string }>;

  const { label, className } = config[category];
  return (
    <span
      className={`text-xs font-semibold uppercase tracking-wide px-2 py-1 rounded border ${className}`}
    >
      {label}
    </span>
  );
}

function SupplierApiTables({ api }: { api: SupplierApiConfigApi }) {
  const fields = useCategorisedFields(api.mapping?.fields);

  return (
    <div className="bg-black/30 border border-zinc-800/60 rounded-xl">
      <div className="px-5 py-4 flex flex-wrap items-center gap-4 justify-between border-b border-zinc-800/60">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-[#B8860B]/10 text-[#B8860B]">
            <Server className="w-5 h-5" />
          </div>
          <div className="space-y-1">
            <div className="text-sm text-zinc-400 uppercase tracking-wide">Base URL</div>
            <div className="text-lg font-semibold text-white break-all">{api.base_url}</div>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-wide text-zinc-300">
          {api.auth_type && (
            <span className="px-2 py-1 rounded-full border border-zinc-700 bg-zinc-900/70">
              Auth : {api.auth_type}
            </span>
          )}
          {typeof api.rate_limit_per_min === 'number' && (
            <span className="px-2 py-1 rounded-full border border-zinc-700 bg-zinc-900/70">
              Limite : {api.rate_limit_per_min}/min
            </span>
          )}
        </div>
      </div>

      <div className="p-5 space-y-6">
        <section>
          <h4 className="text-sm text-zinc-400 uppercase tracking-wide mb-3">Endpoints</h4>
          {api.endpoints.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm text-left text-zinc-200 border border-zinc-800/60 rounded-lg overflow-hidden">
                <thead className="bg-zinc-900/80 text-xs uppercase tracking-wide text-zinc-400">
                  <tr>
                    <th className="px-4 py-2 font-medium">Nom</th>
                    <th className="px-4 py-2 font-medium">Méthode</th>
                    <th className="px-4 py-2 font-medium">Chemin</th>
                    <th className="px-4 py-2 font-medium">Chemin items</th>
                  </tr>
                </thead>
                <tbody>
                  {api.endpoints.map((endpoint) => (
                    <tr
                      key={endpoint.id}
                      className="border-t border-zinc-800/60 even:bg-black/20"
                    >
                      <td className="px-4 py-2 font-medium text-white">{endpoint.name || '—'}</td>
                      <td className="px-4 py-2">
                        <span className="inline-flex items-center gap-2">
                          <span className="px-2 py-1 rounded bg-[#B8860B]/10 text-[#B8860B] uppercase font-semibold">
                            {endpoint.method}
                          </span>
                        </span>
                      </td>
                      <td className="px-4 py-2 font-mono text-sm break-all text-zinc-100">
                        {endpoint.path}
                      </td>
                      <td className="px-4 py-2 text-zinc-300">
                        {endpoint.items_path ? (
                          <div className="flex items-center gap-2">
                            <Link2 className="w-4 h-4" />
                            <span className="break-all">{endpoint.items_path}</span>
                          </div>
                        ) : (
                          <span className="italic text-zinc-500">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-zinc-500 italic">Aucun endpoint configuré.</p>
          )}
        </section>

        <section>
          <h4 className="text-sm text-zinc-400 uppercase tracking-wide mb-3">
            Mapping des champs
          </h4>
          {fields.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm text-left text-zinc-200 border border-zinc-800/60 rounded-lg overflow-hidden">
                <thead className="bg-zinc-900/80 text-xs uppercase tracking-wide text-zinc-400">
                  <tr>
                    <th className="px-4 py-2 font-medium">Champ cible</th>
                    <th className="px-4 py-2 font-medium">Source</th>
                    <th className="px-4 py-2 font-medium">Type</th>
                  </tr>
                </thead>
                <tbody>
                  {fields.map((field) => (
                    <tr
                      key={field.id}
                      className="border-t border-zinc-800/60 even:bg-black/20"
                    >
                      <td className="px-4 py-2 font-medium text-white">
                        {field.target_field}
                      </td>
                      <td className="px-4 py-2 font-mono text-sm text-zinc-100">
                        {field.source_path || '—'}
                      </td>
                      <td className="px-4 py-2">
                        <FieldCategoryBadge category={field.category} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-zinc-500 italic">
              Aucun mapping actif pour cette API.
            </p>
          )}
        </section>
      </div>
    </div>
  );
}

function SupplierApiAdmin({ isVisible, onClose }: SupplierApiAdminProps) {
  const [configs, setConfigs] = useState<SupplierApiConfigSupplier[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isVisible) return;
    setLoading(true);
    setError(null);
    fetchSupplierApiConfigs()
      .then((data) => setConfigs(Array.isArray(data) ? data : []))
      .catch((err) => {
        const message = err instanceof Error ? err.message : 'Impossible de récupérer la configuration API.';
        setError(message);
      })
      .finally(() => setLoading(false));
  }, [isVisible]);

  if (!isVisible) {
    return null;
  }

  return (
    <div className="mt-8 space-y-6">
      <div className="flex items-center gap-3">
        <button
          onClick={onClose}
          className="flex items-center gap-2 px-3 py-2 bg-zinc-800 rounded hover:bg-zinc-700 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Retour</span>
        </button>
        <h2 className="text-xl font-semibold">Gestion des API fournisseurs</h2>
      </div>

      {loading && <p className="text-sm text-zinc-400">Chargement des configurations…</p>}
      {error && (
        <div className="flex items-center gap-2 text-sm text-red-300 bg-red-500/10 border border-red-500/30 px-4 py-3 rounded-lg">
          <AlertCircle className="w-5 h-5" />
          <span>{error}</span>
        </div>
      )}

      {!loading && !error && configs.length === 0 && (
        <p className="text-sm text-zinc-500 italic">
          Aucun fournisseur ne possède de configuration API pour le moment.
        </p>
      )}

      <div className="space-y-10">
        {configs.map((supplier) => (
          <div key={supplier.id} className="space-y-5">
            <div className="flex items-center gap-3 border-b border-zinc-800/60 pb-3">
              <div className="p-2 rounded-lg bg-[#B8860B]/10 text-[#B8860B]">
                <Server className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs uppercase text-zinc-500 tracking-wide">Fournisseur</p>
                <h3 className="text-lg font-semibold text-white">{supplier.name}</h3>
              </div>
            </div>
            {supplier.apis.length > 0 ? (
              <div className="space-y-6">
                {supplier.apis.map((api) => (
                  <SupplierApiTables key={api.id} api={api} />
                ))}
              </div>
            ) : (
              <p className="text-sm text-zinc-500 italic">
                Aucun API configuré pour ce fournisseur.
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default SupplierApiAdmin;
