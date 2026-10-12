import { Check } from 'lucide-react';

// Progress indicator: clickable steps, a filled progress bar and a completion state per step.
export default function Stepper({ steps, current, onSelect }) {
  const progress = (current / (steps.length - 1)) * 100;
  return (
    <nav className="stepper" aria-label="Preference steps">
      <div className="stepper-bar" aria-hidden="true">
        <div className="stepper-bar-fill" style={{ width: `${progress}%` }} />
      </div>
      <ol>
        {steps.map((step, index) => {
          const state = index === current ? 'is-current' : step.done ? 'is-done' : '';
          return (
            <li key={step.id} className={state}>
              <button
                type="button"
                onClick={() => onSelect(index)}
                aria-current={index === current ? 'step' : undefined}
                aria-label={`Step ${index + 1}: ${step.title}${step.done ? ' (done)' : ''}`}
              >
                <span className="step-dot">{step.done && index !== current ? <Check size={14} strokeWidth={3} /> : index + 1}</span>
                <span className="step-label">
                  {step.title}
                  <span className="step-sub">{step.summary}</span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
