import { useState } from 'react';
import { Plus, Tag, X } from 'lucide-react';

export default function KeywordInput({ keywords, suggestions, onAdd, onRemove }) {
  const [value, setValue] = useState('');

  const submit = () => {
    const keyword = value.trim();
    if (keyword) onAdd(keyword);
    setValue('');
  };

  const unused = suggestions.filter((s) => !keywords.includes(s)).slice(0, 18);

  return (
    <div className="keyword-input">
      <div className="input-shell">
        <Tag size={17} />
        <input
          type="text"
          value={value}
          maxLength={60}
          placeholder="Type a theme, e.g. time travel, and press Enter"
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              submit();
            }
          }}
          aria-label="Add a movie theme"
        />
        <button type="button" className="icon-btn" onClick={submit} aria-label="Add theme" disabled={!value.trim()}>
          <Plus size={18} />
        </button>
      </div>

      {keywords.length > 0 && (
        <div className="pill-row">
          {keywords.map((k) => (
            <span key={k} className="pill pill-accent">
              {k}
              <button type="button" onClick={() => onRemove(k)} aria-label={`Remove ${k}`}>
                <X size={12} />
              </button>
            </span>
          ))}
        </div>
      )}

      <p className="field-label">Popular themes in the catalogue</p>
      <div className="suggestions">
        {unused.map((s) => (
          <button key={s} type="button" className="suggestion" onClick={() => onAdd(s)}>
            <Plus size={12} /> {s}
          </button>
        ))}
      </div>
    </div>
  );
}
