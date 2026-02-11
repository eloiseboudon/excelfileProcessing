import { describe, it, expect } from 'vitest';
import { determineBrand, generatePricingHtml } from '../html';

describe('determineBrand', () => {
  it('detects Apple', () => {
    expect(determineBrand('Apple iPhone 15')).toBe('Apple');
  });

  it('detects Samsung', () => {
    expect(determineBrand('Samsung Galaxy S24')).toBe('Samsung');
  });

  it('detects Xiaomi', () => {
    expect(determineBrand('Xiaomi Redmi Note')).toBe('Xiaomi');
  });

  it('is case-insensitive', () => {
    expect(determineBrand('apple iphone 15 pro')).toBe('Apple');
  });

  it('returns "Autre" for unknown brands', () => {
    expect(determineBrand('OnePlus 12')).toBe('Autre');
  });

  it('detects JBL', () => {
    expect(determineBrand('JBL Flip 6')).toBe('JBL');
  });

  it('detects Google', () => {
    expect(determineBrand('Google Pixel 8')).toBe('Google');
  });

  it('detects Honor', () => {
    expect(determineBrand('Honor Magic 6')).toBe('Honor');
  });

  it('detects Nothing', () => {
    expect(determineBrand('Nothing Phone 2')).toBe('Nothing');
  });
});

describe('generatePricingHtml', () => {
  it('generates valid HTML with brand sections', () => {
    const productsByBrand = {
      'Apple': [{ name: 'iPhone 15', price: 999 }],
      'Samsung': [{ name: 'Galaxy S24', price: 899 }],
    };
    const sortedBrands = ['Apple', 'Samsung'];
    const allProducts = [
      { name: 'iPhone 15', price: 999 },
      { name: 'Galaxy S24', price: 899 },
    ];

    const html = generatePricingHtml(productsByBrand, sortedBrands, allProducts, 'S10-2024');

    expect(html).toContain('<!DOCTYPE html>');
    expect(html).toContain('S10-2024');
    expect(html).toContain('Apple');
    expect(html).toContain('Samsung');
    expect(html).toContain('iPhone 15');
    expect(html).toContain('999€');
    expect(html).toContain('2 produits disponibles');
  });

  it('shows correct product count per brand', () => {
    const productsByBrand = {
      'Apple': [
        { name: 'iPhone 15', price: 999 },
        { name: 'iPhone 14', price: 799 },
      ],
    };

    const html = generatePricingHtml(productsByBrand, ['Apple'], [], 'S1-2024');
    expect(html).toContain('Apple (2 produits)');
  });
});
