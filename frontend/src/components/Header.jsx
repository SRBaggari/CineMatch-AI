import { Activity, Clapperboard, ServerCrash } from 'lucide-react';

export default function Header({ status }) {
  return (
    <header className="app-header">
      <div className="brand">
        <div className="brand-logo">
          <Clapperboard size={22} />
        </div>
        <div>
          <h1>CineMatch AI</h1>
          <p>Personalized Movie Recommendation System</p>
        </div>
      </div>
      <nav className="header-right">
        <a href="#how-it-works" className="nav-link">
          How it works
        </a>
        <span className={`status ${status.online ? 'status-online' : 'status-offline'}`}>
          {status.online ? <Activity size={14} /> : <ServerCrash size={14} />}
          {status.online ? `Engine online · ${status.movies} movies` : status.checking ? 'Connecting…' : 'Engine offline'}
        </span>
      </nav>
    </header>
  );
}
