// Thin wrapper around the FastAPI backend. In development VITE_API_URL is empty
// and requests go through the Vite proxy (see vite.config.js).
const BASE_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

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
    throw new ApiError('Cannot reach the CineMatch AI server. Make sure the backend is running.', 0);
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
    throw new ApiError(message, response.status);
  }
  return response.json();
}

const post = (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) });
const put = (path, body) => request(path, { method: 'PUT', body: JSON.stringify(body) });
const del = async (path) => {
  try {
    const response = await fetch(`${BASE_URL}/api${path}`, { method: 'DELETE' });
    if (!response.ok) throw new ApiError(`Request failed (${response.status})`, response.status);
  } catch (e) {
    throw e instanceof ApiError ? e : new ApiError('Cannot reach the CineMatch AI server.', 0);
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
