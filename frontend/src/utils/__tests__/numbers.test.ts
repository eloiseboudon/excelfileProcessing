import { describe, it, expect } from 'vitest';
import { parsePrice } from '../numbers';

describe('parsePrice', () => {
  it('parses simple integer', () => {
    expect(parsePrice('100')).toBe(100);
  });

  it('parses decimal with dot', () => {
    expect(parsePrice('99.99')).toBe(99.99);
  });

  it('parses European comma format', () => {
    expect(parsePrice('99,99')).toBe(99.99);
  });

  it('parses European format with dot as thousand separator', () => {
    // 1.234,56 -> 1234.56
    expect(parsePrice('1.234,56')).toBe(1234.56);
  });

  it('parses US format with comma as thousand separator', () => {
    // 1,234.56 -> 1234.56
    expect(parsePrice('1,234.56')).toBe(1234.56);
  });

  it('strips euro sign', () => {
    expect(parsePrice('99,99€')).toBe(99.99);
  });

  it('strips dollar sign', () => {
    expect(parsePrice('$99.99')).toBe(99.99);
  });

  it('strips spaces', () => {
    expect(parsePrice(' 100 ')).toBe(100);
  });

  it('returns NaN for null', () => {
    expect(parsePrice(null)).toBeNaN();
  });

  it('returns NaN for undefined', () => {
    expect(parsePrice(undefined)).toBeNaN();
  });

  it('returns NaN for empty string', () => {
    expect(parsePrice('')).toBeNaN();
  });

  it('returns NaN for non-numeric string', () => {
    expect(parsePrice('abc')).toBeNaN();
  });

  it('parses number input directly', () => {
    expect(parsePrice(42.5)).toBe(42.5);
  });

  it('parses zero', () => {
    expect(parsePrice('0')).toBe(0);
  });
});
