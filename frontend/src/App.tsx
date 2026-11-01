import { useState } from 'react';
import { useTripAgent } from './lib/agent';
import { useTheme } from './hooks/useTheme';
import Canvas from './components/Canvas';
import ChatPanel from './components/ChatPanel';
import TopBar from './components/TopBar';
import Welcome from './components/Welcome';

export default function App() {
  const { state, health, healthError, submit, approve, reset } = useTripAgent();
  const { theme, toggle } = useTheme();
  const [view, setView] = useState<'chat' | 'trip'>('chat');
  const started = state.items.length > 0;
  const hasResults = state.trip.flights.length > 0 || state.trip.hotels.length > 0 || !!state.trip.plan;

  return (
    <div className="app">
      <TopBar theme={theme} onToggleTheme={toggle} request={state.trip.request} started={started} onNewTrip={() => { reset(); setView('chat'); }} />
      {!started ? (
        <Welcome onSubmit={submit} health={health} healthError={healthError} />
      ) : (
        <>
          <main className="split" data-view={view}>
            <ChatPanel state={state} onSubmit={submit} onApprove={approve} />
            <Canvas trip={state.trip} running={state.running} theme={theme} geoapifyApiKey={health?.geoapify_api_key} />
          </main>
          <nav className="mobile-tabs" aria-label="Switch view">
            <button aria-pressed={view === 'chat'} onClick={() => setView('chat')}>Chat</button>
            <button aria-pressed={view === 'trip'} onClick={() => setView('trip')}>
              Trip{hasResults && view !== 'trip' ? <span className="mobile-tabs__dot" aria-label="new results" /> : null}
            </button>
          </nav>
        </>
      )}
    </div>
  );
}
