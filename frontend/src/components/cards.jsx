// Renders the structured "cards" returned by POST /api/chat.
// Supported card types: medication, medication_list, schedule, adherence,
// alert, alert_list, confirm.
// Unknown types fall back to a generic card so the UI never breaks on new types.

function CardShell({ title, tone = 'brand', children }) {
  const tones = {
    brand: 'border-brand-500 bg-brand-50',
    sun: 'border-sun-500 bg-sun-100',
    alert: 'border-red-400 bg-red-50',
    neutral: 'border-cream-200 bg-white',
  };
  return (
    <div className={`rounded-2xl border-2 ${tones[tone] || tones.neutral} p-4 shadow-sm`}>
      {title && <h4 className="mb-2 text-lg font-bold text-ink-900">{title}</h4>}
      {children}
    </div>
  );
}

function formatTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}

function formatDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' });
}

function MedicationCard({ card }) {
  const c = card || {};
  return (
    <CardShell title={c.name || c.medication_name || 'Medication'} tone="brand">
      <dl className="space-y-1 text-lg">
        {c.dosage && (
          <div className="flex gap-2"><dt className="font-semibold">Dose:</dt><dd>{c.dosage}</dd></div>
        )}
        {c.times && (
          <div className="flex gap-2"><dt className="font-semibold">Times:</dt><dd>{Array.isArray(c.times) ? c.times.join(', ') : c.times}</dd></div>
        )}
        {c.next_dose && (
          <div className="flex gap-2"><dt className="font-semibold">Next dose:</dt><dd>{formatTime(c.next_dose)} ({formatDate(c.next_dose)})</dd></div>
        )}
        {c.notes && <p className="text-ink-500">{c.notes}</p>}
      </dl>
    </CardShell>
  );
}

function ScheduleCard({ card }) {
  const doses = card.doses || card.schedule || [];
  return (
    <CardShell title={card.title || "Today's schedule"} tone="neutral">
      {doses.length === 0 ? (
        <p className="text-lg text-ink-500">Nothing scheduled for today.</p>
      ) : (
        <ul className="space-y-2">
          {doses.slice(0, 6).map((d, i) => (
            <li key={d.dose_id || i} className="flex items-center justify-between gap-3 rounded-xl bg-cream-100 px-3 py-2">
              <span className="text-lg font-semibold">{d.medication_name || d.name}</span>
              <span className="text-lg text-ink-700">{formatTime(d.scheduled_for || d.time)}</span>
            </li>
          ))}
        </ul>
      )}
    </CardShell>
  );
}

function AdherenceCard({ card }) {
  const pct = card.percentage ?? card.adherence;
  return (
    <CardShell title={card.title || 'Adherence'} tone="sun">
      {pct !== undefined ? (
        <>
          <p className="text-4xl font-extrabold text-ink-900">{Math.round(pct)}%</p>
          <p className="text-lg text-ink-700">
            {card.taken !== undefined && card.scheduled !== undefined
              ? `${card.taken} of ${card.scheduled} doses taken`
              : 'of doses taken on time'}
          </p>
        </>
      ) : (
        <p className="text-lg text-ink-500">No adherence data yet.</p>
      )}
    </CardShell>
  );
}

function AlertCard({ card }) {
  return (
    <CardShell title={card.title || 'Alert'} tone="alert">
      <p className="text-lg font-semibold">{card.message || card.text || 'Something needs attention.'}</p>
      {card.created_at && <p className="mt-1 text-ink-500">{formatDate(card.created_at)} · {formatTime(card.created_at)}</p>}
    </CardShell>
  );
}

function ConfirmCard({ card }) {
  return (
    <CardShell title={card.title || 'Please confirm'} tone="sun">
      <p className="text-lg">{card.message || card.text || card.question || 'Are you sure?'}</p>
      {card.options && (
        <div className="mt-3 flex flex-wrap gap-2">
          {card.options.map((opt, i) => (
            <span key={i} className="rounded-full bg-white px-4 py-2 text-lg font-semibold shadow-sm">
              {typeof opt === 'string' ? opt : opt.label || opt.value}
            </span>
          ))}
        </div>
      )}
    </CardShell>
  );
}

export function renderCard(card, key) {
  if (!card || typeof card !== 'object') return null;
  const type = (card.type || '').toLowerCase();
  switch (type) {
    case 'medication':
      return <MedicationCard key={key} card={card} />;
    case 'medication_list':
      return (
        <CardShell key={key} title={card.title || 'Medications'} tone="brand">
          <div className="space-y-2">
            {(card.medications || []).map((m, i) => (
              <MedicationCard key={m.id || i} card={m} />
            ))}
          </div>
        </CardShell>
      );
    case 'schedule':
      return <ScheduleCard key={key} card={card} />;
    case 'adherence':
      return <AdherenceCard key={key} card={card} />;
    case 'alert':
      return <AlertCard key={key} card={card} />;
    case 'alert_list':
      return (
        <CardShell key={key} title={card.title || 'Alerts'} tone="alert">
          <div className="space-y-2">
            {(card.alerts || []).map((a, i) => (
              <AlertCard key={a.id || i} card={a} />
            ))}
          </div>
        </CardShell>
      );
    case 'confirm':
      return <ConfirmCard key={key} card={card} />;
    default:
      // Graceful fallback: show title + message for any future card type.
      return (
        <CardShell key={key} title={card.title || 'Update'} tone="neutral">
          <p className="text-lg">{card.message || card.text || JSON.stringify(card)}</p>
        </CardShell>
      );
  }
}
