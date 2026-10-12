import { Component } from 'react';
import { RefreshCw, TriangleAlert } from 'lucide-react';

// Catches render errors in a page so one broken view never blanks the whole app.
// `resetKey` (the current path) clears the error when the user navigates away.
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null, resetKey: props.resetKey };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  static getDerivedStateFromProps(props, state) {
    return props.resetKey !== state.resetKey ? { error: null, resetKey: props.resetKey } : null;
  }

  componentDidCatch(error, info) {
    console.error('Page crashed:', error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="page container narrow">
        <div className="state-message glass tone-error" role="alert">
          <div className="state-icon">
            <TriangleAlert size={30} />
          </div>
          <h2>This page hit an unexpected error</h2>
          <div className="state-body">
            <p>{String(this.state.error.message || this.state.error)}</p>
          </div>
          <div className="state-actions">
            <button type="button" className="btn btn-primary" onClick={() => this.setState({ error: null })}>
              <RefreshCw size={16} /> Try again
            </button>
          </div>
        </div>
      </div>
    );
  }
}
