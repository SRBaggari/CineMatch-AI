import { Check } from 'lucide-react';

export default function ChipSelector({ options, selected, onToggle, counts, iconFor }) {
  return (
    <div className="chip-group">
      {options.map((option) => {
        const active = selected.includes(option);
        const Icon = iconFor?.(option);
        return (
          <button
            key={option}
            type="button"
            className={`chip ${active ? 'chip-active' : ''}`}
            aria-pressed={active}
            onClick={() => onToggle(option)}
          >
            {active ? <Check size={14} /> : Icon && <Icon size={14} />}
            {option}
            {counts && <span className="chip-count">{counts[option]}</span>}
          </button>
        );
      })}
    </div>
  );
}
