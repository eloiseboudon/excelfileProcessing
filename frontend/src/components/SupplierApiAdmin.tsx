import { AlertCircle, ArrowLeft, Plus, Save, Server, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import {
  createSupplierApi,
  createSupplierApiEndpoint,
  createSupplierApiField,
  createSupplierApiMapping,
  deleteSupplierApi,
  deleteSupplierApiEndpoint,
  deleteSupplierApiField,
  fetchSupplierApiConfigs,
  SupplierApiConfigApi,
  SupplierApiConfigEndpoint,
  SupplierApiConfigField,
  SupplierApiConfigSupplier,
  updateSupplierApi,
  updateSupplierApiEndpoint,
  updateSupplierApiField,
} from '../api';
import { useNotification } from './NotificationProvider';

interface SupplierApiAdminProps {
  isVisible: boolean;
  onClose: () => void;
}

const PRICE_FIELDS = new Set(['price', 'selling_price', 'purchase_price', 'recommended_price']);
const QUANTITY_FIELDS = new Set(['quantity', 'stock']);
const DEFAULT_MAPPING_TARGET_FIELDS = ['product_id', 'price', 'quantity'] as const;
const DEFAULT_FIELD_ORDER = new Map(
  DEFAULT_MAPPING_TARGET_FIELDS.map((target, index) => [target, index])
);
const HTTP_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'];
const AUTH_TYPE_OPTIONS: Array<{ value: string; label: string }> = [
  { value: 'none', label: 'Aucune' },
  { value: 'api_key', label: 'API Key' },
  { value: 'basic', label: 'Basic' },
  { value: 'oauth2', label: 'OAuth2' },
];
const DEFAULT_LOAD_ERROR = 'Impossible de récupérer la configuration API.';

type FieldCategory = 'price' | 'quantity' | 'other';

type CategorisedField = SupplierApiConfigField & { category: FieldCategory };

let tempFieldIdCounter = -1;

function createPlaceholderField(targetField: string): SupplierApiConfigField {
  return {
    id: tempFieldIdCounter--,
    target_field: targetField,
    source_path: '',
    transform: null,
  };
}

function normalizeMappingFields(
  fields: SupplierApiConfigField[] | undefined
): SupplierApiConfigField[] {
  const normalizedFields = [...(fields ?? [])];
  const seen = new Set(
    normalizedFields
      .map((field) => (field.target_field || '').trim().toLowerCase())
      .filter(Boolean)
  );

  for (const target of DEFAULT_MAPPING_TARGET_FIELDS) {
    if (!seen.has(target)) {
      normalizedFields.push(createPlaceholderField(target));
    }
  }

  normalizedFields.sort((a, b) => {
    const aKey = (a.target_field || '').trim().toLowerCase();
    const bKey = (b.target_field || '').trim().toLowerCase();
    const orderA = DEFAULT_FIELD_ORDER.get(aKey);
    const orderB = DEFAULT_FIELD_ORDER.get(bKey);
    if (orderA !== undefined && orderB !== undefined) {
      return orderA - orderB;
    }
    if (orderA !== undefined) return -1;
    if (orderB !== undefined) return 1;
    return 0;
  });

  return normalizedFields;
}

function withDefaultMappingFields(
  mapping: SupplierApiConfigMapping | null
): SupplierApiConfigMapping | null {
  if (!mapping) return null;
  return {
    ...mapping,
    fields: normalizeMappingFields(mapping.fields),
  };
}

function getFieldCategory(field: SupplierApiConfigField): FieldCategory {
  const key = (field.target_field || '').toLowerCase();
  if (PRICE_FIELDS.has(key)) return 'price';
  if (QUANTITY_FIELDS.has(key)) return 'quantity';
  return 'other';
}

function mapFieldsWithCategory(fields: SupplierApiConfigField[] | undefined): CategorisedField[] {
  if (!fields) {
    return [];
  }
  return normalizeMappingFields(fields).map((field) => ({
    ...field,
    category: getFieldCategory(field),
  }));
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
    <span className={`text-xs font-semibold uppercase tracking-wide px-2 py-1 rounded border ${className}`}>
      {label}
    </span>
  );
}

function SupplierApiAdmin({ isVisible, onClose }: SupplierApiAdminProps) {
  const notify = useNotification();
  const [configs, setConfigs] = useState<SupplierApiConfigSupplier[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const showError = useCallback(
    (err: unknown, fallback: string) => {
      const message = err instanceof Error ? err.message : fallback;
      notify(message, 'error');
      return message;
    },
    [notify]
  );

  const reloadConfigs = useCallback(async () => {
    const data = await fetchSupplierApiConfigs();
    const normalized = (Array.isArray(data) ? data : []).map((supplier) => ({
      ...supplier,
      apis: supplier.apis.map((api) => ({
        ...api,
        mapping: withDefaultMappingFields(api.mapping),
      })),
    }));
    setConfigs(normalized);
  }, []);

  const loadConfigs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await reloadConfigs();
    } catch (err) {
      const message = showError(err, DEFAULT_LOAD_ERROR);
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [reloadConfigs, showError]);

  const refreshConfigs = useCallback(async () => {
    try {
      await reloadConfigs();
      setError(null);
    } catch (err) {
      const message = showError(err, DEFAULT_LOAD_ERROR);
      setError(message);
    }
  }, [reloadConfigs, showError]);

  useEffect(() => {
    if (!isVisible) return;
    void loadConfigs();
  }, [isVisible, loadConfigs]);

  const handleAddApi = (supplierId: number) => {
    const tempId = -Math.floor(Date.now() + Math.random() * 1000);
    const newApi: SupplierApiConfigApi = {
      id: tempId,
      base_url: '',
      auth_type: 'none',
      rate_limit_per_min: null,
      endpoints: [],
      mapping: null,
    };

    setConfigs((prev) =>
      prev.map((supplier) =>
        supplier.id === supplierId
          ? { ...supplier, apis: [...supplier.apis, newApi] }
          : supplier
      )
    );
  };

  const handleApiChange = (
    supplierId: number,
    apiId: number,
    field: 'base_url' | 'auth_type' | 'rate_limit_per_min',
    value: string
  ) => {
    setConfigs((prev) =>
      prev.map((supplier) => {
        if (supplier.id !== supplierId) return supplier;
        return {
          ...supplier,
          apis: supplier.apis.map((api) => {
            if (api.id !== apiId) return api;
            if (field === 'base_url') {
              return { ...api, base_url: value };
            }
            if (field === 'auth_type') {
              return { ...api, auth_type: value };
            }
            if (value === '') {
              return { ...api, rate_limit_per_min: null };
            }
            const numeric = Number(value);
            return {
              ...api,
              rate_limit_per_min: Number.isNaN(numeric) ? api.rate_limit_per_min ?? null : numeric,
            };
          }),
        };
      })
    );
  };

  const handleApiSave = async (supplierId: number, api: SupplierApiConfigApi) => {
    const baseUrl = (api.base_url || '').trim();
    if (!baseUrl) {
      notify('La base URL est obligatoire.', 'error');
      return;
    }

    const payload = {
      base_url: baseUrl,
      auth_type: api.auth_type ?? 'none',
      rate_limit_per_min:
        typeof api.rate_limit_per_min === 'number' ? api.rate_limit_per_min : null,
    };

    try {
      if (api.id < 0) {
        await createSupplierApi(supplierId, payload);
        notify('API créée avec succès.', 'success');
      } else {
        await updateSupplierApi(api.id, payload);
        notify('API mise à jour.', 'success');
      }
      await refreshConfigs();
    } catch (err) {
      showError(err, "Impossible d'enregistrer cette API.");
    }
  };

  const handleApiDelete = async (supplierId: number, api: SupplierApiConfigApi) => {
    if (api.id < 0) {
      setConfigs((prev) =>
        prev.map((supplier) =>
          supplier.id === supplierId
            ? { ...supplier, apis: supplier.apis.filter((item) => item.id !== api.id) }
            : supplier
        )
      );
      return;
    }

    try {
      await deleteSupplierApi(api.id);
      notify('API supprimée.', 'success');
      await refreshConfigs();
    } catch (err) {
      showError(err, 'Impossible de supprimer cette API.');
    }
  };

  const handleAddEndpoint = (supplierId: number, api: SupplierApiConfigApi) => {
    if (api.id < 0) {
      notify("Enregistrez l'API avant d'ajouter un endpoint.", 'info');
      return;
    }

    const tempId = -Math.floor(Date.now() + Math.random() * 1000);
    const newEndpoint: SupplierApiConfigEndpoint = {
      id: tempId,
      name: '',
      method: 'GET',
      path: '',
      items_path: '',
    };

    setConfigs((prev) =>
      prev.map((supplier) =>
        supplier.id !== supplierId
          ? supplier
          : {
              ...supplier,
              apis: supplier.apis.map((item) =>
                item.id === api.id
                  ? { ...item, endpoints: [...item.endpoints, newEndpoint] }
                  : item
              ),
            }
      )
    );
  };

  const handleEndpointChange = (
    supplierId: number,
    apiId: number,
    endpointId: number,
    field: 'name' | 'method' | 'path' | 'items_path',
    value: string
  ) => {
    setConfigs((prev) =>
      prev.map((supplier) => {
        if (supplier.id !== supplierId) return supplier;
        return {
          ...supplier,
          apis: supplier.apis.map((api) => {
            if (api.id !== apiId) return api;
            return {
              ...api,
              endpoints: api.endpoints.map((endpoint) => {
                if (endpoint.id !== endpointId) return endpoint;
                if (field === 'name') {
                  return { ...endpoint, name: value };
                }
                if (field === 'method') {
                  return { ...endpoint, method: value.toUpperCase() };
                }
                if (field === 'path') {
                  return { ...endpoint, path: value };
                }
                return { ...endpoint, items_path: value };
              }),
            };
          }),
        };
      })
    );
  };

  const handleEndpointSave = async (
    supplierId: number,
    apiId: number,
    endpoint: SupplierApiConfigEndpoint
  ) => {
    const name = (endpoint.name || '').trim();
    const path = (endpoint.path || '').trim();

    if (!name || !path) {
      notify('Le nom et le chemin sont obligatoires.', 'error');
      return;
    }

    const payload = {
      name,
      method: (endpoint.method || 'GET').toUpperCase(),
      path,
      items_path: (endpoint.items_path || '').trim() || null,
    };

    try {
      if (endpoint.id < 0) {
        await createSupplierApiEndpoint(apiId, payload);
        notify('Endpoint créé.', 'success');
      } else {
        await updateSupplierApiEndpoint(endpoint.id, payload);
        notify('Endpoint mis à jour.', 'success');
      }
      await refreshConfigs();
    } catch (err) {
      showError(err, "Impossible d'enregistrer cet endpoint.");
    }
  };

  const handleEndpointDelete = async (
    supplierId: number,
    api: SupplierApiConfigApi,
    endpoint: SupplierApiConfigEndpoint
  ) => {
    if (endpoint.id < 0) {
      setConfigs((prev) =>
        prev.map((supplier) =>
          supplier.id !== supplierId
            ? supplier
            : {
                ...supplier,
                apis: supplier.apis.map((item) =>
                  item.id === api.id
                    ? {
                        ...item,
                        endpoints: item.endpoints.filter((ept) => ept.id !== endpoint.id),
                      }
                    : item
                ),
              }
        )
      );
      return;
    }

    try {
      await deleteSupplierApiEndpoint(endpoint.id);
      notify('Endpoint supprimé.', 'success');
      await refreshConfigs();
    } catch (err) {
      showError(err, "Impossible de supprimer cet endpoint.");
    }
  };

  const ensureMapping = useCallback(
    async (supplierId: number, api: SupplierApiConfigApi) => {
      if (api.mapping) {
        return api.mapping.id;
      }

      if (api.id < 0) {
        notify("Enregistrez l'API avant d'ajouter un mapping.", 'info');
        return null;
      }

      try {
        const mapping = await createSupplierApiMapping(api.id);
        const mappingWithDefaults = withDefaultMappingFields({
          ...mapping,
          fields: mapping.fields ?? [],
        })!;
        setConfigs((prev) =>
          prev.map((supplier) =>
            supplier.id !== supplierId
              ? supplier
              : {
                  ...supplier,
                  apis: supplier.apis.map((item) =>
                    item.id === api.id
                      ? { ...item, mapping: mappingWithDefaults }
                      : item
                  ),
                }
          )
        );
        notify('Mapping initialisé.', 'info');
        return mapping.id as number;
      } catch (err) {
        showError(err, 'Impossible de créer un mapping pour cette API.');
        return null;
      }
    },
    [notify, showError]
  );

  const handleAddField = async (supplierId: number, api: SupplierApiConfigApi) => {
    const mappingId = await ensureMapping(supplierId, api);
    if (!mappingId) {
      return;
    }

    const tempId = -Math.floor(Date.now() + Math.random() * 1000);
    const newField: SupplierApiConfigField = {
      id: tempId,
      target_field: '',
      source_path: '',
      transform: null,
    };

    setConfigs((prev) =>
      prev.map((supplier) =>
        supplier.id !== supplierId
          ? supplier
          : {
              ...supplier,
              apis: supplier.apis.map((item) => {
                if (item.id !== api.id) return item;
                const mapping = item.mapping
                  ? withDefaultMappingFields({
                      ...item.mapping,
                      fields: [...item.mapping.fields, newField],
                    })!
                  : withDefaultMappingFields({
                      id: mappingId,
                      version: 1,
                      is_active: true,
                      fields: [newField],
                    })!;
                return { ...item, mapping };
              }),
            }
      )
    );
  };

  const handleFieldChange = (
    supplierId: number,
    apiId: number,
    fieldId: number,
    fieldName: 'target_field' | 'source_path',
    value: string
  ) => {
    setConfigs((prev) =>
      prev.map((supplier) => {
        if (supplier.id !== supplierId) return supplier;
        return {
          ...supplier,
          apis: supplier.apis.map((api) => {
            if (api.id !== apiId || !api.mapping) return api;
            return {
              ...api,
              mapping: withDefaultMappingFields({
                ...api.mapping,
                fields: api.mapping.fields.map((field) => {
                  if (field.id !== fieldId) return field;
                  if (fieldName === 'target_field') {
                    return { ...field, target_field: value };
                  }
                  return { ...field, source_path: value };
                }),
              })!,
            };
          }),
        };
      })
    );
  };

  const handleFieldSave = async (
    supplierId: number,
    api: SupplierApiConfigApi,
    field: SupplierApiConfigField
  ) => {
    if (!api.mapping) {
      notify('Aucun mapping actif pour cette API.', 'error');
      return;
    }

    const targetField = (field.target_field || '').trim();
    const sourcePath = (field.source_path || '').trim();

    if (!targetField || !sourcePath) {
      notify('Les champs cible et source sont obligatoires.', 'error');
      return;
    }

    const payload = {
      target_field: targetField,
      source_path: sourcePath,
      transform: field.transform ?? null,
    };

    try {
      if (field.id < 0) {
        await createSupplierApiField(api.mapping.id, payload);
        notify('Champ ajouté.', 'success');
      } else {
        await updateSupplierApiField(field.id, payload);
        notify('Champ mis à jour.', 'success');
      }
      await refreshConfigs();
    } catch (err) {
      showError(err, "Impossible d'enregistrer ce champ.");
    }
  };

  const handleFieldDelete = async (
    supplierId: number,
    api: SupplierApiConfigApi,
    field: SupplierApiConfigField
  ) => {
    if (!api.mapping) {
      return;
    }

    if (field.id < 0) {
      setConfigs((prev) =>
        prev.map((supplier) =>
          supplier.id !== supplierId
            ? supplier
            : {
                ...supplier,
                apis: supplier.apis.map((item) =>
                  item.id === api.id && item.mapping
                    ? {
                        ...item,
                        mapping: withDefaultMappingFields({
                          ...item.mapping,
                          fields: item.mapping.fields.filter((f) => f.id !== field.id),
                        })!,
                      }
                    : item
                ),
              }
        )
      );
      return;
    }

    try {
      await deleteSupplierApiField(field.id);
      notify('Champ supprimé.', 'success');
      await refreshConfigs();
    } catch (err) {
      showError(err, "Impossible de supprimer ce champ.");
    }
  };

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
              <div className="flex-1">
                <p className="text-xs uppercase text-zinc-500 tracking-wide">Fournisseur</p>
                <h3 className="text-lg font-semibold text-white">{supplier.name}</h3>
              </div>
              <button
                onClick={() => handleAddApi(supplier.id)}
                className="flex items-center gap-2 px-3 py-2 bg-emerald-600 text-white rounded hover:bg-emerald-500"
              >
                <Plus className="w-4 h-4" />
                <span>Ajouter une API</span>
              </button>
            </div>

            {supplier.apis.length > 0 ? (
              <div className="space-y-6">
                {supplier.apis.map((api) => {
                  const fields = mapFieldsWithCategory(api.mapping?.fields);

                  return (
                    <div key={api.id} className="bg-black/30 border border-zinc-800/60 rounded-xl">
                      <div className="px-5 py-4 flex flex-col gap-4 border-b border-zinc-800/60">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <div className="flex flex-col gap-2">
                            <label className="text-xs uppercase tracking-wide text-zinc-400">
                              Base URL
                            </label>
                            <input
                              value={api.base_url}
                              onChange={(e) =>
                                handleApiChange(supplier.id, api.id, 'base_url', e.target.value)
                              }
                              placeholder="https://api.fournisseur.com"
                              className="px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-700 text-white placeholder:text-zinc-500"
                            />
                          </div>
                          <div className="flex flex-col gap-2">
                            <label className="text-xs uppercase tracking-wide text-zinc-400">
                              Authentification
                            </label>
                            <select
                              value={api.auth_type ?? 'none'}
                              onChange={(e) =>
                                handleApiChange(supplier.id, api.id, 'auth_type', e.target.value)
                              }
                              className="px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-700 text-white"
                            >
                              {AUTH_TYPE_OPTIONS.map((option) => (
                                <option key={option.value} value={option.value}>
                                  {option.label}
                                </option>
                              ))}
                            </select>
                          </div>
                          <div className="flex flex-col gap-2">
                            <label className="text-xs uppercase tracking-wide text-zinc-400">
                              Limite/minute
                            </label>
                            <input
                              type="number"
                              min={0}
                              value={api.rate_limit_per_min ?? ''}
                              onChange={(e) =>
                                handleApiChange(
                                  supplier.id,
                                  api.id,
                                  'rate_limit_per_min',
                                  e.target.value
                                )
                              }
                              placeholder="Illimité"
                              className="px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-700 text-white placeholder:text-zinc-500"
                            />
                          </div>
                        </div>
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleApiSave(supplier.id, api)}
                            className="inline-flex items-center gap-2 px-3 py-2 bg-emerald-600 text-white rounded hover:bg-emerald-500"
                          >
                            <Save className="w-4 h-4" />
                            <span>{api.id < 0 ? 'Créer' : 'Enregistrer'}</span>
                          </button>
                          <button
                            onClick={() => handleApiDelete(supplier.id, api)}
                            className="inline-flex items-center gap-2 px-3 py-2 bg-red-600 text-white rounded hover:bg-red-500"
                          >
                            <Trash2 className="w-4 h-4" />
                            <span>Supprimer</span>
                          </button>
                        </div>
                      </div>

                      <div className="p-5 space-y-6">
                        <section className="space-y-3">
                          <div className="flex items-center justify-between">
                            <h4 className="text-sm text-zinc-400 uppercase tracking-wide">
                              Endpoints
                            </h4>
                            <button
                              onClick={() => handleAddEndpoint(supplier.id, api)}
                              className="flex items-center gap-2 px-3 py-2 bg-zinc-800 rounded hover:bg-zinc-700"
                            >
                              <Plus className="w-4 h-4" />
                              <span>Ajouter un endpoint</span>
                            </button>
                          </div>

                          {api.endpoints.length > 0 ? (
                            <div className="overflow-x-auto">
                              <table className="min-w-full text-sm text-left text-zinc-200 border border-zinc-800/60 rounded-lg overflow-hidden">
                                <thead className="bg-zinc-900/80 text-xs uppercase tracking-wide text-zinc-400">
                                  <tr>
                                    <th className="px-4 py-2 font-medium">Nom</th>
                                    <th className="px-4 py-2 font-medium">Méthode</th>
                                    <th className="px-4 py-2 font-medium">Chemin</th>
                                    <th className="px-4 py-2 font-medium">Chemin items</th>
                                    <th className="px-4 py-2 font-medium text-right">Actions</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {api.endpoints.map((endpoint) => (
                                    <tr
                                      key={endpoint.id}
                                      className="border-t border-zinc-800/60 even:bg-black/20"
                                    >
                                      <td className="px-4 py-2">
                                        <input
                                          value={endpoint.name}
                                          onChange={(e) =>
                                            handleEndpointChange(
                                              supplier.id,
                                              api.id,
                                              endpoint.id,
                                              'name',
                                              e.target.value
                                            )
                                          }
                                          placeholder="Nom"
                                          className="w-full px-2 py-1 rounded bg-zinc-900 border border-zinc-700 text-white placeholder:text-zinc-500"
                                        />
                                      </td>
                                      <td className="px-4 py-2">
                                        <select
                                          value={endpoint.method}
                                          onChange={(e) =>
                                            handleEndpointChange(
                                              supplier.id,
                                              api.id,
                                              endpoint.id,
                                              'method',
                                              e.target.value
                                            )
                                          }
                                          className="px-2 py-1 rounded bg-zinc-900 border border-zinc-700 text-white"
                                        >
                                          {HTTP_METHODS.map((method) => (
                                            <option key={method} value={method}>
                                              {method}
                                            </option>
                                          ))}
                                        </select>
                                      </td>
                                      <td className="px-4 py-2">
                                        <input
                                          value={endpoint.path}
                                          onChange={(e) =>
                                            handleEndpointChange(
                                              supplier.id,
                                              api.id,
                                              endpoint.id,
                                              'path',
                                              e.target.value
                                            )
                                          }
                                          placeholder="/v1/products"
                                          className="w-full px-2 py-1 rounded bg-zinc-900 border border-zinc-700 text-white placeholder:text-zinc-500"
                                        />
                                      </td>
                                      <td className="px-4 py-2">
                                        <input
                                          value={endpoint.items_path ?? ''}
                                          onChange={(e) =>
                                            handleEndpointChange(
                                              supplier.id,
                                              api.id,
                                              endpoint.id,
                                              'items_path',
                                              e.target.value
                                            )
                                          }
                                          placeholder="data.items"
                                          className="w-full px-2 py-1 rounded bg-zinc-900 border border-zinc-700 text-white placeholder:text-zinc-500"
                                        />
                                      </td>
                                      <td className="px-4 py-2">
                                        <div className="flex justify-end gap-2">
                                          <button
                                            onClick={() =>
                                              handleEndpointSave(supplier.id, api.id, endpoint)
                                            }
                                            className="p-2 rounded bg-emerald-600 text-white hover:bg-emerald-500"
                                          >
                                            <Save className="w-4 h-4" />
                                          </button>
                                          <button
                                            onClick={() =>
                                              handleEndpointDelete(supplier.id, api, endpoint)
                                            }
                                            className="p-2 rounded bg-red-600 text-white hover:bg-red-500"
                                          >
                                            <Trash2 className="w-4 h-4" />
                                          </button>
                                        </div>
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          ) : (
                            <p className="text-sm text-zinc-500 italic">
                              Aucun endpoint configuré. Ajoutez-en un pour commencer.
                            </p>
                          )}
                        </section>

                        <section className="space-y-3">
                          <div className="flex items-center justify-between">
                            <div className="flex flex-col">
                              <h4 className="text-sm text-zinc-400 uppercase tracking-wide">
                                Mapping des champs
                              </h4>
                              {api.mapping && (
                                <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-zinc-400">
                                  <span className="px-2 py-1 rounded-full border border-zinc-700 bg-zinc-900/70">
                                    Version {api.mapping.version}
                                  </span>
                                  {api.mapping.is_active ? (
                                    <span className="px-2 py-1 rounded-full border border-emerald-500/40 bg-emerald-500/10 text-emerald-300">
                                      Actif
                                    </span>
                                  ) : (
                                    <span className="px-2 py-1 rounded-full border border-zinc-700 bg-zinc-900/70">
                                      Inactif
                                    </span>
                                  )}
                                </div>
                              )}
                              <p className="text-xs text-zinc-500 mt-1">
                                Champs obligatoires : <code className="text-zinc-300">product_id</code>,{' '}
                                <code className="text-zinc-300">price</code> et{' '}
                                <code className="text-zinc-300">quantity</code>.
                              </p>
                            </div>
                            <button
                              onClick={() => handleAddField(supplier.id, api)}
                              className="flex items-center gap-2 px-3 py-2 bg-zinc-800 rounded hover:bg-zinc-700"
                            >
                              <Plus className="w-4 h-4" />
                              <span>Ajouter un champ</span>
                            </button>
                          </div>

                          {fields.length > 0 ? (
                            <div className="overflow-x-auto">
                              <table className="min-w-full text-sm text-left text-zinc-200 border border-zinc-800/60 rounded-lg overflow-hidden">
                                <thead className="bg-zinc-900/80 text-xs uppercase tracking-wide text-zinc-400">
                                  <tr>
                                    <th className="px-4 py-2 font-medium">Champ cible</th>
                                    <th className="px-4 py-2 font-medium">Source</th>
                                    <th className="px-4 py-2 font-medium">Type</th>
                                    <th className="px-4 py-2 font-medium text-right">Actions</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {fields.map((field) => (
                                    <tr
                                      key={field.id}
                                      className="border-t border-zinc-800/60 even:bg-black/20"
                                    >
                                      <td className="px-4 py-2">
                                        <input
                                          value={field.target_field}
                                          onChange={(e) =>
                                            handleFieldChange(
                                              supplier.id,
                                              api.id,
                                              field.id,
                                              'target_field',
                                              e.target.value
                                            )
                                          }
                                          placeholder="product_id"
                                          className="w-full px-2 py-1 rounded bg-zinc-900 border border-zinc-700 text-white placeholder:text-zinc-500"
                                        />
                                      </td>
                                      <td className="px-4 py-2">
                                        <input
                                          value={field.source_path}
                                          onChange={(e) =>
                                            handleFieldChange(
                                              supplier.id,
                                              api.id,
                                              field.id,
                                              'source_path',
                                              e.target.value
                                            )
                                          }
                                          placeholder="data.price"
                                          className="w-full px-2 py-1 rounded bg-zinc-900 border border-zinc-700 text-white placeholder:text-zinc-500"
                                        />
                                      </td>
                                      <td className="px-4 py-2">
                                        <FieldCategoryBadge category={field.category} />
                                      </td>
                                      <td className="px-4 py-2">
                                        <div className="flex justify-end gap-2">
                                          <button
                                            onClick={() => handleFieldSave(supplier.id, api, field)}
                                            className="p-2 rounded bg-emerald-600 text-white hover:bg-emerald-500"
                                          >
                                            <Save className="w-4 h-4" />
                                          </button>
                                          <button
                                            onClick={() => handleFieldDelete(supplier.id, api, field)}
                                            className="p-2 rounded bg-red-600 text-white hover:bg-red-500"
                                          >
                                            <Trash2 className="w-4 h-4" />
                                          </button>
                                        </div>
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          ) : (
                            <p className="text-sm text-zinc-500 italic">
                              Aucun mapping actif pour cette API. Ajoutez un champ pour démarrer le mapping.
                            </p>
                          )}
                        </section>
                      </div>
                    </div>
                  );
                })}
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
