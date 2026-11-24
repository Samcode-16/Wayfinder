import { Moon, Plus, Sparkles, Sun } from 'lucide-react';
import { dateRange } from '../lib/format';
import type { TripRequest } from '../lib/types';
import type { Theme } from '../hooks/useTheme';

interface Props {
  theme: Theme;
  onToggleTheme: () => void;
  request?: TripRequest;
  started: boolean;
  onNewTrip: () => void;
  onGetStarted?: () => void;
}

export default function TopBar({ theme, onToggleTheme, request, started, onNewTrip, onGetStarted }: Props) {
  const parts: string[] = [];
  if (request?.origin && request?.destination) parts.push(`${request.origin} to ${request.destination}`);
  else if (request?.destination) parts.push(request.destination);
  if (request?.start_date && request?.end_date) parts.push(dateRange(request.start_date, request.end_date));
  if (request?.destination) parts.push(`${request.travelers} ${request.travelers === 1 ? 'traveler' : 'travelers'}`);

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <header className="topbar">
      <a className="brand" href="/" onClick={(e) => { e.preventDefault(); onNewTrip(); }} aria-label="Wayfinder home">
        <img className="brand__logo" src="/logo-mark.png" alt="" width="36" height="36" />
        <span className="brand__name">Wayfinder</span>
      </a>

      {started ? (
        <div className="tripbar" aria-label="Trip details">
          {parts.length ? (
            parts.map((p, i) => (
              <span key={i} className="tripbar__part">{p}</span>
            ))
          ) : (
            <span className="tripbar__empty">Trip in progress</span>
          )}
        </div>
      ) : (
        <nav className="topbar__nav" aria-label="Main navigation">
          <button className="topbar__nav-link" onClick={() => scrollToSection('planner')}>Plan Trip</button>
          <button className="topbar__nav-link" onClick={() => scrollToSection('how-it-works')}>How It Works</button>
          <button className="topbar__nav-link" onClick={() => scrollToSection('features')}>Features</button>
          <button className="topbar__nav-link" onClick={() => scrollToSection('showcase')}>Showcase</button>
          <button className="topbar__nav-link" onClick={() => scrollToSection('inspirations')}>Inspirations</button>
          <button className="topbar__nav-link" onClick={() => scrollToSection('faq')}>FAQ</button>
        </nav>
      )}

      <div className="topbar__actions">
        {started ? (
          <button className="btn btn--ghost" onClick={onNewTrip}>
            <Plus size={16} aria-hidden /> New trip
          </button>
        ) : (
          <button className="btn btn--primary btn--sm topbar__cta-btn" onClick={onGetStarted}>
            <Sparkles size={14} aria-hidden /> Get Started
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

