import { getCurrentTimestamp } from './utils/date';

export const API_BASE = import.meta.env.VITE_API_BASE || '';

export async function fetchApitest() {
  const res = await fetch(`${API_BASE}/`);
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

  const res = await fetch(`${API_BASE}/import`, {
    method: 'POST',
    body: formData
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
  }
  return res.json();
}

export async function fetchImportPreview(file: File, supplierId?: number) {
  const formData = new FormData();
  formData.append('file', file);
  if (supplierId !== undefined) {
    formData.append('supplier_id', String(supplierId));
  }

  const res = await fetch(`${API_BASE}/import_preview`, {
    method: 'POST',
    body: formData
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
  }
  return res.json();
}

export async function fetchProducts() {
  const res = await fetch(`${API_BASE}/products`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
  }
  return res.json();
}

export async function createProduct(data: any) {
  const res = await fetch(`${API_BASE}/products`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
  }
  return res.json();
}

export async function updateProduct(id: number, data: any) {
  const res = await fetch(`${API_BASE}/products/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
  }
  return res.json();
}

export async function bulkUpdateProducts(data: any[]) {
  const res = await fetch(`${API_BASE}/products/bulk_update`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
  }
  return res.json();
}

export async function deleteProduct(id: number) {
  const res = await fetch(`${API_BASE}/products/${id}`, {
    method: 'DELETE'
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
  }
  return res.json();
}


export async function fetchLastImport(id: number): Promise<{ import_date: string | null } | {}> {
  const res = await fetch(`${API_BASE}/last_import/${id}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
  }
  return res.json();
}

export async function verifyImport(id: number) {
  const res = await fetch(`${API_BASE}/verify_import/${id}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
  }
  return res.json();
}


export async function calculateProducts() {
  const res = await fetch(`${API_BASE}/calculate_products`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
  }
  return res.json();
}

export async function exportCalculations() {
  const res = await fetch(`${API_BASE}/export_calculates`);
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
  const res = await fetch(`${API_BASE}/references/suppliers`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
  }
  return res.json();
}

export async function refreshProduction() {
  const res = await fetch(`${API_BASE}/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
  }
  return res.json();
}


export async function refreshProductionByWeek(array_date: Array<Date>) {
  const res = await fetch(`${API_BASE}/refresh_week`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dates: array_date.map(date => date.toISOString()) })
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
  }
  return res.json();
}

export async function fetchProductCalculations() {
  const res = await fetch(`${API_BASE}/product_calculation`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
  }
  return res.json();
}

export async function fetchProductPriceSummary() {
  const res = await fetch(`${API_BASE}/product_price_summary`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
  }
  return res.json();
}

export async function fetchReferenceTable(table: string) {
  const res = await fetch(`${API_BASE}/references/${table}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
  }
  return res.json();
}

export async function updateReferenceItem(table: string, id: number, data: any) {
  const res = await fetch(`${API_BASE}/references/${table}/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
  }
  return res.json();
}

export async function createReferenceItem(table: string, data: any) {
  const res = await fetch(`${API_BASE}/references/${table}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
  }
  return res.json();
}



export async function deleteReferenceItem(table: string, id: number) {
  const res = await fetch(`${API_BASE}/references/${table}/${id}`, {
    method: 'DELETE'
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
  }
  return res.json();
}

export async function fetchBrands() {
  const res = await fetch(`${API_BASE}/references/brands`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
  }
  return res.json();
}


export async function fetchColors() {
  const res = await fetch(`${API_BASE}/references/colors`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
  }
  return res.json();
}

export async function fetchMemoryOptions() {
  const res = await fetch(`${API_BASE}/references/memory_options`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
  }
  return res.json();
}

export async function fetchDeviceTypes() {
  const res = await fetch(`${API_BASE}/references/device_types`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
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
  const res = await fetch(`${API_BASE}/price_stats${query ? `?${query}` : ''}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
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
  const res = await fetch(
    `${API_BASE}/brand_supplier_average${query ? `?${query}` : ''}`
  );
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
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
  const res = await fetch(
    `${API_BASE}/product_supplier_average${query ? `?${query}` : ''}`
  );
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
  }
  return res.json();
}

export async function fetchGraphSettings() {
  const res = await fetch(`${API_BASE}/graph_settings`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
  }
  return res.json();
}

export async function updateGraphSetting(name: string, visible: boolean) {
  const res = await fetch(`${API_BASE}/graph_settings/${name}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ visible })
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message);
  }
  return res.json();
}
