import { Brain, Filter, Info } from 'lucide-react';
import { COMPONENTS, COMPONENT_INFO } from '../utils/components.js';

const FILTER_LABELS = {
  total: 'Catalogue',
  after_min_rating: 'Min rating',
  after_year_range: 'Year range',
  after_languages: 'Languages',
  after_exclusions: 'Exclude liked',
  with_positive_score: 'Any match',
};

export function FilterReport({ report }) {
  return (
    <div className="filter-report">
      <Filter size={13} />
      {Object.entries(report).map(([key, count], i) => (
        <span key={key}>
          {i > 0 && <span className="arrow">→</span>}
          {FILTER_LABELS[key] ?? key} <strong>{count}</strong>
        </span>
      ))}
    </div>
  );
}

export default function TasteProfile({ result }) {
  const { profile } = result;
  const maxWeight = Math.max(...profile.top_terms.map((t) => t.weight), 0.0001);

  return (
    <section className="panel taste-profile">
      <div className="panel-heading">
        <Brain size={18} />
        <h2>Your Preference Profile</h2>
      </div>

      <div className="profile-grid">
        <div className="profile-facts">
          {profile.genres.length > 0 && (
            <p>
              <span className="field-label">Genres{profile.genres_inferred && ' (inferred from liked movies)'}:</span>{' '}
              {profile.genres.join(', ')}
            </p>
          )}
          {profile.moods.length > 0 && (
            <p>
              <span className="field-label">Moods{profile.moods_inferred && ' (inferred)'}:</span> {profile.moods.join(', ')}
            </p>
          )}
          {profile.languages.length > 0 && (
            <p>
              <span className="field-label">Languages:</span> {profile.languages.join(', ')}
            </p>
          )}
          {(profile.year_min || profile.year_max) && (
            <p>
              <span className="field-label">Years:</span> {profile.year_min ?? 'any'} – {profile.year_max ?? 'any'}
            </p>
          )}
          {profile.top_terms.length > 0 && (
            <>
              <p className="field-label">Strongest terms in your TF-IDF keyword profile</p>
              <div className="term-cloud">
                {profile.top_terms.map((t) => (
                  <span
                    key={t.term}
                    className="term"
                    style={{ '--strength': (0.35 + 0.65 * (t.weight / maxWeight)).toFixed(2) }}
                    title={`TF-IDF weight ${t.weight}`}
                  >
                    {t.term}
                  </span>
                ))}
              </div>
            </>
          )}
        </div>

        <div>
          <p className="field-label">Effective weights (normalised to sum to 1)</p>
          <div className="weights">
            {COMPONENTS.map((k) => (
              <div key={k} className={`weight ${profile.weights[k] === 0 ? 'inactive' : ''}`} title={COMPONENT_INFO[k].help}>
                <span>{COMPONENT_INFO[k].label}</span>
                <strong>{profile.weights[k].toFixed(2)}</strong>
              </div>
            ))}
          </div>
          <FilterReport report={result.filter_report} />
        </div>
      </div>

      {result.warnings.length > 0 && (
        <div className="warnings">
          {result.warnings.map((w) => (
            <p key={w}>
              <Info size={14} /> {w}
            </p>
          ))}
        </div>
      )}
    </section>
  );
}
