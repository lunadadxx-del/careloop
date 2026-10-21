import { useEffect, useState } from 'react';
import { api } from '../api';

// Setup tab — create the patient, add caregivers, add medications.
// Elderly-friendly: large inputs, clear labels, inline success/error states.

const COMMON_TIMEZONES = [
  'Asia/Kolkata',
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'Europe/London',
  'Europe/Berlin',
  'Asia/Dubai',
  'Asia/Singapore',
  'Australia/Sydney',
];

// Backend convention: days [0..6] with 0 = Monday (Python weekday()).
const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const inputCls =
  'min-h-touch w-full rounded-2xl border-2 border-cream-200 bg-white px-4 text-lg shadow-sm outline-none placeholder:text-ink-500 focus:border-brand-500';

function Section({ title, subtitle, children }) {
  return (
    <section className="rounded-3xl bg-white/70 p-5 shadow-sm sm:p-6">
      <h2 className="text-2xl font-extrabold text-ink-900">{title}</h2>
      {subtitle && <p className="mt-1 text-lg text-ink-500">{subtitle}</p>}
      <div className="mt-4 space-y-4">{children}</div>
    </section>
  );
}

function Notice({ kind, message, onDismiss }) {
  if (!message) return null;
  const styles =
    kind === 'error'
      ? 'border-red-300 bg-red-50 text-red-900'
      : 'border-brand-500 bg-brand-50 text-brand-700';
  return (
    <div className={`flex items-start justify-between gap-3 rounded-2xl border-2 px-4 py-3 text-lg ${styles}`} role={kind === 'error' ? 'alert' : 'status'}>
      <span>{message}</span>
      {onDismiss && (
        <button type="button" onClick={onDismiss} aria-label="Dismiss" className="text-2xl leading-none">×</button>
      )}
    </div>
  );
}

export default function SetupTab({ patients, selectedPatient, onSelectPatient, onPatientsChange }) {
  // --- patient form ---
  const [pName, setPName] = useState('');
  const [pRel, setPRel] = useState('');
  const [pTz, setPTz] = useState('Asia/Kolkata');
  const [pBusy, setPBusy] = useState(false);

  // --- caregiver form ---
  const [cName, setCName] = useState('');
  const [cPhone, setCPhone] = useState('');
  const [cRel, setCRel] = useState('');
  const [cBusy, setCBusy] = useState(false);
  const [addedCaregivers, setAddedCaregivers] = useState([]); // in-session list (API has no list endpoint)

  // --- medication form ---
  const [mName, setMName] = useState('');
  const [mDosage, setMDosage] = useState('');
  const [mTimes, setMTimes] = useState([]);
  const [timeInput, setTimeInput] = useState('');
  const [mDays, setMDays] = useState([]); // [] = every day
  const [mNotes, setMNotes] = useState('');
  const [mBusy, setMBusy] = useState(false);
  const [medications, setMedications] = useState([]);

  const [notice, setNotice] = useState(null); // {kind, message}

  const showNotice = (kind, message) => setNotice({ kind, message });

  const loadMedications = async (patientId) => {
    if (!patientId) return;
    try {
      const meds = await api.listMedications(patientId);
      setMedications(Array.isArray(meds) ? meds : []);
    } catch {
      setMedications([]); // non-fatal; form still works
    }
  };

  useEffect(() => {
    loadMedications(selectedPatient?.id);
  }, [selectedPatient?.id]);

  const handleCreatePatient = async (e) => {
    e.preventDefault();
    if (!pName.trim()) return showNotice('error', 'Please enter the patient’s name.');
    setPBusy(true);
    try {
      const created = await api.createPatient({
        name: pName.trim(),
        relationship: pRel.trim(),
        timezone: pTz,
      });
      setPName(''); setPRel(''); setPTz('Asia/Kolkata');
      await onPatientsChange(created?.id);
      showNotice('success', `${created?.name || 'Patient'} was added. Now add their medications below.`);
    } catch (err) {
      showNotice('error', err.message);
    } finally {
      setPBusy(false);
    }
  };

  const handleAddCaregiver = async (e) => {
    e.preventDefault();
    if (!selectedPatient) return showNotice('error', 'Please add a patient first.');
    if (!cName.trim()) return showNotice('error', 'Please enter the caregiver’s name.');
    setCBusy(true);
    try {
      await api.addCaregiver(selectedPatient.id, {
        name: cName.trim(),
        phone: cPhone.trim(),
        relation: cRel.trim(),
      });
      setAddedCaregivers((prev) => [...prev, { name: cName.trim(), phone: cPhone.trim(), relation: cRel.trim() }]);
      setCName(''); setCPhone(''); setCRel('');
      showNotice('success', 'Caregiver added. They’ll be contacted if a dose is missed.');
    } catch (err) {
      showNotice('error', err.message);
    } finally {
      setCBusy(false);
    }
  };

  const addTimeChip = () => {
    if (!timeInput) return;
    if (mTimes.includes(timeInput)) return;
    setMTimes((prev) => [...prev, timeInput].sort());
    setTimeInput('');
  };

  const toggleDay = (d) => {
    setMDays((prev) => (prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d].sort()));
  };

  const handleAddMedication = async (e) => {
    e.preventDefault();
    if (!selectedPatient) return showNotice('error', 'Please add a patient first.');
    if (!mName.trim()) return showNotice('error', 'Please enter the medication name.');
    if (mTimes.length === 0) return showNotice('error', 'Please add at least one daily time for this medication.');
    setMBusy(true);
    try {
      await api.addMedication(selectedPatient.id, {
        name: mName.trim(),
        dosage: mDosage.trim(),
        times: mTimes,
        days: mDays.length > 0 ? mDays : undefined, // omit = every day
        notes: mNotes.trim() || undefined,
      });
      setMName(''); setMDosage(''); setMTimes([]); setMDays([]); setMNotes('');
      await loadMedications(selectedPatient.id);
      showNotice('success', 'Medication added to the daily schedule.');
    } catch (err) {
      showNotice('error', err.message);
    } finally {
      setMBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Notice kind={notice?.kind} message={notice?.message} onDismiss={() => setNotice(null)} />

      {/* Patient */}
      <Section title="Who are we caring for?" subtitle="Add the person whose medications CareLoop will look after.">
        {patients.length > 0 && (
          <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Choose patient">
            {patients.map((p) => (
              <button
                key={p.id}
                type="button"
                role="radio"
                aria-checked={selectedPatient?.id === p.id}
                onClick={() => onSelectPatient(p.id)}
                className={`min-h-touch rounded-full px-5 text-lg font-bold shadow-sm transition ${
                  selectedPatient?.id === p.id
                    ? 'bg-brand-600 text-white'
                    : 'bg-cream-100 text-ink-700 hover:bg-cream-200'
                }`}
              >
                {p.name}
              </button>
            ))}
          </div>
        )}
        <form onSubmit={handleCreatePatient} className="grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="mb-1 block text-lg font-semibold">Full name</span>
            <input className={inputCls} value={pName} onChange={(e) => setPName(e.target.value)} placeholder="e.g. Meera Sharma" />
          </label>
          <label className="block">
            <span className="mb-1 block text-lg font-semibold">Relationship to you</span>
            <input className={inputCls} value={pRel} onChange={(e) => setPRel(e.target.value)} placeholder="e.g. Mother" />
          </label>
          <label className="block sm:col-span-2">
            <span className="mb-1 block text-lg font-semibold">Timezone</span>
            <select className={inputCls} value={pTz} onChange={(e) => setPTz(e.target.value)}>
              {COMMON_TIMEZONES.map((tz) => (
                <option key={tz} value={tz}>{tz}</option>
              ))}
            </select>
          </label>
          <button
            type="submit"
            disabled={pBusy}
            className="min-h-touch rounded-full bg-brand-600 px-6 text-lg font-bold text-white shadow-md transition hover:bg-brand-700 active:scale-95 disabled:opacity-50 sm:col-span-2"
          >
            {pBusy ? 'Adding…' : 'Add patient'}
          </button>
        </form>
      </Section>

      {/* Caregivers */}
      <Section title="Caregivers" subtitle="Family members CareLoop will contact if a dose is missed.">
        {addedCaregivers.length > 0 && (
          <ul className="space-y-2">
            {addedCaregivers.map((c, i) => (
              <li key={i} className="flex flex-wrap items-center justify-between gap-2 rounded-2xl bg-cream-100 px-4 py-2 text-lg">
                <span className="font-bold">{c.name}</span>
                <span className="text-ink-500">{c.relation}{c.phone ? ` · ${c.phone}` : ''}</span>
              </li>
            ))}
          </ul>
        )}
        <form onSubmit={handleAddCaregiver} className="grid gap-3 sm:grid-cols-3">
          <label className="block">
            <span className="mb-1 block text-lg font-semibold">Name</span>
            <input className={inputCls} value={cName} onChange={(e) => setCName(e.target.value)} placeholder="e.g. Rahul Sharma" />
          </label>
          <label className="block">
            <span className="mb-1 block text-lg font-semibold">Phone</span>
            <input className={inputCls} value={cPhone} onChange={(e) => setCPhone(e.target.value)} placeholder="+91 …" inputMode="tel" />
          </label>
          <label className="block">
            <span className="mb-1 block text-lg font-semibold">Relation</span>
            <input className={inputCls} value={cRel} onChange={(e) => setCRel(e.target.value)} placeholder="e.g. Son" />
          </label>
          <button
            type="submit"
            disabled={cBusy || !selectedPatient}
            className="min-h-touch rounded-full bg-brand-600 px-6 text-lg font-bold text-white shadow-md transition hover:bg-brand-700 active:scale-95 disabled:opacity-50 sm:col-span-3"
          >
            {cBusy ? 'Adding…' : 'Add caregiver'}
          </button>
        </form>
      </Section>

      {/* Medications */}
      <Section title="Medications" subtitle="Add each medicine with its daily times.">
        {medications.length > 0 && (
          <ul className="space-y-2">
            {medications.map((m, i) => (
              <li key={m.id || i} className="rounded-2xl bg-cream-100 px-4 py-2 text-lg">
                <span className="font-bold">{m.name}</span>
                {m.dosage && <span className="text-ink-700"> · {m.dosage}</span>}
                {m.times && <span className="text-ink-500"> · {Array.isArray(m.times) ? m.times.join(', ') : m.times}</span>}
              </li>
            ))}
          </ul>
        )}
        <form onSubmit={handleAddMedication} className="grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="mb-1 block text-lg font-semibold">Medication name</span>
            <input className={inputCls} value={mName} onChange={(e) => setMName(e.target.value)} placeholder="e.g. Metformin" />
          </label>
          <label className="block">
            <span className="mb-1 block text-lg font-semibold">Dosage</span>
            <input className={inputCls} value={mDosage} onChange={(e) => setMDosage(e.target.value)} placeholder="e.g. 500 mg" />
          </label>
          <div className="sm:col-span-2">
            <span className="mb-1 block text-lg font-semibold">Daily times</span>
            <div className="flex flex-wrap items-center gap-2">
              {mTimes.map((t) => (
                <span key={t} className="flex items-center gap-2 rounded-full bg-brand-100 px-4 py-2 text-lg font-bold text-brand-700">
                  {t}
                  <button type="button" onClick={() => setMTimes((prev) => prev.filter((x) => x !== t))} aria-label={`Remove ${t}`} className="text-xl leading-none">×</button>
                </span>
              ))}
              <div className="flex items-center gap-2">
                <input
                  type="time"
                  value={timeInput}
                  onChange={(e) => setTimeInput(e.target.value)}
                  aria-label="Time of day"
                  className="min-h-touch rounded-2xl border-2 border-cream-200 bg-white px-3 text-lg outline-none focus:border-brand-500"
                />
                <button
                  type="button"
                  onClick={addTimeChip}
                  className="min-h-touch rounded-full bg-cream-200 px-5 text-lg font-bold text-ink-700 transition hover:bg-cream-200/70 active:scale-95"
                >
                  Add time
                </button>
              </div>
            </div>
          </div>
          <div className="sm:col-span-2">
            <span className="mb-1 block text-lg font-semibold">Days <span className="font-normal text-ink-500">(leave all off for every day)</span></span>
            <div className="flex flex-wrap gap-2">
              {DAY_LABELS.map((label, d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => toggleDay(d)}
                  aria-pressed={mDays.includes(d)}
                  className={`min-h-touch min-w-touch rounded-full px-4 text-lg font-bold transition ${
                    mDays.includes(d) ? 'bg-brand-600 text-white' : 'bg-cream-100 text-ink-700 hover:bg-cream-200'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <label className="block sm:col-span-2">
            <span className="mb-1 block text-lg font-semibold">Notes <span className="font-normal text-ink-500">(optional)</span></span>
            <input className={inputCls} value={mNotes} onChange={(e) => setMNotes(e.target.value)} placeholder="e.g. Take with food" />
          </label>
          <button
            type="submit"
            disabled={mBusy || !selectedPatient}
            className="min-h-touch rounded-full bg-brand-600 px-6 text-lg font-bold text-white shadow-md transition hover:bg-brand-700 active:scale-95 disabled:opacity-50 sm:col-span-2"
          >
            {mBusy ? 'Adding…' : 'Add medication'}
          </button>
        </form>
      </Section>
    </div>
  );
}
