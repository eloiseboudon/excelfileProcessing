import { getCurrentTimestamp } from './utils/date';

export const API_BASE = import.meta.env.VITE_API_BASE || '';


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
    throw new Error("Erreur lors de l'ajout du produit");
  }
  return res.json();
}

export async function fetchProducts() {
  const res = await fetch(`${API_BASE}/products`);
  if (!res.ok) {
    throw new Error('Erreur lors du chargement des produits');
  }
  return res.json();
}


export async function fetchLastImport(id: number): Promise<{ import_date: string | null } | {}> {
  const res = await fetch(`${API_BASE}/last_import/${id}`);
  if (!res.ok) {
    throw new Error('Erreur lors du chargement de la date d\'import');
  }
  return res.json();
}

export async function createProduct() {
  const res = await fetch(`${API_BASE}/populate_products`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    throw new Error("Erreur lors de l'ajout du produit");
  }
  return res.json();
}

export async function calculateProducts() {
  const res = await fetch(`${API_BASE}/calculate_products`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    throw new Error('Erreur lors du calcul des produits');
  }
  return res.json();
}

export async function exportCalculations() {
  const res = await fetch(`${API_BASE}/export_calculates`);
  if (!res.ok) {
    throw new Error('Erreur lors de la génération du fichier');
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

export async function fetchCalculationCount(): Promise<number> {
  const res = await fetch(`${API_BASE}/product_calculations/count`);
  if (!res.ok) {
    throw new Error('Erreur lors du chargement des calculs');
  }
  const data = await res.json();
  return data.count as number;
}


export async function fetchSuppliers() {
  const res = await fetch(`${API_BASE}/suppliers`);
  if (!res.ok) {
    throw new Error("Erreur lors du chargement des suppliers");
  }
  return res.json();
}

export async function refreshProduction() {
  const res = await fetch(`${API_BASE}/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    throw new Error('Erreur lors du rafraîchissement des données de prod');
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
    throw new Error('Erreur lors du rafraîchissement des données de prod');
  }
  return res.json();
}

export async function fetchProductCalculations() {
  const res = await fetch(`${API_BASE}/product_calculation`);
  if (!res.ok) {
    throw new Error('Erreur lors du chargement des calculs produits');
  }
  return res.json();
}

export async function fetchBrands() {
  const res = await fetch(`${API_BASE}/brands`);
  if (!res.ok) {
    throw new Error('Erreur lors du chargement des marques');
  }
  return res.json();
}

export async function fetchColors() {
  const res = await fetch(`${API_BASE}/colors`);
  if (!res.ok) {
    throw new Error('Erreur lors du chargement des couleurs');
  }
  return res.json();
}

export async function fetchMemoryOptions() {
  const res = await fetch(`${API_BASE}/memory_options`);
  if (!res.ok) {
    throw new Error('Erreur lors du chargement des mémoires');
  }
  return res.json();
}

export async function fetchDeviceTypes() {
  const res = await fetch(`${API_BASE}/device_types`);
  if (!res.ok) {
    throw new Error('Erreur lors du chargement des types');
  }
  return res.json();
}
