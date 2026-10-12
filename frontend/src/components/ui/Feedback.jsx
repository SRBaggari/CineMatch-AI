import { LoaderCircle, RefreshCw, TriangleAlert } from 'lucide-react';

export function Spinner({ label = 'Loading…', size = 22 }) {
  return (
    <div className="spinner" role="status">
      <LoaderCircle size={size} className="spin" />
      <span>{label}</span>
    </div>
  );
}

// Generic empty / error / info block with an optional action.
export function StateMessage({ icon: Icon = TriangleAlert, title, children, action, tone = 'neutral' }) {
  return (
    <div className={`state-message glass tone-${tone}`}>
      <div className="state-icon">
        <Icon size={30} />
      </div>
      <h2>{title}</h2>
      {children && <div className="state-body">{children}</div>}
      {action && <div className="state-actions">{action}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry, title = 'Something went wrong' }) {
  return (
    <StateMessage
      title={title}
      tone="error"
      action={
        onRetry && (
          <button type="button" className="btn btn-primary" onClick={onRetry}>
            <RefreshCw size={16} /> Try again
          </button>
        )
      }
    >
      <p>{message}</p>
    </StateMessage>
  );
}

export function SkeletonCard() {
  return (
    <div className="skeleton-card" aria-hidden="true">
      <div className="skeleton skeleton-poster" />
      <div className="skeleton-lines">
        <div className="skeleton skeleton-line w-70" />
        <div className="skeleton skeleton-line w-40" />
        <div className="skeleton skeleton-line" />
        <div className="skeleton skeleton-line w-90" />
        <div className="skeleton skeleton-line w-60" />
      </div>
    </div>
  );
}
