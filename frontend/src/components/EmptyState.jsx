import { Popcorn } from 'lucide-react';

export const PRESETS = [
  {
    label: 'Mind-bending sci-fi',
    prefs: {
      genres: ['Science Fiction'],
      moods: ['Mind-Bending'],
      keywords: ['time travel'],
      likedMovies: [{ movie_id: 6, title: 'Inception', year: 2010 }],
    },
  },
  {
    label: 'Feel-good family night',
    prefs: {
      genres: ['Animation', 'Family'],
      moods: ['Heartwarming', 'Funny'],
      keywords: [],
      likedMovies: [{ movie_id: 30, title: 'Toy Story', year: 1995 }],
    },
  },
  {
    label: 'Dark crime thrillers',
    prefs: {
      genres: ['Crime', 'Thriller'],
      moods: ['Dark', 'Suspenseful'],
      keywords: ['serial killer'],
      likedMovies: [{ movie_id: 15, title: 'Se7en', year: 1995 }],
    },
  },
  {
    label: 'Inspiring Indian cinema',
    prefs: {
      genres: ['Drama'],
      moods: ['Inspiring'],
      keywords: ['friendship'],
      likedMovies: [{ movie_id: 53, title: '3 Idiots', year: 2009 }],
      languages: ['Hindi', 'Telugu'],
    },
  },
];

export default function EmptyState({ onPreset }) {
  return (
    <div className="empty-state panel">
      <Popcorn size={44} strokeWidth={1.4} />
      <h2>Tell us what you love</h2>
      <p className="muted">
        Choose genres, moods, themes or favourite movies on the left and CineMatch AI will build a taste profile and rank
        every movie in the catalogue for you. Or try a quick preset:
      </p>
      <div className="preset-row">
        {PRESETS.map((preset) => (
          <button key={preset.label} type="button" className="btn btn-ghost" onClick={() => onPreset(preset)}>
            {preset.label}
          </button>
        ))}
      </div>
    </div>
  );
}
