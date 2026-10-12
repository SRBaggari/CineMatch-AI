import { Globe, LoaderCircle, RotateCcw, SlidersHorizontal, Sparkles } from 'lucide-react';
import ChipSelector from './ChipSelector.jsx';
import KeywordInput from './KeywordInput.jsx';
import MovieSearch from './MovieSearch.jsx';
import { genreStyle } from '../utils/genres.js';

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

export default function PreferencePanel({ meta, prefs, setPrefs, onSubmit, onReset, loading, hasSignal }) {
  const update = (patch) => setPrefs((p) => ({ ...p, ...patch }));

  const genres = Object.keys(meta.genres).sort();
  const moods = Object.keys(meta.moods).sort();
  const languages = Object.keys(meta.languages);

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

      <Section step="1" title="Favourite genres" hint="Pick any number of genres.">
        <ChipSelector
          options={genres}
          selected={prefs.genres}
          onToggle={(g) => update({ genres: toggle(prefs.genres, g) })}
          iconFor={(g) => genreStyle(g).icon}
        />
      </Section>

      <Section step="2" title="Mood" hint="How do you want to feel?">
        <ChipSelector
          options={moods}
          selected={prefs.moods}
          onToggle={(m) => update({ moods: toggle(prefs.moods, m) })}
        />
      </Section>

      <Section step="3" title="Movies you love" hint="Their content patterns shape your taste profile.">
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

      <Section step="4" title="Themes & keywords" hint="Press Enter to add your own.">
        <KeywordInput
          keywords={prefs.keywords}
          suggestions={Object.keys(meta.popular_keywords)}
          onAdd={(k) => !prefs.keywords.includes(k) && update({ keywords: [...prefs.keywords, k] })}
          onRemove={(k) => update({ keywords: prefs.keywords.filter((x) => x !== k) })}
        />
      </Section>

      <Section step="5" title="Filters">
        <div className="filter-grid">
          <label className="range-field">
            <span>
              From year <strong>{prefs.yearMin}</strong>
            </span>
            <input
              type="range"
              min={meta.year_min}
              max={meta.year_max}
              value={prefs.yearMin}
              onChange={(e) => update({ yearMin: Math.min(Number(e.target.value), prefs.yearMax) })}
            />
          </label>
          <label className="range-field">
            <span>
              To year <strong>{prefs.yearMax}</strong>
            </span>
            <input
              type="range"
              min={meta.year_min}
              max={meta.year_max}
              value={prefs.yearMax}
              onChange={(e) => update({ yearMax: Math.max(Number(e.target.value), prefs.yearMin) })}
            />
          </label>
          <label className="range-field">
            <span>
              Minimum rating <strong>{prefs.minRating.toFixed(1)}</strong>
            </span>
            <input
              type="range"
              min={0}
              max={9}
              step={0.1}
              value={prefs.minRating}
              onChange={(e) => update({ minRating: Number(e.target.value) })}
            />
          </label>
          <label className="range-field">
            <span>
              Results <strong>{prefs.topN}</strong>
            </span>
            <input
              type="range"
              min={4}
              max={24}
              step={1}
              value={prefs.topN}
              onChange={(e) => update({ topN: Number(e.target.value) })}
            />
          </label>
        </div>

        <div className="language-row">
          <span className="field-label">
            <Globe size={14} /> Languages <span className="muted">(none = all)</span>
          </span>
          <ChipSelector
            options={languages}
            selected={prefs.languages}
            counts={meta.languages}
            onToggle={(l) => update({ languages: toggle(prefs.languages, l) })}
          />
        </div>
      </Section>

      <div className="panel-actions">
        <button type="submit" className="btn btn-primary" disabled={loading || !hasSignal}>
          {loading ? <LoaderCircle size={18} className="spin" /> : <Sparkles size={18} />}
          {loading ? 'Analysing…' : 'Get Recommendations'}
        </button>
        <button type="button" className="btn btn-ghost" onClick={onReset} disabled={loading}>
          <RotateCcw size={16} /> Reset
        </button>
      </div>
      {!hasSignal && <p className="hint center">Choose at least one genre, mood, movie or keyword.</p>}
    </form>
  );
}
