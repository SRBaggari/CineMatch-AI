import { Cpu, Layers, ListChecks, Network, Target, UserRound } from 'lucide-react';

const STEPS = [
  {
    icon: UserRound,
    title: '1. Collect preferences',
    text: 'Genres, languages, moods, keywords, liked movies, release years and a minimum rating.',
  },
  {
    icon: Layers,
    title: '2. Feature vectors',
    text: 'Each movie becomes multi-hot genre and mood vectors, a one-hot language vector and its release year.',
  },
  {
    icon: Cpu,
    title: '3. TF-IDF',
    text: 'Keywords and descriptions are converted to TF-IDF vectors, so rare, specific themes weigh more.',
  },
  {
    icon: Network,
    title: '4. Cosine similarity',
    text: 'Your preferences are mapped into the same spaces and compared with every movie, giving scores in [0, 1].',
  },
  {
    icon: Target,
    title: '5. Weighted ranking',
    text: 'Configurable weights are normalised over the preferences you set. Hard filters apply, ties break by rating then id.',
  },
  {
    icon: ListChecks,
    title: '6. Explanation',
    text: 'Each result lists matched preferences, reasons ordered by contribution, and every score component.',
  },
];

export default function HowItWorks({ dataset }) {
  return (
    <section className="how-it-works" id="how-it-works">
      <h2>How the recommendation engine works</h2>
      <p className="muted">
        A transparent, content-based pipeline. No external AI services and no random picks: every score can be traced
        back to the data.
        {dataset &&
          ` The catalogue has ${dataset.total_movies} movies, ${dataset.genres} genres, ${dataset.moods} moods, ${dataset.languages} languages and ${dataset.vocabulary_size} TF-IDF terms.`}
      </p>
      <div className="steps">
        {STEPS.map(({ icon: Icon, title, text }) => (
          <div key={title} className="step-card">
            <Icon size={22} />
            <h3>{title}</h3>
            <p>{text}</p>
          </div>
        ))}
      </div>
      <div className="formula">
        score = w<sub>genre</sub>·cos(genres) + w<sub>keyword</sub>·cos<sub>TF-IDF</sub>/max + w<sub>mood</sub>·cos(moods) +
        w<sub>language</sub>·match + w<sub>year</sub>·year_fit, &nbsp; Σw = 1
      </div>
      <p className="muted small">
        The score is a weighted similarity between 0 and 1. It ranks movies; it is not a probability that you will like
        them.
      </p>
    </section>
  );
}
