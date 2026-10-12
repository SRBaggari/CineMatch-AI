// Display metadata for the five scoring components returned by the API.
export const COMPONENTS = ['genre', 'keyword', 'mood', 'language', 'year'];

export const COMPONENT_INFO = {
  genre: { label: 'Genre', help: 'How closely the movie’s genres match yours (cosine similarity)' },
  keyword: { label: 'Themes', help: 'TF-IDF similarity between your themes and the movie’s keywords + description' },
  mood: { label: 'Mood', help: 'How closely the movie’s moods match yours (cosine similarity)' },
  language: { label: 'Language', help: '1 if the movie is in one of your languages' },
  year: { label: 'Release year', help: '1 inside your year range, lower the further outside it' },
};
