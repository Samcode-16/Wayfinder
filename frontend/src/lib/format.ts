export const money = (n: number, currency: string) => {
  try {
    return new Intl.NumberFormat(undefined, { style: 'currency', currency, maximumFractionDigits: 0 }).format(n);
  } catch {
    return `${Math.round(n)} ${currency}`;
  }
};

/** Parse YYYY-MM-DD as a *local* date (new Date('2026-11-01') would shift by timezone). */
export const parseDay = (s: string) => {
  const [y, m, d] = s.slice(0, 10).split('-').map(Number);
  return new Date(y, m - 1, d);
};

export const fmtDay = (s: string, opts: Intl.DateTimeFormatOptions) => parseDay(s).toLocaleDateString(undefined, opts);

export function dateRange(a: string, b: string) {
  const A = parseDay(a);
  const B = parseDay(b);
  const month = (d: Date) => d.toLocaleDateString(undefined, { month: 'short' });
  return A.getMonth() === B.getMonth()
    ? `${A.getDate()}–${B.getDate()} ${month(B)}`
    : `${A.getDate()} ${month(A)} – ${B.getDate()} ${month(B)}`;
}

export const duration = (min: number) => `${Math.floor(min / 60)}h${min % 60 ? ` ${min % 60}m` : ''}`;

export const clock = (s?: string | null) => s?.match(/(\d{1,2}:\d{2})/)?.[1] ?? null;
