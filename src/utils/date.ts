export function getCurrentWeekYear(): string {
  const now = new Date();
  return getWeekYear(now);
}

export function getCurrentTimestamp(): string {
  const now = new Date();
  const pad = (n: number) => n.toString().padStart(2, '0');
  const year = now.getFullYear();
  const month = pad(now.getMonth() + 1);
  const day = pad(now.getDate());
  const hours = pad(now.getHours());
  const minutes = pad(now.getMinutes());
  const seconds = pad(now.getSeconds());
  return `${year}${month}${day}_${hours}${minutes}${seconds}`;
}

export function getWeekYear(today: Date): string {
  const date = new Date(today);
  const year = date.getFullYear();

  const startOfYear = new Date(year, 0, 1);
  const startOfYearDay = startOfYear.getDay() === 0 ? 7 : startOfYear.getDay();

  const pastDays = (date.getTime() - startOfYear.getTime()) / 86400000;
  const weekNumber = Math.ceil((pastDays + (8 - startOfYearDay)) / 7);

  return `S${weekNumber}-${year}`;
}

