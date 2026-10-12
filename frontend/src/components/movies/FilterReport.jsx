import { Filter } from 'lucide-react';

const LABELS = {
  total: 'Catalogue',
  after_min_rating: 'Min rating',
  after_year_range: 'Year range',
  after_languages: 'Languages',
  after_exclusions: 'Exclusions',
  after_dislikes: 'Not disliked',
  with_positive_score: 'Matching',
};

export default function FilterReport({ report }) {
  return (
    <div className="filter-report" aria-label="Movies remaining after each filter">
      <Filter size={14} />
      {Object.entries(report).map(([key, count], i) => (
        <span key={key} className="filter-step">
          {i > 0 && <span className="arrow">→</span>}
          {LABELS[key] ?? key} <strong>{count}</strong>
        </span>
      ))}
    </div>
  );
}
