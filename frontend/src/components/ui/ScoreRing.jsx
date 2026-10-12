import { useId } from 'react';

// Circular indicator for a match score in [0, 1]. The score is a weighted
// similarity, so it is shown as a decimal rather than as a probability.
export default function ScoreRing({ score, size = 64, label = 'match' }) {
  const gradientId = useId();
  const stroke = Math.max(4, size / 13);
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(1, score));

  return (
    <div
      className="score-ring"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`Match score ${clamped.toFixed(2)} out of 1`}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="var(--purple)" />
            <stop offset="1" stopColor="var(--blue)" />
          </linearGradient>
        </defs>
        <circle className="score-ring-track" cx={size / 2} cy={size / 2} r={radius} strokeWidth={stroke} />
        <circle
          className="score-ring-value"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={stroke}
          stroke={`url(#${gradientId})`}
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - clamped)}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <div className="score-ring-text">
        <strong style={{ fontSize: size / 4.4 }}>{clamped.toFixed(2)}</strong>
        <span>{label}</span>
      </div>
    </div>
  );
}
