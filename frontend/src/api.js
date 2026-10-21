// CareLoop API client.
// Base URL is configurable via VITE_API_URL (defaults to http://localhost:8000).
// Every helper throws a plain Error with a friendly message on failure so the
// UI can show inline, human-readable feedback.

const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

async function request(path, { method = 'GET', body } = {}) {
  let res;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : {},
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    // Network-level failure (backend down, wrong URL, CORS blocked)
    throw new Error(
      `Could not reach the CareLoop backend at ${API_URL}. Make sure it is running and VITE_API_URL is correct.`
    );
  }

  let data = null;
  try {
    data = await res.json();
  } catch {
    // Non-JSON response — treat as an error below if not ok
  }

  if (!res.ok) {
    const detail =
      (data && (data.detail || data.message || data.error)) ||
      `Request failed (${res.status})`;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return data;
}

export const api = {
  getHealth: () => request('/api/health'),

  listPatients: () => request('/api/patients'),
  createPatient: ({ name, relationship, timezone }) =>
    request('/api/patients', { method: 'POST', body: { name, relationship, timezone } }),

  addCaregiver: (patientId, { name, phone, relation }) =>
    request(`/api/patients/${patientId}/caregivers`, {
      method: 'POST',
      body: { name, phone, relation },
    }),

  addMedication: (patientId, { name, dosage, times, days, notes }) =>
    request(`/api/patients/${patientId}/medications`, {
      method: 'POST',
      body: { name, dosage, times, days, notes },
    }),
  listMedications: (patientId) => request(`/api/patients/${patientId}/medications`),

  getTodaySchedule: (patientId) => request(`/api/patients/${patientId}/schedule/today`),

  sendChat: ({ session_id, message, patient_id }) =>
    request('/api/chat', { method: 'POST', body: { session_id, message, patient_id } }),

  recordDoseEvent: (doseId, event) =>
    request(`/api/doses/${doseId}/event`, { method: 'POST', body: { event } }),

  getAdherence: (patientId, days = 7) =>
    request(`/api/patients/${patientId}/adherence?days=${days}`),

  listAlerts: (patientId) => request(`/api/patients/${patientId}/alerts`),

  // NOTE: the API contract lists no explicit acknowledge endpoint; alerts carry
  // an `acknowledged` flag. We try the conventional REST route below and the UI
  // degrades gracefully (friendly inline error) if the backend does not support it.
  acknowledgeAlert: (alertId) =>
    request(`/api/alerts/${alertId}/acknowledge`, { method: 'POST' }),

  // Demo helper: forces the next pending dose into "due" state.
  triggerDueDemo: (patientId) =>
    request('/api/demo/trigger-due', { method: 'POST', body: { patient_id: patientId } }),
};

export { API_URL };
