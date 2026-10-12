import { Brain, Database, Info } from 'lucide-react';

const WEIGHT_LABELS = { content: 'Content', genre: 'Genre', mood: 'Mood', quality: 'Quality' };

export default function TasteProfile({ result }) {
  const { profile } = result;
  const maxWeight = Math.max(...profile.top_terms.map((t) => t.weight), 0.0001);

  return (
    <section className="panel taste-profile">
      <div className="panel-heading">
        <Brain size={18} />
        <h2>Your AI Taste Profile</h2>
      </div>

      <div className="profile-grid">
        <div>
          <p className="field-label">Strongest features in your profile vector</p>
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
        </div>

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
          <div className="weights">
            {Object.entries(profile.weights).map(([k, w]) => (
              <div key={k} className={`weight ${w === 0 ? 'inactive' : ''}`}>
                <span>{WEIGHT_LABELS[k]}</span>
                <strong>{Math.round(w * 100)}%</strong>
              </div>
            ))}
          </div>
          <p className="muted small">
            <Database size={12} /> Scored {result.candidates_considered} of {result.total_movies} movies after filters.
          </p>
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
