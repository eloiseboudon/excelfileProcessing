import { describe, it, expect } from 'vitest';
import { getWeekYear, getCurrentWeekYear, getCurrentTimestamp } from '../date';

describe('getWeekYear', () => {
  it('returns correct ISO week for a known Monday', () => {
    // 2024-01-01 is a Monday in ISO week 1 of 2024
    const date = new Date(2024, 0, 1);
    expect(getWeekYear(date)).toBe('S1-2024');
  });

  it('returns correct week for mid-year date', () => {
    // 2024-06-15 is a Saturday in week 24
    const date = new Date(2024, 5, 15);
    expect(getWeekYear(date)).toBe('S24-2024');
  });

  it('handles year-end dates correctly', () => {
    // 2024-12-30 is a Monday in week 1 of 2025
    const date = new Date(2024, 11, 30);
    expect(getWeekYear(date)).toBe('S1-2025');
  });

  it('returns format S<week>-<year>', () => {
    const result = getWeekYear(new Date(2024, 2, 15));
    expect(result).toMatch(/^S\d{1,2}-\d{4}$/);
  });
});

describe('getCurrentWeekYear', () => {
  it('returns a string matching S<week>-<year> pattern', () => {
    const result = getCurrentWeekYear();
    expect(result).toMatch(/^S\d{1,2}-\d{4}$/);
  });
});

describe('getCurrentTimestamp', () => {
  it('returns a timestamp with format YYYYMMDD_HHMMSS', () => {
    const result = getCurrentTimestamp();
    expect(result).toMatch(/^\d{8}_\d{6}$/);
  });

  it('starts with current year', () => {
    const result = getCurrentTimestamp();
    const year = new Date().getFullYear().toString();
    expect(result.startsWith(year)).toBe(true);
  });
});
