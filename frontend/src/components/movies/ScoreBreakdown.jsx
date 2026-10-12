import { COMPONENTS, COMPONENT_INFO } from '../../utils/components.js';

// Full breakdown: the five preference components sum to the preference score, then
// the feedback adjustment is shown on its own line before the final score.
export default function ScoreBreakdown({ item }) {
  const { components, feedback } = item;
  const adj = item.feedback_adjustment;
  return (
    <div className="breakdown">
      {COMPONENTS.map((key) => {
        const part = components[key];
        return (
          <div key={key} className={`breakdown-row ${part.active ? '' : 'is-inactive'}`}>
            <div className="breakdown-label">
              <span>
                <strong>{COMPONENT_INFO[key].label}</strong>
                <span className="muted small"> {part.active ? COMPONENT_INFO[key].help : 'not used — no preference set'}</span>
              </span>
              <span className="breakdown-math">
                {part.value.toFixed(2)} × {part.weight.toFixed(2)} = <strong>{part.contribution.toFixed(3)}</strong>
              </span>
            </div>
            <div className="bar">
              <div className={`bar-fill fill-${key}`} style={{ width: `${Math.min(100, part.value * 100)}%` }} />
            </div>
          </div>
        );
      })}
      <div className="breakdown-sum">
        <span>Preference score (sum of contributions)</span>
        <strong className="mono">{item.base_score.toFixed(3)}</strong>
      </div>
      <div className={`breakdown-sum feedback-line ${feedback.applied ? '' : 'is-inactive'}`}>
        <span>
          Feedback adjustment
          <span className="muted small">
            {' '}
            {!feedback.applied
              ? 'not used — no saved feedback, or feedback is switched off'
              : feedback.closest_liked && adj > 0
                ? `similar to ${feedback.closest_liked.title} (${feedback.liked_similarity.toFixed(2)}), which you liked`
                : feedback.closest_disliked && adj < 0
                  ? `similar to ${feedback.closest_disliked.title} (${feedback.disliked_similarity.toFixed(2)}), which you disliked`
                  : 'liked and disliked movies balance out'}
          </span>
        </span>
        <strong className="mono">
          {adj >= 0 ? '+' : '−'}
          {Math.abs(adj).toFixed(3)}
        </strong>
      </div>
      <div className="breakdown-total">
        <span>Overall relevance score</span>
        <strong>{item.score.toFixed(3)}</strong>
      </div>
    </div>
  );
}
