import { Building2, ExternalLink, Star } from 'lucide-react';
import { money } from '../lib/format';
import type { HotelOption, Selection } from '../lib/types';

const hash = (s: string) => [...s].reduce((a, c) => (a * 31 + c.charCodeAt(0)) >>> 0, 7);

export default function HotelsGrid({
  hotels,
  selection,
  nights,
  warnings = [],
}: {
  hotels: HotelOption[];
  selection?: Selection | null;
  nights: number;
  warnings?: string[];
}) {
  const sorted = [...hotels].sort((a, b) => Number(b.id === selection?.hotel_id) - Number(a.id === selection?.hotel_id) || (b.rating ?? 0) - (a.rating ?? 0));
  const demo = hotels.some((h) => h.source === 'demo');

  const noteMessage = (() => {
    if (!demo) return null;
    const hotelWarn = warnings.find(
      (w) => w.toLowerCase().includes('hotel') || w.toLowerCase().includes('stay')
    );
    if (hotelWarn) {
      if (hotelWarn.includes('set SERPAPI_API_KEY')) {
        return 'Demo stays. Add a SerpAPI key to see live Google Hotels prices and photos.';
      }
      return hotelWarn;
    }
    return 'Demo stays (live Google Hotels returned no results).';
  })();

  return (
    <div>
      {noteMessage && <p className="note">{noteMessage}</p>}
      <ul className="hotels">
        {sorted.map((h) => {
          const picked = h.id === selection?.hotel_id;
          return (
            <li key={h.id} className="hotel">
              <div className="hotel__media" style={{ '--tint': `var(--tint-${(hash(h.name) % 6) + 1})` } as React.CSSProperties}>
                {h.image ? <img src={h.image} alt="" loading="lazy" /> : <Building2 size={40} strokeWidth={1.4} aria-hidden />}
                {picked && <span className="badge badge--float">Picked for you</span>}
              </div>
              <div className="hotel__head">
                <h3 className="hotel__name">{h.name}</h3>
                {h.rating != null && (
                  <span className="hotel__rating"><Star size={13} fill="currentColor" aria-hidden /> {h.rating.toFixed(1)}</span>
                )}
              </div>
              <p className="hotel__sub">{[h.stars ? `${h.stars}-star` : 'Hotel', ...h.amenities.slice(0, 3)].join(', ')}</p>
              <p className="hotel__price">
                <strong>{money(h.price_per_night, h.currency)}</strong> night
                <span>{money(h.price_per_night * nights, h.currency)} for {nights} {nights === 1 ? 'night' : 'nights'}</span>
              </p>
              {h.link && (
                <a href={h.link} target="_blank" rel="noreferrer" className="link">
                  View stay <ExternalLink size={12} aria-hidden />
                </a>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
