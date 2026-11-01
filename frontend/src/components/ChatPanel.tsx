import { AlertCircle } from 'lucide-react';
import { useEffect, useRef } from 'react';
import type { AgentState } from '../lib/agent';
import ActivityTimeline from './ActivityTimeline';
import ApprovalCard from './ApprovalCard';
import Composer from './Composer';
import EmailCard from './EmailCard';

interface Props {
  state: AgentState;
  onSubmit: (t: string) => void;
  onApprove: () => void;
  onSendEmail?: (email: string) => Promise<void>;
}

export default function ChatPanel({ state, onSubmit, onApprove, onSendEmail }: Props) {
  const { items, running, interrupt, error, trip } = state;
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
    end.current?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'end' });
  }, [items, error, running]);

  const lastApproval = items.map((i) => i.type).lastIndexOf('approval');
  const placeholder = running
    ? 'Planning…'
    : interrupt?.type === 'approval'
      ? 'Describe what to change'
      : interrupt?.type === 'clarify'
        ? 'Type your answer'
        : 'Ask for a change, e.g. make it 6 nights';

  return (
    <section className="chat" aria-label="Conversation">
      <div className="chat__scroll" aria-live="polite">
        {items.map((it, idx) => {
          switch (it.type) {
            case 'user':
              return <p key={it.id} className="msg msg--user">{it.text}</p>;
            case 'assistant':
              return <p key={it.id} className="msg msg--bot">{it.text}</p>;
            case 'timeline':
              return (
                <div key={it.id} className="msg-block">
                  <ActivityTimeline steps={it.steps} mode={it.mode} destination={trip.request?.destination} />
                </div>
              );
            case 'approval':
              return idx === lastApproval && interrupt?.type === 'approval' ? (
                <ApprovalCard key={it.id} onApprove={onApprove} disabled={running} />
              ) : null;
            case 'email_prompt':
              return onSendEmail ? (
                <EmailCard key={it.id} onSend={onSendEmail} disabled={running} />
              ) : null;
          }
        })}
        {error && (
          <div className="callout callout--error" role="alert">
            <AlertCircle size={18} aria-hidden />
            <div><strong>That didn't work.</strong> {error} Send your message again to retry.</div>
          </div>
        )}
        <div ref={end} />
      </div>
      <div className="chat__dock">
        <Composer onSubmit={onSubmit} disabled={running} placeholder={placeholder} />
      </div>
    </section>
  );
}
