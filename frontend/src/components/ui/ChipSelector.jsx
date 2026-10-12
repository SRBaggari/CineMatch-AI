import { Check } from 'lucide-react';

export default function ChipSelector({ options, selected, onToggle, counts, iconFor, label }) {
  return (
    <div className="chip-group" role="group" aria-label={label}>
      {options.map((option) => {
        const active = selected.includes(option);
        const Icon = iconFor?.(option);
        return (
          <button
            key={option}
            type="button"
            className={`chip ${active ? 'is-active' : ''}`}
            aria-pressed={active}
            onClick={() => onToggle(option)}
          >
            {active ? <Check size={15} strokeWidth={2.6} /> : Icon && <Icon size={15} />}
            <span>{option}</span>
            {counts && <span className="chip-count">{counts[option]}</span>}
          </button>
        );
      })}
    </div>
  );
}
