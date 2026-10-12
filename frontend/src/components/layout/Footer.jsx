import { Link } from 'react-router-dom';
import { Clapperboard } from 'lucide-react';
import { useApp } from '../../context/AppContext.jsx';

export default function Footer() {
  const { dataset } = useApp();
  return (
    <footer className="footer">
      <div className="container footer-inner">
        <div className="footer-brand">
          <span className="brand-mark small">
            <Clapperboard size={16} />
          </span>
          <div>
            <strong>CineMatch AI</strong>
            <p className="muted small">DecodeLabs AI Industrial Training · Project 3: AI Recommendation Logic</p>
          </div>
        </div>
        <nav className="footer-links" aria-label="Footer">
          <Link to="/preferences">Preferences</Link>
          <Link to="/recommendations">Recommendations</Link>
          <Link to="/how-it-works">How It Works</Link>
        </nav>
      </div>
      {dataset && (
        <p className="container provenance">
          <strong>About the data:</strong> {dataset.provenance}
        </p>
      )}
    </footer>
  );
}
