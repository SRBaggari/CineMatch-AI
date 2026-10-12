// Shows the preference score and the feedback adjustment as separate numbers.
export default function ScoreSummary({ item, compact = false }) {
  const adj = item.feedback_adjustment;
  const applied = item.feedback?.applied && adj !== 0;
  const sign = adj > 0 ? '+' : '−';
  return (
    <div className={`score-summary ${compact ? 'is-compact' : ''}`}>
      <span title="Weighted match of your preferences (0–1)">
        Preference <strong>{item.base_score.toFixed(2)}</strong>
      </span>
      {applied && (
        <>
          <span className={`adj ${adj > 0 ? 'is-up' : 'is-down'}`} title="Adjustment from your likes, dislikes and favourites">
            {sign} feedback <strong>{Math.abs(adj).toFixed(2)}</strong>
          </span>
          <span>
            = <strong>{item.score.toFixed(2)}</strong>
          </span>
        </>
      )}
    </div>
  );
}
