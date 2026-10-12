// Circular indicator for a relevance score in [0, 1]. It is a weighted similarity,
// so it is shown as a decimal, not as a percentage or probability.
export default function ScoreRing({ score, size = 58, label = 'score' }) {
  const stroke = 5;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(1, score));
  const offset = circumference * (1 - clamped);

  return (
    <div className="score-ring" style={{ width: size, height: size }} title={`Relevance score ${clamped.toFixed(3)} (0-1)`}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle className="score-ring-track" cx={size / 2} cy={size / 2} r={radius} strokeWidth={stroke} />
        <circle
          className="score-ring-value"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <div className="score-ring-text">
        <strong>{clamped.toFixed(2)}</strong>
        <span>{label}</span>
      </div>
    </div>
  );
}
