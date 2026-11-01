import { Building2, Check, ExternalLink, Star } from 'lucide-react';
import { money } from '../lib/format';
import type { HotelOption, Selection } from '../lib/types';

const hash = (s: string) => [...s].reduce((a, c) => (a * 31 + c.charCodeAt(0)) >>> 0, 7);

export default function HotelsGrid({
  hotels,
  selection,
  nights,
  warnings = [],
  onSelectHotel,
  disabled,
}: {
  hotels: HotelOption[];
  selection?: Selection | null;
  nights: number;
  warnings?: string[];
  onSelectHotel?: (hotelId: string) => void;
  disabled?: boolean;
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
            <li
              key={h.id}
              className={`hotel ${picked ? 'is-picked' : 'is-selectable'}`}
              onClick={(e) => {
                if ((e.target as HTMLElement).closest('a, button')) return;
                if (!picked && !disabled) onSelectHotel?.(h.id);
              }}
            >
              <div className="hotel__media" style={{ '--tint': `var(--tint-${(hash(h.name) % 6) + 1})` } as React.CSSProperties}>
                {h.image ? <img src={h.image} alt="" loading="lazy" /> : <Building2 size={40} strokeWidth={1.4} aria-hidden />}
                {picked && (
                  <span className="badge badge--picked badge--float">
                    <Check size={12} aria-hidden /> Picked for you
                  </span>
                )}
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
              <div className="hotel__actions">
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
                      onSelectHotel?.(h.id);
                    }}
                    aria-label={`Select ${h.name}`}
                  >
                    Select stay
                  </button>
                )}
                {h.link && (
                  <a href={h.link} target="_blank" rel="noreferrer" className="link" onClick={(e) => e.stopPropagation()}>
                    View stay <ExternalLink size={12} aria-hidden />
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
