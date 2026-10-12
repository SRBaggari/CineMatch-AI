import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../api/client.js';
import { defaultPrefs, hasPreference, sanitizePrefs, toPayload } from '../utils/prefs.js';
import { loadJSON, saveJSON } from '../utils/storage.js';

const PREFS_KEY = 'cinematch.preferences.v2';
const AppContext = createContext(null);

const EMPTY_RESULTS = { key: null, data: null, loading: false, error: '', feedbackVersion: 0 };

function toFeedbackMap(items) {
  return Object.fromEntries(items.map((i) => [i.movie_id, { reaction: i.reaction, favorite: i.favorite }]));
}

export function AppProvider({ children }) {
  const [options, setOptions] = useState(null);
  const [dataset, setDataset] = useState(null);
  const [status, setStatus] = useState('loading'); // loading | online | offline
  const [statusError, setStatusError] = useState('');
  const [prefs, setPrefsState] = useState(() => defaultPrefs(null));
  const [results, setResults] = useState(EMPTY_RESULTS);
  // Saved likes / dislikes / favourites (stored in the backend's SQLite database).
  const [feedback, setFeedbackMap] = useState({});
  const [feedbackVersion, setFeedbackVersion] = useState(0);
  const [notice, setNotice] = useState(null);
  const requestId = useRef(0);

  const connect = useCallback(() => {
    setStatus('loading');
    setStatusError('');
    Promise.all([api.options(), api.dataset(), api.feedback()])
      .then(([opts, info, saved]) => {
        setOptions(opts);
        setDataset(info);
        setFeedbackMap(toFeedbackMap(saved.items));
        // Restore saved preferences, dropping anything the catalogue no longer has.
        setPrefsState(sanitizePrefs(loadJSON(PREFS_KEY, null), opts));
        setStatus('online');
      })
      .catch((e) => {
        setStatus('offline');
        setStatusError(e.message);
      });
  }, []);

  useEffect(connect, [connect]);

  useEffect(() => {
    if (!notice) return undefined;
    const id = setTimeout(() => setNotice(null), 4000);
    return () => clearTimeout(id);
  }, [notice]);

  const setPrefs = useCallback((updater) => {
    setPrefsState((prev) => {
      const next = typeof updater === 'function' ? updater(prev) : updater;
      saveJSON(PREFS_KEY, next);
      return next;
    });
  }, []);

  const resetPrefs = useCallback(() => {
    setPrefs(defaultPrefs(options));
    setResults(EMPTY_RESULTS);
  }, [options, setPrefs]);

  const payload = useMemo(() => (options ? toPayload(prefs, options) : null), [prefs, options]);
  const payloadKey = payload ? JSON.stringify(payload) : null;
  const ready = Boolean(options) && hasPreference(prefs, options);

  // Fetch recommendations for the current preferences. Cached by request body so
  // moving between pages does not re-query; `force` re-runs the same request.
  const fetchRecommendations = useCallback(
    async ({ force = false } = {}) => {
      if (!payload || !ready) return;
      if (!force && results.key === payloadKey && (results.data || results.loading)) return;
      const id = ++requestId.current;
      const version = feedbackVersion;
      setResults({ key: payloadKey, data: null, loading: true, error: '', feedbackVersion: version });
      try {
        const data = await api.recommend(payload);
        if (id === requestId.current) setResults({ key: payloadKey, data, loading: false, error: '', feedbackVersion: version });
      } catch (e) {
        if (id === requestId.current) setResults({ key: payloadKey, data: null, loading: false, error: e.message, feedbackVersion: version });
      }
    },
    [payload, payloadKey, ready, results.key, results.data, results.loading, feedbackVersion],
  );

  // Optimistic feedback update; reverts and shows a notice if the server rejects it.
  const updateFeedback = useCallback(async (movie, patch) => {
    const id = movie.movie_id;
    let previous;
    setFeedbackMap((map) => {
      previous = map[id];
      const next = { reaction: null, favorite: false, ...map[id], ...patch };
      const copy = { ...map };
      if (!next.reaction && !next.favorite) delete copy[id];
      else copy[id] = next;
      return copy;
    });
    try {
      const saved = await api.setFeedback(id, patch);
      setFeedbackMap((map) => {
        const copy = { ...map };
        if (!saved.reaction && !saved.favorite) delete copy[id];
        else copy[id] = { reaction: saved.reaction, favorite: saved.favorite };
        return copy;
      });
      setFeedbackVersion((v) => v + 1);
    } catch (e) {
      setFeedbackMap((map) => {
        const copy = { ...map };
        if (previous) copy[id] = previous;
        else delete copy[id];
        return copy;
      });
      setNotice({ tone: 'error', text: `Couldn’t save feedback for ${movie.title}: ${e.message}` });
    }
  }, []);

  const clearAllFeedback = useCallback(async () => {
    try {
      await api.clearFeedback();
      setFeedbackMap({});
      setFeedbackVersion((v) => v + 1);
    } catch (e) {
      setNotice({ tone: 'error', text: `Couldn’t clear feedback: ${e.message}` });
    }
  }, []);

  const resultsCurrent = results.key === payloadKey;
  const value = {
    options,
    dataset,
    status,
    statusError,
    connect,
    prefs,
    setPrefs,
    resetPrefs,
    payload,
    ready,
    results,
    resultsCurrent,
    fetchRecommendations,
    feedback,
    feedbackVersion,
    updateFeedback,
    clearAllFeedback,
    // Results were ranked before the latest like / dislike / favourite change.
    feedbackStale: resultsCurrent && Boolean(results.data) && prefs.useFeedback && results.feedbackVersion !== feedbackVersion,
    notice,
    setNotice,
  };
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used inside <AppProvider>');
  return ctx;
}
