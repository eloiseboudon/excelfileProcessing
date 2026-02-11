import { describe, it, expect } from 'vitest';
import { normalizeText } from '../text';

describe('normalizeText', () => {
  it('lowercases text', () => {
    expect(normalizeText('HELLO')).toBe('hello');
  });

  it('removes accents from French characters', () => {
    expect(normalizeText('éàü')).toBe('eau');
  });

  it('removes accent from e-aigu', () => {
    expect(normalizeText('Résumé')).toBe('resume');
  });

  it('handles mixed case and accents', () => {
    expect(normalizeText('Crème Brûlée')).toBe('creme brulee');
  });

  it('returns empty string for empty input', () => {
    expect(normalizeText('')).toBe('');
  });

  it('preserves numbers and spaces', () => {
    expect(normalizeText('iPhone 15 Pro')).toBe('iphone 15 pro');
  });

  it('removes cedilla', () => {
    expect(normalizeText('Français')).toBe('francais');
  });
});
