import { parseDay } from './format';
import type { TripData } from './types';

const START_HOUR = { morning: 9, afternoon: 14, evening: 19 } as const;
const pad = (n: number) => String(n).padStart(2, '0');
const local = (d: Date, h: number) => `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}T${pad(h)}0000`;
const dateOnly = (d: Date) => `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}`;
const esc = (s: string) => s.replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\r?\n/g, '\\n');

/** RFC 5545 line folding at 75 characters. */
const fold = (line: string) => (line.match(/.{1,74}/g) ?? ['']).join('\r\n ');

export function buildICS(trip: TripData, now = new Date()): string {
  const plan = trip.plan;
  if (!plan) return '';
  const stamp = now.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
  const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Wayfinder//Trip planner//EN', 'CALSCALE:GREGORIAN'];
  let n = 0;
  const event = (props: string[]) => {
    lines.push('BEGIN:VEVENT', `UID:wayfinder-${stamp}-${n++}@local`, `DTSTAMP:${stamp}`, ...props, 'END:VEVENT');
  };

  const first = plan.days[0]?.date;
  const last = plan.days[plan.days.length - 1]?.date;
  if (first && last) {
    const end = parseDay(last);
    end.setDate(end.getDate() + 1); // all-day DTEND is exclusive
    event([`DTSTART;VALUE=DATE:${dateOnly(parseDay(first))}`, `DTEND;VALUE=DATE:${dateOnly(end)}`, `SUMMARY:${esc(plan.title)}`]);
  }
  for (const day of plan.days) {
    const d = parseDay(day.date);
    for (const it of day.items) {
      const h = START_HOUR[it.time_of_day];
      event([
        `DTSTART:${local(d, h)}`,
        `DTEND:${local(d, h + 2)}`,
        `SUMMARY:${esc(it.title)}`,
        `DESCRIPTION:${esc(it.description)}`,
        ...(it.place ? [`LOCATION:${esc(it.place)}`] : []),
      ]);
    }
  }
  lines.push('END:VCALENDAR');
  return lines.map(fold).join('\r\n') + '\r\n';
}

export function downloadICS(trip: TripData) {
  const blob = new Blob([buildICS(trip)], { type: 'text/calendar;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${(trip.plan?.title ?? 'trip').toLowerCase().replace(/[^a-z0-9]+/g, '-')}.ics`;
  a.click();
  URL.revokeObjectURL(url);
}
