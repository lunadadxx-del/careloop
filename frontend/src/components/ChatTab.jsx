import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api';
import Orb from './Orb';
import { renderCard } from './cards';

// Chat tab — Alexa-style voice experience.
// - Voice input via webkitSpeechRecognition/SpeechRecognition, with a graceful
//   text-input fallback when the browser doesn't support it.
// - Agent replies are spoken aloud via speechSynthesis (toggleable).
// - Structured cards from /api/chat are rendered under the agent's message.

function newSessionId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
  return `session-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export default function ChatTab({ patient }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [orbState, setOrbState] = useState('idle');
  const [ttsOn, setTtsOn] = useState(true);
  const [voiceSupported] = useState(
    () =>
      typeof window !== 'undefined' &&
      (window.SpeechRecognition || window.webkitSpeechRecognition)
  );
  const [ttsSupported] = useState(
    () => typeof window !== 'undefined' && 'speechSynthesis' in window
  );
  const [error, setError] = useState(null);
  const [sending, setSending] = useState(false);

  const sessionIdRef = useRef(null);
  const recognitionRef = useRef(null);
  const scrollRef = useRef(null);

  if (!sessionIdRef.current) {
    const stored = localStorage.getItem('careloop-session-id');
    sessionIdRef.current = stored || newSessionId();
    if (!stored) localStorage.setItem('careloop-session-id', sessionIdRef.current);
  }

  // Warm welcome message on first load
  useEffect(() => {
    setMessages([
      {
        id: 'welcome',
        role: 'agent',
        text: patient
          ? `Hello! I'm here to help ${patient.name} stay on track with medications. You can ask me about today's schedule, mark a dose as taken, or check how the week is going — just tap the microphone and talk, or type below.`
          : `Hello! I'm your medication companion. Once you've added a patient in the Setup tab, come back here and we'll take care of the rest together.`,
        cards: [],
      },
    ]);
  }, [patient?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Keep the latest message in view
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, orbState]);

  const stopSpeaking = useCallback(() => {
    if (ttsSupported) window.speechSynthesis.cancel();
  }, [ttsSupported]);

  const speak = useCallback(
    (text, done) => {
      if (!ttsOn || !ttsSupported || !text) {
        done && done();
        return;
      }
      stopSpeaking();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.85; // calm, clear pace for elderly listeners
      utterance.onend = () => done && done();
      utterance.onerror = () => done && done();
      setOrbState('speaking');
      window.speechSynthesis.speak(utterance);
    },
    [ttsOn, ttsSupported, stopSpeaking]
  );

  const sendMessage = useCallback(
    async (rawText) => {
      const text = (rawText || '').trim();
      if (!text || sending) return;
      setSending(true);
      setError(null);
      stopSpeaking();

      const userMsg = { id: `u-${Date.now()}`, role: 'user', text };
      setMessages((prev) => [...prev, userMsg]);
      setInput('');
      setOrbState('thinking');

      try {
        const data = await api.sendChat({
          session_id: sessionIdRef.current,
          message: text,
          patient_id: patient?.id || null,
        });
        const reply = (data && data.reply) || "I'm sorry, I didn't catch that. Could you say it once more?";
        const cards = (data && Array.isArray(data.cards) && data.cards) || [];
        const agentMsg = { id: `a-${Date.now()}`, role: 'agent', text: reply, cards };
        setMessages((prev) => [...prev, agentMsg]);
        // Speak the reply when the backend asks for it (speak: true), or always
        // when TTS is on and the reply is short enough to be pleasant.
        const shouldSpeak = data && typeof data.speak === 'boolean' ? data.speak : true;
        if (shouldSpeak) {
          speak(reply, () => setOrbState('idle'));
        } else {
          setOrbState('idle');
        }
      } catch (err) {
        setOrbState('idle');
        setError(err.message || 'Something went wrong talking to CareLoop. Please try again.');
      } finally {
        setSending(false);
      }
    },
    [patient, sending, speak, stopSpeaking]
  );

  const startListening = useCallback(() => {
    if (!voiceSupported || sending) return;
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    // Tear down any previous session
    try {
      recognitionRef.current && recognitionRef.current.abort();
    } catch { /* noop */ }
    stopSpeaking();

    const rec = new SR();
    rec.lang = 'en-US';
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    recognitionRef.current = rec;

    rec.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      sendMessage(transcript);
    };
    rec.onerror = (event) => {
      // 'not-allowed' = mic permission denied; 'no-speech' = silence timeout.
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        setError('Microphone access was blocked. Please allow microphone use in your browser, or type your message instead.');
      }
      setOrbState('idle');
    };
    rec.onend = () => {
      // Only drop back to idle if we aren't already thinking/speaking
      setOrbState((s) => (s === 'listening' ? 'idle' : s));
    };

    setOrbState('listening');
    setError(null);
    try {
      rec.start();
    } catch {
      setOrbState('idle');
    }
  }, [voiceSupported, sending, sendMessage, stopSpeaking]);

  const stopListening = useCallback(() => {
    try {
      recognitionRef.current && recognitionRef.current.stop();
    } catch { /* noop */ }
  }, []);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      try { recognitionRef.current && recognitionRef.current.abort(); } catch { /* noop */ }
      if (ttsSupported) window.speechSynthesis.cancel();
    };
  }, [ttsSupported]);

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col gap-4">
      <Orb state={orbState} />

      {/* Message list */}
      <div
        ref={scrollRef}
        className="chat-scroll min-h-[16rem] flex-1 space-y-4 overflow-y-auto rounded-3xl bg-white/70 p-4 shadow-inner sm:p-6"
        aria-live="polite"
        aria-label="Conversation"
      >
        {messages.map((m) => (
          <div key={m.id} className={`msg-in flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[85%] rounded-3xl px-5 py-3 text-lg leading-relaxed shadow-sm ${
                m.role === 'user'
                  ? 'rounded-br-lg bg-brand-600 text-white'
                  : 'rounded-bl-lg bg-white text-ink-900 ring-1 ring-cream-200'
              }`}
            >
              <p>{m.text}</p>
              {m.cards && m.cards.length > 0 && (
                <div className="mt-3 space-y-3">{m.cards.map((c, i) => renderCard(c, `${m.id}-card-${i}`))}</div>
              )}
            </div>
          </div>
        ))}
        {orbState === 'thinking' && (
          <div className="flex justify-start">
            <div className="rounded-3xl rounded-bl-lg bg-white px-5 py-4 shadow-sm ring-1 ring-cream-200" aria-label="Thinking">
              <span className="typing-dot" /> <span className="typing-dot" /> <span className="typing-dot" />
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="rounded-2xl border-2 border-red-300 bg-red-50 px-4 py-3 text-lg text-red-900" role="alert">
          {error}
        </div>
      )}

      {!voiceSupported && (
        <p className="rounded-2xl bg-cream-200 px-4 py-2 text-center text-ink-500">
          Voice input isn't supported in this browser — you can type your message below instead.
        </p>
      )}

      {/* Input row: mic + text field + send */}
      <div className="flex items-center gap-3">
        {voiceSupported && (
          <button
            type="button"
            onClick={orbState === 'listening' ? stopListening : startListening}
            disabled={sending}
            aria-label={orbState === 'listening' ? 'Stop listening' : 'Talk to CareLoop'}
            className={`flex min-h-touch min-w-touch items-center justify-center rounded-full text-2xl shadow-md transition active:scale-95 disabled:opacity-50 ${
              orbState === 'listening' ? 'bg-red-500 text-white' : 'bg-brand-600 text-white hover:bg-brand-700'
            }`}
          >
            {orbState === 'listening' ? '■' : '🎙'}
          </button>
        )}
        <form
          className="flex flex-1 gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            sendMessage(input);
          }}
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={patient ? `Message CareLoop about ${patient.name}…` : 'Type your message…'}
            aria-label="Type your message"
            className="min-h-touch flex-1 rounded-full border-2 border-cream-200 bg-white px-5 text-lg shadow-sm outline-none placeholder:text-ink-500 focus:border-brand-500"
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="min-h-touch rounded-full bg-brand-600 px-6 text-lg font-bold text-white shadow-md transition hover:bg-brand-700 active:scale-95 disabled:opacity-50"
          >
            Send
          </button>
        </form>
        {ttsSupported && (
          <button
            type="button"
            onClick={() => {
              if (ttsOn) stopSpeaking();
              setTtsOn((v) => !v);
            }}
            aria-pressed={ttsOn}
            aria-label={ttsOn ? 'Turn voice replies off' : 'Turn voice replies on'}
            title={ttsOn ? 'Voice replies on' : 'Voice replies off'}
            className={`flex min-h-touch min-w-touch items-center justify-center rounded-full text-xl shadow-md transition active:scale-95 ${
              ttsOn ? 'bg-sun-400 text-ink-900' : 'bg-cream-200 text-ink-500'
            }`}
          >
            🔊
          </button>
        )}
      </div>
    </div>
  );
}
