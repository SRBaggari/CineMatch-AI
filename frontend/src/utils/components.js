// Display metadata for the five scoring components returned by the API.
export const COMPONENTS = ['genre', 'keyword', 'mood', 'language', 'year'];

export const COMPONENT_INFO = {
  genre: { label: 'Genre', help: 'Cosine similarity of multi-hot genre vectors' },
  keyword: { label: 'Keywords', help: 'TF-IDF cosine of keywords + description, scaled so the best match = 1' },
  mood: { label: 'Mood', help: 'Cosine similarity of multi-hot mood vectors' },
  language: { label: 'Language', help: '1 if the movie is in a preferred language' },
  year: { label: 'Release year', help: '1 inside your year range, decays outside it' },
};
