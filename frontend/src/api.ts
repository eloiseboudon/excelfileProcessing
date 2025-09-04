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
    console.log("🔧 API base URL =", import.meta.env.VITE_API_BASE);
    console.log("🔧 import.meta.env =", import.meta.env);

    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}


async function extractErrorMessage(res: Response): Promise<string> {
  const data = await res.json().catch(() => ({}));
  return data.message || data.error || 'Une erreur est survenue';
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

export async function createProduct(data: any) {
  const res = await fetchWithAuth(`${API_BASE}/products`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function updateProduct(id: number, data: any) {
  const res = await fetchWithAuth(`${API_BASE}/products/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function bulkUpdateProducts(data: any[]) {
  const res = await fetchWithAuth(`${API_BASE}/products/bulk_update`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function deleteProduct(id: number) {
  const res = await fetchWithAuth(`${API_BASE}/products/${id}`, {
    method: 'DELETE'
  });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
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

export async function fetchSuppliers() {
  const res = await fetchWithAuth(`${API_BASE}/references/suppliers`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
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

export async function fetchReferenceTable(table: string) {
  const res = await fetchWithAuth(`${API_BASE}/references/${table}`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function updateReferenceItem(table: string, id: number, data: any) {
  const res = await fetchWithAuth(`${API_BASE}/references/${table}/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function createReferenceItem(table: string, data: any) {
  const res = await fetchWithAuth(`${API_BASE}/references/${table}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}



export async function deleteReferenceItem(table: string, id: number) {
  const res = await fetchWithAuth(`${API_BASE}/references/${table}/${id}`, {
    method: 'DELETE'
  });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function fetchUsers() {
  const res = await fetchWithAuth(`${API_BASE}/users`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function updateUser(id: number, data: any) {
  const res = await fetchWithAuth(`${API_BASE}/users/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function createUser(data: any) {
  const res = await fetchWithAuth(`${API_BASE}/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function deleteUser(id: number) {
  const res = await fetchWithAuth(`${API_BASE}/users/${id}`, {
    method: 'DELETE'
  });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
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

export async function fetchPriceStats(params?: {
  supplierId?: number;
  brandId?: number;
  productId?: number;
  startWeek?: string;
  endWeek?: string;
}) {
  const search = new URLSearchParams();
  if (params?.supplierId) search.set('supplier_id', String(params.supplierId));
  if (params?.brandId) search.set('brand_id', String(params.brandId));
  if (params?.productId) search.set('product_id', String(params.productId));
  if (params?.startWeek) search.set('start_week', params.startWeek);
  if (params?.endWeek) search.set('end_week', params.endWeek);
  const query = search.toString();
  const res = await fetchWithAuth(`${API_BASE}/price_stats${query ? `?${query}` : ''}`);
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function fetchBrandSupplierAverage(params?: {
  supplierId?: number;
  brandId?: number;
  startWeek?: string;
  endWeek?: string;
}) {
  const search = new URLSearchParams();
  if (params?.supplierId) search.set('supplier_id', String(params.supplierId));
  if (params?.brandId) search.set('brand_id', String(params.brandId));
  if (params?.startWeek) search.set('start_week', params.startWeek);
  if (params?.endWeek) search.set('end_week', params.endWeek);
  const query = search.toString();
  const res = await fetchWithAuth(
    `${API_BASE}/brand_supplier_average${query ? `?${query}` : ''}`
  );
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

export async function fetchProductSupplierAverage(params?: {
  supplierId?: number;
  brandId?: number;
  productId?: number;
  startWeek?: string;
  endWeek?: string;
}) {
  const search = new URLSearchParams();
  if (params?.supplierId) search.set('supplier_id', String(params.supplierId));
  if (params?.brandId) search.set('brand_id', String(params.brandId));
  if (params?.productId) search.set('product_id', String(params.productId));
  if (params?.startWeek) search.set('start_week', params.startWeek);
  if (params?.endWeek) search.set('end_week', params.endWeek);
  const query = search.toString();
  const res = await fetchWithAuth(
    `${API_BASE}/product_supplier_average${query ? `?${query}` : ''}`
  );
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
  const res = await fetchWithAuth(`${API_BASE}/graph_settings/${name}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ visible })
  });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}
