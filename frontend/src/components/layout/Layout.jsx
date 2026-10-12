import { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { RefreshCw, WifiOff } from 'lucide-react';
import { useApp } from '../../context/AppContext.jsx';
import Footer from './Footer.jsx';
import Navbar from './Navbar.jsx';

function ScrollToTop() {
  const { pathname } = useLocation();
  // Block body on purpose: newer browsers return a Promise from scrollTo(), and an
  // effect must return nothing or a cleanup function.
  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [pathname]);
  return null;
}

export default function Layout() {
  const { status, statusError, connect } = useApp();
  return (
    <div className="app-shell">
      <ScrollToTop />
      <div className="backdrop" aria-hidden="true" />
      <Navbar />
      {status === 'offline' && (
        <div className="offline-banner" role="alert">
          <div className="container offline-inner">
            <WifiOff size={18} />
            <span>
              <strong>Backend offline.</strong> {statusError} Start it with{' '}
              <code>uvicorn app.main:app --port 8000</code> in the backend folder.
            </span>
            <button type="button" className="btn btn-secondary btn-sm" onClick={connect}>
              <RefreshCw size={14} /> Retry
            </button>
          </div>
        </div>
      )}
      <main className="main">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
