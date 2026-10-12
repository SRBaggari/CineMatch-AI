import { useState } from 'react';
import { Plus, Tag, X } from 'lucide-react';

export default function KeywordInput({ keywords, suggestions, onAdd, onRemove }) {
  const [value, setValue] = useState('');

  const submit = () => {
    const keyword = value.trim();
    if (keyword) onAdd(keyword);
    setValue('');
  };

  const unused = suggestions.filter((s) => !keywords.includes(s)).slice(0, 14);

  return (
    <div className="keyword-input">
      <div className="input-with-icon">
        <Tag size={16} />
        <input
          type="text"
          value={value}
          placeholder="Add a theme, e.g. time travel"
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              submit();
            }
          }}
          aria-label="Add keyword"
        />
        <button type="button" className="icon-button" onClick={submit} aria-label="Add keyword">
          <Plus size={16} />
        </button>
      </div>

      {keywords.length > 0 && (
        <div className="liked-list">
          {keywords.map((k) => (
            <span key={k} className="liked-pill keyword-pill">
              {k}
              <button type="button" onClick={() => onRemove(k)} aria-label={`Remove ${k}`}>
                <X size={12} />
              </button>
            </span>
          ))}
        </div>
      )}

      <div className="suggestions">
        {unused.map((s) => (
          <button key={s} type="button" className="suggestion" onClick={() => onAdd(s)}>
            + {s}
          </button>
        ))}
      </div>
    </div>
  );
}
