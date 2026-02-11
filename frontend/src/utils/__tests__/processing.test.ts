import { describe, it, expect } from 'vitest';
import {
  sanitizeName,
  isExcludedProduct,
  dedupeByLowestPrice,
  calculateRow,
  PRICE_THRESHOLDS,
  PRICE_MULTIPLIERS,
  COMMISSION_RATE,
} from '../processing';

describe('sanitizeName', () => {
  it('replaces "Dual Sim" with "DS"', () => {
    expect(sanitizeName('iPhone 15 Dual Sim')).toBe('iPhone 15 DS');
  });

  it('replaces "GB RAM " with "/"', () => {
    expect(sanitizeName('Samsung 8GB RAM 256GB')).toBe('Samsung 8/256GB');
  });

  it('removes Region East/West', () => {
    expect(sanitizeName('iPhone Region East 128GB')).toBe('iPhone 128GB');
  });

  it('returns empty string for empty input', () => {
    expect(sanitizeName('')).toBe('');
  });

  it('returns empty string for null-ish input', () => {
    expect(sanitizeName(null as any)).toBe('');
  });

  it('collapses multiple spaces', () => {
    expect(sanitizeName('Samsung  Galaxy   S24')).toBe('Samsung Galaxy S24');
  });

  it('replaces Tablet prefixes', () => {
    expect(sanitizeName('Tablet Apple iPad')).toBe('Apple iPad');
  });
});

describe('isExcludedProduct', () => {
  it('excludes products containing "Mac"', () => {
    expect(isExcludedProduct('MacBook Pro')).toBe(true);
  });

  it('excludes products containing "Bulk"', () => {
    expect(isExcludedProduct('iPhone Bulk 128GB')).toBe(true);
  });

  it('excludes products containing "Backbone"', () => {
    expect(isExcludedProduct('Backbone One')).toBe(true);
  });

  it('does not exclude regular products', () => {
    expect(isExcludedProduct('Samsung Galaxy S24')).toBe(false);
  });

  it('is case-insensitive', () => {
    expect(isExcludedProduct('macbook air')).toBe(true);
  });
});

describe('dedupeByLowestPrice', () => {
  it('keeps the row with the lowest price for duplicate names', () => {
    const rows = [
      { name: 'iPhone 15', purchasePrice: 800 },
      { name: 'iPhone 15', purchasePrice: 750 },
      { name: 'Galaxy S24', purchasePrice: 600 },
    ];
    const result = dedupeByLowestPrice(rows);
    expect(result).toHaveLength(2);
    const iphone = result.find(r => r.name === 'iPhone 15');
    expect(iphone?.purchasePrice).toBe(750);
  });

  it('returns empty array for empty input', () => {
    expect(dedupeByLowestPrice([])).toEqual([]);
  });

  it('keeps all unique names', () => {
    const rows = [
      { name: 'A', purchasePrice: 10 },
      { name: 'B', purchasePrice: 20 },
    ];
    expect(dedupeByLowestPrice(rows)).toHaveLength(2);
  });
});

describe('calculateRow', () => {
  it('calculates margin45 as price * commission rate', () => {
    const result = calculateRow({ name: 'Test', purchasePrice: 100 });
    expect(result.margin45).toBe(+(100 * COMMISSION_RATE).toFixed(2));
  });

  it('assigns tcp=10 for 32GB products', () => {
    const result = calculateRow({ name: 'iPhone 32GB', purchasePrice: 100 });
    expect(result.tcp).toBe(10);
  });

  it('assigns tcp=12 for 64GB products', () => {
    const result = calculateRow({ name: 'Samsung 64GB', purchasePrice: 100 });
    expect(result.tcp).toBe(12);
  });

  it('assigns tcp=14 for 128GB products', () => {
    const result = calculateRow({ name: 'iPhone 128GB', purchasePrice: 100 });
    expect(result.tcp).toBe(14);
  });

  it('assigns tcp=14 for 1TB products', () => {
    const result = calculateRow({ name: 'iPad 1TB', purchasePrice: 100 });
    expect(result.tcp).toBe(14);
  });

  it('assigns tcp=0 for products without storage info', () => {
    const result = calculateRow({ name: 'AirPods', purchasePrice: 100 });
    expect(result.tcp).toBe(0);
  });

  it('maxPrice is ceiling of max(priceWithTcp, priceWithMargin)', () => {
    const result = calculateRow({ name: 'Test 128GB', purchasePrice: 50 });
    expect(result.maxPrice).toBe(Math.ceil(Math.max(result.priceWithTcp, result.priceWithMargin)));
  });

  it('uses correct multiplier for price in first threshold', () => {
    const result = calculateRow({ name: 'Test', purchasePrice: 10 });
    expect(result.priceWithMargin).toBe(+(10 * PRICE_MULTIPLIERS[0]).toFixed(2));
  });

  it('uses last multiplier for price above all thresholds', () => {
    const result = calculateRow({ name: 'Test', purchasePrice: 1500 });
    expect(result.priceWithMargin).toBe(+(1500 * PRICE_MULTIPLIERS[PRICE_MULTIPLIERS.length - 1]).toFixed(2));
  });
});

describe('constants', () => {
  it('COMMISSION_RATE is 4.5%', () => {
    expect(COMMISSION_RATE).toBe(0.045);
  });

  it('PRICE_THRESHOLDS has 13 entries', () => {
    expect(PRICE_THRESHOLDS).toHaveLength(13);
  });

  it('PRICE_MULTIPLIERS has 14 entries', () => {
    expect(PRICE_MULTIPLIERS).toHaveLength(14);
  });
});
