import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft,
  ArrowRight,
  Calendar,
  Check,
  ChevronDown,
  ChevronUp,
  Pencil,
  RotateCcw,
  Scale,
  Sparkles,
  Star,
} from 'lucide-react';
import KeywordInput from '../components/preferences/KeywordInput.jsx';
import MovieSearch from '../components/preferences/MovieSearch.jsx';
import Stepper from '../components/preferences/Stepper.jsx';
import ChipSelector from '../components/ui/ChipSelector.jsx';
import { ErrorState, Spinner } from '../components/ui/Feedback.jsx';
import MultiSelectDropdown from '../components/ui/MultiSelectDropdown.jsx';
import RangeSlider from '../components/ui/RangeSlider.jsx';
import Toggle from '../components/ui/Toggle.jsx';
import { useApp } from '../context/AppContext.jsx';
import { COMPONENTS, COMPONENT_INFO } from '../utils/components.js';
import { genreStyle } from '../utils/genres.js';
import { moodStyle } from '../utils/moods.js';
import { countSelections, hasYearPreference } from '../utils/prefs.js';

function toggleValue(list, value) {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

function plural(n, word) {
  return `${n} ${word}${n === 1 ? '' : 's'}`;
}

function StepHeader({ title, text, optional }) {
  return (
    <header className="step-header">
      <h2>
        {title} {optional && <span className="optional">optional</span>}
      </h2>
      <p className="muted">{text}</p>
    </header>
  );
}

export default function PreferencesPage() {
  const { options, status, statusError, connect, prefs, setPrefs, resetPrefs, ready, fetchRecommendations } = useApp();
  const [params, setParams] = useSearchParams();
  const [showWeights, setShowWeights] = useState(false);
  const navigate = useNavigate();

  if (!options) {
    return (
      <div className="page container narrow">
        {status === 'offline' ? (
          <ErrorState title="Can’t load preference options" message={statusError} onRetry={connect} />
        ) : (
          <Spinner label="Loading preference options…" />
        )}
      </div>
    );
  }

  const update = (patch) => setPrefs((p) => ({ ...p, ...patch }));
  const yearSet = hasYearPreference(prefs, options);
  const eras = [
    { label: 'Any era', range: [options.year_min, options.year_max] },
    { label: 'Classics', range: [options.year_min, 1989] },
    { label: '90s & 2000s', range: [1990, 2009] },
    { label: 'Modern', range: [2010, options.year_max] },
  ];

  const steps = [
    { id: 'genres', title: 'Genres', done: prefs.genres.length > 0, summary: prefs.genres.length ? plural(prefs.genres.length, 'genre') : 'Pick a few' },
    { id: 'languages', title: 'Languages', done: prefs.languages.length > 0, summary: prefs.languages.length ? prefs.languages.slice(0, 2).join(', ') : 'Any' },
    { id: 'mood', title: 'Mood', done: prefs.moods.length > 0, summary: prefs.moods.length ? prefs.moods.slice(0, 2).join(', ') : 'Any' },
    { id: 'themes', title: 'Themes', done: prefs.keywords.length + prefs.likedMovies.length > 0, summary: prefs.keywords.length ? plural(prefs.keywords.length, 'theme') : 'Optional' },
    { id: 'era', title: 'Era & rating', done: yearSet || prefs.minRating > 0, summary: yearSet ? `${prefs.yearMin}–${prefs.yearMax}` : 'Any era' },
    { id: 'review', title: 'Review', done: false, summary: ready ? 'Ready' : 'Needs a preference' },
  ];

  const stepIndex = Math.min(steps.length - 1, Math.max(0, Number(params.get('step')) || 0));
  const goTo = (index) => {
    setParams(index ? { step: String(index) } : {}, { replace: false });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };
  const isLast = stepIndex === steps.length - 1;
  const weightTotal = COMPONENTS.reduce((sum, c) => sum + (prefs.weights[c] || 0), 0);
  const selections = countSelections(prefs, options);

  const generate = () => {
    if (!ready || weightTotal === 0) return;
    fetchRecommendations({ force: true });
    navigate('/recommendations');
  };

  return (
    <div className="page preferences-page container">
      <div className="page-head">
        <span className="eyebrow">
          <Sparkles size={14} /> Step {stepIndex + 1} of {steps.length}
        </span>
        <h1>Tell us what you love</h1>
        <p className="muted">Your choices are saved on this device, so you can come back and change them any time.</p>
      </div>

      <Stepper steps={steps} current={stepIndex} onSelect={goTo} />

      <div className="step-panel glass" key={steps[stepIndex].id}>
        {stepIndex === 0 && (
          <>
            <StepHeader title="Favourite genres" text="Select every genre you enjoy. More genres means a broader search." />
            <ChipSelector
              label="Genres"
              options={Object.keys(options.genres).sort()}
              selected={prefs.genres}
              counts={options.genres}
              iconFor={(g) => genreStyle(g).icon}
              onToggle={(g) => update({ genres: toggleValue(prefs.genres, g) })}
            />
          </>
        )}

        {stepIndex === 1 && (
          <>
            <StepHeader
              title="Preferred languages"
              text="Movies in these languages get a boost. Turn on strict mode to see only these languages."
              optional
            />
            <div className="field-grid">
              <MultiSelectDropdown
                label="Languages"
                options={Object.keys(options.languages)}
                selected={prefs.languages}
                counts={options.languages}
                placeholder="Any language"
                onChange={(languages) => update({ languages })}
              />
              <Toggle
                checked={prefs.strictLanguages}
                onChange={(v) => update({ strictLanguages: v })}
                label="Only these languages"
                description="Hard filter: other languages are removed."
              />
            </div>
          </>
        )}

        {stepIndex === 2 && (
          <>
            <StepHeader title="Current mood" text="How do you want to feel tonight? Choose one or more." optional />
            <div className="mood-grid">
              {Object.keys(options.moods)
                .sort()
                .map((mood) => {
                  const { icon: Icon, blurb } = moodStyle(mood);
                  const active = prefs.moods.includes(mood);
                  return (
                    <button
                      key={mood}
                      type="button"
                      className={`mood-card ${active ? 'is-active' : ''}`}
                      aria-pressed={active}
                      onClick={() => update({ moods: toggleValue(prefs.moods, mood) })}
                    >
                      <span className="mood-icon">
                        <Icon size={22} />
                      </span>
                      <strong>{mood}</strong>
                      <span className="muted small">{blurb}</span>
                      {active && (
                        <span className="mood-check">
                          <Check size={14} strokeWidth={3} />
                        </span>
                      )}
                    </button>
                  );
                })}
            </div>
          </>
        )}

        {stepIndex === 3 && (
          <>
            <StepHeader
              title="Movie themes"
              text="Add themes or keywords. They are matched against movie keywords and descriptions using TF-IDF."
              optional
            />
            <KeywordInput
              keywords={prefs.keywords}
              suggestions={Object.keys(options.popular_keywords)}
              onAdd={(k) => !prefs.keywords.some((x) => x.toLowerCase() === k.toLowerCase()) && update({ keywords: [...prefs.keywords, k] })}
              onRemove={(k) => update({ keywords: prefs.keywords.filter((x) => x !== k) })}
            />
            <div className="sub-section">
              <h3>Movies you already love</h3>
              <p className="muted small">Their themes join your profile, and they won’t be recommended back to you.</p>
              <MovieSearch
                liked={prefs.likedMovies}
                onAdd={(movie) =>
                  update({ likedMovies: [...prefs.likedMovies, { movie_id: movie.movie_id, title: movie.title, year: movie.year }] })
                }
                onRemove={(id) => update({ likedMovies: prefs.likedMovies.filter((m) => m.movie_id !== id) })}
              />
            </div>
          </>
        )}

        {stepIndex === 4 && (
          <>
            <StepHeader title="Era & rating" text="Movies inside your year range score higher. Movies below your minimum rating are removed." optional />
            <div className="era-grid">
              {eras.map((era) => {
                const active = prefs.yearMin === era.range[0] && prefs.yearMax === era.range[1];
                return (
                  <button
                    key={era.label}
                    type="button"
                    className={`era-card ${active ? 'is-active' : ''}`}
                    aria-pressed={active}
                    onClick={() => update({ yearMin: era.range[0], yearMax: era.range[1] })}
                  >
                    <Calendar size={18} />
                    <strong>{era.label}</strong>
                    <span className="muted small">
                      {era.range[0]}–{era.range[1]}
                    </span>
                  </button>
                );
              })}
            </div>
            <div className="field-block">
              <span className="field-label">Release-year range</span>
              <RangeSlider
                label="Release year"
                min={options.year_min}
                max={options.year_max}
                low={prefs.yearMin}
                high={prefs.yearMax}
                onChange={([yearMin, yearMax]) => update({ yearMin, yearMax })}
              />
              <Toggle
                checked={prefs.strictYears}
                onChange={(v) => update({ strictYears: v })}
                label="Only movies inside this range"
                description="Hard filter instead of a soft preference."
              />
            </div>
            <div className="field-grid">
              <div className="field-block">
                <span className="field-label">
                  Minimum rating{' '}
                  <strong className="rating-value">
                    <Star size={14} fill="currentColor" /> {prefs.minRating > 0 ? prefs.minRating.toFixed(1) : 'Any'}
                  </strong>
                </span>
                <input
                  type="range"
                  className="single-range"
                  min={0}
                  max={9.5}
                  step={0.1}
                  value={prefs.minRating}
                  style={{ '--fill': `${(prefs.minRating / 9.5) * 100}%` }}
                  aria-label="Minimum rating"
                  onChange={(e) => update({ minRating: Number(e.target.value) })}
                />
                <div className="range-scale muted small">
                  <span>Any</span>
                  <span>9.5</span>
                </div>
              </div>
              <label className="field-block">
                <span className="field-label">Number of recommendations</span>
                <span className="select-shell">
                  <select value={prefs.topN} onChange={(e) => update({ topN: Number(e.target.value) })}>
                    {[5, 10, 15, 20, 30].map((n) => (
                      <option key={n} value={n}>
                        Top {n}
                      </option>
                    ))}
                  </select>
                  <ChevronDown size={18} />
                </span>
              </label>
            </div>
          </>
        )}

        {stepIndex === 5 && (
          <>
            <StepHeader title="Review your preferences" text="Check your choices, then generate your personalised list." />
            <dl className="review-list">
              {[
                ['Genres', prefs.genres.join(', ') || 'Any', 0],
                ['Languages', prefs.languages.length ? `${prefs.languages.join(', ')}${prefs.strictLanguages ? ' (only)' : ''}` : 'Any', 1],
                ['Mood', prefs.moods.join(', ') || 'Any', 2],
                ['Themes', prefs.keywords.join(', ') || 'None', 3],
                ['Movies you love', prefs.likedMovies.map((m) => m.title).join(', ') || 'None', 3],
                ['Release years', yearSet ? `${prefs.yearMin}–${prefs.yearMax}${prefs.strictYears ? ' (only)' : ''}` : 'Any', 4],
                ['Minimum rating', prefs.minRating > 0 ? prefs.minRating.toFixed(1) : 'Any', 4],
                ['Results', `Top ${prefs.topN}`, 4],
              ].map(([label, value, step]) => (
                <div key={label} className="review-row">
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                  <button type="button" className="icon-btn" onClick={() => goTo(step)} aria-label={`Edit ${label}`}>
                    <Pencil size={15} />
                  </button>
                </div>
              ))}
            </dl>

            <div className="sub-section">
              <button type="button" className="disclosure" onClick={() => setShowWeights((s) => !s)} aria-expanded={showWeights}>
                <Scale size={17} /> Advanced: scoring weights
                {showWeights ? <ChevronUp size={17} /> : <ChevronDown size={17} />}
              </button>
              {showWeights && (
                <div className="weight-editor">
                  <p className="muted small">
                    How much each part of the match counts. Weights are rescaled to add up to 1 across the preferences
                    you actually set.
                  </p>
                  {COMPONENTS.map((c) => (
                    <label key={c} className="weight-row">
                      <span>{COMPONENT_INFO[c].label}</span>
                      <input
                        type="range"
                        className="single-range"
                        min={0}
                        max={1}
                        step={0.05}
                        value={prefs.weights[c]}
                        style={{ '--fill': `${prefs.weights[c] * 100}%` }}
                        onChange={(e) => update({ weights: { ...prefs.weights, [c]: Number(e.target.value) } })}
                      />
                      <strong>{weightTotal ? Math.round((prefs.weights[c] / weightTotal) * 100) : 0}%</strong>
                    </label>
                  ))}
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => update({ weights: { ...options.default_weights } })}>
                    <RotateCcw size={14} /> Default weights
                  </button>
                </div>
              )}
            </div>

            <button type="button" className="btn btn-primary btn-xl generate-btn" onClick={generate} disabled={!ready || weightTotal === 0}>
              <Sparkles size={20} /> Generate My Recommendations
            </button>
            {!ready && <p className="muted small center">Choose at least one genre, language, mood, theme, liked movie or a narrower year range.</p>}
          </>
        )}
      </div>

      <div className="action-bar glass">
        <button type="button" className="btn btn-ghost" onClick={() => goTo(stepIndex - 1)} disabled={stepIndex === 0}>
          <ArrowLeft size={17} /> <span className="hide-sm">Back</span>
        </button>
        <div className="action-bar-info">
          <strong>{plural(selections, 'selection')}</strong>
          <button type="button" className="link-btn" onClick={resetPrefs} disabled={selections === 0}>
            Clear all
          </button>
        </div>
        {isLast ? (
          <button type="button" className="btn btn-primary" onClick={generate} disabled={!ready || weightTotal === 0}>
            <Sparkles size={17} /> Generate
          </button>
        ) : (
          <div className="action-bar-right">
            <button type="button" className="btn btn-ghost hide-sm" onClick={generate} disabled={!ready || weightTotal === 0}>
              <Sparkles size={16} /> Generate now
            </button>
            <button type="button" className="btn btn-primary" onClick={() => goTo(stepIndex + 1)}>
              Next <ArrowRight size={17} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
