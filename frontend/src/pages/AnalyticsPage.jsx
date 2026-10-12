import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChartColumn, Database, RefreshCw } from 'lucide-react';
import { api } from '../api/client.js';
import { BarList, ChartCard, DataTable, Histogram, StatTile } from '../components/charts/Charts.jsx';
import { ErrorState, Spinner } from '../components/ui/Feedback.jsx';
import { useApp } from '../context/AppContext.jsx';

const toBars = (obj) => Object.entries(obj).map(([label, value]) => ({ label, value }));

export default function AnalyticsPage() {
  const { status, feedbackVersion } = useApp();
  const [state, setState] = useState({ data: null, loading: true, error: '' });

  const load = useCallback(() => {
    setState((s) => ({ ...s, loading: true, error: '' }));
    api
      .analytics()
      .then((data) => setState({ data, loading: false, error: '' }))
      .catch((e) => setState((s) => ({ ...s, loading: false, error: e.message })));
  }, []);

  useEffect(() => {
    if (status === 'online') load();
  }, [status, load, feedbackVersion]);

  const { data, loading, error } = state;
  if (error && !data) {
    return (
      <div className="page container narrow">
        <ErrorState title="Couldn’t load analytics" message={error} onRetry={load} />
      </div>
    );
  }
  if (!data) {
    return (
      <div className="page container narrow">
        <Spinner label="Loading analytics…" />
      </div>
    );
  }

  const { dataset, usage, feedback } = data;
  const genreBars = toBars(dataset.genre_distribution);
  const selectedBars = toBars(usage.genre_selections).slice(0, 10);
  const noUsage = usage.total_requests === 0;
  const usageEmpty = (
    <>
      No recommendation requests have been logged on this installation yet.{' '}
      <Link to="/preferences">Generate recommendations</Link> to start collecting usage data.
    </>
  );

  return (
    <div className="page analytics-page container">
      <div className="page-head results-head">
        <div>
          <span className="eyebrow">
            <ChartColumn size={14} /> Analytics
          </span>
          <h1>Catalogue & usage analytics</h1>
          <p className="muted">
            Catalogue figures come from the movie dataset. Usage figures come only from recommendation requests logged in
            this installation’s local database. Nothing is estimated.
          </p>
        </div>
        <button type="button" className="btn btn-ghost" onClick={load} disabled={loading}>
          <RefreshCw size={16} className={loading ? 'spin' : ''} /> Refresh
        </button>
      </div>

      <div className="stat-grid">
        <StatTile label="Movies available" value={dataset.total_movies} note={`${Object.keys(dataset.genre_distribution).length} genres · ${Object.keys(dataset.language_distribution).length} languages`} />
        <StatTile label="Recommendation requests" value={usage.total_requests} note={`${usage.recommendations_served} recommendations served`} />
        <StatTile label="Average match score" value={usage.average_score === null ? '—' : usage.average_score.toFixed(2)} note="Of recommendations served (0–1)" />
        <StatTile label="Your feedback" value={feedback.likes + feedback.dislikes + feedback.favorites} note={`${feedback.likes} likes · ${feedback.dislikes} dislikes · ${feedback.favorites} favourites`} />
      </div>

      <div className="chart-grid">
        <ChartCard
          title="Genre distribution"
          subtitle="Movies per genre in the catalogue (a movie can have several genres)"
          table={<DataTable columns={['Genre', 'Movies']} rows={genreBars.map((d) => [d.label, d.value])} />}
        >
          <BarList data={genreBars} unit=" movies" />
        </ChartCard>

        <ChartCard
          title="Most frequently selected genres"
          subtitle={`Explicit genre choices across ${usage.total_requests} logged request${usage.total_requests === 1 ? '' : 's'}`}
          empty={noUsage || selectedBars.length === 0 ? (noUsage ? usageEmpty : 'Requests so far used no explicit genres.') : null}
          table={<DataTable columns={['Genre', 'Times selected']} rows={selectedBars.map((d) => [d.label, d.value])} />}
        >
          <BarList data={selectedBars} unit=" selections" />
        </ChartCard>

        <ChartCard
          title="Recommendation score distribution"
          subtitle="Final relevance scores of every recommendation served, in 0.1-wide bins"
          empty={noUsage ? usageEmpty : null}
          table={<DataTable columns={['Score range', 'Recommendations']} rows={usage.score_distribution.map((b) => [b.label, b.count])} />}
        >
          <Histogram bins={usage.score_distribution} xLabel="Match score (0–1)" yLabel="Recommendations" />
        </ChartCard>

        <ChartCard
          title="Catalogue rating distribution"
          subtitle={`Approximate ratings (unverified); average ${dataset.average_rating}`}
          table={<DataTable columns={['Rating', 'Movies']} rows={dataset.rating_distribution.map((b) => [b.label, b.count])} />}
        >
          <Histogram bins={dataset.rating_distribution} xLabel="Rating out of 10" yLabel="Movies" />
        </ChartCard>

        <ChartCard
          title="Languages"
          subtitle="Movies per original language"
          table={<DataTable columns={['Language', 'Movies']} rows={toBars(dataset.language_distribution).map((d) => [d.label, d.value])} />}
        >
          <BarList data={toBars(dataset.language_distribution)} unit=" movies" />
        </ChartCard>

        <ChartCard
          title="Most recommended movies"
          subtitle="How often each movie appeared in served recommendations"
          empty={noUsage ? usageEmpty : null}
          table={<DataTable columns={['Movie', 'Times recommended']} rows={usage.most_recommended.map((m) => [m.title, m.count])} />}
        >
          <BarList data={usage.most_recommended.map((m) => ({ label: m.title, value: m.count }))} unit=" times" />
        </ChartCard>
      </div>

      <section className="engine-panel glass">
        <h2>
          <Database size={18} /> Engine performance
        </h2>
        <dl>
          <div>
            <dt>Feature vectors</dt>
            <dd>{dataset.feature_source === 'disk-cache' ? 'Loaded from the on-disk cache (no TF-IDF re-fit)' : 'Fitted at startup, then cached to disk'}</dd>
          </div>
          <div>
            <dt>TF-IDF vocabulary</dt>
            <dd>{dataset.vocabulary_size} terms</dd>
          </div>
          <div>
            <dt>Score cache</dt>
            <dd>
              {dataset.score_cache.hits} hits · {dataset.score_cache.misses} misses · {dataset.score_cache.size}/{dataset.score_cache.capacity} preference sets cached
            </dd>
          </div>
        </dl>
        <ul className="muted small notes">
          {data.notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
