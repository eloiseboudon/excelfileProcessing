export interface ProductRow {
  name: string;
  purchasePrice: number;
}

export interface FinalRow extends ProductRow {
  tcp: number;
  margin45: number;
  priceWithTcp: number;
  priceWithMargin: number;
  maxPrice: number;
}

export function sanitizeName(name: string): string {
  if (!name || typeof name !== 'string') return '';
  let cleaned = name;
  cleaned = cleaned.replace(/Region\s+(East|West)/gi, '');
  const replacements: Record<string, string> = {
    'Dual Sim': 'DS',
    'GB RAM ': '/',
    ' - ': ' ',
    'Tablet Apple': 'Apple',
    'Tablet Honor': 'Honor',
    'Tablet Samsung': 'Samsung',
    'Tablet Xiaomi': 'Xiaomi',
    'Watch Apple': 'Apple',
    'Watch Samsung': 'Samsung',
    'Watch Xiaomi': 'Xiaomi',
    'Watch Google': 'Google'
  };
  Object.entries(replacements).forEach(([k, v]) => {
    cleaned = cleaned.replace(new RegExp(k, 'g'), v);
  });
  return cleaned.replace(/\s+/g, ' ').trim();
}

export function isExcludedProduct(name: string): boolean {
  const terms = ['Mac', 'Backbone', 'Bulk', 'OH25B', 'Soundbar'];
  const lower = name.toLowerCase();
  return terms.some(t => lower.includes(t.toLowerCase()));
}

export function dedupeByLowestPrice(rows: ProductRow[]): ProductRow[] {
  const map = new Map<string, ProductRow>();
  rows.forEach(row => {
    const existing = map.get(row.name);
    if (!existing || row.purchasePrice < existing.purchasePrice) {
      map.set(row.name, row);
    }
  });
  return Array.from(map.values());
}

export function calculateRow(row: ProductRow): FinalRow {
  const price = row.purchasePrice;
  const nameUpper = row.name.toUpperCase();
  let tcp = 0;
  if (nameUpper.includes('32GB')) tcp = 10;
  else if (nameUpper.includes('64GB')) tcp = 12;
  else if (['128GB', '256GB', '512GB', '1TB'].some(s => nameUpper.includes(s))) tcp = 14;
  const margin45 = price * 0.045;
  const priceWithTcp = price + tcp + margin45;
  const thresholds = [15, 29, 49, 79, 99, 129, 149, 179, 209, 299, 499, 799, 999];
  const margins = [1.25, 1.22, 1.20, 1.18, 1.15, 1.11, 1.10, 1.09, 1.09, 1.08, 1.08, 1.07, 1.07, 1.06];
  let priceWithMargin = price;
  for (let i = 0; i < thresholds.length; i++) {
    if (price <= thresholds[i]) {
      priceWithMargin = price * margins[i];
      break;
    }
  }
  if (price > thresholds[thresholds.length - 1]) {
    priceWithMargin = price * 1.06;
  }
  const maxPrice = Math.ceil(Math.max(priceWithTcp, priceWithMargin));
  return {
    name: row.name,
    purchasePrice: Number(price.toFixed(2)),
    tcp: Number(tcp.toFixed(2)),
    margin45: Number(margin45.toFixed(2)),
    priceWithTcp: Number(priceWithTcp.toFixed(2)),
    priceWithMargin: Number(priceWithMargin.toFixed(2)),
    maxPrice
  };
}
