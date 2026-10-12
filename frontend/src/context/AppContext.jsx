import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../api/client.js';
import { defaultPrefs, hasPreference, sanitizePrefs, toPayload } from '../utils/prefs.js';
import { loadJSON, saveJSON } from '../utils/storage.js';

const PREFS_KEY = 'cinematch.preferences.v2';
const AppContext = createContext(null);

const EMPTY_RESULTS = { key: null, data: null, loading: false, error: '' };

export function AppProvider({ children }) {
  const [options, setOptions] = useState(null);
  const [dataset, setDataset] = useState(null);
  const [status, setStatus] = useState('loading'); // loading | online | offline
  const [statusError, setStatusError] = useState('');
  const [prefs, setPrefsState] = useState(() => defaultPrefs(null));
  const [results, setResults] = useState(EMPTY_RESULTS);
  const requestId = useRef(0);

  const connect = useCallback(() => {
    setStatus('loading');
    setStatusError('');
    Promise.all([api.options(), api.dataset()])
      .then(([opts, info]) => {
        setOptions(opts);
        setDataset(info);
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
      setResults({ key: payloadKey, data: null, loading: true, error: '' });
      try {
        const data = await api.recommend(payload);
        if (id === requestId.current) setResults({ key: payloadKey, data, loading: false, error: '' });
      } catch (e) {
        if (id === requestId.current) setResults({ key: payloadKey, data: null, loading: false, error: e.message });
      }
    },
    [payload, payloadKey, ready, results.key, results.data, results.loading],
  );

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
    resultsCurrent: results.key === payloadKey,
    fetchRecommendations,
  };
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used inside <AppProvider>');
  return ctx;
}
