// Thin wrapper around the FastAPI backend. In development VITE_API_URL is empty
// and requests go through the Vite proxy (see vite.config.js).
const BASE_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

const UNREACHABLE = 'Cannot reach the CineMatch AI server. Make sure the backend is running.';

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${BASE_URL}/api${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
  } catch {
    throw new ApiError(UNREACHABLE, 0);
  }

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    let parsed = false;
    try {
      const body = await response.json();
      parsed = true;
      if (typeof body.detail === 'string') message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((d) => d.msg).join('; ');
    } catch {
      /* keep the generic message */
    }
    // Behind the dev proxy a stopped backend shows up as 502 Bad Gateway (verified); 503/504 are
    // the other gateway failures. A genuine backend 500 keeps its own message.
    if (!parsed && response.status >= 502 && response.status <= 504) throw new ApiError(UNREACHABLE, 0);
    throw new ApiError(message, response.status);
  }
  return response.json();
}

const post = (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) });
const put = (path, body) => request(path, { method: 'PUT', body: JSON.stringify(body) });
const del = async (path) => {
  try {
    const response = await fetch(`${BASE_URL}/api${path}`, { method: 'DELETE' });
    if (response.status >= 502 && response.status <= 504) throw new ApiError(UNREACHABLE, 0);
    if (!response.ok) throw new ApiError(`Request failed (${response.status})`, response.status);
  } catch (e) {
    throw e instanceof ApiError ? e : new ApiError(UNREACHABLE, 0);
  }
};

export const api = {
  health: () => request('/health'),
  dataset: () => request('/dataset'),
  options: () => request('/preferences/options'),
  listMovies: (params = {}) => request(`/movies?${new URLSearchParams(params)}`),
  searchMovies: (search, limit = 8) => api.listMovies({ search, limit: String(limit) }).then((page) => page.items),
  getMovie: (movieId) => request(`/movies/${movieId}`),
  similar: (movieId, topN = 6) => request(`/movies/${movieId}/similar?top_n=${topN}`),
  recommend: (payload) => post('/recommendations', payload),
  explain: (movieId, payload) => post(`/movies/${movieId}/explain`, payload),
  search: (payload) => post('/movies/search', payload),
  analytics: () => request('/analytics'),
  feedback: () => request('/feedback'),
  setFeedback: (movieId, patch) => put(`/feedback/${movieId}`, patch),
  clearFeedback: (movieId) => del(movieId ? `/feedback/${movieId}` : '/feedback'),
};
