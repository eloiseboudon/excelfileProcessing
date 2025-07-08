export const API_BASE = 'http://localhost:5001';


export async function createImport(file: File) {
  const formData = new FormData();
  formData.append('file', file);

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
