import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Check, Filter, Layers, ListOrdered, Network, Scale, Sigma, Sparkles, Type } from 'lucide-react';
import { useApp } from '../context/AppContext.jsx';
import { COMPONENTS, COMPONENT_INFO } from '../utils/components.js';
import { FALLBACK_WEIGHTS } from '../utils/prefs.js';
import { cosine, tfidf } from '../utils/tfidf.js';

const SECTIONS = [
  { id: 'content-based', label: 'Content-based filtering', icon: Layers },
  { id: 'tf-idf', label: 'TF-IDF', icon: Type },
  { id: 'cosine', label: 'Cosine similarity', icon: Network },
  { id: 'weighted', label: 'Weighted matching', icon: Scale },
  { id: 'ranking', label: 'Ranking', icon: ListOrdered },
];

// Teaching examples only. They are tiny made-up texts, not catalogue data.
const TOY_DOCS = [
  'A thief enters dreams to steal secrets from the mind',
  'A robot falls in love in space',
  'Detectives chase a thief through the city at night',
];

const DEMO_GENRES = ['Science Fiction', 'Thriller', 'Drama', 'Comedy'];
const DEMO_MOVIE = new Set(['Science Fiction', 'Thriller', 'Drama']);

// Illustrative component values for one example movie.
const EXAMPLE_COMPONENTS = { genre: 0.82, keyword: 0.46, mood: 0.58, language: 1, year: 1 };

function Section({ id, icon: Icon, kicker, title, children }) {
  return (
    <section id={id} className="explain-section glass" aria-labelledby={`${id}-title`}>
      <span className="eyebrow">
        <Icon size={14} /> {kicker}
      </span>
      <h2 id={`${id}-title`}>{title}</h2>
      {children}
    </section>
  );
}

function TfidfDemo() {
  const model = useMemo(() => tfidf(TOY_DOCS), []);
  const docIndex = 0;
  const rows = model.vocab
    .map((term, i) => ({ term, df: model.df[term], idf: model.idf[term], weight: model.vectors[docIndex][i] }))
    .filter((r) => r.weight > 0)
    .sort((a, b) => b.weight - a.weight);
  const maxWeight = rows[0]?.weight || 1;

  return (
    <div className="demo">
      <p className="demo-title">Try it: three tiny movie descriptions</p>
      <ol className="toy-docs">
        {TOY_DOCS.map((doc, i) => (
          <li key={doc} className={i === docIndex ? 'is-active' : ''}>
            {doc}
          </li>
        ))}
      </ol>
      <div className="table-wrap">
        <table className="demo-table">
          <thead>
            <tr>
              <th>Word in description 1</th>
              <th>Appears in (of 3)</th>
              <th>IDF (rarity)</th>
              <th>TF-IDF weight</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.term}>
                <td>
                  <strong>{r.term}</strong>
                </td>
                <td>{r.df}</td>
                <td>{r.idf.toFixed(2)}</td>
                <td>
                  <span className="inline-bar">
                    <span style={{ width: `${(r.weight / maxWeight) * 100}%` }} />
                  </span>
                  {r.weight.toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted small">
        “thief” also appears in description 3, so it is less distinctive and gets a lower weight than “dreams” or
        “secrets”. Similarity between descriptions 1 and 3 is{' '}
        <strong className="text">{cosine(model.vectors[0], model.vectors[2]).toFixed(2)}</strong> (they share “thief”);
        between 1 and 2 it is <strong className="text">{cosine(model.vectors[0], model.vectors[1]).toFixed(2)}</strong>.
      </p>
    </div>
  );
}

function CosineDemo() {
  const [picked, setPicked] = useState(['Science Fiction', 'Thriller']);
  const user = DEMO_GENRES.map((g) => (picked.includes(g) ? 1 : 0));
  const movie = DEMO_GENRES.map((g) => (DEMO_MOVIE.has(g) ? 1 : 0));
  const score = cosine(user, movie);
  const shared = picked.filter((g) => DEMO_MOVIE.has(g)).length;
  const angle = Math.acos(Math.min(1, score));
  const end = (a, r = 110) => [20 + r * Math.cos(a), 140 - r * Math.sin(a)];
  const [mx, my] = end(Math.PI / 5);
  const [ux, uy] = end(Math.PI / 5 + (picked.length ? angle : 0));

  return (
    <div className="demo cosine-demo">
      <div>
        <p className="demo-title">Try it: pick your genres</p>
        <div className="chip-group">
          {DEMO_GENRES.map((g) => {
            const active = picked.includes(g);
            return (
              <button
                key={g}
                type="button"
                className={`chip ${active ? 'is-active' : ''}`}
                aria-pressed={active}
                onClick={() => setPicked(active ? picked.filter((x) => x !== g) : [...picked, g])}
              >
                {active && <Check size={14} />} {g}
              </button>
            );
          })}
        </div>
        <div className="table-wrap">
          <table className="demo-table vector-table">
            <thead>
              <tr>
                <th />
                {DEMO_GENRES.map((g) => (
                  <th key={g}>{g}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>You</td>
                {user.map((v, i) => (
                  <td key={DEMO_GENRES[i]} className={v ? 'on' : ''}>
                    {v}
                  </td>
                ))}
              </tr>
              <tr>
                <td>Movie</td>
                {movie.map((v, i) => (
                  <td key={DEMO_GENRES[i]} className={v ? 'on' : ''}>
                    {v}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
        <p className="formula-line">
          cosine = shared / √(yours × movie’s) = {shared} / √({picked.length} × {DEMO_MOVIE.size}) ={' '}
          <strong>{score.toFixed(2)}</strong>
        </p>
      </div>
      <svg viewBox="0 0 160 160" className="vector-svg" role="img" aria-label={`Angle between vectors, cosine ${score.toFixed(2)}`}>
        <defs>
          <marker id="arrow-movie" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
            <path d="M0,0 L8,4 L0,8 z" fill="var(--blue)" />
          </marker>
          <marker id="arrow-user" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
            <path d="M0,0 L8,4 L0,8 z" fill="var(--purple)" />
          </marker>
        </defs>
        <line x1="20" y1="140" x2="150" y2="140" className="axis" />
        <line x1="20" y1="140" x2="20" y2="10" className="axis" />
        <line x1="20" y1="140" x2={mx} y2={my} stroke="var(--blue)" strokeWidth="3" markerEnd="url(#arrow-movie)" />
        {picked.length > 0 && (
          <line x1="20" y1="140" x2={ux} y2={uy} stroke="var(--purple)" strokeWidth="3" markerEnd="url(#arrow-user)" />
        )}
        <text x={mx + 4} y={my + 12} className="svg-label">movie</text>
        {picked.length > 0 && (
          <text x={ux - 6} y={uy - 6} className="svg-label">you</text>
        )}
      </svg>
    </div>
  );
}

function WeightedDemo({ weights }) {
  const total = COMPONENTS.reduce((s, c) => s + weights[c] * EXAMPLE_COMPONENTS[c], 0);
  return (
    <div className="demo">
      <p className="demo-title">Example: one movie’s five scores combined</p>
      <div className="weighted-rows">
        {COMPONENTS.map((c) => (
          <div key={c} className="weighted-row">
            <span>{COMPONENT_INFO[c].label}</span>
            <span className="bar">
              <span className={`bar-fill fill-${c}`} style={{ width: `${EXAMPLE_COMPONENTS[c] * 100}%` }} />
            </span>
            <span className="mono">
              {EXAMPLE_COMPONENTS[c].toFixed(2)} × {weights[c].toFixed(2)} = <strong>{(EXAMPLE_COMPONENTS[c] * weights[c]).toFixed(3)}</strong>
            </span>
          </div>
        ))}
        <div className="weighted-total">
          <Sigma size={18} /> Match score <strong>{total.toFixed(3)}</strong>
        </div>
      </div>
    </div>
  );
}

export default function HowItWorksPage() {
  const { options, dataset } = useApp();
  const weights = options?.default_weights ?? FALLBACK_WEIGHTS;

  return (
    <div className="page how-page container">
      <div className="page-head">
        <span className="eyebrow">
          <Sparkles size={14} /> Explained simply
        </span>
        <h1>How CineMatch AI picks your movies</h1>
        <p className="lead">
          No black box and no random picks. Here is every step the engine takes, with small live examples you can play
          with. {dataset && `The real engine runs these steps over ${dataset.total_movies} movies and ${dataset.vocabulary_size} distinct words.`}
        </p>
      </div>

      <div className="how-layout">
        <nav className="toc glass" aria-label="On this page">
          {SECTIONS.map(({ id, label, icon: Icon }) => (
            <a key={id} href={`#${id}`}>
              <Icon size={15} /> {label}
            </a>
          ))}
        </nav>

        <div className="how-content">
          <Section id="content-based" icon={Layers} kicker="Step 1" title="Content-based filtering">
            <p>
              Imagine a friend who has watched every movie and remembers what each one is <em>made of</em>: its genres,
              its mood, its language, when it came out and what it is about. When you describe your taste, they suggest
              movies made of similar ingredients. That is <strong>content-based filtering</strong>: it recommends by
              comparing the <em>content</em> of movies with your preferences, not by copying what other people watched.
            </p>
            <p>
              To compare things, a computer needs numbers. So every movie becomes a <strong>feature vector</strong>, a
              list of numbers. For genres it is a row of 1s and 0s (1 = the movie has that genre):
            </p>
            <div className="feature-card">
              <div>
                <span className="field-label">Genres</span>
                <code>Sci-Fi 1 · Thriller 1 · Drama 0 · Comedy 0 …</code>
              </div>
              <div>
                <span className="field-label">Mood</span>
                <code>Mind-Bending 1 · Funny 0 · Dark 0 …</code>
              </div>
              <div>
                <span className="field-label">Language</span>
                <code>English 1 · Hindi 0 · Korean 0 …</code>
              </div>
              <div>
                <span className="field-label">Themes & description</span>
                <code>TF-IDF word weights (next step)</code>
              </div>
            </div>
            <p className="callout">
              Why this approach? It works from your very first visit (no viewing history needed), runs entirely on our
              own server, and every result can be explained.
            </p>
          </Section>

          <Section id="tf-idf" icon={Type} kicker="Step 2" title="TF-IDF: turning words into numbers">
            <p>
              Descriptions and keywords are text, so we need a way to score words. <strong>TF-IDF</strong> gives each
              word a weight from two ideas:
            </p>
            <ul className="plain-list">
              <li>
                <strong>TF (term frequency):</strong> a word used more in a movie’s text matters more for that movie.
              </li>
              <li>
                <strong>IDF (inverse document frequency):</strong> a word that appears in <em>many</em> movies (like
                “story”) tells us little, so it is down-weighted. Rare words (like “time loop”) are distinctive, so they
                count more.
              </li>
            </ul>
            <TfidfDemo />
          </Section>

          <Section id="cosine" icon={Network} kicker="Step 3" title="Cosine similarity: measuring how alike two things are">
            <p>
              Think of each vector as an arrow. If your arrow and a movie’s arrow point in the same direction, you want
              the same things. <strong>Cosine similarity</strong> measures the angle between them: <strong>1</strong>{' '}
              means identical direction (a perfect match) and <strong>0</strong> means nothing in common. Because it
              looks at direction rather than length, a movie isn’t favoured just for having lots of tags.
            </p>
            <CosineDemo />
            <p className="muted small">
              The engine uses this for genres, moods and the TF-IDF theme vectors. Language is a simple yes/no match and
              release year scores 1 inside your range, losing a little for each year outside it.
            </p>
          </Section>

          <Section id="weighted" icon={Scale} kicker="Step 4" title="Weighted matching: combining the scores">
            <p>
              Each movie now has five scores between 0 and 1: genre, themes, mood, language and release year. Some
              matter more than others, so each gets a <strong>weight</strong>. The final match score is the weighted
              sum. The current default weights come straight from the backend:
            </p>
            <div className="weight-chips">
              {COMPONENTS.map((c) => (
                <span key={c} className="tag">
                  {COMPONENT_INFO[c].label} <strong>{weights[c].toFixed(2)}</strong>
                </span>
              ))}
            </div>
            <WeightedDemo weights={weights} />
            <p>
              If you skip a preference (say, no language), its weight is set to 0 and the others are scaled up so they
              still add up to 1. That keeps scores comparable no matter how many preferences you set. You can change the
              weights yourself on the Review step of the preferences page.
            </p>
            <p className="callout">
              <strong>Is the match score a probability?</strong> No. 0.72 does not mean a 72% chance you will like the
              movie. It is a similarity score used to put movies in order.
            </p>
          </Section>

          <Section id="ranking" icon={ListOrdered} kicker="Step 5" title="Recommendation ranking">
            <ol className="ranking-steps">
              <li>
                <Filter size={16} />
                <span>
                  <strong>Apply your hard filters.</strong> Movies below your minimum rating are removed, plus other
                  languages or years if you turned on the “only” switches.
                </span>
              </li>
              <li>
                <Check size={16} />
                <span>
                  <strong>Drop non-matches.</strong> Movies you already love, and movies with a score of 0 (nothing in
                  common with your preferences), are left out.
                </span>
              </li>
              <li>
                <ListOrdered size={16} />
                <span>
                  <strong>Sort by match score.</strong> Highest first. If two movies tie, the higher-rated one wins; if
                  they still tie, the lower catalogue id wins, so results never change randomly.
                </span>
              </li>
              <li>
                <Sparkles size={16} />
                <span>
                  <strong>Explain the top 10.</strong> Each card lists what matched, reasons ordered by how much they
                  contributed, and the full score breakdown on its details page.
                </span>
              </li>
            </ol>
          </Section>

          <div className="cta-band">
            <div>
              <h2>See it work on your own taste</h2>
              <p>Set a few preferences and inspect every score.</p>
            </div>
            <Link to="/preferences" className="btn btn-light btn-lg">
              Get Started <ArrowRight size={18} />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
