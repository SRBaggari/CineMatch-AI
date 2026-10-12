import { useState } from 'react';
import { ChevronDown, ChevronUp, LoaderCircle, RotateCcw, Scale, SlidersHorizontal, Sparkles } from 'lucide-react';
import ChipSelector from './ChipSelector.jsx';
import KeywordInput from './KeywordInput.jsx';
import MovieSearch from './MovieSearch.jsx';
import { genreStyle } from '../utils/genres.js';
import { COMPONENTS, COMPONENT_INFO } from '../utils/components.js';

function toggle(list, value) {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

function Section({ step, title, hint, children }) {
  return (
    <section className="pref-section">
      <header>
        <span className="step">{step}</span>
        <div>
          <h3>{title}</h3>
          {hint && <p className="hint">{hint}</p>}
        </div>
      </header>
      {children}
    </section>
  );
}

function StrictToggle({ checked, onChange, label }) {
  return (
    <label className="toggle">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span>{label}</span>
    </label>
  );
}

function RangeField({ label, value, display, ...props }) {
  return (
    <label className="range-field">
      <span>
        {label} <strong>{display ?? value}</strong>
      </span>
      <input type="range" value={value} {...props} />
    </label>
  );
}

export default function PreferencePanel({ options, prefs, setPrefs, onSubmit, onReset, loading, hasSignal }) {
  const [showWeights, setShowWeights] = useState(false);
  const update = (patch) => setPrefs((p) => ({ ...p, ...patch }));

  const genres = Object.keys(options.genres).sort();
  const moods = Object.keys(options.moods).sort();
  const languages = Object.keys(options.languages);
  const weightTotal = COMPONENTS.reduce((sum, c) => sum + prefs.weights[c], 0);

  return (
    <form
      className="panel preference-panel"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
    >
      <div className="panel-heading">
        <SlidersHorizontal size={18} />
        <h2>Your Preferences</h2>
      </div>

      <Section step="1" title="Favourite genres">
        <ChipSelector
          options={genres}
          selected={prefs.genres}
          onToggle={(g) => update({ genres: toggle(prefs.genres, g) })}
          iconFor={(g) => genreStyle(g).icon}
        />
      </Section>

      <Section step="2" title="Preferred languages" hint="Scored as a preference unless you make it strict.">
        <ChipSelector
          options={languages}
          selected={prefs.languages}
          counts={options.languages}
          onToggle={(l) => update({ languages: toggle(prefs.languages, l) })}
        />
        <StrictToggle
          checked={prefs.strictLanguages}
          onChange={(v) => update({ strictLanguages: v })}
          label="Only show these languages (hard filter)"
        />
      </Section>

      <Section step="3" title="Mood" hint="How do you want to feel?">
        <ChipSelector options={moods} selected={prefs.moods} onToggle={(m) => update({ moods: toggle(prefs.moods, m) })} />
      </Section>

      <Section step="4" title="Keywords & themes" hint="Matched against keywords and descriptions with TF-IDF.">
        <KeywordInput
          keywords={prefs.keywords}
          suggestions={Object.keys(options.popular_keywords)}
          onAdd={(k) => !prefs.keywords.includes(k) && update({ keywords: [...prefs.keywords, k] })}
          onRemove={(k) => update({ keywords: prefs.keywords.filter((x) => x !== k) })}
        />
      </Section>

      <Section step="5" title="Movies you love" hint="Optional: their themes join your keyword profile.">
        <MovieSearch
          liked={prefs.likedMovies}
          onAdd={(movie) =>
            update({
              likedMovies: [...prefs.likedMovies, { movie_id: movie.movie_id, title: movie.title, year: movie.year }],
            })
          }
          onRemove={(id) => update({ likedMovies: prefs.likedMovies.filter((m) => m.movie_id !== id) })}
        />
      </Section>

      <Section step="6" title="Release years & rating" hint="A full year range means no year preference.">
        <div className="filter-grid">
          <RangeField
            label="From"
            min={options.year_min}
            max={options.year_max}
            value={prefs.yearMin}
            onChange={(e) => update({ yearMin: Math.min(Number(e.target.value), prefs.yearMax) })}
          />
          <RangeField
            label="To"
            min={options.year_min}
            max={options.year_max}
            value={prefs.yearMax}
            onChange={(e) => update({ yearMax: Math.max(Number(e.target.value), prefs.yearMin) })}
          />
          <RangeField
            label="Minimum rating"
            min={0}
            max={9}
            step={0.1}
            value={prefs.minRating}
            display={prefs.minRating.toFixed(1)}
            onChange={(e) => update({ minRating: Number(e.target.value) })}
          />
          <RangeField
            label="Results"
            min={1}
            max={options.max_top_n}
            value={prefs.topN}
            onChange={(e) => update({ topN: Number(e.target.value) })}
          />
        </div>
        <StrictToggle
          checked={prefs.strictYears}
          onChange={(v) => update({ strictYears: v })}
          label="Only show movies inside this range (hard filter)"
        />
      </Section>

      <section className="pref-section">
        <button type="button" className="advanced-toggle" onClick={() => setShowWeights((s) => !s)}>
          <Scale size={15} /> Scoring weights
          {showWeights ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
        </button>
        {showWeights && (
          <div className="weight-editor">
            <p className="hint">
              Relative importance of each component. Weights are normalised to sum to 1 over the preferences you set.
            </p>
            {COMPONENTS.map((c) => (
              <RangeField
                key={c}
                label={COMPONENT_INFO[c].label}
                min={0}
                max={1}
                step={0.05}
                value={prefs.weights[c]}
                display={`${prefs.weights[c].toFixed(2)} (${weightTotal ? Math.round((prefs.weights[c] / weightTotal) * 100) : 0}%)`}
                onChange={(e) => update({ weights: { ...prefs.weights, [c]: Number(e.target.value) } })}
              />
            ))}
            <button
              type="button"
              className="btn btn-small btn-ghost"
              onClick={() => update({ weights: { ...options.default_weights } })}
            >
              <RotateCcw size={13} /> Default weights
            </button>
          </div>
        )}
      </section>

      <div className="panel-actions">
        <button type="submit" className="btn btn-primary" disabled={loading || !hasSignal || weightTotal === 0}>
          {loading ? <LoaderCircle size={18} className="spin" /> : <Sparkles size={18} />}
          {loading ? 'Scoring…' : 'Get Recommendations'}
        </button>
        <button type="button" className="btn btn-ghost" onClick={onReset} disabled={loading}>
          <RotateCcw size={16} /> Reset
        </button>
      </div>
      {!hasSignal && (
        <p className="hint center">Choose at least one genre, language, mood, keyword, movie or a narrower year range.</p>
      )}
    </form>
  );
}
