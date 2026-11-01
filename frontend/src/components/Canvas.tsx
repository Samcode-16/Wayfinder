import { useState } from 'react';
import type { Theme } from '../hooks/useTheme';
import { downloadICS } from '../lib/ics';
import type { TripData } from '../lib/types';
import FlightsList from './FlightsList';
import HotelsGrid from './HotelsGrid';
import Itinerary from './Itinerary';
import TripSummary from './TripSummary';

type Tab = 'itinerary' | 'flights' | 'stays';

export default function Canvas({
  trip,
  running,
  theme,
  geoapifyApiKey,
}: {
  trip: TripData;
  running: boolean;
  theme: Theme;
  geoapifyApiKey?: string | null;
}) {
  const [tab, setTab] = useState<Tab>('itinerary');
  const req = trip.request;
  const currency = trip.selection?.currency ?? req?.currency ?? 'USD';
  const hotel = trip.hotels.find((h) => h.id === trip.selection?.hotel_id);
  const nights = req?.start_date && req.end_date ? Math.max(1, Math.round((+new Date(req.end_date) - +new Date(req.start_date)) / 86400000)) : 1;

  const print = () => {
    setTab('itinerary');
    setTimeout(() => {
      window.print();
    }, 250);
  };

  const tabs: { id: Tab; label: string; count?: number }[] = [
    { id: 'itinerary', label: 'Itinerary' },
    { id: 'flights', label: 'Flights', count: trip.flights.length },
    { id: 'stays', label: 'Stays', count: trip.hotels.length },
  ];

  return (
    <section className="canvas" aria-label="Your trip">
      <div className="canvas__inner">
        <TripSummary trip={trip} running={running} onPrint={print} onCalendar={() => downloadICS(trip)} />

        <div className="tabs" role="tablist" aria-label="Trip sections">
          {tabs.map((t) => (
            <button key={t.id} role="tab" aria-selected={tab === t.id} className="tab" onClick={() => setTab(t.id)}>
              {t.label}
              {t.count ? <span className="tab__count">{t.count}</span> : null}
            </button>
          ))}
        </div>

        <div className="canvas__panel" role="tabpanel">
          {tab === 'itinerary' &&
            (trip.plan ? (
              <Itinerary
                plan={trip.plan}
                weather={trip.weather}
                hotel={hotel}
                currency={currency}
                theme={theme}
                geoapifyApiKey={geoapifyApiKey}
              />
            ) : (
              <div className="skeletons" aria-hidden>
                <div className="skeleton skeleton--row" />
                <div className="skeleton skeleton--row" />
                <div className="skeleton skeleton--row" />
                <p className="empty">{running ? 'Your itinerary will appear here as soon as it is ready.' : 'Nothing planned yet.'}</p>
              </div>
            ))}
          {tab === 'flights' &&
            (trip.flights.length ? (
              <FlightsList flights={trip.flights} selection={trip.selection} travelers={req?.travelers ?? 1} warnings={trip.warnings} />
            ) : (
              <p className="empty">{running ? 'Searching flights…' : 'No flights yet.'}</p>
            ))}
          {tab === 'stays' &&
            (trip.hotels.length ? (
              <HotelsGrid hotels={trip.hotels} selection={trip.selection} nights={nights} warnings={trip.warnings} />
            ) : (
              <p className="empty">{running ? 'Searching stays…' : 'No stays yet.'}</p>
            ))}
        </div>
      </div>
    </section>
  );
}
