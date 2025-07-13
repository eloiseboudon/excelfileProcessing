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
  // Calculate ISO week number with Monday as the first day of the week
  const date = new Date(Date.UTC(today.getFullYear(), today.getMonth(), today.getDate()));

  // getUTCDay returns 0 for Sunday which should be treated as 7 in ISO format
  const dayOfWeek = date.getUTCDay() || 7;

  // Adjust to the nearest Thursday to correctly determine the ISO week/year
  date.setUTCDate(date.getUTCDate() + 4 - dayOfWeek);

  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  const weekNumber = Math.ceil(((date.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);

  return `S${weekNumber}-${date.getUTCFullYear()}`;
}

