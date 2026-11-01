import { ArrowUp } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

interface Props {
  onSubmit: (text: string) => void;
  placeholder: string;
  disabled?: boolean;
  variant?: 'hero' | 'dock';
  autoFocus?: boolean;
}

export default function Composer({ onSubmit, placeholder, disabled, variant = 'dock', autoFocus }: Props) {
  const [text, setText] = useState('');
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 168)}px`;
  }, [text]);

  const send = () => {
    if (!text.trim() || disabled) return;
    onSubmit(text);
    setText('');
  };

  return (
    <div className={`composer composer--${variant}`}>
      <textarea
        ref={ref}
        className="composer__input"
        aria-label="Message"
        rows={1}
        value={text}
        placeholder={placeholder}
        disabled={disabled}
        autoFocus={autoFocus}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault();
            send();
          }
        }}
      />
      <button className="composer__send" onClick={send} disabled={disabled || !text.trim()} aria-label="Send">
        <ArrowUp size={20} aria-hidden />
      </button>
    </div>
  );
}
