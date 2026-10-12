// Thin wrapper around the FastAPI backend. In development VITE_API_URL is empty
// and requests go through the Vite proxy (see vite.config.js).
const BASE_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${BASE_URL}/api${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
  } catch {
    throw new Error('Cannot reach the recommendation server. Is the backend running on port 8000?');
  }

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === 'string') message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((d) => d.msg).join('; ');
    } catch {
      /* keep the generic message */
    }
    throw new Error(message);
  }
  return response.json();
}

export const api = {
  health: () => request('/health'),
  meta: () => request('/meta'),
  searchMovies: (search, limit = 8) =>
    request(`/movies?${new URLSearchParams({ search, limit: String(limit) })}`),
  similar: (movieId, topN = 6) => request(`/movies/${movieId}/similar?top_n=${topN}`),
  recommend: (payload) => request('/recommend', { method: 'POST', body: JSON.stringify(payload) }),
};
