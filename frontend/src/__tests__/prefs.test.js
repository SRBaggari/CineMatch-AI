import { describe, expect, it } from 'vitest';
import {
  FALLBACK_WEIGHTS,
  MAX_LIST_ITEMS,
  activeComponents,
  activeWeightTotal,
  defaultPrefs,
  hasPreference,
  nearestTopN,
  sanitizePrefs,
  sanitizeWeights,
  toPayload,
} from '../utils/prefs.js';

const OPTIONS = {
  genres: { Drama: 75, Comedy: 29, Horror: 10 },
  moods: { Dark: 30, Funny: 20 },
  languages: { English: 104, Hindi: 10 },
  year_min: 1966,
  year_max: 2023,
  default_top_n: 10,
  max_top_n: 50,
  default_weights: { genre: 0.3, keyword: 0.25, mood: 0.2, language: 0.15, year: 0.1 },
};

describe('sanitizePrefs', () => {
  it('returns defaults for missing or corrupt storage', () => {
    expect(sanitizePrefs(null, OPTIONS)).toEqual(defaultPrefs(OPTIONS));
    expect(sanitizePrefs('garbage', OPTIONS)).toEqual(defaultPrefs(OPTIONS));
  });

  it('drops unknown labels, duplicates and wrong types', () => {
    const p = sanitizePrefs({ genres: ['Drama', 'Western', 'Drama', 7], moods: ['Dark', null], languages: ['Klingon'] }, OPTIONS);
    expect(p.genres).toEqual(['Drama']);
    expect(p.moods).toEqual(['Dark']);
    expect(p.languages).toEqual([]);
  });

  it('caps lists at the backend limit and normalises keywords', () => {
    const keywords = Array.from({ length: 30 }, (_, i) => `  theme   ${i} `);
    const p = sanitizePrefs({ keywords: [...keywords, 'THEME 1', 'x'.repeat(80)] }, OPTIONS);
    expect(p.keywords).toHaveLength(MAX_LIST_ITEMS);
    expect(p.keywords[1]).toBe('theme 1');
    expect(new Set(p.keywords.map((k) => k.toLowerCase())).size).toBe(p.keywords.length);
  });

  it('keeps only valid, unique liked movies', () => {
    const liked = [{ movie_id: 6, title: 'Inception' }, { movie_id: 6, title: 'Dup' }, { movie_id: -1, title: 'x' }, { title: 'no id' }];
    expect(sanitizePrefs({ likedMovies: liked }, OPTIONS).likedMovies).toEqual([{ movie_id: 6, title: 'Inception' }]);
  });

  it('clamps and orders the year range and rating', () => {
    const p = sanitizePrefs({ yearMin: 2050, yearMax: 1800, minRating: 42 }, OPTIONS);
    expect([p.yearMin, p.yearMax]).toEqual([1966, 2023]);
    expect(p.minRating).toBe(9.5);
  });

  it('snaps topN to an available dropdown option', () => {
    expect(sanitizePrefs({ topN: 7 }, OPTIONS).topN).toBe(5);
    expect(sanitizePrefs({ topN: 50 }, OPTIONS).topN).toBe(30);
    expect(sanitizePrefs({ topN: 'ten' }, OPTIONS).topN).toBe(10);
    expect(nearestTopN(13)).toBe(15);
  });

  it('repairs weights from old or corrupt storage', () => {
    expect(sanitizeWeights({ genre: 'abc', keyword: null, mood: -2, language: 5, year: 0.5, extra: 1 })).toEqual({
      genre: FALLBACK_WEIGHTS.genre,
      keyword: 0,
      mood: 0,
      language: 1,
      year: 0.5,
    });
    expect(sanitizeWeights({ genre: 0, keyword: 0, mood: 0, language: 0, year: 0 })).toEqual(FALLBACK_WEIGHTS);
    expect(Object.keys(sanitizePrefs({ weights: { genre: 1, popularity: 3 } }, OPTIONS).weights)).toEqual(
      Object.keys(FALLBACK_WEIGHTS),
    );
  });
});

describe('activeComponents / activeWeightTotal (mirror the backend rules)', () => {
  const prefs = (patch) => ({ ...defaultPrefs(OPTIONS), ...patch });

  it('marks only components the user set', () => {
    expect(activeComponents(prefs({ genres: ['Drama'] }), OPTIONS)).toEqual({
      genre: true,
      keyword: false,
      mood: false,
      language: false,
      year: false,
    });
  });

  it('liked movies imply genre, mood and theme signals', () => {
    const a = activeComponents(prefs({ likedMovies: [{ movie_id: 1, title: 'x' }] }), OPTIONS);
    expect([a.genre, a.mood, a.keyword]).toEqual([true, true, true]);
  });

  it('a strict filter is not scored unless it is the only preference', () => {
    expect(activeComponents(prefs({ genres: ['Drama'], languages: ['Hindi'], strictLanguages: true }), OPTIONS).language).toBe(false);
    expect(activeComponents(prefs({ languages: ['Hindi'], strictLanguages: true }), OPTIONS).language).toBe(true);
  });

  it('detects when every used weight is zero even if others are not', () => {
    expect(activeWeightTotal(prefs({ genres: ['Drama'], weights: { ...FALLBACK_WEIGHTS, genre: 0 } }), OPTIONS)).toBe(0);
    expect(activeWeightTotal(prefs({ genres: ['Drama'] }), OPTIONS)).toBe(0.3);
  });
});

describe('payload', () => {
  it('omits a year preference when the slider is at the catalogue bounds and sends only known fields', () => {
    const body = toPayload(defaultPrefs(OPTIONS), OPTIONS);
    expect([body.year_min, body.year_max]).toEqual([null, null]);
    // The backend rejects unknown fields (extra="forbid"), so the field list is part of the contract.
    expect(Object.keys(body).sort()).toEqual([
      'genres',
      'keywords',
      'languages',
      'liked_movie_ids',
      'min_rating',
      'moods',
      'strict_languages',
      'strict_years',
      'top_n',
      'use_feedback',
      'weights',
      'year_max',
      'year_min',
    ]);
  });

  it('requires at least one preference', () => {
    expect(hasPreference(defaultPrefs(OPTIONS), OPTIONS)).toBe(false);
    expect(hasPreference({ ...defaultPrefs(OPTIONS), yearMin: 2000 }, OPTIONS)).toBe(true);
  });
});
