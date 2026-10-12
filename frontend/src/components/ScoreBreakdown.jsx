const LABELS = {
  content: { name: 'Content similarity', help: 'Cosine similarity of TF-IDF vectors' },
  genre: { name: 'Genre overlap', help: 'Jaccard index of genres' },
  mood: { name: 'Mood overlap', help: 'Jaccard index of moods' },
  quality: { name: 'Quality', help: 'Normalised rating' },
};

export default function ScoreBreakdown({ breakdown, total }) {
  return (
    <div className="breakdown">
      {Object.entries(breakdown).map(([key, part]) => (
        <div key={key} className={`breakdown-row ${part.weight === 0 ? 'inactive' : ''}`} title={LABELS[key]?.help}>
          <div className="breakdown-label">
            <span>{LABELS[key]?.name ?? key}</span>
            <span className="muted">
              {part.score.toFixed(2)} × {part.weight.toFixed(2)} = <strong>{part.contribution.toFixed(3)}</strong>
            </span>
          </div>
          <div className="bar">
            <div className={`bar-fill bar-${key}`} style={{ width: `${Math.min(100, part.score * 100)}%` }} />
          </div>
        </div>
      ))}
      <div className="breakdown-total">
        Final score <strong>{total.toFixed(3)}</strong>
      </div>
    </div>
  );
}
