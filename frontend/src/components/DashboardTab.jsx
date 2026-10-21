import { useCallback, useEffect, useState } from 'react';
import { api } from '../api';

// Dashboard tab — today's schedule with Take/Miss/Snooze, a 7-day adherence
// bar chart (pure SVG, no chart library), a recent-alerts feed, and a clearly
// labeled demo control that forces the next pending dose into "due".

const STATUS_STYLE = {
  pending: 'bg-cream-200 text-ink-700',
  due: 'bg-sun-400 text-ink-900',
  taken: 'bg-brand-100 text-brand-700',
  missed: 'bg-red-100 text-red-800',
  snoozed: 'bg-sky-100 text-sky-800',
};

function formatTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}

function formatDayLabel(isoDate) {
  // by_day entries carry a date like "2026-10-21"
  const d = new Date(`${isoDate}T12:00:00`);
  if (Number.isNaN(d.getTime())) return isoDate;
  return d.toLocaleDateString([], { weekday: 'short' });
}

function AdherenceChart({ byDay }) {
  if (!byDay || byDay.length === 0) {
    return <p className="text-lg text-ink-500">No adherence data yet — check back after a few doses.</p>;
  }
  const width = 560;
  const height = 180;
  const pad = 28;
  const n = byDay.length;
  const slot = (width - pad * 2) / n;
  const barW = Math.min(44, slot * 0.55);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full" role="img" aria-label="Adherence over the last 7 days">
      {byDay.map((d, i) => {
        const scheduled = d.scheduled || 0;
        const taken = d.taken || 0;
        const ratio = scheduled > 0 ? taken / scheduled : 0;
        const barH = Math.max(4, ratio * (height - pad * 2 - 24));
        const x = pad + i * slot + (slot - barW) / 2;
        const y = height - pad - barH;
        return (
          <g key={d.date || i}>
            <rect x={x} y={pad} width={barW} height={height - pad * 2 - 24} rx="8" fill="#F3EAD8" />
            <rect x={x} y={y} width={barW} height={barH} rx="8" fill={ratio >= 0.8 ? '#1F7A64' : ratio >= 0.5 ? '#EFA31B' : '#D64545'} />
            <text x={x + barW / 2} y={height - 8} textAnchor="middle" fontSize="14" fill="#6B5F52">
              {formatDayLabel(d.date)}
            </text>
            <text x={x + barW / 2} y={y - 6} textAnchor="middle" fontSize="13" fontWeight="bold" fill="#1F1B16">
              {scheduled > 0 ? `${taken}/${scheduled}` : '–'}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export default function DashboardTab({ patient }) {
  const [doses, setDoses] = useState([]);
  const [adherence, setAdherence] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busyDose, setBusyDose] = useState(null);
  const [demoBusy, setDemoBusy] = useState(false);
  const [demoMsg, setDemoMsg] = useState(null);

  const load = useCallback(async () => {
    if (!patient) return;
    setLoading(true);
    setError(null);
    try {
      const [schedule, adh, al] = await Promise.all([
        api.getTodaySchedule(patient.id),
        api.getAdherence(patient.id, 7).catch(() => null),
        api.listAlerts(patient.id).catch(() => []),
      ]);
      const list = Array.isArray(schedule) ? schedule : schedule?.doses || [];
      setDoses(list.slice().sort((a, b) => new Date(a.scheduled_for) - new Date(b.scheduled_for)));
      setAdherence(adh);
      setAlerts(Array.isArray(al) ? al : al?.alerts || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [patient]);

  useEffect(() => {
    load();
  }, [load]);

  // Gentle polling so "due" states appear without a manual refresh during demos
  useEffect(() => {
    if (!patient) return;
    const t = setInterval(() => {
      api.getTodaySchedule(patient.id)
        .then((s) => {
          const list = Array.isArray(s) ? s : s?.doses || [];
          setDoses(list.slice().sort((a, b) => new Date(a.scheduled_for) - new Date(b.scheduled_for)));
        })
        .catch(() => {});
    }, 30000);
    return () => clearInterval(t);
  }, [patient]);

  const handleDoseEvent = async (doseId, event) => {
    setBusyDose(doseId);
    try {
      await api.recordDoseEvent(doseId, event);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyDose(null);
    }
  };

  const handleDemoTrigger = async () => {
    setDemoBusy(true);
    setDemoMsg(null);
    try {
      await api.triggerDueDemo(patient.id);
      setDemoMsg('Demo: the next pending dose was marked as due.');
      await load();
    } catch (err) {
      setDemoMsg(`Demo control failed: ${err.message}`);
    } finally {
      setDemoBusy(false);
    }
  };

  if (!patient) return null;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {error && (
        <div className="rounded-2xl border-2 border-red-300 bg-red-50 px-4 py-3 text-lg text-red-900" role="alert">
          {error}
        </div>
      )}

      {/* Demo control — clearly labeled, hackathon demo helper */}
      <div className="rounded-3xl border-2 border-dashed border-sun-500 bg-sun-100 p-4">
        <p className="text-lg font-bold text-ink-900">🎬 Demo control</p>
        <p className="text-ink-500">For the demo video: forces the next pending dose into the “due” state so you can show the reminder flow.</p>
        <button
          type="button"
          onClick={handleDemoTrigger}
          disabled={demoBusy}
          className="mt-2 min-h-touch rounded-full bg-sun-500 px-6 text-lg font-bold text-ink-900 shadow-md transition hover:bg-sun-400 active:scale-95 disabled:opacity-50"
        >
          {demoBusy ? 'Working…' : 'Mark next dose as due now'}
        </button>
        {demoMsg && <p className="mt-2 text-lg font-semibold" role="status">{demoMsg}</p>}
      </div>

      {/* Today's schedule */}
      <section className="rounded-3xl bg-white/70 p-5 shadow-sm sm:p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-2xl font-extrabold text-ink-900">Today's schedule</h2>
          <button
            type="button"
            onClick={load}
            className="min-h-touch rounded-full bg-cream-200 px-5 text-lg font-bold text-ink-700 transition hover:bg-cream-200/70 active:scale-95"
          >
            Refresh
          </button>
        </div>
        {loading ? (
          <p className="text-lg text-ink-500">Loading today's doses…</p>
        ) : doses.length === 0 ? (
          <p className="text-lg text-ink-500">
            No doses scheduled for today. Add medications in the Setup tab to build the schedule.
          </p>
        ) : (
          <ul className="space-y-3">
            {doses.map((d) => {
              const status = (d.status || 'pending').toLowerCase();
              const actionable = status === 'pending' || status === 'due' || status === 'snoozed';
              return (
                <li key={d.dose_id} className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-cream-200">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-xl font-bold text-ink-900">{d.medication_name}</p>
                      <p className="text-lg text-ink-500">
                        {d.dosage ? `${d.dosage} · ` : ''}{formatTime(d.scheduled_for)}
                      </p>
                    </div>
                    <span className={`rounded-full px-4 py-1 text-lg font-bold capitalize ${STATUS_STYLE[status] || STATUS_STYLE.pending}`}>
                      {status}
                    </span>
                  </div>
                  {actionable && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        type="button"
                        disabled={busyDose === d.dose_id}
                        onClick={() => handleDoseEvent(d.dose_id, 'taken')}
                        className="min-h-touch flex-1 rounded-full bg-brand-600 px-4 text-lg font-bold text-white shadow-sm transition hover:bg-brand-700 active:scale-95 disabled:opacity-50"
                      >
                        ✓ Taken
                      </button>
                      <button
                        type="button"
                        disabled={busyDose === d.dose_id}
                        onClick={() => handleDoseEvent(d.dose_id, 'snoozed')}
                        className="min-h-touch flex-1 rounded-full bg-cream-200 px-4 text-lg font-bold text-ink-700 transition hover:bg-cream-200/70 active:scale-95 disabled:opacity-50"
                      >
                        Snooze
                      </button>
                      <button
                        type="button"
                        disabled={busyDose === d.dose_id}
                        onClick={() => handleDoseEvent(d.dose_id, 'missed')}
                        className="min-h-touch flex-1 rounded-full bg-red-100 px-4 text-lg font-bold text-red-800 transition hover:bg-red-200 active:scale-95 disabled:opacity-50"
                      >
                        Missed
                      </button>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>

      {/* Adherence */}
      <section className="rounded-3xl bg-white/70 p-5 shadow-sm sm:p-6">
        <h2 className="mb-1 text-2xl font-extrabold text-ink-900">This week</h2>
        {adherence ? (
          <>
            <p className="mb-3 text-lg text-ink-700">
              <span className="text-4xl font-extrabold text-ink-900">{Math.round(adherence.percentage ?? 0)}%</span>
              {' '}of doses taken
              {adherence.taken !== undefined && adherence.scheduled !== undefined && (
                <span className="text-ink-500"> ({adherence.taken} of {adherence.scheduled})</span>
              )}
            </p>
            <AdherenceChart byDay={adherence.by_day} />
          </>
        ) : (
          <p className="text-lg text-ink-500">Adherence data will appear here once doses are recorded.</p>
        )}
      </section>

      {/* Recent alerts */}
      <section className="rounded-3xl bg-white/70 p-5 shadow-sm sm:p-6">
        <h2 className="mb-3 text-2xl font-extrabold text-ink-900">Recent alerts</h2>
        {alerts.length === 0 ? (
          <p className="text-lg text-ink-500">No alerts. Everything is on track. 🎉</p>
        ) : (
          <ul className="space-y-2">
            {alerts.slice(0, 5).map((a) => (
              <li key={a.id} className="rounded-2xl bg-cream-100 px-4 py-2 text-lg">
                <span className="font-semibold">{a.message}</span>
                {a.acknowledged && <span className="ml-2 text-ink-500">(acknowledged)</span>}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
