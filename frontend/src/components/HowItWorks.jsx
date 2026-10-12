import { Cpu, Layers, ListChecks, Network, Target, UserRound } from 'lucide-react';

const STEPS = [
  {
    icon: UserRound,
    title: '1. Collect preferences',
    text: 'Genres, moods, themes and favourite movies are gathered from the form.',
  },
  {
    icon: Layers,
    title: '2. Feature engineering',
    text: 'Each movie becomes a weighted text "soup" of genres ×3, moods ×2, keywords ×2, director, cast and overview.',
  },
  {
    icon: Cpu,
    title: '3. TF-IDF vectors',
    text: 'Scikit-learn converts every soup into a vector. Rare, specific terms weigh more than common ones.',
  },
  {
    icon: Network,
    title: '4. Cosine similarity',
    text: 'Your profile vector (preferences + liked movies) is compared with every movie vector.',
  },
  {
    icon: Target,
    title: '5. Hybrid ranking',
    text: 'Content similarity is blended with genre and mood Jaccard overlap plus a quality score, then filtered.',
  },
  {
    icon: ListChecks,
    title: '6. Explanation',
    text: 'Each result shows matched patterns, the liked movie it resembles and the full score maths.',
  },
];

export default function HowItWorks({ meta }) {
  return (
    <section className="how-it-works" id="how-it-works">
      <h2>How the recommendation engine works</h2>
      <p className="muted">
        A transparent, content-based pipeline. No external AI services, no random picks: every score can be traced back
        to the data.
        {meta && ` The current model has ${meta.total_movies} movies and ${meta.vocabulary_size} TF-IDF features.`}
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
        score = w<sub>c</sub>·cos(profile, movie) + w<sub>g</sub>·Jaccard(genres) + w<sub>m</sub>·Jaccard(moods) +
        w<sub>q</sub>·rating<sub>norm</sub>
      </div>
    </section>
  );
}
