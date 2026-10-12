import { useEffect, useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { Clapperboard, Menu, Sparkles, X } from 'lucide-react';
import { useApp } from '../../context/AppContext.jsx';

const LINKS = [
  { to: '/', label: 'Home', end: true },
  { to: '/preferences', label: 'Preferences' },
  { to: '/recommendations', label: 'Recommendations' },
  { to: '/how-it-works', label: 'How It Works' },
];

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const location = useLocation();
  const { ready } = useApp();

  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header className={`navbar ${scrolled ? 'is-scrolled' : ''} ${open ? 'is-open' : ''}`}>
      <div className="navbar-inner container">
        <Link to="/" className="brand" aria-label="CineMatch AI home">
          <span className="brand-mark">
            <Clapperboard size={20} />
          </span>
          <span className="brand-name">
            CineMatch <span className="gradient-text">AI</span>
          </span>
        </Link>

        <nav className="nav-links" aria-label="Main">
          {LINKS.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.end} className={({ isActive }) => (isActive ? 'is-active' : '')}>
              {link.label}
            </NavLink>
          ))}
        </nav>

        <Link to={ready ? '/recommendations' : '/preferences'} className="btn btn-primary btn-sm nav-cta">
          <Sparkles size={15} /> {ready ? 'My Picks' : 'Get Started'}
        </Link>

        <button
          type="button"
          className="icon-btn nav-toggle"
          aria-label={open ? 'Close menu' : 'Open menu'}
          aria-expanded={open}
          onClick={() => setOpen((o) => !o)}
        >
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {open && (
        <nav className="mobile-menu" aria-label="Mobile">
          {LINKS.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.end} className={({ isActive }) => (isActive ? 'is-active' : '')}>
              {link.label}
            </NavLink>
          ))}
          <Link to={ready ? '/recommendations' : '/preferences'} className="btn btn-primary">
            <Sparkles size={16} /> {ready ? 'My Picks' : 'Get Started'}
          </Link>
        </nav>
      )}
    </header>
  );
}
