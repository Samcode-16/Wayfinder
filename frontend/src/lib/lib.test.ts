import { describe, expect, it } from 'vitest';
import { initialState, reducer, type AgentState } from './agent';
import { buildICS } from './ics';
import { parseBlock, parseSSE } from './sse';
import type { TripData } from './types';

function streamOf(...chunks: string[]) {
  const enc = new TextEncoder();
  return new ReadableStream<Uint8Array>({
    start(c) {
      chunks.forEach((x) => c.enqueue(enc.encode(x)));
      c.close();
    },
  });
}

describe('sse', () => {
  it('parses events split across chunk boundaries', async () => {
    const out = [];
    for await (const e of parseSSE(streamOf('event: step\ndata: {"no', 'de":"flights"}\n\nevent: done\r\ndata: {}\r\n\r\n'))) out.push(e);
    expect(out).toEqual([
      { event: 'step', data: { node: 'flights' } },
      { event: 'done', data: {} },
    ]);
  });
  it('ignores malformed blocks', () => {
    expect(parseBlock('event: x\ndata: {oops')).toBeNull();
    expect(parseBlock(': keepalive')).toBeNull();
  });
});

describe('reducer', () => {
  const started = reducer(initialState, { type: 'run_start', mode: 'full' });

  it('tracks parallel steps on the latest timeline', () => {
    let s = reducer(started, { type: 'step', node: 'flights', status: 'start' });
    s = reducer(s, { type: 'step', node: 'hotels', status: 'start' });
    s = reducer(s, { type: 'step', node: 'flights', status: 'done', detail: '6 options' });
    const t = s.items.find((i) => i.type === 'timeline');
    expect(t && t.type === 'timeline' && [t.steps.flights, t.steps.hotels]).toEqual([
      { status: 'done', detail: '6 options' },
      { status: 'running', detail: undefined },
    ]);
  });

  it('merges updates and de-duplicates warnings', () => {
    let s = reducer(started, { type: 'update', data: { flights: [{ id: 'a' }], warnings: ['demo'] } });
    s = reducer(s, { type: 'update', data: { hotels: [{ id: 'h' }], warnings: ['demo', 'fx'] } });
    expect(s.trip.warnings).toEqual(['demo', 'fx']);
    expect(s.trip.flights).toHaveLength(1);
    expect(s.trip.hotels).toHaveLength(1);
  });

  it('turns interrupts into assistant messages (and an approval card)', () => {
    const clarify = reducer(started, {
      type: 'interrupt',
      value: { type: 'clarify', missing: ['dates'], questions: ['When?'], request: { travelers: 1, currency: 'USD', interests: [] } },
    });
    expect(clarify.items.at(-1)).toMatchObject({ type: 'assistant', text: 'When?' });
    const approval = reducer(started, {
      type: 'interrupt',
      value: { type: 'approval', selection: null, plan: { title: 't', summary: 'sum', days: [], tips: [] } },
    });
    expect(approval.items.map((i) => i.type).slice(-2)).toEqual(['assistant', 'approval']);
  });

  it('a new full run clears old results but a revise keeps them', () => {
    const withData: AgentState = { ...started, trip: { ...started.trip, flights: [{ id: 'x' } as never] } };
    expect(reducer(withData, { type: 'run_start', mode: 'full' }).trip.flights).toHaveLength(0);
    expect(reducer(withData, { type: 'run_start', mode: 'revise' }).trip.flights).toHaveLength(1);
  });
});

describe('ics', () => {
  it('builds a valid calendar with one event per item plus the trip', () => {
    const trip: TripData = {
      flights: [], hotels: [], activities: [], weather: [], warnings: [],
      plan: {
        title: 'Amsterdam, with canals; museums', summary: '', tips: [],
        days: [{ date: '2026-12-01', theme: 'x', items: [
          { time_of_day: 'morning', title: 'Rijksmuseum', description: 'Art, lots of it', place: 'Rijksmuseum' },
          { time_of_day: 'evening', title: 'Dinner', description: 'x' },
        ] }],
      },
    };
    const ics = buildICS(trip, new Date('2026-11-01T10:00:00Z'));
    expect(ics.match(/BEGIN:VEVENT/g)).toHaveLength(3);
    expect(ics).toContain('DTSTART:20261201T090000');
    expect(ics).toContain('DTEND;VALUE=DATE:20261202');
    expect(ics).toContain('SUMMARY:Amsterdam\\, with canals\\; museums');
    expect(ics.endsWith('END:VCALENDAR\r\n')).toBe(true);
  });
});
