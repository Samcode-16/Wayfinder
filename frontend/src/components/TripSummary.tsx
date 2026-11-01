import { BedDouble, CalendarPlus, Info, Printer, Plane } from 'lucide-react';
import { money } from '../lib/format';
import type { TripData } from '../lib/types';

interface Props {
  trip: TripData;
  running: boolean;
  onPrint: () => void;
  onCalendar: () => void;
}

export default function TripSummary({ trip, running, onPrint, onCalendar }: Props) {
  const { plan, selection: sel, request: req } = trip;
  const flight = trip.flights.find((f) => f.id === sel?.flight_id);
  const hotel = trip.hotels.find((h) => h.id === sel?.hotel_id);
  const title = plan?.title ?? (req?.destination ? `Trip to ${req.destination}` : 'Planning your trip');
  const notes = trip.warnings;

  const scale = sel ? Math.max(sel.total, sel.budget ?? 0) || 1 : 1;
  const diff = sel?.budget != null ? sel.budget - sel.total : null;

  return (
    <header className="summary">
      <div className="summary__top">
        <div className="summary__text">
          <h2 className="summary__title">{title}</h2>
          {plan ? <p className="summary__lede">{plan.summary}</p> : <div className="skeleton skeleton--text" aria-hidden />}
        </div>
        {plan && (
          <div className="summary__actions">
            <button className="btn btn--ghost" onClick={onCalendar}><CalendarPlus size={16} aria-hidden /> <span className="btn__label">Add to calendar</span></button>
            <button className="btn btn--ghost" onClick={onPrint}><Printer size={16} aria-hidden /> <span className="btn__label">Save as PDF</span></button>
          </div>
        )}
      </div>

      {(flight || hotel) && (
        <p className="summary__picks">
          {flight && <span><Plane size={14} aria-hidden /> {flight.airline}, {flight.stops === 0 ? 'nonstop' : `${flight.stops} ${flight.stops === 1 ? 'stop' : 'stops'}`}</span>}
          {hotel && <span><BedDouble size={14} aria-hidden /> {hotel.name}</span>}
        </p>
      )}

      {sel ? (
        <div className="cost">
          <div
            className="cost__track"
            role="img"
            aria-label={`Estimated total ${money(sel.total, sel.currency)}: flights ${money(sel.flights_cost, sel.currency)}, stay ${money(sel.hotel_cost, sel.currency)}, food and activities ${money(sel.daily_cost, sel.currency)}`}
          >
            <span className="cost__seg cost__seg--flights" style={{ width: `${(sel.flights_cost / scale) * 100}%` }} />
            <span className="cost__seg cost__seg--stay" style={{ width: `${(sel.hotel_cost / scale) * 100}%` }} />
            <span className="cost__seg cost__seg--daily" style={{ width: `${(sel.daily_cost / scale) * 100}%` }} />
            {sel.budget != null && <span className="cost__budget" style={{ left: `${(sel.budget / scale) * 100}%` }} />}
          </div>
          <div className="cost__row">
            <div className="cost__total">
              <strong>{money(sel.total, sel.currency)}</strong> estimated total
              {diff != null && (
                <span className={diff >= 0 ? 'ok' : 'warn'}>, {money(Math.abs(diff), sel.currency)} {diff >= 0 ? 'under' : 'over'} budget</span>
              )}
            </div>
            <ul className="cost__legend">
              <li><i className="dot dot--flights" />Flights {money(sel.flights_cost, sel.currency)}</li>
              <li><i className="dot dot--stay" />Stay {money(sel.hotel_cost, sel.currency)}</li>
              <li><i className="dot dot--daily" />Food and activities {money(sel.daily_cost, sel.currency)}</li>
            </ul>
          </div>
        </div>
      ) : running ? (
        <div className="skeleton skeleton--bar" aria-hidden />
      ) : null}

      {(notes.length > 0 || (sel && sel.notes.length > 0)) && (
        <details className="notes">
          <summary><Info size={14} aria-hidden /> {notes.length + (sel?.notes.length ?? 0)} notes about this plan</summary>
          <ul>
            {sel?.notes.map((n) => <li key={n}>{n}</li>)}
            {notes.map((n) => <li key={n}>{n}</li>)}
          </ul>
        </details>
      )}
    </header>
  );
}
