import { useCallback, useEffect, useReducer, useRef, useState } from 'react';
import { getHealth, streamChat, type Health } from './api';
import type { Interrupt, TripData } from './types';

export const STEP_IDS = ['parse', 'prepare', 'flights', 'hotels', 'activities', 'weather', 'optimize', 'compose'] as const;
export type StepId = (typeof STEP_IDS)[number];
export interface StepState {
  status: 'idle' | 'running' | 'done';
  detail?: string | null;
}
export type Steps = Record<StepId, StepState>;
export type RunMode = 'full' | 'revise';

export type ChatItem =
  | { id: string; type: 'user'; text: string }
  | { id: string; type: 'assistant'; text: string }
  | { id: string; type: 'timeline'; mode: RunMode; steps: Steps }
  | { id: string; type: 'approval' };

export interface AgentState {
  items: ChatItem[];
  trip: TripData;
  interrupt: Interrupt | null;
  running: boolean;
  approved: boolean;
  error: string | null;
}

export type Action =
  | { type: 'user'; text: string }
  | { type: 'assistant'; text: string }
  | { type: 'run_start'; mode: RunMode | 'silent' }
  | { type: 'step'; node: string; status: 'start' | 'done'; detail?: string | null }
  | { type: 'update'; data: Record<string, unknown> }
  | { type: 'interrupt'; value: Interrupt }
  | { type: 'approved' }
  | { type: 'error'; message: string }
  | { type: 'run_end' }
  | { type: 'reset' };

export const emptyTrip = (): TripData => ({ flights: [], hotels: [], activities: [], weather: [], warnings: [] });
export const initialState: AgentState = {
  items: [],
  trip: emptyTrip(),
  interrupt: null,
  running: false,
  approved: false,
  error: null,
};

const idleSteps = (): Steps =>
  Object.fromEntries(STEP_IDS.map((id) => [id, { status: 'idle' }])) as Steps;

let counter = 0;
const uid = () => `i${++counter}`;

export function reducer(state: AgentState, a: Action): AgentState {
  switch (a.type) {
    case 'user':
      return { ...state, items: [...state.items, { id: uid(), type: 'user', text: a.text }] };
    case 'assistant':
      return { ...state, items: [...state.items, { id: uid(), type: 'assistant', text: a.text }] };
    case 'run_start': {
      const base = { ...state, running: true, error: null, interrupt: null, approved: false };
      if (a.mode === 'silent') return base;
      const trip = a.mode === 'full' ? { ...emptyTrip(), request: state.trip.request } : state.trip;
      return {
        ...base,
        trip,
        items: [...state.items, { id: uid(), type: 'timeline', mode: a.mode, steps: idleSteps() }],
      };
    }
    case 'step': {
      const idx = state.items.map((i) => i.type).lastIndexOf('timeline');
      const item = state.items[idx];
      if (!item || item.type !== 'timeline' || !(STEP_IDS as readonly string[]).includes(a.node)) return state;
      const steps = {
        ...item.steps,
        [a.node]: { status: a.status === 'start' ? 'running' : 'done', detail: a.detail },
      } as Steps;
      const items = state.items.slice();
      items[idx] = { ...item, steps };
      return { ...state, items };
    }
    case 'update': {
      const { warnings, ...rest } = a.data as { warnings?: string[] } & Partial<TripData>;
      const merged = [...state.trip.warnings];
      for (const w of warnings ?? []) if (!merged.includes(w)) merged.push(w);
      return { ...state, trip: { ...state.trip, ...rest, warnings: merged } };
    }
    case 'interrupt': {
      const v = a.value;
      const text = v.type === 'clarify' ? v.questions.join('\n') : v.plan.summary;
      const items: ChatItem[] = [...state.items, { id: uid(), type: 'assistant', text }];
      if (v.type === 'approval') items.push({ id: uid(), type: 'approval' });
      return { ...state, interrupt: v, items };
    }
    case 'approved':
      return { ...state, approved: true, interrupt: null };
    case 'error':
      return { ...state, error: a.message };
    case 'run_end':
      return { ...state, running: false };
    case 'reset':
      return initialState;
  }
}

export function useTripAgent() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState(false);
  const stateRef = useRef(state);
  stateRef.current = state;
  const thread = useRef<string | null>(null);
  const abort = useRef<AbortController | null>(null);

  useEffect(() => {
    const ac = new AbortController();
    getHealth(ac.signal).then(setHealth).catch(() => !ac.signal.aborted && setHealthError(true));
    return () => ac.abort();
  }, []);

  const run = useCallback(async (body: { message?: string; resume?: unknown }, mode: RunMode | 'silent') => {
    dispatch({ type: 'run_start', mode });
    const ac = new AbortController();
    abort.current = ac;
    try {
      for await (const ev of streamChat({ thread_id: thread.current ?? undefined, ...body }, ac.signal)) {
        if (ev.event === 'thread') thread.current = ev.data.thread_id;
        else if (ev.event === 'step') dispatch({ type: 'step', node: ev.data.node, status: ev.data.status, detail: ev.data.detail });
        else if (ev.event === 'update') dispatch({ type: 'update', data: ev.data.data });
        else if (ev.event === 'interrupt') dispatch({ type: 'interrupt', value: ev.data });
        else if (ev.event === 'error') dispatch({ type: 'error', message: ev.data.message });
      }
    } catch (e) {
      if (!ac.signal.aborted) dispatch({ type: 'error', message: e instanceof Error ? e.message : 'Something went wrong.' });
    } finally {
      dispatch({ type: 'run_end' });
    }
  }, []);

  /** One entry point for the composer: routes text to a new request, a clarification, or plan feedback. */
  const submit = useCallback(
    (text: string) => {
      const t = text.trim();
      if (!t || stateRef.current.running) return;
      const pending = stateRef.current.interrupt;
      dispatch({ type: 'user', text: t });
      if (pending?.type === 'approval') run({ resume: { approved: false, feedback: t } }, 'revise');
      else if (pending?.type === 'clarify') run({ resume: t }, 'full');
      else run({ message: t }, 'full');
    },
    [run],
  );

  const approve = useCallback(() => {
    if (stateRef.current.running) return;
    dispatch({ type: 'approved' });
    dispatch({ type: 'assistant', text: 'Approved. You can add the trip to your calendar or save it as a PDF from the summary.' });
    run({ resume: { approved: true } }, 'silent');
  }, [run]);

  const reset = useCallback(() => {
    abort.current?.abort();
    thread.current = null;
    dispatch({ type: 'reset' });
  }, []);

  return { state, health, healthError, submit, approve, reset };
}
