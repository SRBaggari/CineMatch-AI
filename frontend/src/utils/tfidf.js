// Tiny TF-IDF + cosine implementation used only for the teaching examples on the
// How It Works page. It mirrors scikit-learn's defaults used by the backend:
// smooth idf = ln((1 + N) / (1 + df)) + 1, sublinear tf = 1 + ln(tf), L2 normalisation.

const STOP_WORDS = new Set([
  'a', 'an', 'the', 'and', 'of', 'in', 'on', 'to', 'with', 'his', 'her', 'their', 'into', 'for', 'from', 'at', 'through',
]);

export function tokenize(text) {
  return text
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((t) => t.length > 1 && !STOP_WORDS.has(t));
}

export function tfidf(documents) {
  const docs = documents.map(tokenize);
  const vocab = [...new Set(docs.flat())].sort();
  const df = Object.fromEntries(vocab.map((t) => [t, docs.filter((d) => d.includes(t)).length]));
  const n = docs.length;
  const idf = Object.fromEntries(vocab.map((t) => [t, Math.log((1 + n) / (1 + df[t])) + 1]));
  const vectors = docs.map((tokens) => {
    const counts = {};
    tokens.forEach((t) => {
      counts[t] = (counts[t] || 0) + 1;
    });
    const raw = vocab.map((t) => (counts[t] ? (1 + Math.log(counts[t])) * idf[t] : 0));
    const norm = Math.sqrt(raw.reduce((s, v) => s + v * v, 0)) || 1;
    return raw.map((v) => v / norm);
  });
  return { vocab, df, idf, vectors };
}

export function cosine(a, b) {
  const dot = a.reduce((s, v, i) => s + v * b[i], 0);
  const na = Math.sqrt(a.reduce((s, v) => s + v * v, 0));
  const nb = Math.sqrt(b.reduce((s, v) => s + v * v, 0));
  return na && nb ? dot / (na * nb) : 0;
}
