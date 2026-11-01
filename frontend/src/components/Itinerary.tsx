import { MapPin } from 'lucide-react';
import { lazy, Suspense, useMemo, useState } from 'react';
import type { Theme } from '../hooks/useTheme';
import { fmtDay, money } from '../lib/format';
import type { DayWeather, HotelOption, ItineraryItem, TripPlan } from '../lib/types';
import type { Pin } from './TripMap';
import WeatherIcon from './WeatherIcon';

// maplibre-gl is ~800 kB, so it loads only when an itinerary is shown.
const TripMap = lazy(() => import('./TripMap'));

export const DAY_COLORS = ['#D6284A', '#0B7A62', '#3B6FE0', '#A65F00', '#8A4FD0', '#08799A', '#C23B7A'];
const WHEN = { morning: 'Morning', afternoon: 'Afternoon', evening: 'Evening' } as const;

interface Props {
  plan: TripPlan;
  weather: DayWeather[];
  hotel?: HotelOption;
  currency: string;
  theme: Theme;
  geoapifyApiKey?: string | null;
}

const hasCoords = (i: ItineraryItem): i is ItineraryItem & { lat: number; lon: number } => i.lat != null && i.lon != null;

export default function Itinerary({ plan, weather, hotel, currency, theme, geoapifyApiKey }: Props) {
  const [day, setDay] = useState(0);
  const [focus, setFocus] = useState<{ lat: number; lon: number } | null>(null);
  const current = plan.days[Math.min(day, plan.days.length - 1)];
  const color = DAY_COLORS[day % DAY_COLORS.length];

  const pins = useMemo<Pin[]>(() => {
    if (!current) return [];
    const stops = current.items.filter(hasCoords).map<Pin>((it, i) => ({
      lat: it.lat, lon: it.lon, label: String(i + 1), title: it.place ?? it.title, color, kind: 'stop',
    }));
    if (hotel?.lat != null && hotel.lon != null) {
      stops.push({ lat: hotel.lat, lon: hotel.lon, label: 'H', title: `${hotel.name} (your stay)`, color: '#0B7A62', kind: 'hotel' });
    }
    return stops;
  }, [current, hotel, color]);

  const anyCoords = plan.days.some((d) => d.items.some(hasCoords));

  return (
    <div className="itin">
      <div className="itin__main">
        <div className="daytabs" role="tablist" aria-label="Days">
          {plan.days.map((d, i) => (
            <button
              key={d.date + i}
              role="tab"
              aria-selected={i === day}
              className="daytab"
              style={{ '--day': DAY_COLORS[i % DAY_COLORS.length] } as React.CSSProperties}
              onClick={() => { setDay(i); setFocus(null); }}
            >
              <span className="daytab__n">Day {i + 1}</span>
              <span className="daytab__d">{fmtDay(d.date, { weekday: 'short', day: 'numeric' })}</span>
            </button>
          ))}
        </div>

        {plan.days.map((d, di) => {
          const w = weather.find((x) => x.date === d.date);
          let n = 0;
          return (
            <section key={d.date + di} className={`day ${di === day ? '' : 'day--hidden'}`} role="tabpanel" aria-label={`Day ${di + 1}`}>
              <header className="day__head">
                <div>
                  <p className="day__date">{fmtDay(d.date, { weekday: 'long', day: 'numeric', month: 'long' })}</p>
                  <h3 className="day__theme">{d.theme}</h3>
                </div>
                {w && (
                  <div className="wx" title={w.kind === 'historical' ? 'Typical weather, based on last year' : 'Forecast'}>
                    <WeatherIcon summary={w.summary} size={22} />
                    <div>
                      <div className="wx__t">{w.tmax != null ? `${Math.round(w.tmax)}°` : ''}{w.tmin != null ? ` / ${Math.round(w.tmin)}°` : ''}</div>
                      <div className="wx__s">{w.summary}{w.kind === 'historical' ? ' (typical)' : ''}</div>
                    </div>
                  </div>
                )}
              </header>

              <ol className="stops">
                {d.items.map((it, i) => {
                  const mapped = hasCoords(it);
                  if (mapped) n += 1;
                  const body = (
                    <>
                      <span className="stop__when">{WHEN[it.time_of_day]}</span>
                      <span className="stop__main">
                        <span className="stop__title">
                          {mapped && <span className="stop__pin" style={{ '--pin': DAY_COLORS[di % DAY_COLORS.length] } as React.CSSProperties}>{n}</span>}
                          {it.title}
                        </span>
                        <span className="stop__desc">{it.description}</span>
                        {(it.place || it.est_cost != null) && (
                          <span className="stop__meta">
                            {it.place && <span className="stop__place"><MapPin size={13} aria-hidden /> {it.place}</span>}
                            {it.est_cost != null && it.est_cost > 0 && <span>about {money(it.est_cost, currency)} each</span>}
                          </span>
                        )}
                      </span>
                    </>
                  );
                  return (
                    <li key={i} className="stop">
                      {mapped ? (
                        <button className="stop__btn" onClick={() => setFocus({ lat: it.lat, lon: it.lon })}>{body}</button>
                      ) : (
                        <div className="stop__btn stop__btn--static">{body}</div>
                      )}
                    </li>
                  );
                })}
              </ol>
            </section>
          );
        })}

        {plan.tips.length > 0 && (
          <aside className="tips">
            <h3 className="tips__title">Good to know</h3>
            <ul>{plan.tips.map((t, i) => <li key={i}>{t}</li>)}</ul>
            {plan.exchange_rate && plan.local_currency && plan.local_currency.toUpperCase() !== currency.toUpperCase() && (
              <p className="tips__fx">
                {plan.exchange_rate < 0.1
                  ? `1 ${plan.local_currency} ≈ ${(1 / plan.exchange_rate).toFixed(1)} ${currency}`
                  : `1 ${currency} ≈ ${plan.exchange_rate.toFixed(2)} ${plan.local_currency}`}
              </p>
            )}
          </aside>
        )}
      </div>

      <div className="itin__map">
        {anyCoords || pins.length ? (
          <Suspense fallback={<div className="map skeleton" aria-hidden />}>
            <TripMap pins={pins} theme={theme} focus={focus} geoapifyApiKey={geoapifyApiKey} />
          </Suspense>
        ) : (
          <div className="map map--empty">
            <MapPin size={22} aria-hidden />
            <p>The map appears when places can be located. Try a larger city or check your connection.</p>
          </div>
        )}
      </div>
    </div>
  );
}
