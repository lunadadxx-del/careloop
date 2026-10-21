import { useCallback, useEffect, useState } from 'react';
import { api } from '../api';

// Alerts tab — escalation list (e.g. missed doses that pinged a caregiver).
// Each unacknowledged alert can be acknowledged. If the backend does not
// implement the acknowledge endpoint, the button degrades to a friendly
// inline message instead of breaking.

function formatDateTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return `${d.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })} · ${d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}`;
}

export default function AlertsTab({ patient }) {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    if (!patient) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.listAlerts(patient.id);
      const list = Array.isArray(data) ? data : data?.alerts || [];
      setAlerts(list.slice().sort((a, b) => new Date(b.created_at) - new Date(a.created_at)));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [patient]);

  useEffect(() => {
    load();
  }, [load]);

  const handleAcknowledge = async (alert) => {
    setBusyId(alert.id);
    try {
      await api.acknowledgeAlert(alert.id);
      setAlerts((prev) => prev.map((a) => (a.id === alert.id ? { ...a, acknowledged: true } : a)));
    } catch (err) {
      setError(`Could not acknowledge this alert: ${err.message}`);
    } finally {
      setBusyId(null);
    }
  };

  if (!patient) return null;

  const unacked = alerts.filter((a) => !a.acknowledged);

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      {error && (
        <div className="rounded-2xl border-2 border-red-300 bg-red-50 px-4 py-3 text-lg text-red-900" role="alert">
          {error}
        </div>
      )}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-extrabold text-ink-900">
          Alerts {unacked.length > 0 && <span className="ml-1 rounded-full bg-red-500 px-3 py-1 text-lg text-white">{unacked.length} new</span>}
        </h2>
        <button
          type="button"
          onClick={load}
          className="min-h-touch rounded-full bg-cream-200 px-5 text-lg font-bold text-ink-700 transition hover:bg-cream-200/70 active:scale-95"
        >
          Refresh
        </button>
      </div>

      {loading ? (
        <p className="text-lg text-ink-500">Loading alerts…</p>
      ) : alerts.length === 0 ? (
        <div className="rounded-3xl bg-white/70 p-8 text-center shadow-sm">
          <p className="text-5xl">🎉</p>
          <p className="mt-2 text-xl font-bold text-ink-900">All clear</p>
          <p className="text-lg text-ink-500">No missed doses or escalations. {patient.name} is doing great.</p>
        </div>
      ) : (
        <ul className="space-y-3">
          {alerts.map((a) => (
            <li
              key={a.id}
              className={`rounded-3xl p-5 shadow-sm ${a.acknowledged ? 'bg-white/60 ring-1 ring-cream-200' : 'border-2 border-red-300 bg-red-50'}`}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex-1">
                  {a.type && (
                    <p className="text-sm font-bold uppercase tracking-wide text-ink-500">{String(a.type).replace(/_/g, ' ')}</p>
                  )}
                  <p className="text-xl font-bold text-ink-900">{a.message}</p>
                  {a.created_at && <p className="mt-1 text-ink-500">{formatDateTime(a.created_at)}</p>}
                </div>
                {a.acknowledged ? (
                  <span className="rounded-full bg-cream-200 px-4 py-2 text-lg font-bold text-ink-500">Seen ✓</span>
                ) : (
                  <button
                    type="button"
                    disabled={busyId === a.id}
                    onClick={() => handleAcknowledge(a)}
                    className="min-h-touch rounded-full bg-brand-600 px-6 text-lg font-bold text-white shadow-md transition hover:bg-brand-700 active:scale-95 disabled:opacity-50"
                  >
                    {busyId === a.id ? 'Saving…' : 'I’ve seen this'}
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
