import { useCallback, useEffect, useReducer, useRef, useState } from 'react';
import { getHealth, sendItineraryEmail, streamChat, type Health } from './api';
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
  | { id: string; type: 'approval' }
  | { id: string; type: 'email_prompt' };

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
  | { type: 'prompt_email' }
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
      let text = '';
      if (v.type === 'clarify') {
        text = v.questions.join('\n');
      } else if (v.type === 'approval') {
        text = v.plan.summary;
      } else if (v.type === 'ask_email' || v.type === 'email_confirmation') {
        text = v.message;
      }
      const items: ChatItem[] = [...state.items, { id: uid(), type: 'assistant', text }];
      if (v.type === 'approval') items.push({ id: uid(), type: 'approval' });
      if (v.type === 'ask_email') items.push({ id: uid(), type: 'email_prompt' });
      return { ...state, interrupt: v, items };
    }
    case 'approved': {
      const items: ChatItem[] = [
        ...state.items,
        {
          id: uid(),
          type: 'assistant',
          text: 'Approved! You can add this trip to your calendar or save it as a PDF. Would you also like me to email you the complete itinerary?',
        },
        { id: uid(), type: 'email_prompt' },
      ];
      return { ...state, approved: true, interrupt: null, items };
    }
    case 'prompt_email': {
      const hasPrompt = state.items.some((i) => i.type === 'email_prompt');
      const items: ChatItem[] = hasPrompt
        ? state.items
        : [
            ...state.items,
            { id: uid(), type: 'assistant', text: 'Where should I email your itinerary?' },
            { id: uid(), type: 'email_prompt' },
          ];
      return { ...state, items };
    }
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

  const sendEmail = useCallback(async (email: string) => {
    const cleanEmail = email.trim();
    if (!cleanEmail) return;

    dispatch({ type: 'user', text: `Please email my itinerary to ${cleanEmail}` });
    const { plan, request, selection, flights, hotels } = stateRef.current.trip;

    try {
      const res = await sendItineraryEmail({
        email: cleanEmail,
        thread_id: thread.current ?? undefined,
        plan,
        request,
        selection,
        flights,
        hotels,
      });
      dispatch({
        type: 'assistant',
        text: `✉️ ${res.message}`,
      });
    } catch (e) {
      dispatch({
        type: 'assistant',
        text: `Sorry, I couldn't send the email: ${e instanceof Error ? e.message : 'Unknown error'}`,
      });
    }
  }, []);

  const promptEmail = useCallback(() => {
    dispatch({ type: 'prompt_email' });
  }, []);

  /** One entry point for the composer: routes text to a new request, a clarification, or plan feedback. */
  const submit = useCallback(
    (text: string) => {
      const t = text.trim();
      if (!t || stateRef.current.running) return;
      const pending = stateRef.current.interrupt;

      // Handle user typing email address when plan is ready
      const emailMatch = t.match(/[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+/);
      if (emailMatch && stateRef.current.trip.plan && (stateRef.current.approved || pending == null || pending.type === 'ask_email')) {
        sendEmail(emailMatch[0]);
        return;
      }

      dispatch({ type: 'user', text: t });
      if (pending?.type === 'approval') run({ resume: { approved: false, feedback: t } }, 'revise');
      else if (pending?.type === 'clarify') run({ resume: t }, 'full');
      else run({ message: t }, 'full');
    },
    [run, sendEmail],
  );

  const approve = useCallback(() => {
    if (stateRef.current.running) return;
    dispatch({ type: 'approved' });
    run({ resume: { approved: true } }, 'silent');
  }, [run]);

  const selectFlight = useCallback(
    (flightId: string) => {
      if (stateRef.current.running) return;
      const current = stateRef.current.trip.selection;
      if (current?.flight_id === flightId) return;

      const f = stateRef.current.trip.flights.find((flight) => flight.id === flightId);
      const label = f ? `${f.airline} flight` : 'flight';
      dispatch({ type: 'user', text: `Selected ${label}` });

      // Optimistic update of local selection
      if (current && f) {
        const travelers = stateRef.current.trip.request?.travelers ?? 1;
        const newFlightCost = f.price * travelers;
        const newTotal = newFlightCost + current.hotel_cost + current.daily_cost;
        const budget = current.budget;
        dispatch({
          type: 'update',
          data: {
            selection: {
              ...current,
              flight_id: flightId,
              flights_cost: Math.round(newFlightCost),
              total: Math.round(newTotal),
              within_budget: budget == null || newTotal <= budget,
            },
          },
        });
      }

      run({ resume: { flight_id: flightId } }, 'revise');
    },
    [run],
  );

  const selectHotel = useCallback(
    (hotelId: string) => {
      if (stateRef.current.running) return;
      const current = stateRef.current.trip.selection;
      if (current?.hotel_id === hotelId) return;

      const h = stateRef.current.trip.hotels.find((hotel) => hotel.id === hotelId);
      const label = h ? h.name : 'hotel';
      dispatch({ type: 'user', text: `Selected stay: ${label}` });

      // Optimistic update of local selection
      if (current && h) {
        const req = stateRef.current.trip.request;
        const travelers = req?.travelers ?? 1;
        const nights =
          req?.start_date && req.end_date
            ? Math.max(1, Math.round((+new Date(req.end_date) - +new Date(req.start_date)) / 86400000))
            : 1;
        const rooms = Math.ceil(travelers / 2);
        const newHotelCost = h.price_per_night * nights * rooms;
        const newTotal = current.flights_cost + newHotelCost + current.daily_cost;
        const budget = current.budget;
        dispatch({
          type: 'update',
          data: {
            selection: {
              ...current,
              hotel_id: hotelId,
              hotel_cost: Math.round(newHotelCost),
              total: Math.round(newTotal),
              within_budget: budget == null || newTotal <= budget,
            },
          },
        });
      }

      run({ resume: { hotel_id: hotelId } }, 'revise');
    },
    [run],
  );

  const reset = useCallback(() => {
    abort.current?.abort();
    thread.current = null;
    dispatch({ type: 'reset' });
  }, []);

  return { state, health, healthError, submit, approve, selectFlight, selectHotel, promptEmail, sendEmail, reset };
}
