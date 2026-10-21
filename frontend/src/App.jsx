import { useCallback, useEffect, useState } from 'react';
import { api, API_URL } from './api';
import ChatTab from './components/ChatTab';
import SetupTab from './components/SetupTab';
import DashboardTab from './components/DashboardTab';
import AlertsTab from './components/AlertsTab';

// CareLoop app shell — four tabs: Chat (default), Setup, Dashboard, Alerts.
// Loads the patient list once; if none exists, prompts the user to visit Setup.

const TABS = [
  { id: 'chat', label: '💬 Chat' },
  { id: 'setup', label: '⚙️ Setup' },
  { id: 'dashboard', label: '📅 Today' },
  { id: 'alerts', label: '🔔 Alerts' },
];

export default function App() {
  const [tab, setTab] = useState('chat');
  const [patients, setPatients] = useState([]);
  const [selectedId, setSelectedId] = useState(() => localStorage.getItem('careloop-patient-id'));
  const [backendOk, setBackendOk] = useState(null); // null = checking
  const [loadError, setLoadError] = useState(null);

  const refreshPatients = useCallback(async (preferId) => {
    try {
      const list = await api.listPatients();
      const arr = Array.isArray(list) ? list : list?.patients || [];
      setPatients(arr);
      const pick = preferId || selectedId || localStorage.getItem('careloop-patient-id');
      const chosen = arr.find((p) => String(p.id) === String(pick)) || arr[0] || null;
      setSelectedId(chosen ? String(chosen.id) : null);
      if (chosen) localStorage.setItem('careloop-patient-id', String(chosen.id));
      else localStorage.removeItem('careloop-patient-id');
      setLoadError(null);
    } catch (err) {
      setLoadError(err.message);
    }
  }, [selectedId]);

  useEffect(() => {
    let cancelled = false;
    api.getHealth()
      .then(() => !cancelled && setBackendOk(true))
      .catch(() => !cancelled && setBackendOk(false));
    refreshPatients();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectedPatient = patients.find((p) => String(p.id) === String(selectedId)) || null;
  const hasPatients = patients.length > 0;

  const handleSelectPatient = (id) => {
    setSelectedId(String(id));
    localStorage.setItem('careloop-patient-id', String(id));
  };

  return (
    <div className="flex min-h-screen flex-col bg-cream-100">
      {/* Header */}
      <header className="border-b-2 border-cream-200 bg-cream-50/90 px-4 py-3 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-full bg-brand-600 text-2xl text-white shadow-md" aria-hidden="true">💊</span>
            <div>
              <h1 className="text-2xl font-extrabold leading-tight text-ink-900">CareLoop</h1>
              <p className="text-sm text-ink-500">Your medication companion</p>
            </div>
          </div>
          {selectedPatient && (
            <p className="hidden rounded-full bg-brand-100 px-4 py-1 text-lg font-bold text-brand-700 sm:block">
              Caring for {selectedPatient.name}
            </p>
          )}
        </div>
      </header>

      {/* Backend status banner */}
      {backendOk === false && (
        <div className="bg-red-100 px-4 py-2 text-center text-lg font-semibold text-red-900" role="alert">
          ⚠️ Can't reach the CareLoop backend at {API_URL}. Start it, or set VITE_API_URL and rebuild.
        </div>
      )}

      {/* Tab navigation — large touch targets */}
      <nav className="border-b-2 border-cream-200 bg-cream-50 px-2 py-2" aria-label="Main">
        <div className="mx-auto grid max-w-5xl grid-cols-4 gap-2">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              aria-current={tab === t.id ? 'page' : undefined}
              className={`min-h-touch rounded-2xl text-lg font-bold transition sm:text-xl ${
                tab === t.id
                  ? 'bg-brand-600 text-white shadow-md'
                  : 'bg-white text-ink-700 ring-1 ring-cream-200 hover:bg-cream-200'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 px-3 py-5 sm:px-6">
        {loadError && tab !== 'setup' && (
          <div className="mx-auto mb-4 max-w-3xl rounded-2xl border-2 border-red-300 bg-red-50 px-4 py-3 text-lg text-red-900" role="alert">
            {loadError}
          </div>
        )}

        {!hasPatients && !loadError && tab !== 'setup' ? (
          <div className="mx-auto max-w-xl rounded-3xl bg-white/70 p-8 text-center shadow-sm">
            <p className="text-5xl">👋</p>
            <h2 className="mt-2 text-2xl font-extrabold text-ink-900">Let's get set up first</h2>
            <p className="mt-1 text-lg text-ink-500">
              Add the person CareLoop will look after, along with their medications — it only takes a minute.
            </p>
            <button
              type="button"
              onClick={() => setTab('setup')}
              className="mt-4 min-h-touch rounded-full bg-brand-600 px-8 text-xl font-bold text-white shadow-md transition hover:bg-brand-700 active:scale-95"
            >
              Go to Setup
            </button>
          </div>
        ) : (
          <>
            {tab === 'chat' && <ChatTab patient={selectedPatient} />}
            {tab === 'setup' && (
              <SetupTab
                patients={patients}
                selectedPatient={selectedPatient}
                onSelectPatient={handleSelectPatient}
                onPatientsChange={refreshPatients}
              />
            )}
            {tab === 'dashboard' && <DashboardTab patient={selectedPatient} />}
            {tab === 'alerts' && <AlertsTab patient={selectedPatient} />}
          </>
        )}
      </main>

      <footer className="px-4 py-3 text-center text-sm text-ink-500">
        CareLoop · built for the Amazon Developer Hackathon · simulated Alexa+ experience
      </footer>
    </div>
  );
}
