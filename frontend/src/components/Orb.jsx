// Alexa-style orb with four states: idle, listening, thinking, speaking.
// Pure CSS animations (see index.css); honours prefers-reduced-motion.

const STATE_CLASS = {
  idle: 'orb-idle',
  listening: 'orb-listening',
  thinking: 'orb-thinking',
  speaking: 'orb-speaking',
};

const STATE_LABEL = {
  idle: 'CareLoop is ready',
  listening: 'Listening…',
  thinking: 'Thinking…',
  speaking: 'Speaking…',
};

export default function Orb({ state = 'idle' }) {
  const cls = STATE_CLASS[state] || STATE_CLASS.idle;
  return (
    <div className="flex flex-col items-center gap-3" aria-live="polite">
      <div
        className={`orb ${cls}`}
        role="img"
        aria-label={STATE_LABEL[state] || STATE_LABEL.idle}
      />
      <p className="text-lg font-semibold text-ink-700">{STATE_LABEL[state] || STATE_LABEL.idle}</p>
    </div>
  );
}
