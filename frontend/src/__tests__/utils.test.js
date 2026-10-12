import { describe, expect, it } from 'vitest';
import { formatRuntime } from '../utils/format.js';
import { cosine, tfidf } from '../utils/tfidf.js';

describe('formatRuntime', () => {
  it('shows unknown runtimes as a dash', () => {
    expect(formatRuntime(148)).toBe('148 min');
    expect(formatRuntime(0)).toBe('Runtime —');
  });
});

describe('teaching TF-IDF (matches scikit-learn smooth idf)', () => {
  const model = tfidf(['a thief enters dreams', 'a robot in space', 'a thief in the city']);

  it('down-weights words that appear in more documents', () => {
    expect(model.idf.thief).toBeCloseTo(Math.log(4 / 3) + 1, 10);
    expect(model.idf.dreams).toBeCloseTo(Math.log(4 / 2) + 1, 10);
    expect(model.idf.dreams).toBeGreaterThan(model.idf.thief);
  });

  it('produces unit vectors and correct cosine similarities', () => {
    for (const v of model.vectors) expect(Math.hypot(...v)).toBeCloseTo(1, 10);
    expect(cosine(model.vectors[0], model.vectors[1])).toBe(0);
    expect(cosine(model.vectors[0], model.vectors[2])).toBeGreaterThan(0);
    expect(cosine([1, 1, 0], [1, 1, 1])).toBeCloseTo(2 / Math.sqrt(6), 10);
    expect(cosine([0, 0], [1, 1])).toBe(0);
  });
});
