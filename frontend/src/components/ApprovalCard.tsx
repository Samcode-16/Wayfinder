import { Check } from 'lucide-react';

export default function ApprovalCard({ onApprove, disabled }: { onApprove: () => void; disabled?: boolean }) {
  return (
    <div className="approval">
      <p className="approval__text">Happy with this plan? Approve it, or tell me what to change below.</p>
      <button className="btn btn--primary" onClick={onApprove} disabled={disabled}>
        <Check size={16} aria-hidden /> Approve itinerary
      </button>
    </div>
  );
}
