import { Moon, Plus, Sun } from 'lucide-react';
import { dateRange } from '../lib/format';
import type { TripRequest } from '../lib/types';
import type { Theme } from '../hooks/useTheme';

interface Props {
  theme: Theme;
  onToggleTheme: () => void;
  request?: TripRequest;
  started: boolean;
  onNewTrip: () => void;
}

export default function TopBar({ theme, onToggleTheme, request, started, onNewTrip }: Props) {
  const parts: string[] = [];
  if (request?.origin && request?.destination) parts.push(`${request.origin} to ${request.destination}`);
  else if (request?.destination) parts.push(request.destination);
  if (request?.start_date && request?.end_date) parts.push(dateRange(request.start_date, request.end_date));
  if (request?.destination) parts.push(`${request.travelers} ${request.travelers === 1 ? 'traveler' : 'travelers'}`);

  return (
    <header className="topbar">
      <a className="brand" href="/" onClick={(e) => { e.preventDefault(); onNewTrip(); }} aria-label="Wayfinder home">
        <img className="brand__logo" src="/logo-mark.png" alt="" width="36" height="36" />
        <span className="brand__name">Wayfinder</span>
      </a>

      <div className="tripbar" aria-label="Trip details">
        {parts.length ? (
          parts.map((p, i) => (
            <span key={i} className="tripbar__part">{p}</span>
          ))
        ) : (
          <span className="tripbar__empty">Describe your trip to get started</span>
        )}
      </div>

      <div className="topbar__actions">
        {started && (
          <button className="btn btn--ghost" onClick={onNewTrip}>
            <Plus size={16} aria-hidden /> New trip
          </button>
        )}
        <button
          className="icon-btn"
          onClick={onToggleTheme}
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {theme === 'dark' ? <Sun size={18} aria-hidden /> : <Moon size={18} aria-hidden />}
        </button>
      </div>
    </header>
  );
}
