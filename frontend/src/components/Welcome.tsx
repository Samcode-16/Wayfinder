import { AlertTriangle } from 'lucide-react';
import type { Health } from '../lib/api';
import Composer from './Composer';

const IDEAS = [
  'Long weekend in Lisbon from Madrid for 2, around €900',
  'A week in Tokyo from Bengaluru next April. We love food and temples',
  'Cheap beach week in Goa from Delhi, 4 friends, ₹60,000 total',
  'Romantic 4 nights in Rome from London in December, 4-star hotel',
];

interface Props {
  onSubmit: (t: string) => void;
  health: Health | null;
  healthError: boolean;
}

export default function Welcome({ onSubmit, health, healthError }: Props) {
  const noModel = health && health.llm_providers.length === 0;
  return (
    <main className="welcome">
      <div className="welcome__badge">
        <img src="/logo-mark.png" alt="" className="welcome__badge-logo" width="22" height="22" />
        <span>Wayfinder Travel AI</span>
      </div>
      <h1 className="welcome__title">Where to next?</h1>
      <p className="welcome__lede">
        Tell me where you're leaving from, where you'd like to go and when. I'll find flights and stays, check the weather
        and build a day-by-day plan that fits your budget.
      </p>

      <Composer variant="hero" autoFocus onSubmit={onSubmit} placeholder="e.g. Madrid to Amsterdam, 1–5 December, 2 people, €2,500" />

      <ul className="ideas" aria-label="Trip ideas">
        {IDEAS.map((idea) => (
          <li key={idea}>
            <button className="chip" onClick={() => onSubmit(idea)}>{idea}</button>
          </li>
        ))}
      </ul>

      {healthError && (
        <div className="callout callout--error" role="alert">
          <AlertTriangle size={18} aria-hidden />
          <div>
            <strong>Can't reach the backend.</strong> Start it from the <code>backend</code> folder with{' '}
            <code>uvicorn app.main:app --reload --port 8000</code>.
          </div>
        </div>
      )}
      {noModel && (
        <div className="callout callout--error" role="alert">
          <AlertTriangle size={18} aria-hidden />
          <div>
            <strong>No AI model is configured.</strong> Add <code>GROQ_API_KEY</code> or <code>GOOGLE_API_KEY</code> to{' '}
            <code>backend/.env</code> and restart the server.
          </div>
        </div>
      )}
      {health && !health.live_travel_data && !noModel && (
        <p className="welcome__note">Flights and stays use demo data until you add a SerpAPI key. Weather, places and exchange rates are live.</p>
      )}
    </main>
  );
}
