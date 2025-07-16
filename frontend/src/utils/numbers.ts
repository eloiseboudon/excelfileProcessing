export function parsePrice(value: any): number {
  if (value === undefined || value === null) return NaN;
  let str = String(value).trim();
  // remove spaces and currency symbols
  str = str.replace(/[^0-9.,-]/g, '');
  str = str.replace(/\s+/g, '');
  if (str.includes(',') && str.includes('.')) {
    if (str.lastIndexOf('.') < str.lastIndexOf(',')) {
      str = str.replace(/\./g, '').replace(',', '.');
    } else {
      str = str.replace(/,/g, '');
    }
  } else {
    str = str.replace(',', '.');
  }
  const num = parseFloat(str);
  return Number.isNaN(num) ? NaN : num;
}
