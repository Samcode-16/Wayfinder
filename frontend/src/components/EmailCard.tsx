import { Check, Mail, Send } from 'lucide-react';
import { useState } from 'react';

export default function EmailCard({
  onSend,
  disabled,
}: {
  onSend: (email: string) => Promise<void>;
  disabled?: boolean;
}) {
  const [email, setEmail] = useState('');
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const clean = email.trim();
    if (!clean || sending || disabled) return;
    setSending(true);
    try {
      await onSend(clean);
      setSent(true);
    } finally {
      setSending(false);
    }
  };

  if (sent) {
    return (
      <div className="email-card email-card--sent">
        <p className="email-card__msg">
          <Check size={16} className="ok-icon" aria-hidden /> Itinerary sent to <strong>{email}</strong>!
        </p>
      </div>
    );
  }

  return (
    <div className="email-card">
      <div className="email-card__header">
        <Mail size={16} aria-hidden />
        <strong>Email this itinerary</strong>
      </div>
      <p className="email-card__desc">
        Enter your email address to receive your flight details, stay info, and full daily schedule.
      </p>
      <form onSubmit={handleSubmit} className="email-card__form">
        <input
          type="email"
          className="email-card__input"
          placeholder="traveler@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          disabled={disabled || sending}
          aria-label="Email address"
        />
        <button
          type="submit"
          className="btn btn--primary btn--sm"
          disabled={disabled || sending || !email.trim()}
        >
          <Send size={14} aria-hidden />
          {sending ? 'Sending…' : 'Send'}
        </button>
      </form>
    </div>
  );
}
