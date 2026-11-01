import { BedDouble, Check, CloudSun, Landmark, Plane } from 'lucide-react';
import type { ReactNode } from 'react';
import type { RunMode, StepId, Steps } from '../lib/agent';

function Node({ status }: { status: 'idle' | 'running' | 'done' }) {
  return (
    <span className={`node node--${status}`} aria-hidden>
      {status === 'done' && <Check size={12} strokeWidth={3} />}
    </span>
  );
}

const label = (status: string) => (status === 'done' ? 'done' : status === 'running' ? 'in progress' : 'waiting');

function Row({ id, steps, children, last }: { id: StepId; steps: Steps; children: ReactNode; last?: boolean }) {
  const s = steps[id];
  return (
    <li className={`leg ${last ? 'leg--last' : ''}`} aria-label={`${children}: ${label(s.status)}`}>
      <Node status={s.status} />
      <div className="leg__body">
        <span className={`leg__label ${s.status === 'idle' ? 'is-idle' : ''}`}>{children}</span>
        {s.detail && s.status === 'done' && <span className="leg__detail">{s.detail}</span>}
      </div>
    </li>
  );
}

const PARALLEL: { id: StepId; label: string; icon: ReactNode }[] = [
  { id: 'flights', label: 'Flights', icon: <Plane size={15} aria-hidden /> },
  { id: 'hotels', label: 'Stays', icon: <BedDouble size={15} aria-hidden /> },
  { id: 'activities', label: 'Places', icon: <Landmark size={15} aria-hidden /> },
  { id: 'weather', label: 'Weather', icon: <CloudSun size={15} aria-hidden /> },
];

export default function ActivityTimeline({ steps, mode, destination }: { steps: Steps; mode: RunMode; destination?: string | null }) {
  if (mode === 'revise') {
    return (
      <ol className="timeline" aria-label="Progress">
        <Row id="compose" steps={steps} last>Revising your itinerary</Row>
      </ol>
    );
  }
  const gathering = PARALLEL.map((p) => steps[p.id].status);
  const groupStatus = gathering.every((s) => s === 'done') ? 'done' : gathering.some((s) => s !== 'idle') ? 'running' : 'idle';

  return (
    <ol className="timeline" aria-label="Progress">
      <Row id="parse" steps={steps}>Understanding your request</Row>
      <Row id="prepare" steps={steps}>{`Locating ${destination || 'your destination'}`}</Row>

      <li className="leg">
        <Node status={groupStatus} />
        <div className="leg__body">
          <span className={`leg__label ${groupStatus === 'idle' ? 'is-idle' : ''}`}>Searching in parallel</span>
          <ul className="lanes">
            {PARALLEL.map((p) => {
              const s = steps[p.id];
              return (
                <li key={p.id} className={`lane lane--${s.status}`} aria-label={`${p.label}: ${label(s.status)}`}>
                  <span className="lane__icon">{p.icon}</span>
                  <span className="lane__text">
                    <span className="lane__name">{p.label}</span>
                    <span className="lane__detail">{s.status === 'done' ? s.detail : s.status === 'running' ? 'Searching…' : ''}</span>
                  </span>
                  {s.status === 'done' && <Check size={14} strokeWidth={3} className="lane__check" aria-hidden />}
                </li>
              );
            })}
          </ul>
        </div>
      </li>

      <Row id="optimize" steps={steps}>Balancing your budget</Row>
      <Row id="compose" steps={steps} last>Writing your itinerary</Row>
    </ol>
  );
}
