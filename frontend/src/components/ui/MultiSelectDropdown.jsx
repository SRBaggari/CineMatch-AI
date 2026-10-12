import { useEffect, useId, useRef, useState } from 'react';
import { Check, ChevronDown, X } from 'lucide-react';

// Accessible multi-select dropdown: a button that opens a listbox of options.
export default function MultiSelectDropdown({ label, options, selected, onChange, counts, placeholder = 'Any' }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);
  const listId = useId();

  useEffect(() => {
    if (!open) return undefined;
    const onPointer = (e) => !rootRef.current?.contains(e.target) && setOpen(false);
    const onKey = (e) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('pointerdown', onPointer);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('pointerdown', onPointer);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const toggle = (value) =>
    onChange(selected.includes(value) ? selected.filter((v) => v !== value) : [...selected, value]);

  const summary = selected.length === 0 ? placeholder : selected.length <= 2 ? selected.join(', ') : `${selected.length} selected`;

  return (
    <div className="dropdown" ref={rootRef}>
      <span className="field-label">{label}</span>
      <button
        type="button"
        className={`dropdown-trigger ${open ? 'is-open' : ''}`}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        onClick={() => setOpen((o) => !o)}
      >
        <span className={selected.length ? '' : 'muted'}>{summary}</span>
        <ChevronDown size={18} className="dropdown-caret" />
      </button>
      {open && (
        <ul className="dropdown-menu glass" id={listId} role="listbox" aria-multiselectable="true">
          {options.map((option) => {
            const active = selected.includes(option);
            return (
              <li key={option} role="option" aria-selected={active}>
                <button type="button" className={active ? 'is-active' : ''} onClick={() => toggle(option)}>
                  <span className="check-box">{active && <Check size={13} strokeWidth={3} />}</span>
                  <span>{option}</span>
                  {counts && <span className="muted small">{counts[option]} movies</span>}
                </button>
              </li>
            );
          })}
        </ul>
      )}
      {selected.length > 0 && (
        <div className="pill-row">
          {selected.map((value) => (
            <span key={value} className="pill">
              {value}
              <button type="button" onClick={() => toggle(value)} aria-label={`Remove ${value}`}>
                <X size={12} />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
