import { COMPONENTS, COMPONENT_INFO } from '../utils/components.js';

export default function ScoreBreakdown({ components, total }) {
  return (
    <div className="breakdown">
      {COMPONENTS.map((key) => {
        const part = components[key];
        return (
          <div key={key} className={`breakdown-row ${part.active ? '' : 'inactive'}`} title={COMPONENT_INFO[key].help}>
            <div className="breakdown-label">
              <span>
                {COMPONENT_INFO[key].label}
                {!part.active && <span className="muted"> (not used)</span>}
                {key === 'keyword' && part.active && <span className="muted"> · raw cosine {part.raw.toFixed(3)}</span>}
              </span>
              <span className="muted">
                {part.value.toFixed(2)} × {part.weight.toFixed(2)} = <strong>{part.contribution.toFixed(3)}</strong>
              </span>
            </div>
            <div className="bar">
              <div className={`bar-fill bar-${key}`} style={{ width: `${Math.min(100, part.value * 100)}%` }} />
            </div>
          </div>
        );
      })}
      <div className="breakdown-total">
        Relevance score <strong>{total.toFixed(3)}</strong>
      </div>
    </div>
  );
}
