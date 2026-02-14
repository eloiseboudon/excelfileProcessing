import { useState, useRef, useEffect } from 'react';

interface MultiSelectFilterProps {
  options: string[];
  selected: string[];
  onChange: (values: string[]) => void;
}

function MultiSelectFilter({ options, selected, onChange }: MultiSelectFilterProps) {
  const [open, setOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (!open) {
      setSearchQuery('');
    }
  }, [open]);

  const toggleOption = (opt: string, checked: boolean) => {
    if (checked) {
      onChange([...selected, opt]);
    } else {
      onChange(selected.filter((v) => v !== opt));
    }
  };

  const filteredOptions = options.filter((opt) =>
    opt.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full px-2 py-1 bg-[var(--color-bg-surface)] text-[var(--color-text-primary)] border border-[var(--color-border-strong)] rounded text-left overflow-hidden whitespace-nowrap text-ellipsis"
      >
        {selected.length ? selected.join(', ') : 'Tous'}
      </button>
      {open && (
        <div className="absolute z-10 mt-1 max-h-60 overflow-auto bg-[var(--color-bg-surface)] text-[var(--color-text-primary)] border border-[var(--color-border-strong)] rounded shadow-lg">
          <div className="p-1.5 border-b border-[var(--color-border-default)]">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onClick={(e) => e.stopPropagation()}
              placeholder="Rechercher..."
              className="w-full px-2 py-1 text-sm bg-[var(--color-bg-input)] border border-[var(--color-border-default)] rounded-md text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)]"
            />
          </div>
          {filteredOptions.map((opt) => (
            <label key={opt} className="flex items-center space-x-2 px-2 py-1 hover:bg-[var(--color-bg-elevated)]">
              <input
                type="checkbox"
                checked={selected.includes(opt)}
                onChange={(e) => toggleOption(opt, e.target.checked)}
                className="rounded"
              />
              <span>{opt}</span>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}

export default MultiSelectFilter;
