import { COMPONENTS, COMPONENT_INFO } from '../../utils/components.js';

export default function ScoreBreakdown({ components, total }) {
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
      <div className="breakdown-total">
        <span>Match score (sum of contributions)</span>
        <strong>{total.toFixed(3)}</strong>
      </div>
    </div>
  );
}
