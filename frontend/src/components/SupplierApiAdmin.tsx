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

function groupFields(fields: SupplierApiConfigField[] | undefined, keys: Set<string>) {
  if (!fields) return [];
  return fields.filter((field) => keys.has((field.target_field || '').toLowerCase()));
}

function SupplierApiCard({ api }: { api: SupplierApiConfigApi }) {
  const priceFields = useMemo(
    () => groupFields(api.mapping?.fields, PRICE_FIELDS),
    [api.mapping?.fields],
  );
  const quantityFields = useMemo(
    () => groupFields(api.mapping?.fields, QUANTITY_FIELDS),
    [api.mapping?.fields],
  );

  return (
    <div className="border border-zinc-800/60 rounded-xl bg-black/30 divide-y divide-zinc-800/60">
      <div className="px-5 py-4 flex flex-wrap items-center gap-3 justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-[#B8860B]/10 text-[#B8860B]">
            <Server className="w-5 h-5" />
          </div>
          <div>
            <p className="text-sm text-zinc-400 uppercase tracking-wide">Base URL</p>
            <p className="text-lg font-semibold text-white break-all">{api.base_url}</p>
          </div>
        </div>
        {api.auth_type && (
          <span className="text-xs uppercase tracking-wide text-zinc-400 bg-zinc-900/70 border border-zinc-800 px-2 py-1 rounded-full">
            Auth : {api.auth_type}
          </span>
        )}
      </div>

      <div className="p-5 space-y-5">
        <div>
          <h4 className="text-sm text-zinc-400 uppercase tracking-wide mb-2">Endpoints</h4>
          {api.endpoints.length > 0 ? (
            <div className="space-y-2">
              {api.endpoints.map((endpoint) => (
                <div
                  key={endpoint.id}
                  className="bg-black/20 border border-zinc-800/60 rounded-lg px-4 py-3 flex flex-wrap gap-3 justify-between"
                >
                  <div className="flex items-center gap-2 text-sm text-zinc-200">
                    <span className="px-2 py-1 rounded bg-[#B8860B]/10 text-[#B8860B] uppercase font-semibold">
                      {endpoint.method}
                    </span>
                    <span className="font-medium break-all">{endpoint.path}</span>
                  </div>
                  {endpoint.items_path && (
                    <div className="flex items-center gap-2 text-xs text-zinc-400">
                      <Link2 className="w-4 h-4" />
                      <span>Chemin items : {endpoint.items_path}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-zinc-500 italic">Aucun endpoint configuré.</p>
          )}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="bg-black/20 border border-zinc-800/60 rounded-lg p-4">
            <h5 className="text-sm font-semibold text-white mb-3">Champs prix</h5>
            {priceFields.length > 0 ? (
              <ul className="space-y-2 text-sm text-zinc-300">
                {priceFields.map((field) => (
                  <li key={field.id} className="flex flex-col">
                    <span className="text-xs uppercase tracking-wide text-zinc-500">
                      {field.target_field}
                    </span>
                    <span className="font-medium">
                      {field.source_path || '—'}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-zinc-500 italic">Aucun mapping de prix configuré.</p>
            )}
          </div>
          <div className="bg-black/20 border border-zinc-800/60 rounded-lg p-4">
            <h5 className="text-sm font-semibold text-white mb-3">Champs quantité</h5>
            {quantityFields.length > 0 ? (
              <ul className="space-y-2 text-sm text-zinc-300">
                {quantityFields.map((field) => (
                  <li key={field.id} className="flex flex-col">
                    <span className="text-xs uppercase tracking-wide text-zinc-500">
                      {field.target_field}
                    </span>
                    <span className="font-medium">
                      {field.source_path || '—'}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-zinc-500 italic">Aucun mapping de quantité configuré.</p>
            )}
          </div>
        </div>
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

      <div className="space-y-6">
        {configs.map((supplier) => (
          <div key={supplier.id} className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-[#B8860B]/10 text-[#B8860B]">
                <Server className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs uppercase text-zinc-500 tracking-wide">Fournisseur</p>
                <h3 className="text-lg font-semibold text-white">{supplier.name}</h3>
              </div>
            </div>
            {supplier.apis.length > 0 ? (
              <div className="space-y-4">
                {supplier.apis.map((api) => (
                  <SupplierApiCard key={api.id} api={api} />
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
