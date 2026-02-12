import { getCurrentTimestamp } from './utils/date';

export const API_BASE = import.meta.env.VITE_API_BASE || '/api';

export let authToken: string | null = localStorage.getItem('token');
export let refreshToken: string | null = localStorage.getItem('refresh_token');

export function setAuthToken(token: string | null) {
  authToken = token;
  if (token) localStorage.setItem('token', token);
  else localStorage.removeItem('token');
}

export function setRefreshToken(token: string | null) {
  refreshToken = token;
  if (token) localStorage.setItem('refresh_token', token);
  else localStorage.removeItem('refresh_token');
}

function authHeaders(headers: Record<string, string> = {}) {
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }
  return headers;
}

async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const opts: RequestInit = { ...options };
  opts.headers = authHeaders(options.headers as Record<string, string>);
  let res = await fetch(url, opts);
  if (res.status === 401 && refreshToken) {
    const refreshRes = await fetch(`${API_BASE}/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken })
    });
    if (refreshRes.ok) {
      const data = await refreshRes.json();
      setAuthToken(data.token);
      setRefreshToken(data.refresh_token);
      opts.headers = authHeaders(options.headers as Record<string, string>);
      res = await fetch(url, opts);
    } else {
      setAuthToken(null);
      setRefreshToken(null);
      window.dispatchEvent(new Event('auth:logout'));
    }
  }
  return res;
}

export async function login(email: string, password: string) {
  const res = await fetch(`${API_BASE}/login`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ email, password })
  });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}


async function extractErrorMessage(res: Response): Promise<string> {
  const data = await res.json().catch(() => ({}));
  return data.message || data.error || 'Une erreur est survenue';
}

async function crudRequest(method: string, url: string, body?: unknown) {
  const options: RequestInit = { method };
  if (body !== undefined) {
    options.headers = { 'Content-Type': 'application/json' };
    options.body = JSON.stringify(body);
  }
  const res = await fetchWithAuth(url, options);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  if (method === 'DELETE' && res.status === 204) return;
  return res.json();
}

interface StatsFilterParams {
  supplierId?: number;
  brandId?: number;
  productId?: number;
  startWeek?: string;
  endWeek?: string;
}

function _buildStatsParams(params?: StatsFilterParams): string {
  const search = new URLSearchParams();
  if (params?.supplierId) search.set('supplier_id', String(params.supplierId));
  if (params?.brandId) search.set('brand_id', String(params.brandId));
  if (params?.productId) search.set('product_id', String(params.productId));
  if (params?.startWeek) search.set('start_week', params.startWeek);
  if (params?.endWeek) search.set('end_week', params.endWeek);
  const query = search.toString();
  return query ? `?${query}` : '';
}

export async function fetchApitest() {
  const res = await fetchWithAuth(`${API_BASE}/`);
  if (!res.ok) {
    throw new Error("Impossible de communiquer avec l'API.");
  }
  return res.json();
}


export async function createImport(file: File, supplierId?: number) {
  const formData = new FormData();
  formData.append('file', file);
  if (supplierId !== undefined) {
    formData.append('supplier_id', String(supplierId));
  }

  const res = await fetchWithAuth(`${API_BASE}/import`, {
    method: 'POST',
    body: formData
  });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function fetchImportPreview(file: File, supplierId?: number) {
  const formData = new FormData();
  formData.append('file', file);
  if (supplierId !== undefined) {
    formData.append('supplier_id', String(supplierId));
  }

  const res = await fetchWithAuth(`${API_BASE}/import_preview`, {
    method: 'POST',
    body: formData
  });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function fetchProducts() {
  const res = await fetchWithAuth(`${API_BASE}/products`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export interface SupplierApiRow {
  description?: string | null;
  model?: string | null;
  quantity?: number | null;
  selling_price?: number | null;
  ean?: string | null;
  part_number?: string | null;
  supplier_sku?: string | null;
}

export interface SupplierApiReportEntryItem {
  product_id?: number | null;
  product_name?: string | null;
  description?: string | null;
  ean?: string | null;
  part_number?: string | null;
  supplier_sku?: string | null;
  price?: number | null;
  reason?: string | null;
}

export interface SupplierApiReportData {
  updated_products: SupplierApiReportEntryItem[];
  database_missing_products: SupplierApiReportEntryItem[];
  api_missing_products: SupplierApiReportEntryItem[];
}

export interface SupplierApiMappingSummary {
  id: number;
  version: number;
  is_active: boolean;
  field_count?: number;
}

export interface SupplierApiSyncResponse {
  job_id: number;
  supplier_id: number;
  supplier: string;
  status: string;
  parsed_count: number;
  temporary_import_count: number;
  started_at?: string | null;
  ended_at?: string | null;
  items: SupplierApiRow[];
  rows?: SupplierApiRow[];
  report?: SupplierApiReportData;
  api_raw_items?: unknown[];
  mapping?: SupplierApiMappingSummary | null;
}

export interface SupplierApiReportEntry extends SupplierApiReportData {
  job_id: number;
  supplier_id: number | null;
  supplier: string | null;
  started_at: string | null;
  ended_at: string | null;
  api_raw_items?: unknown[];
  mapping?: SupplierApiMappingSummary | null;
}

export interface SupplierApiConfigField {
  id: number;
  target_field: string;
  source_path: string;
  transform?: Record<string, unknown> | null;
}

export interface SupplierApiConfigMapping {
  id: number;
  version: number;
  is_active: boolean;
  fields: SupplierApiConfigField[];
}

export interface SupplierApiConfigEndpoint {
  id: number;
  name: string;
  method: string;
  path: string;
  items_path?: string | null;
}

export interface SupplierApiConfigApi {
  id: number;
  base_url: string;
  auth_type?: string | null;
  rate_limit_per_min?: number | null;
  endpoints: SupplierApiConfigEndpoint[];
  mapping: SupplierApiConfigMapping | null;
}

export interface SupplierApiConfigSupplier {
  id: number;
  name: string;
  apis: SupplierApiConfigApi[];
}

export interface SupplierApiPayload {
  base_url: string;
  auth_type?: string | null;
  rate_limit_per_min?: number | null;
  auth_config?: Record<string, unknown> | null;
  default_headers?: Record<string, string> | null;
}

export interface SupplierApiEndpointPayload {
  name: string;
  method?: string;
  path: string;
  items_path?: string | null;
}

export interface SupplierApiFieldPayload {
  target_field: string;
  source_path: string;
  transform?: Record<string, unknown> | null;
}

export interface SupplierApiRefreshPayload {
  endpoint_id?: number;
  endpoint_name?: string;
  mapping_version_id?: number;
  query_params?: Record<string, unknown>;
  body?: Record<string, unknown>;
}

export async function refreshSupplierCatalog(
  supplierId: number,
  payload: SupplierApiRefreshPayload = {}
) {
  const res = await fetchWithAuth(`${API_BASE}/supplier_api/${supplierId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json() as Promise<SupplierApiSyncResponse>;
}

export async function fetchSupplierApiReports(limit = 20) {
  const params = new URLSearchParams({ limit: String(limit) });
  const res = await fetchWithAuth(`${API_BASE}/supplier_api/reports?${params.toString()}`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json() as Promise<SupplierApiReportEntry[]>;
}

export async function createProduct(data: any) {
  return crudRequest('POST', `${API_BASE}/products`, data);
}

export async function fetchSupplierApiConfigs() {
  const res = await fetchWithAuth(`${API_BASE}/supplier_api/config`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json() as Promise<SupplierApiConfigSupplier[]>;
}

export async function createSupplierApi(supplierId: number, payload: SupplierApiPayload) {
  return crudRequest('POST', `${API_BASE}/supplier_api/${supplierId}/apis`, payload);
}

export async function updateSupplierApi(apiId: number, payload: Partial<SupplierApiPayload>) {
  return crudRequest('PATCH', `${API_BASE}/supplier_api/apis/${apiId}`, payload);
}

export async function deleteSupplierApi(apiId: number) {
  return crudRequest('DELETE', `${API_BASE}/supplier_api/apis/${apiId}`);
}

export async function createSupplierApiEndpoint(apiId: number, payload: SupplierApiEndpointPayload) {
  return crudRequest('POST', `${API_BASE}/supplier_api/apis/${apiId}/endpoints`, payload);
}

export async function updateSupplierApiEndpoint(endpointId: number, payload: Partial<SupplierApiEndpointPayload>) {
  return crudRequest('PATCH', `${API_BASE}/supplier_api/endpoints/${endpointId}`, payload);
}

export async function deleteSupplierApiEndpoint(endpointId: number) {
  return crudRequest('DELETE', `${API_BASE}/supplier_api/endpoints/${endpointId}`);
}

export async function createSupplierApiMapping(apiId: number) {
  return crudRequest('POST', `${API_BASE}/supplier_api/apis/${apiId}/mapping`, {});
}

export async function createSupplierApiField(mappingId: number, payload: SupplierApiFieldPayload) {
  return crudRequest('POST', `${API_BASE}/supplier_api/mappings/${mappingId}/fields`, payload);
}

export async function updateSupplierApiField(fieldId: number, payload: Partial<SupplierApiFieldPayload>) {
  return crudRequest('PATCH', `${API_BASE}/supplier_api/fields/${fieldId}`, payload);
}

export async function deleteSupplierApiField(fieldId: number) {
  return crudRequest('DELETE', `${API_BASE}/supplier_api/fields/${fieldId}`);
}

export async function updateProduct(id: number, data: any) {
  return crudRequest('PUT', `${API_BASE}/products/${id}`, data);
}

export async function bulkUpdateProducts(data: any[]) {
  return crudRequest('PUT', `${API_BASE}/products/bulk_update`, data);
}

export async function deleteProduct(id: number) {
  return crudRequest('DELETE', `${API_BASE}/products/${id}`);
}

export async function bulkDeleteProducts(ids: number[]) {
  return crudRequest('POST', `${API_BASE}/products/bulk_delete`, { ids });
}


export async function fetchLastImport(id: number): Promise<{ import_date: string | null } | {}> {
  const res = await fetchWithAuth(`${API_BASE}/last_import/${id}`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function verifyImport(id: number) {
  const res = await fetchWithAuth(`${API_BASE}/verify_import/${id}`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}


export async function calculateProducts() {
  const res = await fetchWithAuth(`${API_BASE}/calculate_products`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function exportCalculations() {
  const res = await fetchWithAuth(`${API_BASE}/export_calculates`);
  if (!res.ok) {
    throw new Error('La génération du fichier a échoué.');
  }
  const blob = await res.blob();
  let filename = `product_calculates_${getCurrentTimestamp()}.xlsx`;
  const disposition = res.headers.get('Content-Disposition');
  if (disposition) {
    const match = disposition.match(/filename="?([^";]+)"?/);
    if (match) {
      filename = match[1];
    }
  }
  return { blob, filename };
}

export async function refreshProduction() {
  const res = await fetchWithAuth(`${API_BASE}/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}


export async function refreshProductionByWeek(array_date: Array<Date>) {
  const res = await fetchWithAuth(`${API_BASE}/refresh_week`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dates: array_date.map(date => date.toISOString()) })
  });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function fetchProductCalculations() {
  const res = await fetchWithAuth(`${API_BASE}/product_calculation`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function fetchProductPriceSummary() {
  const res = await fetchWithAuth(`${API_BASE}/product_price_summary`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function fetchSearchCatalog() {
  const res = await fetchWithAuth(`${API_BASE}/search_catalog`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function fetchSuppliers() {
  const res = await fetchWithAuth(`${API_BASE}/references/suppliers`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function fetchReferenceTable(table: string) {
  const res = await fetchWithAuth(`${API_BASE}/references/${table}`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function updateReferenceItem(table: string, id: number, data: any) {
  return crudRequest('PUT', `${API_BASE}/references/${table}/${id}`, data);
}

export async function createReferenceItem(table: string, data: any) {
  return crudRequest('POST', `${API_BASE}/references/${table}`, data);
}

export async function deleteReferenceItem(table: string, id: number) {
  return crudRequest('DELETE', `${API_BASE}/references/${table}/${id}`);
}

export async function fetchUsers() {
  const res = await fetchWithAuth(`${API_BASE}/users`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function updateUser(id: number, data: any) {
  return crudRequest('PUT', `${API_BASE}/users/${id}`, data);
}

export async function createUser(data: any) {
  return crudRequest('POST', `${API_BASE}/users`, data);
}

export async function deleteUser(id: number) {
  return crudRequest('DELETE', `${API_BASE}/users/${id}`);
}

export async function fetchBrands() {
  const res = await fetchWithAuth(`${API_BASE}/references/brands`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}


export async function fetchColors() {
  const res = await fetchWithAuth(`${API_BASE}/references/colors`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function fetchMemoryOptions() {
  const res = await fetchWithAuth(`${API_BASE}/references/memory_options`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function fetchRAMOptions() {
  const res = await fetchWithAuth(`${API_BASE}/references/ram_options`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function fetchNormeOptions() {
  const res = await fetchWithAuth(`${API_BASE}/references/norme_options`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function fetchDeviceTypes() {
  const res = await fetchWithAuth(`${API_BASE}/references/device_types`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function fetchPriceStats(params?: StatsFilterParams) {
  const qs = _buildStatsParams(params);
  const res = await fetchWithAuth(`${API_BASE}/price_stats${qs}`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function fetchBrandSupplierAverage(params?: StatsFilterParams) {
  const qs = _buildStatsParams(params);
  const res = await fetchWithAuth(`${API_BASE}/brand_supplier_average${qs}`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function fetchProductSupplierAverage(params?: StatsFilterParams) {
  const qs = _buildStatsParams(params);
  const res = await fetchWithAuth(`${API_BASE}/product_supplier_average${qs}`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function fetchGraphSettings() {
  const res = await fetchWithAuth(`${API_BASE}/graph_settings`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function updateGraphSetting(name: string, visible: boolean) {
  return crudRequest('PUT', `${API_BASE}/graph_settings/${name}`, { visible });
}

// ---------------------------------------------------------------------------
// Odoo Sync
// ---------------------------------------------------------------------------

export interface OdooConfigData {
  configured: boolean;
  url?: string;
  database?: string;
  login?: string;
  password?: string;
  auto_sync_enabled?: boolean;
  auto_sync_interval_minutes?: number;
  last_auto_sync_at?: string | null;
}

export interface OdooTestResult {
  server_version: string;
  uid: number;
  product_count: number;
}

export interface OdooSyncReportItem {
  odoo_id: string;
  name: string;
  ean?: string;
  part_number?: string;
  error?: string;
}

export interface OdooSyncReport {
  report_created?: OdooSyncReportItem[];
  report_updated?: OdooSyncReportItem[];
  report_unchanged?: OdooSyncReportItem[];
  report_errors?: OdooSyncReportItem[];
}

export interface OdooSyncJobResponse {
  id: number;
  started_at: string | null;
  ended_at: string | null;
  status: string;
  trigger: string;
  error_message: string | null;
  total_odoo_products: number;
  created_count: number;
  updated_count: number;
  unchanged_count: number;
  error_count: number;
  report_created?: OdooSyncReportItem[];
  report_updated?: OdooSyncReportItem[];
  report_unchanged?: OdooSyncReportItem[];
  report_errors?: OdooSyncReportItem[];
}

export async function fetchOdooConfig() {
  const res = await fetchWithAuth(`${API_BASE}/odoo/config`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json() as Promise<OdooConfigData>;
}

export async function updateOdooConfig(data: { url: string; database: string; login: string; password: string }) {
  return crudRequest('PUT', `${API_BASE}/odoo/config`, data);
}

export async function testOdooConnection() {
  const res = await fetchWithAuth(`${API_BASE}/odoo/test`, { method: 'POST' });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json() as Promise<OdooTestResult>;
}

export async function triggerOdooSync() {
  const res = await fetchWithAuth(`${API_BASE}/odoo/sync`, { method: 'POST' });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json() as Promise<{ job_id: number; status: string }>;
}

export async function fetchOdooSyncJobs(limit = 20) {
  const params = new URLSearchParams({ limit: String(limit) });
  const res = await fetchWithAuth(`${API_BASE}/odoo/jobs?${params.toString()}`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json() as Promise<OdooSyncJobResponse[]>;
}

export async function fetchOdooSyncJob(jobId: number) {
  const res = await fetchWithAuth(`${API_BASE}/odoo/jobs/${jobId}`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json() as Promise<OdooSyncJobResponse>;
}

export async function updateOdooAutoSync(data: { enabled?: boolean; interval_minutes?: number }) {
  return crudRequest('PUT', `${API_BASE}/odoo/auto-sync`, data);
}
