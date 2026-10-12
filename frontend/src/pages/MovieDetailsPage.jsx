import { useCallback, useEffect, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  CircleCheck,
  Clock,
  Film,
  Globe,
  Lightbulb,
  SearchX,
  SlidersHorizontal,
  Sparkles,
  Star,
  Users,
} from 'lucide-react';
import { api } from '../api/client.js';
import MovieTile from '../components/movies/MovieTile.jsx';
import ScoreBreakdown from '../components/movies/ScoreBreakdown.jsx';
import { ErrorState, Spinner, StateMessage } from '../components/ui/Feedback.jsx';
import Poster from '../components/ui/Poster.jsx';
import ScoreRing from '../components/ui/ScoreRing.jsx';
import { useApp } from '../context/AppContext.jsx';

function similarCaption(item) {
  const shared = [...item.shared_genres, ...item.shared_moods].slice(0, 3).join(', ');
  return `similarity ${item.similarity.toFixed(2)}${shared ? ` · ${shared}` : ''}`;
}

function MatchPanel({ explanation, loading, error, ready }) {
  if (!ready) {
    return (
      <div className="match-panel glass match-empty">
        <Sparkles size={26} />
        <h2>How well does this match you?</h2>
        <p className="muted">Set your preferences to see this movie’s match score and a full explanation.</p>
        <Link to="/preferences" className="btn btn-primary">
          <SlidersHorizontal size={16} /> Set preferences
        </Link>
      </div>
    );
  }
  if (loading) {
    return (
      <div className="match-panel glass">
        <Spinner label="Scoring this movie against your preferences…" />
      </div>
    );
  }
  if (error) {
    return (
      <div className="match-panel glass">
        <p className="error-text">{error}</p>
      </div>
    );
  }
  if (!explanation) return null;

  const { rank, passes_filters: passes, filtered_by: filteredBy, candidates, score, matched } = explanation;
  let status;
  if (rank) status = `Ranked #${rank} of ${candidates} matching movies for your preferences.`;
  else if (filteredBy.length) status = `Not in your results: ${filteredBy.join('; ')}.`;
  else status = 'This movie does not match any of your current preferences.';

  const highlights = [
    ...matched.genres.map((g) => `Genre: ${g}`),
    ...matched.moods.map((m) => `Mood: ${m}`),
    ...matched.keywords.map((k) => `Theme: ${k}`),
    ...(matched.language ? [`Language: ${matched.language}`] : []),
    ...(matched.year_in_range ? ['Release year in your range'] : []),
  ];

  return (
    <section className="match-panel glass" aria-labelledby="match-heading">
      <div className="match-top">
        <ScoreRing score={score} size={96} label="match" />
        <div>
          <h2 id="match-heading">Match explanation</h2>
          <p className={passes && rank ? 'match-status' : 'match-status is-muted'}>{status}</p>
        </div>
      </div>

      {highlights.length > 0 && (
        <div className="tag-row">
          {highlights.map((h) => (
            <span key={h} className="tag is-match">
              <CircleCheck size={12} /> {h}
            </span>
          ))}
        </div>
      )}

      <ul className="reason-list">
        {explanation.reasons.map((reason) => (
          <li key={reason}>
            <Lightbulb size={15} /> {reason}
          </li>
        ))}
      </ul>

      {explanation.top_terms.length > 0 && (
        <p className="muted small">
          Strongest shared TF-IDF terms: <strong className="text">{explanation.top_terms.join(' · ')}</strong>
        </p>
      )}

      <ScoreBreakdown components={explanation.components} total={score} />
    </section>
  );
}

export default function MovieDetailsPage() {
  const { movieId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { status, payload, ready } = useApp();
  const id = Number(movieId);
  const validId = Number.isInteger(id) && id > 0;

  const [movieState, setMovieState] = useState({ movie: null, similar: [], loading: true, error: '', notFound: false });
  const [explain, setExplain] = useState({ data: null, loading: false, error: '' });

  const loadMovie = useCallback(() => {
    if (!validId) {
      setMovieState({ movie: null, similar: [], loading: false, error: '', notFound: true });
      return () => {};
    }
    let cancelled = false;
    setMovieState((s) => ({ ...s, loading: true, error: '', notFound: false }));
    Promise.all([api.getMovie(id), api.similar(id, 6)])
      .then(([movie, similar]) => !cancelled && setMovieState({ movie, similar: similar.similar, loading: false, error: '', notFound: false }))
      .catch((e) => {
        if (cancelled) return;
        setMovieState({ movie: null, similar: [], loading: false, error: e.status === 404 ? '' : e.message, notFound: e.status === 404 });
      });
    return () => {
      cancelled = true;
    };
  }, [id, validId]);

  useEffect(() => {
    if (status === 'offline') return undefined;
    return loadMovie();
  }, [loadMovie, status]);

  // Explanation for the current preferences (same scoring as the results page).
  const payloadKey = payload ? JSON.stringify(payload) : '';
  const movieLoaded = movieState.movie?.movie_id === id;
  useEffect(() => {
    if (!movieLoaded || !ready || !payloadKey) {
      setExplain({ data: null, loading: false, error: '' });
      return undefined;
    }
    let cancelled = false;
    setExplain({ data: null, loading: true, error: '' });
    api
      .explain(id, JSON.parse(payloadKey))
      .then((data) => !cancelled && setExplain({ data, loading: false, error: '' }))
      .catch((e) => !cancelled && setExplain({ data: null, loading: false, error: e.message }));
    return () => {
      cancelled = true;
    };
  }, [id, movieLoaded, ready, payloadKey]);

  const goBack = () => (location.key !== 'default' ? navigate(-1) : navigate('/recommendations'));
  const { movie, similar, loading, error, notFound } = movieState;

  if (notFound) {
    return (
      <div className="page container narrow">
        <StateMessage
          icon={SearchX}
          title="Movie not found"
          action={
            <Link to="/recommendations" className="btn btn-primary">
              Back to recommendations
            </Link>
          }
        >
          <p>There is no movie with id “{movieId}” in the catalogue.</p>
        </StateMessage>
      </div>
    );
  }
  if (error) {
    return (
      <div className="page container narrow">
        <ErrorState title="Couldn’t load this movie" message={error} onRetry={loadMovie} />
      </div>
    );
  }
  if (loading || !movie) {
    return (
      <div className="page container narrow">
        <Spinner label="Loading movie…" />
      </div>
    );
  }

  return (
    <div className="page details-page">
      <section className="details-hero">
        <div className="details-backdrop" aria-hidden="true">
          <Poster movie={movie} size="backdrop" showCaption={false} />
        </div>
        <div className="container details-hero-inner">
          <button type="button" className="btn btn-ghost btn-sm back-btn" onClick={goBack}>
            <ArrowLeft size={16} /> Back
          </button>
          <div className="details-main">
            <Poster movie={movie} size="xl" />
            <div className="details-info">
              <h1>{movie.title}</h1>
              <div className="meta-row large">
                <span>{movie.year}</span>
                <span title="Approximate rating (unverified)">
                  <Star size={15} fill="currentColor" className="star" /> {movie.rating.toFixed(1)}/10
                </span>
                <span>
                  <Clock size={15} /> {movie.runtime} min
                </span>
                <span>
                  <Globe size={15} /> {movie.language}
                </span>
              </div>
              <div className="tag-row">
                {movie.genres.map((g) => (
                  <span key={g} className="tag tag-genre">
                    {g}
                  </span>
                ))}
                {movie.moods.map((m) => (
                  <span key={m} className="tag tag-mood">
                    {m}
                  </span>
                ))}
              </div>
              <p className="details-overview">{movie.overview}</p>
              <dl className="details-credits">
                <div>
                  <dt>
                    <Film size={14} /> Director
                  </dt>
                  <dd>{movie.director}</dd>
                </div>
                <div>
                  <dt>
                    <Users size={14} /> Cast
                  </dt>
                  <dd>{movie.cast.join(', ')}</dd>
                </div>
              </dl>
              <div>
                <span className="field-label">Keywords</span>
                <div className="tag-row">
                  {movie.keywords.map((k) => (
                    <span key={k} className="tag tag-keyword">
                      #{k}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="container details-body">
        <MatchPanel explanation={explain.data} loading={explain.loading} error={explain.error} ready={ready} />

        <section className="section" aria-labelledby="similar-heading">
          <div className="section-head">
            <div>
              <span className="eyebrow">More like this</span>
              <h2 id="similar-heading">Similar movies</h2>
            </div>
            <p className="muted small section-note">Cosine similarity of the movies’ genre, mood, theme and language vectors.</p>
          </div>
          <div className="similar-grid">
            {similar.map((item) => (
              <MovieTile key={item.movie.movie_id} movie={item.movie} caption={similarCaption(item)} />
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
