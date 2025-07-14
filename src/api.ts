import { getCurrentTimestamp } from './utils/date';

export const API_BASE = import.meta.env.VITE_API_BASE || '';

export async function fetchApitest() {
  const res = await fetch(`${API_BASE}/`);
  if (!res.ok) {
    throw new Error('Erreur lors du chargement des produits');
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

export async function createProduct(data: any) {
  const res = await fetch(`${API_BASE}/products`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    throw new Error("Erreur lors de la création du produit");
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
    throw new Error("Erreur lors de la mise à jour du produit");
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
    throw new Error("Erreur lors de la mise à jour des produits");
  }
  return res.json();
}

export async function deleteProduct(id: number) {
  const res = await fetch(`${API_BASE}/products/${id}`, {
    method: 'DELETE'
  });
  if (!res.ok) {
    throw new Error("Erreur lors de la suppression du produit");
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

export async function verifyImport(id: number) {
  const res = await fetch(`${API_BASE}/verify_import/${id}`);
  if (!res.ok) {
    throw new Error("Erreur lors de la vérification de l'import");
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

export async function fetchSuppliers() {
  const res = await fetch(`${API_BASE}/references/suppliers`);
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

export async function fetchReferenceTable(table: string) {
  const res = await fetch(`${API_BASE}/references/${table}`);
  if (!res.ok) {
    throw new Error('Erreur lors du chargement des références');
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
    throw new Error('Erreur lors de la mise à jour');
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
    throw new Error('Erreur lors de la création');
  }
  return res.json();
}



export async function deleteReferenceItem(table: string, id: number) {
  const res = await fetch(`${API_BASE}/references/${table}/${id}`, {
    method: 'DELETE'
  });
  if (!res.ok) {
    throw new Error('Erreur lors de la suppression');
  }
  return res.json();
}

export async function fetchBrands() {
  const res = await fetch(`${API_BASE}/references/brands`);
  if (!res.ok) {
    throw new Error('Erreur lors du chargement des marques');
  }
  return res.json();
}


export async function fetchColors() {
  const res = await fetch(`${API_BASE}/references/colors`);
  if (!res.ok) {
    throw new Error('Erreur lors du chargement des couleurs');
  }
  return res.json();
}

export async function fetchMemoryOptions() {
  const res = await fetch(`${API_BASE}/references/memory_options`);
  if (!res.ok) {
    throw new Error('Erreur lors du chargement des mémoires');
  }
  return res.json();
}

export async function fetchDeviceTypes() {
  const res = await fetch(`${API_BASE}/references/device_types`);
  if (!res.ok) {
    throw new Error('Erreur lors du chargement des types');
  }
  return res.json();
}
