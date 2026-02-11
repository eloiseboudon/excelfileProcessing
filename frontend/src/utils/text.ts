/**
 * Normalize text by removing diacritics and lowercasing for search/comparison.
 */
export function normalizeText(value: string): string {
  return value
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase();
}
