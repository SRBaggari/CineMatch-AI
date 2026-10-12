import { useState } from 'react';
import { Table2 } from 'lucide-react';

// Single-series charts built from plain HTML so they stay responsive and accessible.
// One validated series colour (--chart-1); text always uses text colours, never the bar colour.

// Axis scale for counts: whole-number ticks stepping by 1, 2 or 5 × 10^n (about 4 intervals).
function countScale(value) {
  if (value <= 0) return { max: 1, ticks: [0, 1] };
  const raw = value / 4;
  const exp = 10 ** Math.floor(Math.log10(raw));
  const step = Math.max(1, [1, 2, 5, 10].find((s) => s * exp >= raw) * exp);
  const max = Math.ceil(value / step) * step;
  return { max, ticks: Array.from({ length: max / step + 1 }, (_, i) => i * step) };
}

export function ChartCard({ title, subtitle, children, table, empty }) {
  const [showTable, setShowTable] = useState(false);
  return (
    <section className="chart-card glass">
      <header className="chart-head">
        <div>
          <h2>{title}</h2>
          {subtitle && <p className="muted small">{subtitle}</p>}
        </div>
        {table && !empty && (
          <button type="button" className={`chip chip-sm ${showTable ? 'is-active' : ''}`} aria-pressed={showTable} onClick={() => setShowTable((s) => !s)}>
            <Table2 size={14} /> Table
          </button>
        )}
      </header>
      {empty ? <div className="chart-empty muted">{empty}</div> : showTable ? table : children}
    </section>
  );
}

export function DataTable({ rows, columns }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c} scope="col">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, r) => (
            <tr key={`${r}-${row[0]}`}>
              {row.map((cell, i) => (
                <td key={columns[i]}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Horizontal bars: label column, bar from a shared baseline, value at the tip.
export function BarList({ data, unit = '', formatValue = (v) => v }) {
  const [hover, setHover] = useState(null);
  const { max, ticks } = countScale(Math.max(...data.map((d) => d.value)));
  const total = data.reduce((s, d) => s + d.value, 0);
  return (
    <div className="bar-list" role="list">
      <div className="bar-grid" aria-hidden="true">
        {ticks.map((t) => (
          <span key={t} style={{ left: `${(t / max) * 100}%` }}>
            <i>{t}</i>
          </span>
        ))}
      </div>
      {data.map((d, i) => {
        const share = total ? Math.round((d.value / total) * 100) : 0;
        return (
          <div
            key={`${i}-${d.label}`}
            className={`bar-row ${hover === i ? 'is-hover' : ''}`}
            role="listitem"
            tabIndex={0}
            aria-label={`${d.label}: ${formatValue(d.value)}${unit}`}
            onMouseEnter={() => setHover(i)}
            onMouseLeave={() => setHover(null)}
            onFocus={() => setHover(i)}
            onBlur={() => setHover(null)}
          >
            <span className="bar-label">{d.label}</span>
            <span className="bar-track">
              <span className="bar-mark" style={{ width: `${(d.value / max) * 100}%` }} />
              <span className="bar-value">{formatValue(d.value)}</span>
              {hover === i && (
                <span className="chart-tooltip" role="tooltip" style={{ left: `${Math.min(80, (d.value / max) * 100)}%` }}>
                  <strong>{d.label}</strong>
                  <span>
                    {formatValue(d.value)}
                    {unit} · {share}% of total
                  </span>
                </span>
              )}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// Vertical columns for histograms: touching bins separated by a 2px surface gap.
export function Histogram({ bins, xLabel, yLabel = 'Count', highlight }) {
  const [hover, setHover] = useState(null);
  const { max, ticks } = countScale(Math.max(...bins.map((b) => b.count)));
  return (
    <figure className="histogram">
      <div className="hist-plot">
        <div className="hist-grid" aria-hidden="true">
          {ticks.map((t) => (
            <span key={t} style={{ bottom: `${(t / max) * 100}%` }}>
              <i>{t}</i>
            </span>
          ))}
        </div>
        <div className="hist-bars" role="list">
          {bins.map((b) => (
            <div
              key={b.label}
              className={`hist-bin ${hover === b.label ? 'is-hover' : ''}`}
              role="listitem"
              tabIndex={0}
              aria-label={`${b.label}: ${b.count}`}
              onMouseEnter={() => setHover(b.label)}
              onMouseLeave={() => setHover(null)}
              onFocus={() => setHover(b.label)}
              onBlur={() => setHover(null)}
            >
              {b.count > 0 && (
                <span className={`hist-mark ${highlight?.(b) ? 'is-accent' : ''}`} style={{ height: `${(b.count / max) * 100}%` }} />
              )}
              {hover === b.label && (
                <span className="chart-tooltip hist-tooltip" role="tooltip">
                  <strong>{b.label}</strong>
                  <span>
                    {b.count} {yLabel.toLowerCase()}
                  </span>
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
      <div className="hist-axis" aria-hidden="true">
        {bins.map((b, i) => (
          <span key={b.label}>{i % 2 === 0 || bins.length <= 8 ? b.start : ''}</span>
        ))}
      </div>
      <figcaption className="muted small">
        {xLabel}; each column is labelled by its bin’s lower bound · y-axis: {yLabel.toLowerCase()}
      </figcaption>
    </figure>
  );
}

export function StatTile({ label, value, note }) {
  return (
    <div className="stat-tile glass">
      <span className="stat-label">{label}</span>
      <strong className="stat-value">{value}</strong>
      {note && <span className="muted small">{note}</span>}
    </div>
  );
}
