export const API_BASE = 'http://localhost:5001';


export async function createImport(file: File, fournisseurId?: number) {
  const formData = new FormData();
  formData.append('file', file);
  if (fournisseurId !== undefined) {
    formData.append('id_fournisseur', String(fournisseurId));
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
  return res.blob();
}

export async function fetchFournisseurs() {
  const res = await fetch(`${API_BASE}/fournisseurs`);
  if (!res.ok) {
    throw new Error("Erreur lors du chargement des fournisseurs");
  }
  return res.json();
}
