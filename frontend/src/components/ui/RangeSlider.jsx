// Dual-thumb range slider built from two overlaid native range inputs, so it
// keeps keyboard and screen-reader support for free.
export default function RangeSlider({ min, max, step = 1, low, high, onChange, label, format = (v) => v }) {
  const pct = (v) => ((v - min) / (max - min)) * 100;
  return (
    <div className="range-slider">
      <div className="range-values">
        <span>{format(low)}</span>
        <span className="muted">to</span>
        <span>{format(high)}</span>
      </div>
      <div className="range-track-wrap">
        <div className="range-track" />
        <div className="range-fill" style={{ left: `${pct(low)}%`, right: `${100 - pct(high)}%` }} />
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={low}
          aria-label={`${label} from`}
          onChange={(e) => onChange([Math.min(Number(e.target.value), high), high])}
        />
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={high}
          aria-label={`${label} to`}
          onChange={(e) => onChange([low, Math.max(Number(e.target.value), low)])}
        />
      </div>
      <div className="range-scale muted small">
        <span>{format(min)}</span>
        <span>{format(max)}</span>
      </div>
    </div>
  );
}
