import { Check, ExternalLink, Plane } from 'lucide-react';
import { clock, duration, money } from '../lib/format';
import type { FlightOption, Selection } from '../lib/types';

export default function FlightsList({
  flights,
  selection,
  travelers,
  warnings = [],
  onSelectFlight,
  disabled,
}: {
  flights: FlightOption[];
  selection?: Selection | null;
  travelers: number;
  warnings?: string[];
  onSelectFlight?: (flightId: string) => void;
  disabled?: boolean;
}) {
  // Show cheaper flights to costly ones: sorted strictly by price ascending
  const sorted = [...flights].sort((a, b) => a.price - b.price);
  const demo = flights.some((f) => f.source === 'demo');

  const noteMessage = (() => {
    if (!demo) return null;
    const flightWarn = warnings.find(
      (w) => w.toLowerCase().includes('flight') || w.toLowerCase().includes('airport')
    );
    if (flightWarn) {
      if (flightWarn.includes('set SERPAPI_API_KEY')) {
        return 'Demo flights. Add a SerpAPI key for live prices. The link opens a real Google Flights search.';
      }
      return `${flightWarn} The link opens a real Google Flights search.`;
    }
    return 'Demo flights (live prices unavailable for this route). The link opens a real Google Flights search.';
  })();

  return (
    <div>
      {noteMessage && <p className="note">{noteMessage}</p>}
      <ul className="flights">
        {sorted.map((f) => {
          const first = f.legs[0];
          const last = f.legs[f.legs.length - 1];
          const picked = f.id === selection?.flight_id;
          const dep = clock(first?.departs);
          const arr = clock(last?.arrives);
          return (
            <li
              key={f.id}
              className={`flight ${picked ? 'is-picked' : 'is-selectable'}`}
              onClick={(e) => {
                if ((e.target as HTMLElement).closest('a, button')) return;
                if (!picked && !disabled) onSelectFlight?.(f.id);
              }}
            >
              <div className="flight__logo">
                {f.airline_logo ? <img src={f.airline_logo} alt="" width={36} height={36} loading="lazy" /> : <Plane size={18} aria-hidden />}
              </div>
              <div className="flight__main">
                <div className="flight__route">
                  {dep && arr ? `${dep} → ${arr}` : `${first?.from_airport} → ${last?.to_airport}`}
                  {picked && (
                    <span className="badge badge--picked">
                      <Check size={12} aria-hidden /> Picked for you
                    </span>
                  )}
                </div>
                <div className="flight__meta">
                  {f.airline}, {f.stops === 0 ? 'nonstop' : `${f.stops} ${f.stops === 1 ? 'stop' : 'stops'} via ${f.legs.slice(0, -1).map((l) => l.to_airport).join(', ')}`}, {duration(f.total_duration_min)}
                </div>
              </div>
              <div className="flight__price">
                <strong>{money(f.price, f.currency)}</strong>
                <span>
                  {travelers > 1
                    ? `total for ${travelers} travelers (${money(Math.round(f.price / travelers), f.currency)}/person)`
                    : 'round trip'}
                </span>
                <div className="flight__action">
                  {picked ? (
                    <span className="badge badge--selected">
                      <Check size={12} aria-hidden /> Selected
                    </span>
                  ) : (
                    <button
                      type="button"
                      className="btn btn--sm btn--primary"
                      disabled={disabled}
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectFlight?.(f.id);
                      }}
                      aria-label={`Select ${f.airline} flight`}
                    >
                      Select flight
                    </button>
                  )}
                </div>
                {f.link && (
                  <a href={f.link} target="_blank" rel="noreferrer" className="link" onClick={(e) => e.stopPropagation()}>
                    Google Flights <ExternalLink size={12} aria-hidden />
                  </a>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
